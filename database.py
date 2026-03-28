# database.py
import sqlite3
from contextlib import contextmanager
from config import DB_PATH

@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасной работы с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Доступ к колонкам по имени
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Ошибка БД: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """Создает таблицы, если их нет"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица вопросов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                is_multiple BOOLEAN NOT NULL,
                correct_indices TEXT NOT NULL
            )
        ''')
        
        # Таблица вариантов ответов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        ''')
        
        # Таблица запусков тестов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица результатов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                ai_selected_indices TEXT,
                score REAL,
                FOREIGN KEY(run_id) REFERENCES test_runs(id) ON DELETE CASCADE,
                FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
            )
        ''')
        print("✓ Таблицы базы данных созданы/проверены")

def save_question(text: str, is_multiple: bool, correct_indices: list, options_list: list) -> int:
    """
    Сохраняет вопрос и его варианты в БД
    Возвращает ID сохраненного вопроса
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Сохраняем вопрос
        cursor.execute(
            "INSERT INTO questions (text, is_multiple, correct_indices) VALUES (?, ?, ?)",
            (text, is_multiple, ",".join(map(str, sorted(correct_indices))))
        )
        question_id = cursor.lastrowid
        
        # Сохраняем варианты ответов
        for idx, opt_text in enumerate(options_list, start=1):
            cursor.execute(
                "INSERT INTO options (question_id, option_index, text) VALUES (?, ?, ?)",
                (question_id, idx, opt_text.strip())
            )
        
        return question_id

def get_all_questions():
    """Возвращает все вопросы из БД"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, text, is_multiple, correct_indices FROM questions ORDER BY id")
        return cursor.fetchall()

def get_options_by_question_id(question_id: int):
    """Возвращает список вариантов для вопроса: [(1, 'текст'), (2, 'текст'), ...]"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT option_index, text FROM options WHERE question_id = ? ORDER BY option_index",
            (question_id,)
        )
        return cursor.fetchall()

def clear_database():
    """Очищает все таблицы (для отладки)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM results")
        cursor.execute("DELETE FROM test_runs")
        cursor.execute("DELETE FROM options")
        cursor.execute("DELETE FROM questions")
        print("✓ База данных очищена")

