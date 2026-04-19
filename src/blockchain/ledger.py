"""
Блокчейн-реестр — основное хранилище системы.
Симулирует распределённый реестр с неизменяемыми записями.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .crypto import CryptoUtils
from .models import DrugPackage, Transaction, TransactionType


class BlockchainLedger:
    """
    Основной реестр блокчейн-системы.
    Хранит все препараты и обеспечивает неизменяемость записей.
    """

    def __init__(self):
        # Основное хранилище: серийный номер → препарат
        self._drugs: Dict[str, DrugPackage] = {}

        # Глобальная история всех транзакций (неизменяемый лог)
        self._global_history: List[dict] = []

        # Хэш последнего состояния (симуляция корня Merkle)
        self._state_hash = "0" * 64

    def _update_state_hash(self):
        """Обновление хэша состояния (симуляция)"""
        combined = "".join([d.serial_number for d in self._drugs.values()])
        self._state_hash = CryptoUtils.calculate_hash(
            {"drugs": combined, "time": datetime.now().isoformat()}
        )

    def register_drug(
        self, drug: DrugPackage, private_key: str = "default"
    ) -> Tuple[bool, str]:
        """
        Регистрация нового препарата
        Возвращает (успех, сообщение)
        """
        # Проверка уникальности серийного номера
        if drug.serial_number in self._drugs:
            return False, f"Drug with serial number {drug.serial_number} already exists"

        # Создание транзакции регистрации
        tx = Transaction(
            tx_type=TransactionType.REGISTER,
            serial_number=drug.serial_number,
            from_org="ManufacturerMSP",
            to_org=None,
            data=drug.to_dict(),
            private_key=private_key,
        )

        # Добавление в реестр
        drug.add_transaction(tx)
        self._drugs[drug.serial_number] = drug
        self._global_history.append(tx.to_dict())
        self._update_state_hash()

        return True, "Drug registered successfully"

    def record_temperature(
        self,
        serial_number: str,
        temperature: float,
        location: str,
        private_key: str = "default",
    ) -> Tuple[bool, str, bool]:
        """
        Запись температуры от IoT датчика
        Возвращает (успех, сообщение, было_ли_нарушение)
        """
        if serial_number not in self._drugs:
            return False, "Drug not found", False

        drug = self._drugs[serial_number]

        if drug.is_blocked:
            return False, f"Drug is blocked: {drug.block_reason}", False

        # Проверка нарушения
        is_breach = temperature < drug.min_temp or temperature > drug.max_temp

        # Создание транзакции
        tx = Transaction(
            tx_type=TransactionType.TEMPERATURE,
            serial_number=serial_number,
            from_org="LogisticsMSP",
            to_org=None,
            data={
                "temperature": temperature,
                "location": location,
                "isBreach": is_breach,
            },
            private_key=private_key,
        )

        # Обновление данных
        drug.add_temperature_record(temperature, location, is_breach)
        drug.add_transaction(tx)
        self._global_history.append(tx.to_dict())
        self._update_state_hash()

        message = f"Temperature recorded: {temperature}°C at {location}"
        if is_breach:
            message += f" (BREACH! Count: {drug.temp_breach_count})"

        if drug.is_blocked:
            message += " Drug has been BLOCKED due to multiple breaches"

        return True, message, is_breach

    def transfer_to_distributor(
        self, serial_number: str, distributor_license: str, private_key: str = "default"
    ) -> Tuple[bool, str]:
        """Передача препарата дистрибьютору"""
        if serial_number not in self._drugs:
            return False, "Drug not found"

        drug = self._drugs[serial_number]

        if drug.is_blocked:
            return False, f"Cannot transfer: drug is blocked - {drug.block_reason}"

        if drug.is_expired():
            return False, "Cannot transfer: drug has expired"

        # Создание транзакции
        tx = Transaction(
            tx_type=TransactionType.TRANSFER_TO_DISTRIBUTOR,
            serial_number=serial_number,
            from_org=drug.current_owner,
            to_org="DistributorMSP",
            data={"licenseNumber": distributor_license},
            private_key=private_key,
        )

        # Обновление состояния
        drug.current_owner = "DistributorMSP"
        drug.current_stage = "distributor"
        drug.add_transaction(tx)
        self._global_history.append(tx.to_dict())
        self._update_state_hash()

        return True, f"Drug transferred to distributor (license: {distributor_license})"

    def transfer_to_pharmacy(
        self, serial_number: str, pharmacy_license: str, private_key: str = "default"
    ) -> Tuple[bool, str]:
        """Передача препарата в аптеку"""
        if serial_number not in self._drugs:
            return False, "Drug not found"

        drug = self._drugs[serial_number]

        if drug.is_blocked:
            return False, f"Cannot transfer: drug is blocked - {drug.block_reason}"

        if drug.temp_breach_count > 0:
            return (
                False,
                f"Cannot transfer: temperature chain breached {drug.temp_breach_count} times",
            )

        if drug.current_stage != "distributor":
            return False, f"Drug is at {drug.current_stage}, must be at distributor"

        # Создание транзакции
        tx = Transaction(
            tx_type=TransactionType.TRANSFER_TO_PHARMACY,
            serial_number=serial_number,
            from_org=drug.current_owner,
            to_org="PharmacyMSP",
            data={"licenseNumber": pharmacy_license},
            private_key=private_key,
        )

        # Обновление состояния
        drug.current_owner = "PharmacyMSP"
        drug.current_stage = "pharmacy"
        drug.add_transaction(tx)
        self._global_history.append(tx.to_dict())
        self._update_state_hash()

        return True, f"Drug transferred to pharmacy (license: {pharmacy_license})"

    def sell_to_patient(
        self, serial_number: str, private_key: str = "default"
    ) -> Tuple[bool, str]:
        """Продажа препарата пациенту"""
        if serial_number not in self._drugs:
            return False, "Drug not found"

        drug = self._drugs[serial_number]

        if drug.current_stage != "pharmacy":
            return False, f"Drug is at {drug.current_stage}, must be at pharmacy"

        # Создание транзакции
        tx = Transaction(
            tx_type=TransactionType.SALE,
            serial_number=serial_number,
            from_org=drug.current_owner,
            to_org="Patient",
            data={},
            private_key=private_key,
        )

        # Обновление состояния
        drug.current_stage = "sold"
        drug.add_transaction(tx)
        self._global_history.append(tx.to_dict())
        self._update_state_hash()

        return True, "Drug sold to patient"

    def verify_drug(self, serial_number: str) -> Tuple[bool, str, str]:
        """
        Проверка подлинности препарата
        Возвращает (действителен, статус, название)
        """
        if serial_number not in self._drugs:
            return False, "not_found", ""

        drug = self._drugs[serial_number]

        if drug.is_blocked:
            return False, f"blocked: {drug.block_reason}", drug.product_name

        if drug.is_expired():
            return False, "expired", drug.product_name

        return True, "authentic", drug.product_name

    def get_drug_info(self, serial_number: str) -> Optional[dict]:
        """Получение полной информации о препарате"""
        if serial_number not in self._drugs:
            return None
        return self._drugs[serial_number].to_dict()

    def get_temperature_history(self, serial_number: str) -> List[dict]:
        """Получение истории температуры"""
        if serial_number not in self._drugs:
            return []
        return self._drugs[serial_number].temperature_log

    def get_transactions(self, serial_number: str) -> List[dict]:
        """Получение всех транзакций препарата"""
        if serial_number not in self._drugs:
            return []
        return [tx.to_dict() for tx in self._drugs[serial_number].transactions]

    def block_drug(
        self, serial_number: str, reason: str, private_key: str = "default"
    ) -> Tuple[bool, str]:
        """Блокировка препарата (регулятор)"""
        if serial_number not in self._drugs:
            return False, "Drug not found"

        drug = self._drugs[serial_number]

        if drug.is_blocked:
            return False, f"Drug already blocked: {drug.block_reason}"

        # Создание транзакции
        tx = Transaction(
            tx_type=TransactionType.BLOCK,
            serial_number=serial_number,
            from_org="RegulatorMSP",
            to_org=None,
            data={"reason": reason},
            private_key=private_key,
        )

        # Обновление состояния
        drug.is_blocked = True
        drug.block_reason = reason
        drug.add_transaction(tx)
        self._global_history.append(tx.to_dict())
        self._update_state_hash()

        return True, f"Drug blocked: {reason}"

    def get_all_drugs(self) -> List[dict]:
        """Получение всех препаратов"""
        return [drug.to_dict() for drug in self._drugs.values()]

    def search_by_batch(self, batch_number: str) -> List[dict]:
        """Поиск по номеру партии"""
        results = []
        for drug in self._drugs.values():
            if drug.batch_number == batch_number:
                results.append(drug.to_dict())
        return results

    def get_statistics(self) -> dict:
        """Получение статистики"""
        drugs_list = self.get_all_drugs()
        total = len(drugs_list)
        blocked = sum(1 for d in drugs_list if d["isBlocked"])
        sold = sum(1 for d in drugs_list if d["currentStage"] == "sold")

        return {
            "total": total,
            "blocked": blocked,
            "sold": sold,
            "in_transit": total - blocked - sold,
            "state_hash": self._state_hash,
            "total_transactions": len(self._global_history),
        }


# Глобальный экземпляр реестра
ledger = BlockchainLedger()
