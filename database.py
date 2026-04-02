# database.py
"""
MedAITest — База данных для управления тестами и результатами
Поддержка множественных тестов с возможностью обмена между пользователями
"""
import sqlite3
import json
import hashlib
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from config import DB_PATH


@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасной работы с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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

        # Таблица тестов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                source TEXT,
                author TEXT,
                version TEXT DEFAULT '1.0',
                category TEXT,
                difficulty TEXT,
                question_count INTEGER DEFAULT 0,
                checksum TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица вопросов (связь с тестом)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                external_id TEXT,
                text TEXT NOT NULL,
                is_multiple BOOLEAN NOT NULL,
                correct_indices TEXT NOT NULL,
                explanation TEXT,
                FOREIGN KEY(test_id) REFERENCES tests(id) ON DELETE CASCADE
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

        # Таблица запусков тестов (связь с тестом)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                score_percentage REAL DEFAULT 0,
                FOREIGN KEY(test_id) REFERENCES tests(id) ON DELETE SET NULL
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

        # Создаем индексы для производительности
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_questions_test_id ON questions(test_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_results_run_id ON results(run_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_runs_test_id ON test_runs(test_id)')


# =============================================================================
# УПРАВЛЕНИЕ ТЕСТАМИ
# =============================================================================

def create_test(name: str, description: str = "", source: str = "", author: str = "",
                category: str = "", difficulty: str = "") -> int:
    """
    Создает новый тест.
    Returns: ID созданного теста
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tests (name, description, source, author, category, difficulty)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, source, author, category, difficulty))
        return cursor.lastrowid


def get_test_by_id(test_id: int) -> Optional[Dict]:
    """Получает информацию о тесте по ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tests WHERE id = ?', (test_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_test_by_name(name: str) -> Optional[Dict]:
    """Получает информацию о тесте по имени"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tests WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_tests(include_inactive: bool = False) -> List[Dict]:
    """Получает список всех тестов"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if include_inactive:
            cursor.execute('SELECT * FROM tests ORDER BY created_at DESC')
        else:
            cursor.execute('SELECT * FROM tests WHERE is_active = 1 ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]


def update_test(test_id: int, **kwargs):
    """Обновляет информацию о тесте"""
    allowed_fields = ['name', 'description', 'source', 'author', 'category',
                     'difficulty', 'is_active', 'version']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not updates:
        return

    updates['updated_at'] = datetime.now().isoformat()

    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [test_id]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f'UPDATE tests SET {set_clause} WHERE id = ?', values)


def delete_test(test_id: int, permanent: bool = False):
    """
    Удаляет тест.
    permanent=False: мягкое удаление (is_active = 0)
    permanent=True: полное удаление из БД
    """
    if permanent:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM tests WHERE id = ?', (test_id,))
    else:
        update_test(test_id, is_active=False)


def update_test_question_count(test_id: int):
    """Обновляет счётчик вопросов в тесте"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM questions WHERE test_id = ?', (test_id,))
        count = cursor.fetchone()[0]
        cursor.execute('UPDATE tests SET question_count = ? WHERE id = ?', (count, test_id))


# =============================================================================
# УПРАВЛЕНИЕ ВОПРОСАМИ
# =============================================================================

def save_question(test_id: int, text: str, is_multiple: bool, correct_indices: list,
                 options_list: list, external_id: str = None, explanation: str = None) -> int:
    """
    Сохраняет вопрос в тест.
    Returns: ID сохраненного вопроса
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Сохраняем вопрос
        cursor.execute('''
            INSERT INTO questions (test_id, external_id, text, is_multiple, correct_indices, explanation)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (test_id, external_id, text, is_multiple,
              ",".join(map(str, sorted(correct_indices))), explanation))
        question_id = cursor.lastrowid

        # Сохраняем варианты ответов
        for idx, opt_text in enumerate(options_list, start=1):
            cursor.execute('''
                INSERT INTO options (question_id, option_index, text)
                VALUES (?, ?, ?)
            ''', (question_id, idx, opt_text.strip()))

        # Обновляем счётчик вопросов
        update_test_question_count(test_id)

        return question_id


def get_questions_by_test(test_id: int) -> List[Dict]:
    """Возвращает все вопросы для указанного теста"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, test_id, external_id, text, is_multiple, correct_indices, explanation
            FROM questions WHERE test_id = ? ORDER BY id
        ''', (test_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_question_by_id(question_id: int) -> Optional[Dict]:
    """Возвращает информацию о вопросе"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_options_by_question_id(question_id: int) -> List[tuple]:
    """Возвращает варианты ответов для вопроса: [(1, 'текст'), ...]"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT option_index, text FROM options
            WHERE question_id = ? ORDER BY option_index
        ''', (question_id,))
        return [(row['option_index'], row['text']) for row in cursor.fetchall()]


def delete_questions_by_test(test_id: int):
    """Удаляет все вопросы теста"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM questions WHERE test_id = ?', (test_id,))
        update_test_question_count(test_id)


# =============================================================================
# УПРАВЛЕНИЕ ЗАПУСКАМИ И РЕЗУЛЬТАТАМИ
# =============================================================================

def create_test_run(test_id: int, model_name: str) -> int:
    """Создает новый запуск теста"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO test_runs (test_id, model_name, timestamp)
            VALUES (?, ?, ?)
        ''', (test_id, model_name, datetime.now().isoformat()))
        return cursor.lastrowid


def update_run_summary(run_id: int):
    """Обновляет сводку по запуску (счётчики и проценты)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Получаем статистику
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN score = 1.0 THEN 1 ELSE 0 END) as correct
            FROM results WHERE run_id = ?
        ''', (run_id,))
        stats = cursor.fetchone()
        total = stats['total'] or 0
        correct = stats['correct'] or 0
        percentage = (correct / total * 100) if total > 0 else 0

        # Обновляем запись
        cursor.execute('''
            UPDATE test_runs
            SET total_questions = ?, correct_answers = ?, score_percentage = ?
            WHERE id = ?
        ''', (total, correct, percentage, run_id))


def save_result(run_id: int, question_id: int, ai_selected_indices: List[int], score: float = None):
    """Сохраняет результат ответа"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        indices_str = ",".join(map(str, sorted(ai_selected_indices))) if ai_selected_indices else ""
        cursor.execute('''
            INSERT INTO results (run_id, question_id, ai_selected_indices, score)
            VALUES (?, ?, ?, ?)
        ''', (run_id, question_id, indices_str, score))

        # Обновляем сводку
        update_run_summary(run_id)


def get_run_results(run_id: int) -> List[Dict]:
    """Получает все результаты для запуска"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, q.text as question_text, q.is_multiple, q.correct_indices,
                   q.explanation
            FROM results r
            JOIN questions q ON r.question_id = q.id
            WHERE r.run_id = ?
            ORDER BY r.id
        ''', (run_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_run_info(run_id: int) -> Optional[Dict]:
    """Получает информацию о запуске"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tr.*, t.name as test_name, t.category
            FROM test_runs tr
            JOIN tests t ON tr.test_id = t.id
            WHERE tr.id = ?
        ''', (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_runs_by_test(test_id: int, limit: int = 10) -> List[Dict]:
    """Получает запуски для указанного теста"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tr.*, t.name as test_name
            FROM test_runs tr
            JOIN tests t ON tr.test_id = t.id
            WHERE tr.test_id = ?
            ORDER BY tr.timestamp DESC
            LIMIT ?
        ''', (test_id, limit))
        return [dict(row) for row in cursor.fetchall()]


def get_all_runs(limit: int = 10) -> List[Dict]:
    """Получает все запуски"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT tr.*, t.name as test_name, t.category
            FROM test_runs tr
            JOIN tests t ON tr.test_id = t.id
            ORDER BY tr.timestamp DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def calculate_score(ai_indices: List[int], correct_indices: List[int]) -> float:
    """Вычисляет оценку за ответ"""
    return 1.0 if set(ai_indices) == set(correct_indices) else 0.0


def clear_database():
    """Очищает все таблицы"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM results")
        cursor.execute("DELETE FROM test_runs")
        cursor.execute("DELETE FROM options")
        cursor.execute("DELETE FROM questions")
        cursor.execute("DELETE FROM tests")


# =============================================================================
# ИМПОРТ/ЭКСПОРТ ТЕСТОВ
# =============================================================================

def export_test(test_id: int, filepath: str = None) -> str:
    """
    Экспортирует тест в JSON-файл для обмена.
    Returns: путь к файлу
    """
    test = get_test_by_id(test_id)
    if not test:
        raise ValueError(f"Тест с ID {test_id} не найден")

    questions = get_questions_by_test(test_id)
    export_data = {
        "format_version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "test": {
            "name": test['name'],
            "description": test['description'],
            "source": test['source'],
            "author": test['author'],
            "category": test['category'],
            "difficulty": test['difficulty'],
            "version": test['version']
        },
        "questions": []
    }

    for q in questions:
        options = get_options_by_question_id(q['id'])
        export_data["questions"].append({
            "external_id": q['external_id'],
            "text": q['text'],
            "is_multiple": bool(q['is_multiple']),
            "correct_indices": [int(x) for x in q['correct_indices'].split(',')],
            "options": [{"index": idx, "text": text} for idx, text in options],
            "explanation": q['explanation']
        })

    # Вычисляем checksum
    content_str = json.dumps(export_data, ensure_ascii=False, sort_keys=True)
    export_data["checksum"] = hashlib.md5(content_str.encode()).hexdigest()

    # Генерируем имя файла
    if not filepath:
        safe_name = "".join(c for c in test['name'] if c.isalnum() or c in (' ', '-', '_')).strip()
        filepath = f"test_{test['name'].lower().replace(' ', '_')}_{test['version']}.json"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return filepath


