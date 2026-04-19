"""
Криптографические функции для блокчейна
Хэширование, симуляция цифровых подписей
"""

import hashlib
import json
from typing import Any, Dict


class CryptoUtils:
    """Утилиты для криптографии"""

    @staticmethod
    def calculate_hash(data: Dict[str, Any]) -> str:
        """
        Вычисление SHA-256 хэша от данных.
        Это аналог "цифрового отпечатка" блока или транзакции.
        """
        # Сортируем ключи для детерминированного результата
        json_string = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_string.encode()).hexdigest()

    @staticmethod
    def calculate_merkle_root(transactions: list) -> str:
        """
        Вычисление корня Merkle-дерева.
        Позволяет быстро проверить, входит ли транзакция в блок.
        """
        if not transactions:
            return hashlib.sha256(b"empty").hexdigest()

        # Простая реализация: хэшируем все транзакции вместе
        combined = "".join([tx.hash for tx in transactions])
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def sign_transaction(transaction_data: Dict, private_key: str) -> str:
        """
        Симуляция цифровой подписи транзакции.
        В реальном блокчейне здесь была бы ECDSA подпись.
        """
        # Для симуляции: подпись = хэш данных + "signed_by_" + ключ
        data_hash = CryptoUtils.calculate_hash(transaction_data)
        return hashlib.sha256(f"{data_hash}:{private_key}".encode()).hexdigest()

    @staticmethod
    def verify_signature(
        transaction_data: Dict, signature: str, public_key: str
    ) -> bool:
        """Проверка цифровой подписи"""
        expected = CryptoUtils.sign_transaction(transaction_data, public_key)
        return signature == expected
