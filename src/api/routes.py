"""
API маршруты (endpoints)
"""

from typing import List

from fastapi import APIRouter, HTTPException

from blockchain.ledger import ledger
from blockchain.models import DrugPackage

from .schemas import (
    BlockRequest,
    DrugInfoResponse,
    RegisterDrugRequest,
    SaleRequest,
    StatisticsResponse,
    TemperatureRecord,
    TemperatureRecordRequest,
    TransactionResponse,
    TransferRequest,
    VerifyResponse,
)

router = APIRouter(prefix="/api", tags=["PharmaTrack"])


# ============ Основные операции ============


@router.post("/drugs/register", summary="Register new drug")
async def register_drug(request: RegisterDrugRequest):
    """
    Регистрация нового препарата (только производитель)
    """
    # Создание препарата
    drug = DrugPackage(
        gtin=request.gtin,
        serial_number=request.serialNumber,
        product_name=request.productName,
        batch_number=request.batchNumber,
        manufacturing_date=request.manufacturingDate,
        expiry_date=request.expiryDate,
        min_temp=request.minTemp,
        max_temp=request.maxTemp,
        registration_certificate=request.registrationCertificate,
        manufacturer_license=request.manufacturerLicense,
    )

    # Регистрация в блокчейне
    success, message = ledger.register_drug(drug)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "serialNumber": request.serialNumber,
    }


@router.post("/drugs/temperature", summary="Record temperature (IoT)")
async def record_temperature(request: TemperatureRecordRequest):
    """
    Запись температуры от IoT датчика (логистическая компания)
    """
    success, message, is_breach = ledger.record_temperature(
        serial_number=request.serialNumber,
        temperature=request.temperature,
        location=request.location,
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "isBreach": is_breach,
        "serialNumber": request.serialNumber,
    }


@router.post("/drugs/transfer-to-distributor", summary="Transfer to distributor")
async def transfer_to_distributor(request: TransferRequest):
    """
    Передача препарата дистрибьютору (производитель или логист)
    """
    success, message = ledger.transfer_to_distributor(
        serial_number=request.serialNumber, distributor_license=request.licenseNumber
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "serialNumber": request.serialNumber,
    }


@router.post("/drugs/transfer-to-pharmacy", summary="Transfer to pharmacy")
async def transfer_to_pharmacy(request: TransferRequest):
    """
    Передача препарата в аптеку (дистрибьютор)
    """
    success, message = ledger.transfer_to_pharmacy(
        serial_number=request.serialNumber, pharmacy_license=request.licenseNumber
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "serialNumber": request.serialNumber,
    }


@router.post("/drugs/sell", summary="Sell to patient")
async def sell_to_patient(request: SaleRequest):
    """
    Продажа препарата пациенту (аптека)
    """
    success, message = ledger.sell_to_patient(request.serialNumber)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "serialNumber": request.serialNumber,
    }


@router.post("/drugs/block", summary="Block drug")
async def block_drug(request: BlockRequest):
    """
    Блокировка препарата (регулятор)
    """
    success, message = ledger.block_drug(
        serial_number=request.serialNumber, reason=request.reason
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": success,
        "message": message,
        "serialNumber": request.serialNumber,
    }


# ============ Публичные запросы (read-only) ============


@router.get("/drugs/verify/{serial_number}", response_model=VerifyResponse)
async def verify_drug(serial_number: str):
    """
    Проверка подлинности препарата (публичный endpoint)
    """
    is_valid, status, product_name = ledger.verify_drug(serial_number)

    return VerifyResponse(
        serialNumber=serial_number,
        isValid=is_valid,
        status=status,
        productName=product_name if product_name else None,
    )


@router.get("/drugs/{serial_number}", response_model=DrugInfoResponse)
async def get_drug_info(serial_number: str):
    """
    Получение полной информации о препарате
    """
    drug_info = ledger.get_drug_info(serial_number)

    if not drug_info:
        raise HTTPException(status_code=404, detail="Drug not found")

    return DrugInfoResponse(**drug_info)


@router.get(
    "/drugs/{serial_number}/temperature", response_model=List[TemperatureRecord]
)
async def get_temperature_history(serial_number: str):
    """
    Получение истории температуры препарата
    """
    history = ledger.get_temperature_history(serial_number)
    return [TemperatureRecord(**record) for record in history]


@router.get(
    "/drugs/{serial_number}/transactions", response_model=List[TransactionResponse]
)
async def get_transactions(serial_number: str):
    """
    Получение всех транзакций препарата
    """
    transactions = ledger.get_transactions(serial_number)
    return [TransactionResponse(**tx) for tx in transactions]


@router.get("/drugs/batch/{batch_number}", summary="Search by batch")
async def search_by_batch(batch_number: str):
    """
    Поиск всех препаратов по номеру партии
    """
    results = ledger.search_by_batch(batch_number)
    return {"batchNumber": batch_number, "count": len(results), "drugs": results}


@router.get("/drugs", summary="List all drugs")
async def list_all_drugs():
    """
    Получение списка всех препаратов
    """
    return {"count": len(ledger.get_all_drugs()), "drugs": ledger.get_all_drugs()}


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """
    Получение статистики системы
    """
    stats = ledger.get_statistics()
    return StatisticsResponse(**stats)
