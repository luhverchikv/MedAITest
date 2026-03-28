# load_data.py
from database import init_db, save_question, clear_database, get_all_questions
from parser import parse_tests_file
from config import DB_PATH, INPUT_FILE
import os

def load_questions_to_db(filepath: str, clear_first: bool = False):
    """Загружает вопросы из файла в базу данных"""
    
    # Инициализируем БД
    init_db()
    
    if clear_first:
        clear_database()
    
    # Парсим файл
    print(f"\n📄 Читаем файл: {filepath}")
    questions = parse_tests_file(filepath, verbose=True)
    
    if not questions:
        print("❌ Не найдено вопросов для загрузки")
        return
    
    # Сохраняем в БД
    print(f"\n💾 Сохраняем {len(questions)} вопросов в базу...")
    saved_count = 0
    for q in questions:
        try:
            save_question(
                text=q['text'],
                is_multiple=q['is_multiple'],
                correct_indices=q['correct_indices'],
                options_list=q['options']
            )
            saved_count += 1
        except Exception as e:
            print(f"❌ Ошибка сохранения вопроса '{q['text'][:30]}...': {e}")
    
    print(f"\n✅ Готово! Загружено вопросов: {saved_count}/{len(questions)}")
    
    # Краткая статистика
    print("\n📊 Статистика:")
    print(f"   - Всего вопросов: {saved_count}")
    print(f"   - Файл БД: {DB_PATH}")

def show_db_stats():
    """Показывает статистику по загруженным вопросам"""
    if not os.path.exists(DB_PATH):
        print("❌ База данных не найдена")
        return
    
    questions = get_all_questions()
    if not questions:
        print("⚪ База пуста")
        return
    
    total = len(questions)
    multiple = sum(1 for q in questions if q['is_multiple'])
    
    print(f"\n📊 Статистика базы данных ({DB_PATH}):")
    print(f"   - Всего вопросов: {total}")
    print(f"   - С одним ответом: {total - multiple}")
    print(f"   - С несколькими ответами: {multiple}")
    
if __name__ == "__main__":
    import sys
    
    # Простой CLI: python load_data.py [--clear] [--stats]
    if '--stats' in sys.argv:
        show_db_stats()
    else:
        clear_flag = '--clear' in sys.argv
        load_questions_to_db(INPUT_FILE, clear_first=clear_flag)

