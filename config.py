# config.py
import os

DB_PATH = "test_database.sqlite"
INPUT_FILE = "tests_data.txt"

# Настройки API (заполните позже)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = "gpt-3.5-turbo"

