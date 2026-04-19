FROM python:3.13-slim

WORKDIR /app

# Установка Poetry
RUN pip install --no-cache-dir poetry==2.3.2

# Копирование конфигурации Poetry
COPY pyproject.toml poetry.lock* ./

# Установка зависимостей (без dev)
RUN poetry config virtualenvs.create false && poetry install --no-root

COPY . .

# Запуск приложения
CMD ["python",  "./src/app.py"]