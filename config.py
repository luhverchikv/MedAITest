# config.py
import os
from pathlib import Path
from typing import List, Dict

# Загружаем переменные из .env файла
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv не установлен, используем os.getenv

# === Базовые настройки ===
DB_PATH = "test_database.sqlite"
INPUT_FILE = "tests_data.txt"

# === API настройки (VedAI - универсальный OpenAI-compatible) ===
VEDAI_API_KEY = os.getenv("VEDAI_API_KEY", "")
VEDAI_BASE_URL = os.getenv("VEDAI_BASE_URL", "https://vedai.by/api/v1")

# === Конфигурация моделей для тестирования ===
# ЭКОНОМНЫЕ модели (быстрые и дешёвые)
MODELS_TO_TEST: List[Dict[str, str]] = [
    {"name": "gemma-3-27b-it:free", "display_name": "Gemma 3 27B (Free) 🆓"},
    {"name": "gpt-5-nano", "display_name": "GPT-5 Nano ⚡"},
    {"name": "gemini-2.5-flash-lite", "display_name": "Gemini 2.5 Flash Lite 💎"},
    {"name": "gpt-5-mini", "display_name": "GPT-5 Mini 📱"},
    {"name": "llama-4-maverick", "display_name": "Llama 4 Maverick 🦙"},
    # Стандартные (качественнее, но дороже)
    {"name": "gemini-2.5-pro", "display_name": "Gemini 2.5 Pro ⭐"},
]

# Модель по умолчанию (бесплатная для тестов)
DEFAULT_MODEL = "gemma-3-27b-it:free"

# === Настройки тестирования ===
MAX_QUESTIONS = None  # None = все вопросы, или число (например 50)
SAVE_PROGRESS_EVERY = 10  # Сохранять прогресс каждые N вопросов
REQUEST_DELAY = 0.5  # Задержка между запросами (сек) для избежания лимитов
TEMPERATURE = 0.3  # Температура генерации
MAX_TOKENS = 100  # Максимум токенов в ответе

