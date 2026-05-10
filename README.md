# PharmaTrack

Блокчейн-реестр для отслеживания лекарственных препаратов от завода до пациента.
Учебный проект по курсу блокчейна, май 2026.

Основной слой — смарт-контракт на Solidity, развёрнутый в локальной EVM-сети
(Hardhat). Поверх него — веб-интерфейс на ethers.js и опциональный
FastAPI-шлюз для off-chain интеграций.

Подробности в:

- [docs/whitepaper.md](docs/whitepaper.md) — концепция стартапа.
- [docs/architecture.md](docs/architecture.md) — обоснование архитектуры.
- [contracts/PharmaTrack.sol](contracts/PharmaTrack.sol) — сам контракт.
- [CLAUDE.md](CLAUDE.md) — внутренние требования к проекту.

---

## Быстрый старт

Понадобится Node.js 18+ и npm.

```bash
npm install
npx hardhat compile
npx hardhat test            # должно быть 8 passing
```

Запуск локальной сети и деплой:

```bash
# терминал 1 — нода
npx hardhat node

# терминал 2 — деплой контракта в эту ноду
npm run deploy:local
```

Скрипт деплоя сам положит ABI и адрес контракта в
[frontend/contract.json](frontend/contract.json), а также раздаст роли
LOGISTICS / DISTRIBUTOR / PHARMACY / REGULATOR второму-пятому аккаунтам
из hardhat-ноды (admin = первый аккаунт, у него все роли).

Поднять фронт можно любым статическим сервером:

```bash
cd frontend
python -m http.server 5173
# открыть http://localhost:5173
```

В браузере подключиться через MetaMask к сети `localhost:8545`
(chainId 31337). Импортируйте в MetaMask приватные ключи hardhat-аккаунтов
(они печатаются при `hardhat node`), переключайтесь между ними, чтобы
прокликать всю цепочку «завод → дистрибьютор → аптека → продажа».

## Структура

```
contracts/PharmaTrack.sol   смарт-контракт — единственный источник истины
test/                       hardhat-тесты (8 штук, покрывают основные сценарии)
scripts/deploy.js           деплой + выгрузка ABI во фронт
frontend/                   index.html + app.js + style.css, ходит в контракт через ethers.js
src/                        legacy off-chain симулятор + FastAPI (опционально)
docs/                       whitepaper и обоснование архитектуры
```

## Что про off-chain (Python/FastAPI)

В `src/` лежит изначальная in-memory симуляция реестра — она была
основной до того, как мы перенесли логику в Solidity. Сейчас она играет
роль:

- API-шлюза для клиентов, которые не хотят ходить в EVM напрямую,
- IoT-симулятора (`src/scripts/iot_simulator.py`),
- референсной реализации, по которой удобно проверять контракт.

Запуск:

```bash
docker-compose up --build
# Swagger: http://localhost:8000/docs
```

В будущем Python-слой переключится с собственного `ledger` на вызовы
смарт-контракта через `web3.py`. Это запланировано, но не сделано — на
защите off-chain показываем как вспомогательный слой.

## Лицензия

MIT.
