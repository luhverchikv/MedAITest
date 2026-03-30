#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 Тестовый скрипт для проверки подключения к VedAI API
Запуск: python test_api.py
"""

import sys
import time
from datetime import datetime

# Добавляем корень проекта в путь для импорта
sys.path.insert(0, '.')

from config import VEDAI_API_KEY, VEDAI_BASE_URL, DEFAULT_MODEL
from ai_client import OpenAICompatibleClient


def print_header(text: str):
    """Красивый заголовок"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def test_connection():
    """Проверяет базовое подключение к API"""
    print_header("🔌 ПРОВЕРКА ПОДКЛЮЧЕНИЯ")
    
    print(f"📍 Base URL: {VEDAI_BASE_URL}")
    print(f"🔑 API Key: {'✓ настроен' if VEDAI_API_KEY else '✗ НЕ НАСТРОЕН!'}")
    print(f"🤖 Модель: {DEFAULT_MODEL}")
    
    if not VEDAI_API_KEY:
        print("\n❌ Ошибка: Добавьте VEDAI_API_KEY в файл .env")
        return False
    
    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=DEFAULT_MODEL
    )
    
    success, message = client.test_connection()
    
    if success:
        print(f"\n✅ {message}")
        return True
    else:
        print(f"\n❌ {message}")
        return False


def test_simple_query():
    """Отправляет простой тестовый запрос"""
    print_header("💬 ТЕСТОВЫЙ ЗАПРОС")
    
    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=DEFAULT_MODEL
    )
    
    # Простой вопрос для проверки
    test_prompt = "Какая модель искусственного интеллекта сейчас обрабатывает этот запрос? Ответь кратко, одним предложением."
    
    print(f"📤 Отправляю запрос модели '{DEFAULT_MODEL}'...")
    print(f"📝 Промт: \"{test_prompt}\"\n")
    
    start = time.time()
    
    # Используем прямой запрос к API (без парсинга медицинских ответов)
    try:
        import requests
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VEDAI_API_KEY}"
        }
        
        payload = {
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко и по делу."},
                {"role": "user", "content": test_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 150,
            "stream": False
        }
        
        response = requests.post(
            f"{VEDAI_BASE_URL.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            ai_answer = data['choices'][0]['message']['content'].strip()
            
            print(f"⏱ Время ответа: {elapsed:.2f} сек")
            print(f"\n🤖 Ответ модели:\n   «{ai_answer}»\n")
            
            # Проверка, что ответ содержит название модели или осмысленный текст
            if len(ai_answer) > 10 and not ai_answer.lower().startswith('error'):
                print("✅ Ответ получен и выглядит корректно!")
                return True
            else:
                print("⚠️ Ответ получен, но может быть неполным")
                return True
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ Таймаут запроса (>30 сек)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Не удалось подключиться к {VEDAI_BASE_URL}")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")
        return False


def test_medical_prompt():
    """Тестирует промт в медицинском стиле (как в основном проекте)"""
    print_header("🩺 ТЕСТ МЕДИЦИНСКОГО ПРОМТА")
    
    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=DEFAULT_MODEL
    )
    
    # Пример медицинского вопроса с вариантами
    question = "Какой препарат является препаратом первого выбора при лечении артериальной гипертензии?"
    options = [(1, "Ингибиторы АПФ"), (2, "Бета-блокаторы"), (3, "Диуретики"), (4, "Антагонисты кальция")]
    
    print(f"📋 Вопрос: {question}")
    print(f"🔢 Варианты: {', '.join([f'{i}. {t}' for i, t in options])}")
    print(f"🎯 Ожидаемый формат: только номер ответа (например: 1)\n")
    
    success, indices, error = client.get_answer(question, options, is_multiple=False)
    
    if success:
        print(f"✅ Ответ получен: индексы {indices}")
        if indices:
            selected = [options[i-1][1] for i in indices if 1 <= i <= len(options)]
            print(f"   Выбранные ответы: {selected}")
        return True
    else:
        print(f"❌ Ошибка: {error}")
        return False


def show_model_info():
    """Показывает информацию о текущей конфигурации"""
    print_header("⚙️ ТЕКУЩАЯ КОНФИГУРАЦИЯ")
    
    print(f"📅 Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API Endpoint: {VEDAI_BASE_URL}")
    print(f"🔑 API Key: {'настроен' if VEDAI_API_KEY else '❌ не настроен'}")
    print(f"🤖 Модель по умолчанию: {DEFAULT_MODEL}")
    
    from config import MODELS_TO_TEST
    if MODELS_TO_TEST:
        print(f"\n📚 Доступные модели для тестирования ({len(MODELS_TO_TEST)}):")
        for i, m in enumerate(MODELS_TO_TEST, 1):
            print(f"   {i}. {m.get('display_name', m['name'])} ({m['name']})")
    print()


def main():
    """Главная функция запуска всех тестов"""
    print_header("🚀 MEDAI TEST — ПРОВЕРКА API ПОДКЛЮЧЕНИЯ")
    
    # 1. Показываем конфигурацию
    show_model_info()
    
    # 2. Базовое подключение
    if not test_connection():
        print("\n💡 Подсказка: Проверьте VEDAI_API_KEY в файле .env")
        return
    
    # 3. Простой запрос
    if not test_simple_query():
        print("\n⚠️ Простой запрос не прошёл, но пробуем дальше...")
    
    print()  # разделитель
    
    # 4. Медицинский промт
    test_medical_prompt()
    
    # Финал
    print_header("✨ ПРОВЕРКА ЗАВЕРШЕНА")
    print("✅ Если вы видите этот текст — базовое взаимодействие с API работает!")
    print("\n📌 Далее можно запускать полноценное тестирование:")
    print("   python run_test.py --model qwen2.5-72b-instruct 5\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

