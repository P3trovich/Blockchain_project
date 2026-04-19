"""
Pydantic схемы для валидации запросов и ответов API
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# ============ Request Schemas ============


class RegisterDrugRequest(BaseModel):
    """Запрос на регистрацию препарата"""

    gtin: str = Field(..., min_length=13, max_length=14, description="GTIN код")
    serialNumber: str = Field(
        ..., min_length=5, max_length=50, description="Уникальный серийный номер"
    )
    productName: str = Field(
        ..., min_length=2, max_length=200, description="Название препарата"
    )
    batchNumber: str = Field(
        ..., min_length=3, max_length=50, description="Номер партии"
    )
    manufacturingDate: str = Field(..., description="Дата производства (YYYY-MM-DD)")
    expiryDate: datetime = Field(..., description="Срок годности (YYYY-MM-DD)")
    minTemp: float = Field(..., description="Минимальная температура хранения")
    maxTemp: float = Field(..., description="Максимальная температура хранения")
    registrationCertificate: str = Field(
        ..., description="Регистрационное удостоверение"
    )
    manufacturerLicense: str = Field(..., description="Лицензия производителя")


class TemperatureRecordRequest(BaseModel):
    """Запрос на запись температуры"""

    serialNumber: str = Field(..., description="Серийный номер препарата")
    temperature: float = Field(
        ..., ge=-50, le=100, description="Температура в градусах Цельсия"
    )
    location: str = Field(
        ..., min_length=1, max_length=200, description="Место измерения"
    )


class TransferRequest(BaseModel):
    """Запрос на передачу препарата"""

    serialNumber: str = Field(..., description="Серийный номер препарата")
    licenseNumber: str = Field(..., description="Номер лицензии получателя")


class SaleRequest(BaseModel):
    """Запрос на продажу"""

    serialNumber: str = Field(..., description="Серийный номер препарата")


class BlockRequest(BaseModel):
    """Запрос на блокировку"""

    serialNumber: str = Field(..., description="Серийный номер препарата")
    reason: str = Field(
        ..., min_length=5, max_length=500, description="Причина блокировки"
    )


# ============ Response Schemas ============


class VerifyResponse(BaseModel):
    """Ответ на проверку подлинности"""

    serialNumber: str
    isValid: bool
    status: str
    productName: Optional[str] = None


class TemperatureRecord(BaseModel):
    """Запись температуры в ответе"""

    temperature: float
    location: str
    timestamp: str
    isBreach: bool


class DrugInfoResponse(BaseModel):
    """Полная информация о препарате"""

    gtin: str
    serialNumber: str
    productName: str
    batchNumber: str
    manufacturingDate: str
    expiryDate: str
    minTemp: float
    maxTemp: float
    registrationCertificate: str
    manufacturerLicense: str
    currentOwner: str
    currentStage: str
    isBlocked: bool
    blockReason: str
    tempBreachCount: int
    transactionCount: int


class TransactionResponse(BaseModel):
    """Транзакция в ответе"""

    tx_id: str
    type: str
    serialNumber: str
    fromOrg: str
    toOrg: Optional[str]
    timestamp: str
    data: dict


class StatisticsResponse(BaseModel):
    """Статистика системы"""

    total: int
    blocked: int
    sold: int
    in_transit: int
    state_hash: str
    total_transactions: int
