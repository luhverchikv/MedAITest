# run_test.py
import time
from database import (
    init_db, get_all_questions, get_options_by_question_id,
    create_test_run, save_result, calculate_score, get_run_summary, get_run_results
)
from ai_client import DeepSeekClient
from config import DEEPSEEK_MODEL, MAX_QUESTIONS, SAVE_PROGRESS_EVERY


def run_test(model_name: str = None, max_questions: int = None, verbose: bool = True):
    """
    Запускает тестирование AI на вопросах из базы данных

    Args:
        model_name: имя модели для записи в БД
        max_questions: ограничение количества вопросов (None = все)
        verbose: показывать прогресс
    """
    # Инициализация
    init_db()

    # Получаем вопросы
    questions = get_all_questions()
    if not questions:
        print("❌ Нет вопросов в базе. Загрузите вопросы через load_data.py")
        return None

    # Ограничиваем количество
    if max_questions:
        questions = questions[:max_questions]
    elif MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]

    print(f"\n🚀 Запуск тестирования: {len(questions)} вопросов")

    # Создаем клиент AI
    client = DeepSeekClient()

    # Проверяем подключение
    success, msg = client.test_connection()
    if not success:
        print(f"❌ Ошибка подключения: {msg}")
        print("💡 Убедитесь, что DEEPSEEK_API_KEY установлен в переменных окружения")
        return None

    print(f"✅ Подключение к API: {msg}")

    # Создаем запуск в БД
    run_id = create_test_run(model_name or DEEPSEEK_MODEL)
    print(f"📋 Запуск #{run_id}")

    # Статистика
    correct = 0
    errors = 0
    start_time = time.time()

    # Основной цикл
    for i, q in enumerate(questions, 1):
        question_id = q['id']
        question_text = q['text']
        is_multiple = bool(q['is_multiple'])
        correct_indices = [int(x) for x in q['correct_indices'].split(',')]

        # Получаем варианты ответов
        options = get_options_by_question_id(question_id)

        # Отправляем вопрос AI
        ai_success, ai_indices, error_msg = client.get_answer(
            question_text, options, is_multiple
        )

        if not ai_success:
            errors += 1
            if verbose:
                print(f"  ❌ Вопрос #{i}: ошибка AI - {error_msg}")
            # Сохраняем с пустым ответом
            save_result(run_id, question_id, [], 0.0)
            continue

        # Вычисляем оценку
        score = calculate_score(ai_indices, correct_indices)
        if score == 1.0:
            correct += 1

        # Сохраняем результат
        save_result(run_id, question_id, ai_indices, score)

        # Прогресс
        if verbose and (i % 5 == 0 or i == len(questions)):
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (len(questions) - i) * avg_time
            print(f"  📊 {i}/{len(questions)} | Правильно: {correct}/{i} ({correct/i*100:.1f}%) | Осталось: {remaining:.0f}с")

        # Сохраняем прогресс каждые N вопросов
        if SAVE_PROGRESS_EVERY and i % SAVE_PROGRESS_EVERY == 0:
            print(f"  💾 Сохранено {i} результатов...")

        # Небольшая задержка между запросами
        time.sleep(0.5)

    # Итоги
    total_time = time.time() - start_time
    summary = get_run_summary(run_id)

    print(f"\n{'='*60}")
    print(f"🏁 ТЕСТ ЗАВЕРШЕН")
    print(f"{'='*60}")
    print(f"  Модель: {summary['model_name']}")
    print(f"  Всего вопросов: {summary['total_questions']}")
    print(f"  Правильных ответов: {summary['correct_answers']}")
    print(f"  Процент: {summary['score_percentage']}%")
    print(f"  Ошибок API: {errors}")
    print(f"  Время: {total_time:.1f}с")
    print(f"{'='*60}\n")

    return run_id


def show_results(run_id: int):
    """Показывает детальные результаты запуска"""
    results = get_run_results(run_id)
    if not results:
        print(f"❌ Нет результатов для запуска #{run_id}")
        return

    print(f"\n📋 Результаты запуска #{run_id}")
    print("="*80)

    for r in results:
        q_text = r['question_text'][:60]
        is_multiple = r['is_multiple']
        correct_indices = [int(x) for x in r['correct_indices'].split(',')]
        ai_indices = [int(x) for x in r['ai_selected_indices'].split(',')] if r['ai_selected_indices'] else []
        score = r['score']

        status = "✅" if score == 1.0 else "❌"
        print(f"\n{status} Вопрос #{r['question_id']}: {q_text}...")

        if is_multiple:
            print(f"   Ожидалось: {correct_indices}")
            print(f"   Получено: {ai_indices}")
        else:
            expected = correct_indices[0] if correct_indices else "?"
            got = ai_indices[0] if ai_indices else "?"
            print(f"   Ожидалось: {expected}, получено: {got}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--results" and len(sys.argv) > 2:
            show_results(int(sys.argv[2]))
        elif sys.argv[1].isdigit():
            show_results(int(sys.argv[1]))
        else:
            print("Использование:")
            print("  python run_test.py                    — запустить тест")
            print("  python run_test.py --results <id>    — показать результаты")
    else:
        run_test()