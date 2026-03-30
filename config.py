# config.py
import os
from pathlib import Path

# Загружаем переменные из .env файла
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv не установлен, используем os.getenv

DB_PATH = "test_database.sqlite"
INPUT_FILE = "tests_data.txt"

# OpenAI API (если используется)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = "gpt-3.5-turbo"

# DeepSeek API (рекомендуется)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Настройки тестирования
MAX_QUESTIONS = None  # None = все вопросы, или число (например 50)
SAVE_PROGRESS_EVERY = 10  # Сохранять прогресс каждые N вопросов