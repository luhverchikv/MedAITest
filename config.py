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
# Список моделей для сравнения (можно добавлять любые из каталога vedai.by)
MODELS_TO_TEST: List[Dict[str, str]] = [
    {"name": "qwen2.5-72b-instruct", "display_name": "Qwen 2.5 72B"},
    {"name": "deepseek-chat", "display_name": "DeepSeek Chat"},
    {"name": "gemini-2.0-flash", "display_name": "Gemini 2.0 Flash"},
    # Добавьте другие модели по желанию:
    # {"name": "llama-3.1-70b-instruct", "display_name": "Llama 3.1 70B"},
]

# Модель по умолчанию (для одиночного запуска)
DEFAULT_MODEL = MODELS_TO_TEST[0]["name"] if MODELS_TO_TEST else "qwen2.5-72b-instruct"

# === Настройки тестирования ===
MAX_QUESTIONS = None  # None = все вопросы, или число (например 50)
SAVE_PROGRESS_EVERY = 10  # Сохранять прогресс каждые N вопросов
REQUEST_DELAY = 0.5  # Задержка между запросами (сек) для избежания лимитов
TEMPERATURE = 0.3  # Температура генерации
MAX_TOKENS = 100  # Максимум токенов в ответе

