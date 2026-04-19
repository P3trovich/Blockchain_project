#!/usr/bin/env python3
"""
Тестовый клиент для проверки API PharmaTrack
Поддерживает запуск в Docker и локально
"""

import os
import sys
import time

import requests

# Получение URL из переменной окружения или используется localhost
API_URL = os.environ.get("API_URL", "http://localhost:8000")


def test_health():
    print("\nTesting health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"   Cannot connect to API at {API_URL}")
        return False


def test_register_drug():
    print("\nTesting drug registration...")

    data = {
        "gtin": "4601234567890",
        "serialNumber": "SN-DOCKER-001",
        "productName": "Тестовый препарат Docker",
        "batchNumber": "DOCKER-BATCH-01",
        "manufacturingDate": "2025-01-01",
        "expiryDate": "2027-01-01",
        "minTemp": 2.0,
        "maxTemp": 8.0,
        "registrationCertificate": "REG-DOCKER-001",
        "manufacturerLicense": "LIC-DOCKER-001",
    }

    response = requests.post(f"{API_URL}/api/drugs/register", json=data)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200


def test_verify_drug(serial_number: str):
    print(f"\nVerifying drug {serial_number}...")
    response = requests.get(f"{API_URL}/api/drugs/verify/{serial_number}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200


def test_record_temperature(serial_number: str):
    print("\nRecording temperature...")
    data = {
        "serialNumber": serial_number,
        "temperature": 3.5,
        "location": "Docker Container - Cold Storage",
    }
    response = requests.post(f"{API_URL}/api/drugs/temperature", json=data)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    return response.status_code == 200


def test_get_statistics():
    print("\nGetting system statistics...")
    response = requests.get(f"{API_URL}/api/statistics")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total drugs: {data['total']}")
        print(f"   State hash: {data['state_hash'][:32]}...")
    return response.status_code == 200


def run_full_test():
    print("=" * 60)
    print("PharmaTrack - Docker Test Suite")
    print(f"API URL: {API_URL}")
    print("=" * 60)

    # Небольшая задержка для запуска API
    time.sleep(2)

    if not test_health():
        print("\nAPI is not responding!")
        print("   Make sure the container is running: docker-compose up -d")
        return False

    if not test_register_drug():
        print("\nRegistration failed")
        return False

    serial = "SN-DOCKER-001"

    test_verify_drug(serial)
    test_record_temperature(serial)
    test_get_statistics()

    print("\n" + "=" * 60)
    print("✅ Test suite completed successfully!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_full_test()
    sys.exit(0 if success else 1)
