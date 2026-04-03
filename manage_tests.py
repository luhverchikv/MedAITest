# manage_tests.py
"""
MedAITest — Управление тестами
Импорт, экспорт и управление тестами
"""
import sys
import os
from pathlib import Path

from database import (
    init_db, get_all_tests, get_test_by_id, get_test_by_name,
    create_test, delete_test, delete_questions_by_test,
    export_test, import_test, get_database_stats,
    get_questions_by_test, save_question
)
from parser import parse_tests_file


def list_tests():
    """Показывает список всех тестов"""
    tests = get_all_tests()

    if not tests:
        print("📭 Нет доступных тестов")
        return

    print(f"\n📚 Тесты в базе ({len(tests)}):")
    print("=" * 80)

    for t in tests:
        cat = f"[{t['category']}]" if t['category'] else ""
        diff = f"[{t['difficulty']}]" if t['difficulty'] else ""

        print(f"\n  🏷️ #{t['id']} | {t['name']}")
        print(f"     Вопросов: {t['question_count']} {cat} {diff}")

        if t['description']:
            print(f"     📝 {t['description'][:70]}")

        if t['author']:
            print(f"     👤 Автор: {t['author']}")

        if t['source']:
            print(f"     📖 Источник: {t['source']}")

    print("\n" + "=" * 80)


def show_test(test_id: int):
    """Показывает детали теста"""
    test = get_test_by_id(test_id)

    if not test:
        print(f"❌ Тест #{test_id} не найден")
        return

    questions = get_questions_by_test(test_id)

    print(f"\n📋 ТЕСТ #{test['id']}")
    print("=" * 80)
    print(f"  Название: {test['name']}")

    if test['description']:
        print(f"  Описание: {test['description']}")

    if test['category']:
        print(f"  Категория: {test['category']}")

    if test['difficulty']:
        print(f"  Сложность: {test['difficulty']}")

    if test['author']:
        print(f"  Автор: {test['author']}")

    if test['source']:
        print(f"  Источник: {test['source']}")

    print(f"  Версия: {test['version']}")
    print(f"  Вопросов: {test['question_count']}")
    print(f"  Создан: {test['created_at']}")
    print(f"  Обновлён: {test['updated_at']}")

    # Показываем первые 5 вопросов
    if questions:
        print(f"\n  📌 Примеры вопросов (первые 5):")
        for i, q in enumerate(questions[:5], 1):
            mult = "� multiple" if q['is_multiple'] else ""
            print(f"    {i}. {q['text'][:60]}... {mult}")

        if len(questions) > 5:
            print(f"    ... и ещё {len(questions) - 5} вопросов")

    print("=" * 80)


def create_test_interactive():
    """Создаёт новый тест интерактивно"""
    print("\n🆕 Создание нового теста")
    print("=" * 40)

    name = input("Название теста: ").strip()
    if not name:
        print("❌ Название обязательно")
        return None

    description = input("Описание (опционально): ").strip()
    category = input("Категория (опционально): ").strip()
    difficulty = input("Сложность (easy/medium/hard, опционально): ").strip()
    author = input("Автор (опционально): ").strip()
    source = input("Источник (опционально): ").strip()

    # Проверяем, что тест с таким именем не существует
    existing = get_test_by_name(name)
    if existing:
        print(f"❌ Тест '{name}' уже существует (ID: {existing['id']})")
        return None

    test_id = create_test(
        name=name,
        description=description,
        category=category,
        difficulty=difficulty,
        author=author,
        source=source
    )

    print(f"✅ Тест создан (ID: {test_id})")
    return test_id


def import_test_file(filepath: str, replace: bool = False):
    """Импортирует тест из файла"""
    if not os.path.exists(filepath):
        print(f"❌ Файл не найден: {filepath}")
        return None

    print(f"\n📥 Импорт теста из: {filepath}")

    try:
        test_id = import_test(filepath, replace_existing=replace)
        test = get_test_by_id(test_id)
        print(f"✅ Тест импортирован!")
        print(f"   Название: {test['name']}")
        print(f"   ID: {test_id}")
        print(f"   Вопросов: {test['question_count']}")
        return test_id
    except ValueError as e:
        print(f"❌ Ошибка: {e}")
        return None


def export_test_file(test_id: int, filepath: str = None):
    """Экспортирует тест в файл"""
    test = get_test_by_id(test_id)
    if not test:
        print(f"❌ Тест #{test_id} не найден")
        return None

    print(f"\n📤 Экспорт теста: {test['name']}")

    try:
        output_path = export_test(test_id, filepath)
        print(f"✅ Тест экспортирован!")
        print(f"   Файл: {output_path}")
        print(f"   Вопросов: {test['question_count']}")
        print(f"\n💡 Поделитесь файлом {output_path} с другими!")
        return output_path
    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")
        return None


