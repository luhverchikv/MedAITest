# run_test.py
import time
import json
from datetime import datetime
from database import (
    init_db, get_all_questions, get_options_by_question_id,
    create_test_run, save_result, calculate_score, 
    get_run_summary, get_run_results
)
from ai_client import OpenAICompatibleClient
from config import (
    VEDAI_API_KEY, VEDAI_BASE_URL, MODELS_TO_TEST,
    MAX_QUESTIONS, SAVE_PROGRESS_EVERY, REQUEST_DELAY
)

def run_single_model_test(
    model_name: str, 
    display_name: str = None,
    max_questions: int = None, 
    verbose: bool = True
) -> dict:
    """Запускает тестирование для одной модели"""
    init_db()
    
    questions = get_all_questions()
    if not questions:
        print("❌ Нет вопросов в базе. Загрузите вопросы через load_data.py")
        return None

    if max_questions:
        questions = questions[:max_questions]
    elif MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]

    if verbose:
        print(f"\n🚀 Тестирование модели: {display_name or model_name}")
        print(f"   Вопросов: {len(questions)}")

    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=model_name
    )

    # Проверка подключения
    success, msg = client.test_connection()
    if not success:
        print(f"❌ Ошибка подключения: {msg}")
        return {"model": model_name, "error": msg, "success": False}
    
    if verbose:
        print(f"✅ {msg}")

    # Создаем запись запуска
    run_id = create_test_run(display_name or model_name)
    
    # Статистика
    correct = 0
    errors = 0
    start_time = time.time()

    for i, q in enumerate(questions, 1):
        question_id = q['id']
        question_text = q['text']
        is_multiple = bool(q['is_multiple'])
        correct_indices = [int(x) for x in q['correct_indices'].split(',')]
        options = get_options_by_question_id(question_id)

        ai_success, ai_indices, error_msg = client.get_answer(
            question_text, options, is_multiple
        )

        if not ai_success:
            errors += 1
            if verbose:
                print(f" ❌ В#{i}: {error_msg}")
            save_result(run_id, question_id, [], 0.0)
            continue

        score = calculate_score(ai_indices, correct_indices)
        if score == 1.0:
            correct += 1

        save_result(run_id, question_id, ai_indices, score)

        # Прогресс
        if verbose and (i % 5 == 0 or i == len(questions)):
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (len(questions) - i) * avg_time
            pct = correct/i*100
            print(f" 📊 {i}/{len(questions)} | ✅ {correct} ({pct:.1f}%) | ⏱ {remaining:.0f}с")

        if SAVE_PROGRESS_EVERY and i % SAVE_PROGRESS_EVERY == 0:
            if verbose:
                print(f" 💾 Прогресс сохранён...")

        time.sleep(REQUEST_DELAY)

    # Итоги
    total_time = time.time() - start_time
    summary = get_run_summary(run_id)
    
    result = {
        "run_id": run_id,
        "model": model_name,
        "display_name": display_name,
        "success": True,
        "total_questions": summary['total_questions'],
        "correct_answers": summary['correct_answers'],
        "score_percentage": summary['score_percentage'],
        "errors": errors,
        "time_seconds": round(total_time, 1)
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"🏁 {display_name or model_name} — ЗАВЕРШЕНО")
        print(f"{'='*60}")
        print(f" ✅ Правильно: {result['correct_answers']}/{result['total_questions']}")
        print(f" 📈 Точность: {result['score_percentage']}%")
        print(f" ⚠️ Ошибок API: {errors}")
        print(f" ⏱ Время: {result['time_seconds']}с")
        print(f"{'='*60}\n")

    return result


def run_all_models_comparison(max_questions: int = None, verbose: bool = True):
    """Запускает тестирование всех моделей из конфига и сравнивает результаты"""
    if not MODELS_TO_TEST:
        print("❌ Нет моделей в конфигурации (MODELS_TO_TEST в config.py)")
        return

    print(f"\n🔬 ЗАПУСК СРАВНИТЕЛЬНОГО ТЕСТИРОВАНИЯ")
    print(f"   Моделей: {len(MODELS_TO_TEST)}")
    print(f"   API: {VEDAI_BASE_URL}")
    print("="*70)

    all_results = []
    
    for model_config in MODELS_TO_TEST:
        model_name = model_config["name"]
        display_name = model_config.get("display_name", model_name)
        
        result = run_single_model_test(
            model_name=model_name,
            display_name=display_name,
            max_questions=max_questions,
            verbose=verbose
        )
        
        if result:
            all_results.append(result)
        
        # Пауза между моделями
        if model_config != MODELS_TO_TEST[-1]:
            print(f"\n⏳ Пауза 10с перед следующей моделью...")
            time.sleep(10)

    # 📊 Сводная таблица результатов
    if all_results:
        print(f"\n📊 СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
        print(f"{'='*70}")
        print(f"{'Модель':<25} {'Точность':>10} {'Прав/Всего':>12} {'Время':>8} {'Ошибки':>7}")
        print(f"{'-'*70}")
        
        # Сортировка по точности (по убыванию)
        sorted_results = sorted(
            [r for r in all_results if r.get('success')], 
            key=lambda x: x['score_percentage'], 
            reverse=True
        )
        
        for r in sorted_results:
            name = r['display_name'] or r['model']
            if len(name) > 24:
                name = name[:21] + "..."
            print(f"{name:<25} {r['score_percentage']:>9.1f}% {r['correct_answers']}/{r['total_questions']:>8} {r['time_seconds']:>7.1f}с {r['errors']:>7}")
        
        print(f"{'='*70}")
        
        # Сохранение результатов в файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_comparison_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "base_url": VEDAI_BASE_URL,
                "results": all_results
            }, f, ensure_ascii=False, indent=2)
        print(f"💾 Результаты сохранены в {filename}")

    return all_results


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
        arg = sys.argv[1]
        
        if arg == "--results" and len(sys.argv) > 2:
            show_results(int(sys.argv[2]))
        elif arg == "--compare":
            # Запуск сравнения всех моделей
            max_q = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
            run_all_models_comparison(max_questions=max_q)
        elif arg == "--model" and len(sys.argv) > 2:
            # Запуск одной конкретной модели
            model_name = sys.argv[2]
            max_q = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
            run_single_model_test(model_name=model_name, max_questions=max_q)
        elif arg.isdigit():
            show_results(int(arg))
        else:
            print("""
Использование:
  python run_test.py                    — запуск всех моделей из config.py
  python run_test.py --compare          — то же, явно
  python run_test.py --compare 50       — сравнение, первые 50 вопросов
  python run_test.py --model qwen2.5-72b-instruct  — одна модель
  python run_test.py --model <name> 50  — одна модель, 50 вопросов
  python run_test.py --results <run_id> — показать результаты
  python run_test.py <run_id>           — показать результаты (короткая форма)
            """)
    else:
        # По умолчанию — запуск сравнения всех моделей
        run_all_models_comparison()

