#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Тестовый скрипт для проверки подключения к VedAI API
Запуск: python test_api.py
"""

import sys
import time
import json
from datetime import datetime

sys.path.insert(0, '.')

from config import VEDAI_API_KEY, VEDAI_BASE_URL, DEFAULT_MODEL


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def debug_api_endpoints():
    """Проверяем доступные endpoint'ы API"""
    print_header("🔍 ДИАГНОСТИКА API ENDPOINTS")
    
    import requests
    
    base = VEDAI_BASE_URL.rstrip('/')
    endpoints_to_check = [
        "",
        "/models",
        "/chat/completions",
        "/v1/models",
        "/v1/chat/completions",
    ]
    
    headers = {"Authorization": f"Bearer {VEDAI_API_KEY}"}
    
    for endpoint in endpoints_to_check:
        url = base + endpoint
        try:
            response = requests.get(url, headers=headers, timeout=5)
            status = response.status_code
            if status == 200:
                print(f"✅ {endpoint:25} → HTTP {status}")
                # Показываем часть ответа
                try:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        print(f"      Доступно моделей: {len(data['data'])}")
                        if endpoint.endswith('models'):
                            first_model = data['data'][0].get('id', 'unknown')
                            print(f"      Пример: {first_model}")
                except:
                    pass
            elif status == 404:
                print(f"❌ {endpoint:25} → HTTP {status} (не найден)")
            elif status == 401:
                print(f"🔐 {endpoint:25} → HTTP {status} (неверный ключ)")
            else:
                print(f"⚠️  {endpoint:25} → HTTP {status}")
        except Exception as e:
            print(f"❌ {endpoint:25} → Ошибка: {e}")


def test_model_direct(model_name: str):
    """Прямой тест конкретной модели"""
    print_header(f"🧪 ТЕСТ МОДЕЛИ: {model_name}")
    
    import requests
    
    base = VEDAI_BASE_URL.rstrip('/')
    # Пробуем несколько вариантов endpoint
    possible_endpoints = [
        f"{base}/chat/completions",
        f"{base}/v1/chat/completions",
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {VEDAI_API_KEY}"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Привет! Какая ты модель? Ответь кратко."}
        ],
        "max_tokens": 50,
        "temperature": 0.3
    }
    
    for endpoint in possible_endpoints:
        print(f"\n📡 Пробую endpoint: {endpoint}")
        try:
            start = time.time()
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ УСПЕХ! HTTP 200 за {elapsed:.2f}с")
                
                # Парсим ответ
                if 'choices' in data and len(data['choices']) > 0:
                    answer = data['choices'][0]['message']['content']
                    print(f"\n🤖 Ответ модели:\n   \"{answer.strip()}\"\n")
                    
                    # Показываем полную информацию
                    print("📊 Полный ответ API:")
                    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
                    return True
                    
            elif response.status_code == 404:
                print(f"❌ HTTP 404 - Модель или endpoint не найден")
                print(f"   Ответ сервера: {response.text[:200]}")
                
            elif response.status_code == 401:
                print(f"🔐 HTTP 401 - Неверный API ключ")
                return False
                
            elif response.status_code == 429:
                print(f"⏳ HTTP 429 - Превышен лимит запросов")
                
            else:
                print(f"⚠️  HTTP {response.status_code}")
                print(f"   Ответ: {response.text[:300]}")
                
        except requests.exceptions.Timeout:
            print(f"⏱ Таймаут (>30 сек)")
        except Exception as e:
            print(f"❌ Ошибка: {type(e).__name__}: {e}")
    
    return False


def list_available_models():
    """Получаем список доступных моделей от API"""
    print_header("📚 ДОСТУПНЫЕ МОДЕЛИ ОТ API")
    
    import requests
    
    base = VEDAI_BASE_URL.rstrip('/')
    endpoints = [f"{base}/models", f"{base}/v1/models"]
    
    headers = {"Authorization": f"Bearer {VEDAI_API_KEY}"}
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    models = data['data']
                    print(f"✅ Найдено моделей: {len(models)}\n")
                    
                    # Группируем по категориям
                    for model in models[:20]:  # Показываем первые 20
                        model_id = model.get('id', 'unknown')
                        print(f"  • {model_id}")
                    
                    if len(models) > 20:
                        print(f"  ... и ещё {len(models) - 20}")
                    return True
        except:
            continue
    
    print("❌ Не удалось получить список моделей")
    return False


def main():
    print_header("🚀 VEDAI API — ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ")
    
    print(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API: {VEDAI_BASE_URL}")
    print(f"🔑 Ключ: {'настроен' if VEDAI_API_KEY else '❌ НЕ настроен!'}")
    print(f"🤖 Модель: {DEFAULT_MODEL}")
    
    if not VEDAI_API_KEY:
        print("\n❌ Добавьте VEDAI_API_KEY в .env файл!")
        return
    
    # 1. Проверяем endpoints
    debug_api_endpoints()
    
    # 2. Получаем список моделей
    list_available_models()
    
    # 3. Тестируем конкретную модель
    test_model_direct(DEFAULT_MODEL)
    
    print_header("✨ ГОТОВО")
    print("💡 Попробуйте другие модели из списка выше:")
    print("   python -c \"from test_api import test_model_direct; test_model_direct('gemini-2.5-flash-lite')\"")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹ Прервано")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

