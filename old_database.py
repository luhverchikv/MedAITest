# database.py
import sqlite3
from contextlib import contextmanager
from typing import List, Dict
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

def create_test_run(model_name: str) -> int:
    """Создает новый запуск теста и возвращает его ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO test_runs (model_name) VALUES (?)",
            (model_name,)
        )
        return cursor.lastrowid

def save_result(run_id: int, question_id: int, ai_selected_indices: List[int], score: float = None):
    """Сохраняет результат ответа на вопрос"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        indices_str = ",".join(map(str, sorted(ai_selected_indices))) if ai_selected_indices else ""
        cursor.execute(
            "INSERT INTO results (run_id, question_id, ai_selected_indices, score) VALUES (?, ?, ?, ?)",
            (run_id, question_id, indices_str, score)
        )

def get_run_results(run_id: int):
    """Получает все результаты для конкретного запуска"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, q.text as question_text, q.is_multiple, q.correct_indices
            FROM results r
            JOIN questions q ON r.question_id = q.id
            WHERE r.run_id = ?
            ORDER BY r.question_id
        """, (run_id,))
        return cursor.fetchall()

def calculate_score(ai_indices: List[int], correct_indices: List[int]) -> float:
    """Вычисляет оценку за ответ (1 - правильно, 0 - неправильно)"""
    ai_set = set(ai_indices)
    correct_set = set(correct_indices)
    return 1.0 if ai_set == correct_set else 0.0

def get_run_summary(run_id: int) -> Dict:
    """Получает сводку по запуску"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Информация о запуске
        cursor.execute("SELECT model_name, timestamp FROM test_runs WHERE id = ?", (run_id,))
        run_info = cursor.fetchone()

        # Статистика
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN score = 1.0 THEN 1 ELSE 0 END) as correct
            FROM results
            WHERE run_id = ?
        """, (run_id,))
        stats = cursor.fetchone()

        total = stats['total'] or 0
        correct = stats['correct'] or 0
        percentage = (correct / total * 100) if total > 0 else 0

        return {
            'run_id': run_id,
            'model_name': run_info['model_name'],
            'timestamp': run_info['timestamp'],
            'total_questions': total,
            'correct_answers': correct,
            'score_percentage': round(percentage, 2)
        }


def get_run_info(run_id: int):
    """Получает базовую информацию о запуске"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, model_name, timestamp FROM test_runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_runs(limit: int = 10):
    """Получает список последних запусков"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, model_name, timestamp 
            FROM test_runs 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
