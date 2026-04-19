"""
PharmaTrack - Блокчейн-система отслеживания лекарственных препаратов
Симуляция блокчейн-реестра с REST API на FastAPI

Запуск: uvicorn app:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

# Создание приложения
app = FastAPI(
    title="PharmaTrack API",
    description="""
    Блокчейн-система для отслеживания медицинских препаратов от завода до аптеки.
    
    ## Основные возможности:
    - Регистрация препаратов с уникальными серийными номерами
    - Мониторинг температуры (холодовая цепь)
    - Отслеживание перемещений по цепочке поставок
    - Проверка подлинности (борьба с контрафактом)
    - Автоматическая блокировка при нарушениях
    - Полная история каждого препарата
    
    ## Участники системы:
    - **Завод** - регистрация препаратов
    - **Логистика** - запись температуры
    - **Дистрибьютор** - оптовая передача
    - **Аптека** - розничная продажа
    - **Регулятор** - блокировка контрафакта
    """,
    version="1.0.0",
    contact={"name": "PharmaTrack Support", "email": "support@pharmatrack.ru"},
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение маршрутов
app.include_router(router)


@app.get("/")
async def root():
    """Корневой endpoint с информацией о сервисе"""
    return {
        "service": "PharmaTrack",
        "description": "Blockchain-based pharmaceutical tracking system",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "register": "POST /api/drugs/register",
            "temperature": "POST /api/drugs/temperature",
            "verify": "GET /api/drugs/verify/{serial_number}",
            "info": "GET /api/drugs/{serial_number}",
            "statistics": "GET /api/statistics",
        },
    }


@app.get("/health")
async def health():
    """Health check для мониторинга"""
    from blockchain.ledger import ledger

    return {
        "status": "healthy",
        "drugs_count": len(ledger.get_all_drugs()),
        "state_hash": ledger.get_statistics()["state_hash"][:16] + "...",
    }


# Для прямого запуска
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
