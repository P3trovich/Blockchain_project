"""
Модели данных блокчейна: препараты и транзакции
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional

from . import crypto


class TransactionType(StrEnum):
    """Типы транзакций в системе"""

    REGISTER = "REGISTER"  # Регистрация препарата
    TEMPERATURE = "TEMPERATURE"  # Запись температуры
    TRANSFER_TO_DISTRIBUTOR = "TRANSFER_TO_DISTRIBUTOR"
    TRANSFER_TO_PHARMACY = "TRANSFER_TO_PHARMACY"
    SALE = "SALE"  # Продажа пациенту
    BLOCK = "BLOCK"  # Блокировка препарата


class Transaction:
    """
    Транзакция — неделимая операция в блокчейне.
    Каждая транзакция подписывается отправителем.
    """

    def __init__(
        self,
        tx_type: TransactionType,
        serial_number: str,
        from_org: str,
        to_org: Optional[str],
        data: Dict[str, Any],
        private_key: str = "default_key",
    ):
        self.tx_id = crypto.calculate_hash(
            {
                "type": tx_type,
                "serial": serial_number,
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }
        )
        self.type = tx_type
        self.serial_number = serial_number
        self.from_org = from_org
        self.to_org = to_org
        self.timestamp = datetime.now()
        self.data = data
        self.tx_type = tx_type

        # Создаём хэш транзакции
        tx_data_for_hash = {
            "type": self.tx_type.value,
            "serial": self.serial_number,
            "from": self.from_org,
            "to": self.to_org,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

        # Создание подписи
        self.signature = crypto.calculate_hash(
            {**tx_data_for_hash, "private_key": private_key}
        )

    def to_dict(self) -> Dict:
        return {
            "tx_id": self.tx_id,
            "type": self.type.value,
            "serialNumber": self.serial_number,
            "fromOrg": self.from_org,
            "toOrg": self.to_org,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "signature": self.signature,
        }


class DrugPackage:
    """
    Модель препарата — основная сущность системы.
    Хранит всю информацию о лекарстве и его текущем состоянии.
    """

    def __init__(
        self,
        gtin: str,
        serial_number: str,
        product_name: str,
        batch_number: str,
        manufacturing_date: str,
        expiry_date: datetime,
        min_temp: float,
        max_temp: float,
        registration_certificate: str,
        manufacturer_license: str,
    ):
        self.gtin = gtin
        self.serial_number = serial_number
        self.product_name = product_name
        self.batch_number = batch_number
        self.manufacturing_date = manufacturing_date
        self.expiry_date = expiry_date
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.registration_certificate = registration_certificate
        self.manufacturer_license = manufacturer_license

        # Состояние
        self.current_owner = "ManufacturerMSP"
        self.current_stage = "manufacturer"
        self.is_blocked = False
        self.block_reason = ""
        self.temp_breach_count = 0

        # История (заполняется транзакциями)
        self.transactions: List[Transaction] = []
        self.temperature_log: List[Dict] = []

    def to_dict(self) -> Dict:
        """Преобразование в словарь для JSON"""
        return {
            "gtin": self.gtin,
            "serialNumber": self.serial_number,
            "productName": self.product_name,
            "batchNumber": self.batch_number,
            "manufacturingDate": self.manufacturing_date,
            "expiryDate": self.expiry_date,
            "minTemp": self.min_temp,
            "maxTemp": self.max_temp,
            "registrationCertificate": self.registration_certificate,
            "manufacturerLicense": self.manufacturer_license,
            "currentOwner": self.current_owner,
            "currentStage": self.current_stage,
            "isBlocked": self.is_blocked,
            "blockReason": self.block_reason,
            "tempBreachCount": self.temp_breach_count,
            "temperatureLog": self.temperature_log,
            "transactionCount": len(self.transactions),
        }

    def is_expired(self) -> bool:
        """Проверка срока годности"""
        return datetime.now() > self.expiry_date

    def add_transaction(self, tx: Transaction):
        """Добавление транзакции в историю препарата"""
        self.transactions.append(tx)

    def add_temperature_record(
        self, temperature: float, location: str, is_breach: bool
    ):
        """Добавление записи температуры"""

        self.temperature_log.append(
            {
                "temperature": temperature,
                "location": location,
                "timestamp": datetime.now().isoformat(),
                "isBreach": is_breach,
            }
        )

        if is_breach:
            self.temp_breach_count += 1
            if self.temp_breach_count >= 3:
                self.is_blocked = True
                self.block_reason = f"Temperature breach {self.temp_breach_count} times"
