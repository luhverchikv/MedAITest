# find_bad_questions.py
"""
🔍 MedAITest — Поиск подозрительных вопросов

Гипотеза: Если несколько моделей при прохождении теста делают
одинаковые ошибки (выбирают полностью совпадающий НЕПРАВИЛЬНЫЙ ответ),
это может говорить о некорректно составленном вопросе.

Использование:
    python find_bad_questions.py 1 2 3           # сравнить запуски 1, 2, 3
    python find_bad_questions.py 1 2 3 7        # добавить запуск 7
    python find_bad_questions.py 1 2 -t 0.3      # порог согласия 30%
    python find_bad_questions.py 1 2 3 --min-models 4  # минимум 4 модели
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple
from datetime import datetime

# Добавляем корень проекта в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from database import get_run_results, get_run_info, get_all_runs, get_options_by_question_id


def get_consistent_errors(run_ids: List[int], min_models: int = None, agreement_threshold: float = 1.0) -> List[Dict]:
    """
    Находит вопросы, где все указанные модели дали одинаковый НЕПРАВИЛЬНЫЙ ответ.

    Args:
        run_ids: Список ID запусков для анализа
        min_models: Минимальное количество моделей (по умолчанию = len(run_ids))
        agreement_threshold: Порог согласия (1.0 = все модели, 0.5 = половина)

    Returns:
        List[Dict]: Список подозрительных вопросов с деталями
    """
    if min_models is None:
        min_models = len(run_ids)

    # Собираем данные по всем запускам
    run_data = {}
    for run_id in run_ids:
        run_info = get_run_info(run_id)
        if not run_info:
            print(f"⚠️ Запуск #{run_id} не найден, пропускаем")
            continue
        results = get_run_results(run_id)
        if not results:
            print(f"⚠️ Нет результатов для запуска #{run_id}, пропускаем")
            continue
        run_data[run_id] = {
            'model': run_info['model_name'],
            'results': results
        }

    if len(run_data) < 2:
        print("❌ Нужно минимум 2 запуска для сравнения")
        return []

    # Группируем ответы по question_id
    # question_answers[question_id] = {answer_tuple: [run_ids with this answer]}
    question_answers = defaultdict(lambda: defaultdict(list))

    for run_id, data in run_data.items():
        for r in data['results']:
            q_id = r['question_id']
            ai_indices = r['ai_selected_indices'] if r['ai_selected_indices'] else ""
            correct_indices = r['correct_indices']

            # Сохраняем как отсортированный кортеж для сравнения
            answer = tuple(sorted(int(x) for x in ai_indices.split(',') if x))
            correct = tuple(sorted(int(x) for x in correct_indices.split(',')))

            question_answers[q_id][answer].append({
                'run_id': run_id,
                'is_correct': answer == correct,
                'ai_indices': list(answer),
                'correct_indices': list(correct)
            })

    # Находим подозрительные вопросы
    suspicious_questions = []

    for q_id, answers_group in question_answers.items():
        total_responses = sum(len(runs) for runs in answers_group.values())

        # Проверяем каждый уникальный ответ
        for answer, responses in answers_group.items():
            # Ответ должен быть НЕ правильным
            if responses[0]['is_correct']:
                continue

            # Количество моделей с этим ответом
            model_count = len(responses)

            # Проверяем порог согласия
            agreement = model_count / len(run_data) if run_data else 0
            if agreement < agreement_threshold:
                continue

            # Проверяем минимальное количество моделей
            if model_count < min_models:
                continue

            # Получаем текст вопроса и варианты ответов
            question_text = responses[0].get('question_text', 'Текст недоступен')
            correct_indices = responses[0]['correct_indices']

            # Получаем информацию о моделях
            models_info = []
            for resp in responses:
                run_info = run_data.get(resp['run_id'], {})
                models_info.append(f"#{resp['run_id']} ({run_info.get('model', 'unknown')})")

            suspicious_questions.append({
                'question_id': q_id,
                'question_text': question_text,
                'wrong_answer': list(answer),
                'correct_answer': correct_indices,
                'models_count': model_count,
                'agreement': agreement,
                'models': models_info,
                'run_ids': [r['run_id'] for r in responses]
            })

    # Сортируем по количеству моделей (больше = важнее) и согласию
    suspicious_questions.sort(key=lambda x: (x['models_count'], x['agreement']), reverse=True)

    return suspicious_questions


def print_suspicious_questions(questions: List[Dict], run_ids: List[int]):
    """Выводит результаты в красивом формате"""

    if not questions:
        print("\n✅ Подозрительных вопросов не найдено!")
        print("   Все модели давали разные ответы на неправильные вопросы.")
        return

    print(f"\n{'='*80}")
    print(f"🔍 НАЙДЕНЫ ПОДОЗРИТЕЛЬНЫЕ ВОПРОСЫ")
    print(f"{'='*80}")
    print(f"📊 Проанализировано запусков: {len(run_ids)}")
    print(f"🔎 Найдено вопросов с одинаковыми ошибками: {len(questions)}")
    print(f"{'='*80}")

    for i, q in enumerate(questions, 1):
        # Эмодзи в зависимости от количества моделей
        if q['models_count'] >= 4:
            severity = "🚨"
        elif q['models_count'] >= 3:
            severity = "⚠️"
        else:
            severity = "📌"

        print(f"\n{severity} ВОПРОС #{q['question_id']} | Моделей с одинаковым ответом: {q['models_count']}/{len(run_ids)} ({q['agreement']*100:.0f}%)")

        # Текст вопроса (обрезаем если длинный)
        q_text = q['question_text'][:100] + "..." if len(q['question_text']) > 100 else q['question_text']
        print(f"   ❓ {q_text}")

        # Ответы
        print(f"   ✅ Правильный ответ: {q['correct_answer']}")
        print(f"   ❌ Ответ всех моделей: {q['wrong_answer']}")

        # Какие модели
        print(f"   🤖 Модели: {', '.join(q['models'])}")

    print(f"\n{'='*80}")
    print(f"💡 ИНТЕРПРЕТАЦИЯ:")
    print(f"   Чем больше моделей дали одинаковый НЕПРАВИЛЬНЫЙ ответ,")
    print(f"   тем выше вероятность, что вопрос сформулирован некорректно.")
    print(f"{'='*80}\n")


def export_to_json(questions: List[Dict], run_ids: List[int], filename: str):
    """Экспортирует результаты в JSON"""
    import json

    data = {
        'timestamp': datetime.now().isoformat(),
        'analyzed_runs': run_ids,
        'total_suspicious': len(questions),
        'questions': questions
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"💾 Экспорт сохранён: {filename}")


def analyze_question_detail(question_id: int, run_ids: List[int]):
    """Детальный анализ конкретного вопроса"""
    from database import get_run_results

    print(f"\n{'='*80}")
    print(f"🔬 ДЕТАЛЬНЫЙ АНАЛИЗ ВОПРОСА #{question_id}")
    print(f"{'='*80}")

    for run_id in run_ids:
        results = get_run_results(run_id)
        for r in results:
            if r['question_id'] == question_id:
                ai_indices = r['ai_selected_indices'] if r['ai_selected_indices'] else ""
                ai_answer = sorted(int(x) for x in ai_indices.split(',') if x)
                correct = sorted(int(x) for x in r['correct_indices'].split(','))

                print(f"\n🤖 Запуск #{run_id}")
                print(f"   Модель: {get_run_info(run_id)['model_name']}")
                print(f"   Вопрос: {r['question_text'][:80]}...")
                print(f"   Правильно: {correct}")
                print(f"   Ответ модели: {ai_answer}")
                print(f"   Результат: {'✅ ПРАВИЛЬНО' if ai_answer == correct else '❌ НЕПРАВИЛЬНО'}")

                # Показываем варианты ответов
                options = get_options_by_question_id(question_id)
                print(f"   📋 Варианты ответов:")
                for opt_idx, opt_text in options:
                    marker = "→" if opt_idx in ai_answer else ("✓" if opt_idx in correct else " ")
                    print(f"      {marker} [{opt_idx}] {opt_text[:60]}...")

    print(f"{'='*80}\n")


# ============================================================================
# 🎯 MAIN — ТОЧКА ВХОДА
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🔍 MedAITest — Поиск подозрительных вопросов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Гипотеза:
  Если несколько моделей при прохождении теста делают одинаковые
  ошибки (выбирают полностью совпадающий НЕПРАВИЛЬНЫЙ ответ),
  это может говорить о некорректно составленном вопросе.

Примеры:
  %(prog)s 1 2 3                        — сравнить запуски 1, 2, 3
  %(prog)s 1 2 3 7                     — добавить запуск 7
  %(prog)s 1 2 3 -t 0.5               — порог согласия 50%
  %(prog)s 1 2 3 --min-models 3        — минимум 3 модели с одинаковым ответом
  %(prog)s 1 2 3 --json bad_questions.json  — экспорт в JSON
  %(prog)s --detail 42 --runs 1 2 3   — детальный анализ вопроса 42
        """
    )

    # Основные аргументы
    parser.add_argument('run_ids', type=int, nargs='*', help='ID запусков для анализа')
    parser.add_argument('-t', '--threshold', type=float, default=1.0,
                        help='Порог согласия (0.0-1.0, по умолчанию 1.0 = все модели)')
    parser.add_argument('--min-models', type=int, default=None,
                        help='Минимальное количество моделей с одинаковым ответом')
    parser.add_argument('--json', type=str, help='Экспорт результатов в JSON')

    # Детальный анализ
    parser.add_argument('--detail', type=int, help='ID вопроса для детального анализа')
    parser.add_argument('--runs', type=int, nargs='*', help='ID запусков для детального анализа')

    args = parser.parse_args()

    # Детальный анализ вопроса
    if args.detail:
        runs_for_detail = args.runs if args.runs else [r['id'] for r in get_all_runs(limit=3)]
        analyze_question_detail(args.detail, runs_for_detail)
        sys.exit(0)

    # Основной анализ
    if not args.run_ids:
        # Показать доступные запуски
        print("📋 Доступные запуски:")
        runs = get_all_runs(limit=10)
        for r in runs:
            print(f"  #{r['id']} | {r['model_name']} | {r['timestamp']}")

        print(f"\n💡 Использование: python find_bad_questions.py <run_id_1> <run_id_2> ...")
        print(f"   Пример: python find_bad_questions.py 1 2 3")
        sys.exit(0)

    # Устанавливаем min_models
    min_models = args.min_models if args.min_models else len(args.run_ids)

    print(f"\n🔍 Поиск подозрительных вопросов...")
    print(f"   Запуски: {args.run_ids}")
    print(f"   Мин. моделей с одинаковым ответом: {min_models}")
    print(f"   Порог согласия: {args.threshold * 100:.0f}%")

    # Выполняем анализ
    suspicious = get_consistent_errors(
        args.run_ids,
        min_models=min_models,
        agreement_threshold=args.threshold
    )

    # Выводим результаты
    print_suspicious_questions(suspicious, args.run_ids)

    # Экспорт в JSON
    if args.json and suspicious:
        export_to_json(suspicious, args.run_ids, args.json)
