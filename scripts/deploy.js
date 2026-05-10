const { ethers, artifacts } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer, ...rest] = await ethers.getSigners();
  console.log("deploying from:", deployer.address);

  const Factory = await ethers.getContractFactory("PharmaTrack");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("PharmaTrack deployed at:", address);

  // выгружаем ABI и адрес в frontend/, чтобы UI его сразу подтянул
  const artifact = await artifacts.readArtifact("PharmaTrack");
  const out = {
    address,
    abi: artifact.abi,
    network: (await ethers.provider.getNetwork()).chainId.toString(),
  };

  const frontendDir = path.join(__dirname, "..", "frontend");
  if (!fs.existsSync(frontendDir)) fs.mkdirSync(frontendDir, { recursive: true });
  fs.writeFileSync(
    path.join(frontendDir, "contract.json"),
    JSON.stringify(out, null, 2)
  );
  console.log("ABI written to frontend/contract.json");

  // Если есть второй и третий аккаунт — выдадим им роли, чтобы из браузера
  // можно было разыграть всю цепочку с разных адресов.
  if (rest.length >= 4) {
    const [logistics, distributor, pharmacy, regulator] = rest;
    const roles = {
      LOGISTICS: logistics.address,
      DISTRIBUTOR: distributor.address,
      PHARMACY: pharmacy.address,
      REGULATOR: regulator.address,
    };
    for (const [name, addr] of Object.entries(roles)) {
      const roleHash = ethers.keccak256(ethers.toUtf8Bytes(name));
      const tx = await contract.grantRole(roleHash, addr);
      await tx.wait();
      console.log(`granted ${name} -> ${addr}`);
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
