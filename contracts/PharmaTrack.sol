// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// PharmaTrack — реестр лекарственных препаратов.
/// Логика портирована из off-chain симуляции (src/blockchain/ledger.py).
contract PharmaTrack {
    enum Stage { Manufacturer, Distributor, Pharmacy, Sold }

    enum TxType {
        Register,
        Temperature,
        TransferToDistributor,
        TransferToPharmacy,
        Sale,
        Block
    }

    struct Drug {
        string gtin;
        string serial;
        string productName;
        string batchNumber;
        uint64 manufactureDate;     // unix
        uint64 expiryDate;          // unix
        int16  minTemp;             // десятые °C, например 25 = 2.5°C
        int16  maxTemp;
        string regCert;
        string mfrLicense;

        address currentOwner;
        Stage  stage;
        bool   blocked;
        string blockReason;
        uint16 breachCount;

        bool   exists;
    }

    struct TempRecord {
        int16  temperature; // десятые °C
        string location;
        uint64 timestamp;
        bool   isBreach;
    }

    struct TxRecord {
        TxType  txType;
        address from;
        address to;
        uint64  timestamp;
        bytes32 dataHash; // хэш доп. данных, чтоб не раздувать storage
    }

    // --- Роли ---
    bytes32 public constant ROLE_MANUFACTURER = keccak256("MANUFACTURER");
    bytes32 public constant ROLE_LOGISTICS    = keccak256("LOGISTICS");
    bytes32 public constant ROLE_DISTRIBUTOR  = keccak256("DISTRIBUTOR");
    bytes32 public constant ROLE_PHARMACY     = keccak256("PHARMACY");
    bytes32 public constant ROLE_REGULATOR    = keccak256("REGULATOR");

    address public admin;
    mapping(bytes32 => mapping(address => bool)) public hasRole;

    // serial => Drug
    mapping(string => Drug) private drugs;
    mapping(string => TempRecord[]) private tempLog;
    mapping(string => TxRecord[])   private txLog;

    string[] private serials; // для перебора

    // batch => list of serials, для поиска по партии
    mapping(string => string[]) private byBatch;

    uint16 public constant BREACH_THRESHOLD = 3;

    // --- События ---
    event DrugRegistered(string indexed serial, string productName, address indexed manufacturer);
    event TemperatureRecorded(string indexed serial, int16 temperature, string location, bool isBreach);
    event Transferred(string indexed serial, Stage to, address indexed by);
    event Sold(string indexed serial, address indexed pharmacy);
    event Blocked(string indexed serial, string reason, address indexed by);
    event RoleGranted(bytes32 indexed role, address indexed account);

    // --- Модификаторы ---
    modifier onlyAdmin() {
        require(msg.sender == admin, "not admin");
        _;
    }

    modifier only(bytes32 role) {
        require(hasRole[role][msg.sender], "forbidden");
        _;
    }

    constructor() {
        admin = msg.sender;
        // админ изначально может всё, удобно для локального демо
        hasRole[ROLE_MANUFACTURER][msg.sender] = true;
        hasRole[ROLE_LOGISTICS][msg.sender]    = true;
        hasRole[ROLE_DISTRIBUTOR][msg.sender]  = true;
        hasRole[ROLE_PHARMACY][msg.sender]     = true;
        hasRole[ROLE_REGULATOR][msg.sender]    = true;
    }

    function grantRole(bytes32 role, address account) external onlyAdmin {
        hasRole[role][account] = true;
        emit RoleGranted(role, account);
    }

    // --- Регистрация ---

    function registerDrug(
        string calldata gtin,
        string calldata serial,
        string calldata productName,
        string calldata batchNumber,
        uint64 manufactureDate,
        uint64 expiryDate,
        int16  minTemp,
        int16  maxTemp,
        string calldata regCert,
        string calldata mfrLicense
    ) external only(ROLE_MANUFACTURER) {
        require(!drugs[serial].exists, "serial taken");
        require(expiryDate > manufactureDate, "bad dates");
        require(maxTemp >= minTemp, "bad temp range");

        Drug storage d = drugs[serial];
        d.gtin = gtin;
        d.serial = serial;
        d.productName = productName;
        d.batchNumber = batchNumber;
        d.manufactureDate = manufactureDate;
        d.expiryDate = expiryDate;
        d.minTemp = minTemp;
        d.maxTemp = maxTemp;
        d.regCert = regCert;
        d.mfrLicense = mfrLicense;
        d.currentOwner = msg.sender;
        d.stage = Stage.Manufacturer;
        d.exists = true;

        serials.push(serial);
        byBatch[batchNumber].push(serial);

        _logTx(serial, TxType.Register, msg.sender, address(0), keccak256(abi.encode(gtin, batchNumber)));
        emit DrugRegistered(serial, productName, msg.sender);
    }

    // --- Температура ---

    function recordTemperature(
        string calldata serial,
        int16 temperature,
        string calldata location
    ) external only(ROLE_LOGISTICS) returns (bool isBreach) {
        Drug storage d = drugs[serial];
        require(d.exists, "not found");
        require(!d.blocked, "blocked");

        isBreach = temperature < d.minTemp || temperature > d.maxTemp;

        tempLog[serial].push(TempRecord({
            temperature: temperature,
            location: location,
            timestamp: uint64(block.timestamp),
            isBreach: isBreach
        }));

        if (isBreach) {
            d.breachCount += 1;
            if (d.breachCount >= BREACH_THRESHOLD && !d.blocked) {
                d.blocked = true;
                d.blockReason = "temperature breach threshold";
                emit Blocked(serial, d.blockReason, msg.sender);
            }
        }

        _logTx(serial, TxType.Temperature, msg.sender, address(0), keccak256(abi.encode(temperature, location, isBreach)));
        emit TemperatureRecorded(serial, temperature, location, isBreach);
    }

    // --- Передача ---

    function transferToDistributor(string calldata serial, string calldata licenseNumber)
        external only(ROLE_MANUFACTURER)
    {
        Drug storage d = drugs[serial];
        require(d.exists, "not found");
        require(!d.blocked, "blocked");
        require(d.expiryDate > block.timestamp, "expired");
        require(d.stage == Stage.Manufacturer, "wrong stage");

        d.stage = Stage.Distributor;
        d.currentOwner = msg.sender; // в реальном кейсе сюда писали бы адрес дистрибьютора
        _logTx(serial, TxType.TransferToDistributor, msg.sender, address(0), keccak256(bytes(licenseNumber)));
        emit Transferred(serial, Stage.Distributor, msg.sender);
    }

    function transferToPharmacy(string calldata serial, string calldata licenseNumber)
        external only(ROLE_DISTRIBUTOR)
    {
        Drug storage d = drugs[serial];
        require(d.exists, "not found");
        require(!d.blocked, "blocked");
        require(d.breachCount == 0, "cold chain breached");
        require(d.stage == Stage.Distributor, "wrong stage");

        d.stage = Stage.Pharmacy;
        d.currentOwner = msg.sender;
        _logTx(serial, TxType.TransferToPharmacy, msg.sender, address(0), keccak256(bytes(licenseNumber)));
        emit Transferred(serial, Stage.Pharmacy, msg.sender);
    }

    function sellToPatient(string calldata serial) external only(ROLE_PHARMACY) {
        Drug storage d = drugs[serial];
        require(d.exists, "not found");
        require(!d.blocked, "blocked");
        require(d.stage == Stage.Pharmacy, "wrong stage");

        d.stage = Stage.Sold;
        _logTx(serial, TxType.Sale, msg.sender, address(0), bytes32(0));
        emit Sold(serial, msg.sender);
    }

    function blockDrug(string calldata serial, string calldata reason) external only(ROLE_REGULATOR) {
        Drug storage d = drugs[serial];
        require(d.exists, "not found");
        require(!d.blocked, "already blocked");

        d.blocked = true;
        d.blockReason = reason;
        _logTx(serial, TxType.Block, msg.sender, address(0), keccak256(bytes(reason)));
        emit Blocked(serial, reason, msg.sender);
    }

    // --- Чтение ---

    /// Проверка подлинности. Возвращает (валиден, статус-строка).
    function verifyDrug(string calldata serial) external view returns (bool valid, string memory status, string memory productName) {
        Drug storage d = drugs[serial];
        if (!d.exists) return (false, "not_found", "");
        if (d.blocked) return (false, d.blockReason, d.productName);
        if (d.expiryDate <= block.timestamp) return (false, "expired", d.productName);
        return (true, "authentic", d.productName);
    }

    function getDrug(string calldata serial) external view returns (Drug memory) {
        require(drugs[serial].exists, "not found");
        return drugs[serial];
    }

    function getTemperatureLog(string calldata serial) external view returns (TempRecord[] memory) {
        return tempLog[serial];
    }

    function getTransactions(string calldata serial) external view returns (TxRecord[] memory) {
        return txLog[serial];
    }

    function getSerialsByBatch(string calldata batchNumber) external view returns (string[] memory) {
        return byBatch[batchNumber];
    }

    function totalDrugs() external view returns (uint256) {
        return serials.length;
    }

    function serialAt(uint256 index) external view returns (string memory) {
        return serials[index];
    }

    // --- Внутреннее ---

    function _logTx(string memory serial, TxType t, address from, address to, bytes32 dataHash) internal {
        txLog[serial].push(TxRecord({
            txType: t,
            from: from,
            to: to,
            timestamp: uint64(block.timestamp),
            dataHash: dataHash
        }));
    }
}
