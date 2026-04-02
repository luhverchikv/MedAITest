# run_test.py
"""
MedAITest — Запуск AI на тестах
Поддержка множественных тестов с выбором конкретного теста
"""
import time
import logging
import sys
from pathlib import Path
from datetime import datetime

from database import (
    init_db, get_questions_by_test, get_options_by_question_id,
    create_test_run, save_result, calculate_score, get_test_by_id, get_test_by_name,
    get_all_tests
)
from ai_client import OpenAICompatibleClient
from config import (
    VEDAI_API_KEY, VEDAI_BASE_URL, DEFAULT_MODEL,
    MAX_QUESTIONS, SAVE_PROGRESS_EVERY, REQUEST_DELAY,
    TEMPERATURE, MAX_TOKENS
)


def setup_logger(run_id: int, test_name: str, log_dir: str = "logs", console: bool = True):
    """Настраивает логгер: файл + опционально консоль"""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    logger = logging.getLogger(f"run_{run_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # Файл: пишем ВСЁ
    file_handler = logging.FileHandler(
        log_path / f"run_{run_id}.log",
        mode='w', encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-7s | %(message)s',
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(file_handler)

    # Консоль: только важное
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)

    return logger


def run_test(
    test_id: int = None,
    test_name: str = None,
    model_name: str = None,
    max_questions: int = None,
    verbose: bool = True,
    log_to_file: bool = True
):
    """
    Запускает тестирование AI на вопросах указанного теста.

    Args:
        test_id: ID теста в базе (приоритетнее чем test_name)
        test_name: Имя теста (альтернатива test_id)
        model_name: Название модели AI
        max_questions: Максимум вопросов (None = все)
        verbose: Вывод в консоль
        log_to_file: Запись в лог-файл

    Returns:
        run_id: ID запуска
    """
    # 1️⃣ Инициализация БД
    init_db()

    # 2️⃣ Находим тест
    if test_id:
        test = get_test_by_id(test_id)
    elif test_name:
        test = get_test_by_name(test_name)
    else:
        # Показываем список тестов
        tests = get_all_tests()
        if not tests:
            print("❌ Нет доступных тестов. Загрузите через: python manage_tests.py --import <file>")
            return None
        print("📚 Доступные тесты:")
        for t in tests:
            print(f"   #{t['id']} | {t['name']} ({t['question_count']} вопросов)")
        print("\n💡 Используйте: python run_test.py --test-id <ID>")
        return None

    if not test:
        print(f"❌ Тест не найден: {test_id or test_name}")
        return None

    if test['question_count'] == 0:
        print(f"❌ Тест '{test['name']}' не содержит вопросов")
        return None

    # 3️⃣ Загрузка вопросов
    questions = get_questions_by_test(test['id'])
    if not questions:
        print(f"❌ Нет вопросов в тесте '{test['name']}'")
        return None

    if max_questions:
        questions = questions[:max_questions]
    elif MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]

    # 4️⃣ Создаём запуск
    model = model_name or DEFAULT_MODEL
    run_id = create_test_run(test['id'], model)

    # 5️⃣ Настраиваем логирование
    logger = None
    if log_to_file:
        logger = setup_logger(run_id, test['name'], console=verbose)
        logger.info(f"🚀 ЗАПУСК #{run_id}")
        logger.info(f"📚 Тест: {test['name']} (ID: {test['id']})")
        logger.info(f"🤖 Модель: {model} | Вопросов: {len(questions)}")
        logger.info(f"🌐 API: {VEDAI_BASE_URL} | Temp: {TEMPERATURE}")
        logger.info("-" * 70)
    elif verbose:
        print(f"\n🚀 Запуск #{run_id}")
        print(f"📚 Тест: {test['name']}")
        print(f"🤖 Модель: {model} | {len(questions)} вопросов")

    # 6️⃣ Инициализация AI-клиента
    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=model,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )

    # 7️⃣ Проверка подключения
    success, msg = client.test_connection()
    if not success:
        error = f"❌ Ошибка подключения: {msg}"
        if logger:
            logger.error(error)
        else:
            print(error)
        return None

    if logger:
        logger.info(f"✅ Подключение: {msg}")
    elif verbose:
        print(f"✅ {msg}")

    # 8️⃣ Статистика
    correct = 0
    errors = 0
    start_time = time.time()

    # 9️⃣ Главный цикл
    for i, q in enumerate(questions, 1):
        q_start = time.time()

        question_id = q['id']
        question_text = q['text']
        is_multiple = bool(q['is_multiple'])
        correct_indices = [int(x) for x in q['correct_indices'].split(',')]
        options = get_options_by_question_id(question_id)

        # Запрос к AI
        ai_success, ai_indices, error_msg = client.get_answer(
            question_text, options, is_multiple
        )

        q_time = time.time() - q_start

        # Обработка ошибки API
        if not ai_success:
            errors += 1
            if logger:
                logger.error(f"Q{i:03d} ❌ API ERROR: {error_msg}")
            elif verbose:
                print(f" ❌ В#{i}: {error_msg}")
            save_result(run_id, question_id, [], 0.0)
            continue

        # Оценка и сохранение
        score = calculate_score(ai_indices, correct_indices)
        if score == 1.0:
            correct += 1

        save_result(run_id, question_id, ai_indices, score)

        # Логирование
        if logger:
            status = "✅" if score == 1.0 else "❌"
            q_short = question_text[:80].replace('\n', ' ')
            logger.info(f"Q{i:03d} {status} \"{q_short}...\" → {ai_indices} [{q_time:.2f}с]")

            if score < 1.0:
                logger.info(f" ⚠️ Ошибка: ожидалось {correct_indices}, получено {ai_indices}")

        # Прогресс
        if verbose and (i % 5 == 0 or i == len(questions)):
            elapsed = time.time() - start_time
            avg = elapsed / i
            remaining = (len(questions) - i) * avg
            pct = correct / i * 100
            print(f" 📊 {i}/{len(questions)} | ✅ {correct} ({pct:.1f}%) | ⏱ {remaining:.0f}с")

        # Сохранение прогресса
        if SAVE_PROGRESS_EVERY and i % SAVE_PROGRESS_EVERY == 0:
            if logger:
                logger.info(f"💾 Сохранено {i}/{len(questions)}")

        time.sleep(REQUEST_DELAY)

    # 🔟 Итоги
    total_time = time.time() - start_time

    # Обновляем сводку (один раз, в конце теста)
    from database import update_run_summary, get_run_info
    update_run_summary(run_id)
    summary = get_run_info(run_id)

    result_msg = (
        f"\n{'='*60}\n"
        f"🏁 ТЕСТ ЗАВЕРШЁН\n"
        f"{'='*60}\n"
        f" 📚 Тест: {test['name']}\n"
        f" 🤖 Модель: {summary['model_name']}\n"
        f" 📋 Вопросов: {summary['total_questions']}\n"
        f" ✅ Правильных: {summary['correct_answers']}\n"
        f" 📊 Процент: {summary['score_percentage']:.1f}%\n"
        f" ⏱ Время: {total_time:.1f}с\n"
        f"{'='*60}"
    )

    if logger:
        logger.info(result_msg)
        logger.info(f"📄 Лог: logs/run_{run_id}.log")
    else:
        print(result_msg)

    return run_id


