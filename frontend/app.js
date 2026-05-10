import { BrowserProvider, Contract, JsonRpcProvider } from "https://cdn.jsdelivr.net/npm/ethers@6.13.4/+esm";

// контракт и ABI пишутся скриптом scripts/deploy.js в файл contract.json
const meta = await fetch("./contract.json").then(r => r.json()).catch(() => null);
if (!meta) {
  document.body.innerHTML = "<p style='padding:24px'>Сначала задеплойте контракт: <code>npm run deploy:local</code></p>";
  throw new Error("no contract.json");
}
document.getElementById("contractAddr").textContent = meta.address;

// read-only контракт работает без кошелька (для verifyDrug, getDrug и т.п.)
const readProvider = new JsonRpcProvider("http://127.0.0.1:8545");
const readContract = new Contract(meta.address, meta.abi, readProvider);

let signer = null;
let writeContract = null;

const $ = (id) => document.getElementById(id);
const show = (id, data) => { $(id).textContent = typeof data === "string" ? data : JSON.stringify(data, replacer, 2); };

// ethers возвращает BigInt'ы — JSON.stringify их не умеет
function replacer(_, v) { return typeof v === "bigint" ? v.toString() : v; }

$("connect").addEventListener("click", async () => {
  if (!window.ethereum) {
    alert("MetaMask не найден. Поставьте расширение или используйте hardhat-аккаунт через приватный ключ.");
    return;
  }
  const provider = new BrowserProvider(window.ethereum);
  await provider.send("eth_requestAccounts", []);
  signer = await provider.getSigner();
  writeContract = new Contract(meta.address, meta.abi, signer);
  $("account").textContent = await signer.getAddress();
});

function requireSigner() {
  if (!writeContract) throw new Error("сначала подключите кошелёк");
  return writeContract;
}

// --- Verify ---
$("verifyBtn").addEventListener("click", async () => {
  try {
    const serial = $("verifySerial").value.trim();
    const [valid, status, name] = await readContract.verifyDrug(serial);
    show("verifyOut", { serial, valid, status, productName: name });
  } catch (e) { show("verifyOut", String(e.message || e)); }
});

// --- Register ---
$("registerBtn").addEventListener("click", async () => {
  try {
    const c = requireSigner();
    const now = Math.floor(Date.now() / 1000);
    const year = 60 * 60 * 24 * 365;
    const tx = await c.registerDrug(
      $("regGtin").value, $("regSerial").value, $("regName").value, $("regBatch").value,
      now - 3600, now + year,
      Number($("regMin").value), Number($("regMax").value),
      $("regCert").value, $("regLic").value
    );
    show("registerOut", "ждём подтверждения... tx: " + tx.hash);
    const r = await tx.wait();
    show("registerOut", { ok: true, gasUsed: r.gasUsed.toString(), block: r.blockNumber });
  } catch (e) { show("registerOut", String(e.shortMessage || e.message || e)); }
});

// --- Temperature ---
$("tempBtn").addEventListener("click", async () => {
  try {
    const c = requireSigner();
    const tx = await c.recordTemperature($("tempSerial").value, Number($("tempValue").value), $("tempLoc").value);
    const r = await tx.wait();
    // парсим event TemperatureRecorded
    const ev = r.logs
      .map(l => { try { return readContract.interface.parseLog(l); } catch { return null; } })
      .find(l => l && l.name === "TemperatureRecorded");
    show("tempOut", {
      tx: tx.hash,
      isBreach: ev ? ev.args.isBreach : null,
      gasUsed: r.gasUsed.toString(),
    });
  } catch (e) { show("tempOut", String(e.shortMessage || e.message || e)); }
});

// --- History ---
$("histBtn").addEventListener("click", async () => {
  try {
    const serial = $("histSerial").value.trim();
    const [drug, temps, txs] = await Promise.all([
      readContract.getDrug(serial),
      readContract.getTemperatureLog(serial),
      readContract.getTransactions(serial),
    ]);
    show("histOut", {
      productName: drug.productName,
      stage: ["Manufacturer", "Distributor", "Pharmacy", "Sold"][Number(drug.stage)],
      blocked: drug.blocked,
      blockReason: drug.blockReason,
      breachCount: Number(drug.breachCount),
      tempLog: temps.map(t => ({
        t: Number(t.temperature) / 10 + "°C",
        loc: t.location,
        breach: t.isBreach,
        at: new Date(Number(t.timestamp) * 1000).toISOString(),
      })),
      transactions: txs.map(x => ({
        type: ["Register", "Temperature", "ToDistributor", "ToPharmacy", "Sale", "Block"][Number(x.txType)],
        from: x.from,
        at: new Date(Number(x.timestamp) * 1000).toISOString(),
      })),
    });
  } catch (e) { show("histOut", String(e.shortMessage || e.message || e)); }
});

// --- Move / sell / block ---
document.querySelectorAll("[data-action]").forEach(btn => {
  btn.addEventListener("click", async () => {
    try {
      const c = requireSigner();
      const serial = $("moveSerial").value.trim();
      const lic = $("moveLicense").value.trim();
      const action = btn.dataset.action;
      let tx;
      if (action === "toDistributor") tx = await c.transferToDistributor(serial, lic);
      else if (action === "toPharmacy") tx = await c.transferToPharmacy(serial, lic);
      else if (action === "sell") tx = await c.sellToPatient(serial);
      else if (action === "block") {
        const reason = prompt("причина блокировки?", "контрафакт") || "контрафакт";
        tx = await c.blockDrug(serial, reason);
      }
      const r = await tx.wait();
      show("moveOut", { action, tx: tx.hash, block: r.blockNumber });
    } catch (e) { show("moveOut", String(e.shortMessage || e.message || e)); }
  });
});