def import_test(filepath: str, replace_existing: bool = False) -> int:
    """
    Импортирует тест из JSON-файла.
    replace_existing=True заменит существующий тест с тем же именем

    Returns: ID импортированного теста
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Валидация формата
    required = ['format_version', 'test', 'questions']
    for field in required:
        if field not in data:
            raise ValueError(f"Неверный формат файла: отсутствует '{field}'")

    test_info = data['test']

    # Проверяем checksum
    if 'checksum' in data:
        check_data = {k: v for k, v in data.items() if k != 'checksum'}
        check_str = json.dumps(check_data, ensure_ascii=False, sort_keys=True)
        calc_checksum = hashlib.md5(check_str.encode()).hexdigest()
        if calc_checksum != data['checksum']:
            raise ValueError("Ошибка целостности: контрольная сумма не совпадает")

    # Проверяем, существует ли тест
    existing = get_test_by_name(test_info['name'])

    if existing:
        if replace_existing:
            # Удаляем старый тест и импортируем новый
            delete_questions_by_test(existing['id'])
            test_id = existing['id']
            update_test(test_id, **test_info, is_active=True)
        else:
            raise ValueError(f"Тест '{test_info['name']}' уже существует. "
                           f"Используйте --replace для замены.")
    else:
        # Создаём новый тест
        test_id = create_test(
            name=test_info['name'],
            description=test_info.get('description', ''),
            source=test_info.get('source', ''),
            author=test_info.get('author', ''),
            category=test_info.get('category', ''),
            difficulty=test_info.get('difficulty', '')
        )

    # Импортируем вопросы
    for q_data in data['questions']:
        options_list = [opt['text'] for opt in sorted(q_data['options'], key=lambda x: x['index'])]

        save_question(
            test_id=test_id,
            text=q_data['text'],
            is_multiple=q_data['is_multiple'],
            correct_indices=q_data['correct_indices'],
            options_list=options_list,
            external_id=q_data.get('external_id'),
            explanation=q_data.get('explanation')
        )

    return test_id


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def get_database_stats() -> Dict:
    """Возвращает статистику по базе данных"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        stats = {}

        # Количество тестов
        cursor.execute('SELECT COUNT(*) FROM tests WHERE is_active = 1')
        stats['tests_count'] = cursor.fetchone()[0]

        # Количество вопросов
        cursor.execute('SELECT COUNT(*) FROM questions q JOIN tests t ON q.test_id = t.id WHERE t.is_active = 1')
        stats['questions_count'] = cursor.fetchone()[0]

        # Количество запусков
        cursor.execute('SELECT COUNT(*) FROM test_runs')
        stats['runs_count'] = cursor.fetchone()[0]

        # Тесты по категориям
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM tests WHERE is_active = 1 AND category != ''
            GROUP BY category
        ''')
        stats['by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}

        return stats
