#!/usr/bin/env python3
"""
IoT Temperature Simulator — симуляция датчиков температуры
Поддерживает запуск в Docker и локально
"""

import os
import random
import time

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Тестовые серийные номера
TEST_SERIALS = ["SN-IOT-DOCKER-001", "SN-IOT-DOCKER-002"]

LOCATIONS = [
    "Docker Container - Warehouse A",
    "Docker Container - Truck #123",
    "Docker Container - Distribution Center",
]


def register_test_drugs():
    """Регистрация тестовых препаратов"""
    print("📝 Registering test drugs...")

    test_drugs = [
        {
            "gtin": "4601000000101",
            "serialNumber": "SN-IOT-DOCKER-001",
            "productName": "Docker Vaccine Test",
            "batchNumber": "DOCKER-VACC-01",
            "manufacturingDate": "2025-01-01",
            "expiryDate": "2026-01-01",
            "minTemp": 2.0,
            "maxTemp": 8.0,
            "registrationCertificate": "REG-DOCKER-001",
            "manufacturerLicense": "LIC-DOCKER-001",
        },
        {
            "gtin": "4601000000102",
            "serialNumber": "SN-IOT-DOCKER-002",
            "productName": "Docker Insulin Test",
            "batchNumber": "DOCKER-INS-01",
            "manufacturingDate": "2025-01-15",
            "expiryDate": "2026-01-15",
            "minTemp": 2.0,
            "maxTemp": 8.0,
            "registrationCertificate": "REG-DOCKER-002",
            "manufacturerLicense": "LIC-DOCKER-001",
        },
    ]

    for drug in test_drugs:
        try:
            response = requests.post(
                f"{API_URL}/api/drugs/register", json=drug, timeout=5
            )
            if response.status_code == 200:
                print(f"   ✅ Registered {drug['serialNumber']}")
            else:
                print(f"   ⚠️ Failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def simulate_temperature_logging(
    serial_number: str, duration_seconds: int = 30, interval: int = 3
):
    """Симуляция логирования температуры"""
    print(f"\n🌡️ Simulating for {serial_number}")

    start_time = time.time()
    reading_count = 0

    while time.time() - start_time < duration_seconds:
        if random.random() < 0.15:
            temp = random.uniform(-2.0, 1.9) or random.uniform(8.1, 15.0)
            breach = "⚠️ BREACH"
        else:
            temp = random.uniform(2.0, 8.0)
            breach = "✓"

        location = random.choice(LOCATIONS)

        try:
            response = requests.post(
                f"{API_URL}/api/drugs/temperature",
                json={
                    "serialNumber": serial_number,
                    "temperature": round(temp, 1),
                    "location": location,
                },
                timeout=5,
            )
            reading_count += 1

            if response.status_code == 200:
                data = response.json()
                print(f"   [{reading_count:2d}] {temp:4.1f}°C - {breach}")
                if "BLOCKED" in data.get("message", ""):
                    print("   🛑 Drug BLOCKED!")
                    break
        except Exception as e:
            print(f"   ❌ Error: {e}")

        time.sleep(interval)

    print(f"   Finished: {reading_count} readings")


def run_simulation():
    print("=" * 60)
    print("PharmaTrack IoT Simulator (Docker)")
    print(f"API URL: {API_URL}")
    print("=" * 60)

    # Проверка API
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ API not responding")
            return
        print("✅ API available")
    except Exception as e:
        print(f"❌ Cannot connect: {e}")
        return

    register_test_drugs()

    for serial in TEST_SERIALS:
        simulate_temperature_logging(serial)
        time.sleep(2)

    print("\n✅ Simulation completed!")


if __name__ == "__main__":
    run_simulation()
