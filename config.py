# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


DB_PATH = "test_database.sqlite"
INPUT_FILE = "tests_data.txt"

# Настройки API (заполните позже)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = "gpt-3.5-turbo"


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MAX_QUESTIONS = None  # или ограничение (например 50)
SAVE_PROGRESS_EVERY = 10