# ============================================================================
# 🎯 MAIN — ТОЧКА ВХОДА
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🏥 MedAITest — Тестирование AI на медицинских тестах",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --test-id 1                    — запуск теста #1
  %(prog)s --test-id 1 -m gemini-2.5    — тест #1 с моделью gemini
  %(prog)s --test-name "Фармакология"    — запуск по имени теста
  %(prog)s --test-id 1 -n 50             — только 50 вопросов
  %(prog)s --list-tests                  — показать доступные тесты
        """
    )

    # Выбор теста
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument('--test-id', type=int, help='ID теста в базе')
    test_group.add_argument('--test-name', type=str, help='Имя теста')
    test_group.add_argument('--list-tests', action='store_true', help='Показать доступные тесты')

    # Параметры запуска
    parser.add_argument('-m', '--model', type=str, help='Модель AI')
    parser.add_argument('-n', '--questions', type=int, help='Количество вопросов')
    parser.add_argument('--fast', action='store_true', help='Без задержек')
    parser.add_argument('-q', '--quiet', action='store_true', help='Минимум вывода')

    args = parser.parse_args()

    # Список тестов
    if args.list_tests:
        init_db()
        tests = get_all_tests()
        if not tests:
            print("❌ Нет доступных тестов")
            print("💡 Загрузите тест: python manage_tests.py --import <file.json>")
        else:
            print(f"\n📚 Доступные тесты ({len(tests)}):")
            print("-" * 70)
            for t in tests:
                cat = f"[{t['category']}]" if t['category'] else ""
                print(f"  #{t['id']:2d} | {t['name']:30s} | {t['question_count']:3d} вопр. {cat}")
                if t['description']:
                    print(f"       {t['description'][:60]}...")
            print("-" * 70)
            print(f"💡 Запуск: python run_test.py --test-id <ID>")
        sys.exit(0)

    # Переопределяем задержку
    if args.fast:
        import config
        config.REQUEST_DELAY = 0.0

    # Запускаем тест
    run_test(
        test_id=args.test_id,
        test_name=args.test_name,
        model_name=args.model,
        max_questions=args.questions,
        verbose=not args.quiet,
        log_to_file=True
    )