def load_from_folder(folder: str = "tests"):
    """Загружает тесты из файлов .txt в папке"""
    folder_path = Path(folder)

    if not folder_path.exists():
        print(f"❌ Папка не найдена: {folder}")
        return []

    txt_files = list(folder_path.glob("*.txt"))

    if not txt_files:
        print(f"❌ В папке {folder} нет файлов .txt")
        return []

    print(f"\n📂 Найдено файлов: {len(txt_files)}")

    imported = []
    for filepath in txt_files:
        print(f"\n📄 Обработка: {filepath.name}")

        # Парсим файл
        questions = parse_tests_file(str(filepath), verbose=False)

        if not questions:
            print(f"   ⚠️ Вопросы не найдены")
            continue

        # Извлекаем имя теста из имени файла
        test_name = filepath.stem.replace("_", " ").replace("-", " ").title()

        # Проверяем, существует ли тест
        existing = get_test_by_name(test_name)

        if existing:
            print(f"   ⚠️ Тест '{test_name}' уже существует (ID: {existing['id']})")
            response = input("   Заменить? (y/N): ").strip().lower()
            if response != 'y':
                print("   ⏭️ Пропущено")
                continue
            delete_questions_by_test(existing['id'])
            test_id = existing['id']
        else:
            # Определяем категорию из имени файла
            category_map = {
                'anaphylaxis': 'Анафилаксия и шок',
                'pharmacology': 'Клиническая фармакология',
                'emergency': 'Неотложная помощь',
                'disaster_medicine': 'Медицина катастроф',
                'bioethics': 'Биоэтика',
                'cardiology': 'Кардиология',
                'toxicology': 'Токсикология',
                'infectious_diseases': 'Инфекционные болезни',
                'evidence_based_medicine': 'Доказательная медицина',
            }

            category = category_map.get(filepath.stem.lower(), 'Общие вопросы')

            test_id = create_test(
                name=test_name,
                description=f"Загружено из {filepath.name}",
                category=category,
                source="MedAITest default"
            )

        # Сохраняем вопросы
        for q in questions:
            save_question(
                test_id=test_id,
                text=q['text'],
                is_multiple=q['is_multiple'],
                correct_indices=q['correct_indices'],
                options_list=q['options']
            )

        print(f"   ✅ '{test_name}' — {len(questions)} вопросов")
        imported.append(test_id)

    print(f"\n✅ Импортировано тестов: {len(imported)}")
    return imported


def delete_test_interactive(test_id: int, permanent: bool = False):
    """Удаляет тест"""
    test = get_test_by_id(test_id)

    if not test:
        print(f"❌ Тест #{test_id} не найден")
        return False

    action = "удалён навсегда" if permanent else "помечен как удалённый"

    if not permanent:
        confirm = input(f"🗑️ Удалить тест '{test['name']}'? (y/N): ").strip().lower()
        if confirm != 'y':
            print("⏭️ Отменено")
            return False
        delete_test(test_id, permanent=False)
    else:
        confirm = input(f"⚠️ ПОЛНОСТЬЮ удалить тест '{test['name']}'? Это необратимо! (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("⏭️ Отменено")
            return False
        delete_test(test_id, permanent=True)

    print(f"✅ Тест {action}")
    return True


def show_stats():
    """Показывает статистику базы данных"""
    stats = get_database_stats()

    print(f"\n📊 Статистика базы данных")
    print("=" * 50)
    print(f"  📚 Тестов: {stats['tests_count']}")
    print(f"  ❓ Вопросов: {stats['questions_count']}")
    print(f"  🏃 Запусков: {stats['runs_count']}")

    if stats['by_category']:
        print(f"\n  📂 По категориям:")
        for cat, count in stats['by_category'].items():
            print(f"     • {cat}: {count}")

    print("=" * 50)


# ============================================================================
# 🎯 MAIN — ТОЧКА ВХОДА
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="📚 MedAITest — Управление тестами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Просмотр тестов
  %(prog)s --list                    — список всех тестов
  %(prog)s --stats                   — статистика базы
  %(prog)s --show 1                 — детали теста #1

  # Импорт тестов
  %(prog)s --import tests/pharmacology.txt          — из txt файла
  %(prog)s --import my_test.json         — из JSON файла
  %(prog)s --import-folder tests/       — все txt из папки
  %(prog)s --import tests/ pharmacology.txt --replace  — с заменой

  # Экспорт тестов
  %(prog)s --export 1                  — экспорт теста #1
  %(prog)s --export 1 -o my_test.json   — экспорт в конкретный файл

  # Управление
  %(prog)s --create                     — создать тест интерактивно
  %(prog)s --delete 1                   — удалить тест #1
  %(prog)s --delete 1 --permanent       — удалить полностью
        """
    )

    # Действия
    parser.add_argument('--list', action='store_true', help='Список тестов')
    parser.add_argument('--stats', action='store_true', help='Статистика базы')
    parser.add_argument('--show', type=int, metavar='ID', help='Показать тест')
    parser.add_argument('--create', action='store_true', help='Создать тест')

    # Импорт
    parser.add_argument('--import', dest='import_file', type=str, help='Импорт из файла')
    parser.add_argument('--import-folder', type=str, help='Импорт всех txt из папки')
    parser.add_argument('--replace', action='store_true', help='Заменить существующий тест')

    # Экспорт
    parser.add_argument('--export', type=int, metavar='ID', help='Экспорт теста')
    parser.add_argument('-o', '--output', type=str, help='Путь для экспорта')

    # Удаление
    parser.add_argument('--delete', type=int, metavar='ID', help='Удалить тест')
    parser.add_argument('--permanent', action='store_true', help='Полное удаление')

    args = parser.parse_args()

    # Инициализируем БД
    init_db()

    # Выполняем действие
    if args.list:
        list_tests()

    elif args.stats:
        show_stats()

    elif args.show:
        show_test(args.show)

    elif args.create:
        create_test_interactive()

    elif args.import_file:
        import_test_file(args.import_file, replace=args.replace)

    elif args.import_folder:
        load_from_folder(args.import_folder)

    elif args.export:
        export_test_file(args.export, filepath=args.output)

    elif args.delete:
        delete_test_interactive(args.delete, permanent=args.permanent)

    else:
        # Показываем справку и список тестов
        print("📚 MedAITest — Управление тестами\n")
        print("Используйте --help для справки")
        list_tests()
