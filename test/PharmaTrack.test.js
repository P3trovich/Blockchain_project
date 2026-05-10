const { expect } = require("chai");
const { ethers } = require("hardhat");

const ROLE = (name) => ethers.keccak256(ethers.toUtf8Bytes(name));

async function deploy() {
  const [admin, logistics, distributor, pharmacy, regulator, outsider] =
    await ethers.getSigners();
  const C = await ethers.getContractFactory("PharmaTrack");
  const c = await C.deploy();
  await c.waitForDeployment();

  // admin держит все роли по конструктору, остальным выдаём явно
  await c.grantRole(ROLE("LOGISTICS"), logistics.address);
  await c.grantRole(ROLE("DISTRIBUTOR"), distributor.address);
  await c.grantRole(ROLE("PHARMACY"), pharmacy.address);
  await c.grantRole(ROLE("REGULATOR"), regulator.address);

  return { c, admin, logistics, distributor, pharmacy, regulator, outsider };
}

const now = () => Math.floor(Date.now() / 1000);

async function register(c, admin, serial = "SN-001") {
  return c.connect(admin).registerDrug(
    "0461234567890",
    serial,
    "Парацетамол 500мг",
    "BATCH-2026-05",
    now() - 3600,
    now() + 60 * 60 * 24 * 365,
    20, // 2.0°C
    80, // 8.0°C
    "RU.RC.001",
    "MFR-LIC-42"
  );
}

describe("PharmaTrack", function () {
  it("регистрирует препарат и не даёт зарегистрировать дубль", async () => {
    const { c, admin } = await deploy();
    await register(c, admin);
    expect(await c.totalDrugs()).to.equal(1n);

    await expect(register(c, admin)).to.be.revertedWith("serial taken");
  });

  it("проверяет роли — посторонний не может регистрировать", async () => {
    const { c, outsider } = await deploy();
    await expect(register(c, outsider)).to.be.revertedWith("forbidden");
  });

  it("записывает температуру и помечает нарушения", async () => {
    const { c, admin, logistics } = await deploy();
    await register(c, admin);

    await c.connect(logistics).recordTemperature("SN-001", 50, "склад-1"); // 5.0°C — норма
    await c.connect(logistics).recordTemperature("SN-001", 120, "грузовик"); // 12.0°C — нарушение

    const log = await c.getTemperatureLog("SN-001");
    expect(log.length).to.equal(2);
    expect(log[1].isBreach).to.equal(true);
  });

  it("после трёх нарушений препарат блокируется автоматически", async () => {
    const { c, admin, logistics } = await deploy();
    await register(c, admin);

    for (let i = 0; i < 3; i++) {
      await c.connect(logistics).recordTemperature("SN-001", 200, "грузовик");
    }
    const drug = await c.getDrug("SN-001");
    expect(drug.blocked).to.equal(true);
  });

  it("полный путь: завод → дистрибьютор → аптека → продажа", async () => {
    const { c, admin, distributor, pharmacy } = await deploy();
    await register(c, admin);

    await c.connect(admin).transferToDistributor("SN-001", "DIST-LIC-1");
    await c.connect(distributor).transferToPharmacy("SN-001", "PHARM-LIC-9");
    await c.connect(pharmacy).sellToPatient("SN-001");

    const drug = await c.getDrug("SN-001");
    expect(drug.stage).to.equal(3); // Sold
  });

  it("нельзя передать в аптеку, если была нарушена холодовая цепь", async () => {
    const { c, admin, logistics, distributor } = await deploy();
    await register(c, admin);

    await c.connect(logistics).recordTemperature("SN-001", 200, "грузовик"); // 1 нарушение
    await c.connect(admin).transferToDistributor("SN-001", "DIST-1");

    await expect(
      c.connect(distributor).transferToPharmacy("SN-001", "PHARM-1")
    ).to.be.revertedWith("cold chain breached");
  });

  it("регулятор может заблокировать препарат", async () => {
    const { c, admin, regulator } = await deploy();
    await register(c, admin);

    await c.connect(regulator).blockDrug("SN-001", "подозрение на контрафакт");
    const [valid, status] = await c.verifyDrug("SN-001");
    expect(valid).to.equal(false);
    expect(status).to.equal("подозрение на контрафакт");
  });

  it("verifyDrug возвращает not_found для незнакомого серийника", async () => {
    const { c } = await deploy();
    const [valid, status] = await c.verifyDrug("NOPE");
    expect(valid).to.equal(false);
    expect(status).to.equal("not_found");
  });
});
