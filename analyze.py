# analyze.py
"""
MedAITest — Анализ результатов тестирования
Поддержка фильтрации по тестам
"""
import sys
from pathlib import Path
from datetime import datetime

from database import (
    init_db, get_run_results, get_run_info, get_all_runs,
    get_run_summary, get_test_by_id, get_all_tests, get_runs_by_test,
    get_questions_by_test, get_options_by_question_id
)
from config import DB_PATH


# ============================================================================
# 🧮 ИНДЕКС ЖАККАРА
# ============================================================================
def jaccard_score(ai_indices: list, correct_indices: list) -> float:
    """
    Вычисляет индекс Жаккара.
    J(A, C) = |A ∩ C| / |A ∪ C|
    """
    A = set(ai_indices)
    C = set(correct_indices)

    if not A and not C:
        return 1.0

    intersection = len(A & C)
    union = len(A | C)

    if union == 0:
        return 0.0

    return intersection / union


# ============================================================================
# 📊 АНАЛИЗ ОДНОГО ЗАПУСКА
# ============================================================================
def analyze_run(run_id: int, detailed: bool = False) -> dict:
    """Анализирует результаты запуска"""
    run_info = get_run_info(run_id)
    if not run_info:
        print(f"❌ Запуск #{run_id} не найден")
        return {}

    results = get_run_results(run_id)
    if not results:
        print(f"⚠️ Нет результатов для запуска #{run_id}")
        return {"run_id": run_id, "error": "no_results"}

    # Информация о тесте
    test = get_test_by_id(run_info['test_id']) if run_info.get('test_id') else None

    # Считаем Jaccard для каждого вопроса
    scores = []
    question_details = []

    for r in results:
        ai_indices = [int(x) for x in r['ai_selected_indices'].split(',')] if r['ai_selected_indices'] else []
        correct_indices = [int(x) for x in r['correct_indices'].split(',')]

        score = jaccard_score(ai_indices, correct_indices)
        scores.append(score)

        question_details.append({
            'question_id': r['question_id'],
            'question_text': r['question_text'][:80],
            'is_multiple': r['is_multiple'],
            'correct': correct_indices,
            'ai_answer': ai_indices,
            'jaccard': score,
            'intersection': len(set(ai_indices) & set(correct_indices)),
            'union': len(set(ai_indices) | set(correct_indices))
        })

    # Статистика
    n = len(scores)
    stats = {
        'run_id': run_id,
        'test_id': run_info.get('test_id'),
        'test_name': run_info.get('test_name') or (test['name'] if test else 'Unknown'),
        'model': run_info['model_name'],
        'timestamp': run_info['timestamp'],
        'total_questions': n,
        'mean_jaccard': sum(scores) / n if n > 0 else 0,
        'median_jaccard': sorted(scores)[n // 2] if n > 0 else 0,
        'min_jaccard': min(scores) if scores else 0,
        'max_jaccard': max(scores) if scores else 0,
        'perfect': sum(1 for s in scores if s == 1.0),
        'high': sum(1 for s in scores if 0.67 <= s < 1.0),
        'medium': sum(1 for s in scores if 0.33 <= s < 0.67),
        'low': sum(1 for s in scores if 0 < s < 0.33),
        'zero': sum(1 for s in scores if s == 0.0),
        'details': question_details if detailed else None
    }

    return stats


def print_analysis(stats: dict, detailed: bool = False):
    """Выводит отчёт в консоль"""
    if not stats or 'error' in stats:
        return

    print(f"\n{'='*70}")
    print(f"📊 АНАЛИЗ ЗАПУСКА #{stats['run_id']} | Индекс Жаккара")
    print(f"{'='*70}")
    print(f"📚 Тест: {stats['test_name']}")
    print(f"🤖 Модель: {stats['model']}")
    print(f"📅 Дата: {stats['timestamp']}")
    print(f"{'-'*70}")

    n = stats['total_questions']
    print(f"📋 Всего вопросов: {n}")
    print(f"\n🎯 СРЕДНИЙ ИНДЕКС ЖАККАРА: {stats['mean_jaccard']:.3f}")
    print(f"   Медиана: {stats['median_jaccard']:.3f}")
    print(f"   Диапазон: [{stats['min_jaccard']:.3f} — {stats['max_jaccard']:.3f}]")

    # Распределение
    print(f"\n📈 РАСПРЕДЕЛЕНИЕ РЕЗУЛЬТАТОВ:")
    print(f"   ✅ Идеально (J=1.00):  {stats['perfect']:3d} ({stats['perfect']/n*100:5.1f}%)")
    print(f"   🔷 Высокий (J≥0.67):   {stats['high']:3d} ({stats['high']/n*100:5.1f}%)")
    print(f"   🔶 Средний (0.33≤J<0.67): {stats['medium']:3d} ({stats['medium']/n*100:5.1f}%)")
    print(f"   🔸 Низкий (0<J<0.33): {stats['low']:3d} ({stats['low']/n*100:5.1f}%)")
    print(f"   ❌ Нулевой (J=0.00):  {stats['zero']:3d} ({stats['zero']/n*100:5.1f}%)")

    # Детали
    if detailed and stats['details']:
        print(f"\n{'─'*70}")
        print(f"📝 ДЕТАЛИ ПО ВОПРОСАМ:")
        for i, q in enumerate(stats['details'][:20], 1):
            status = "✅" if q['jaccard'] == 1.0 else "🔷" if q['jaccard'] >= 0.67 else "🔶" if q['jaccard'] >= 0.33 else "❌"
            print(f"{i:3d}. {status} J={q['jaccard']:.2f} {q['question_text'][:50]}...")

    print(f"\n{'='*70}\n")


# ============================================================================
# 🔄 СРАВНЕНИЕ ЗАПУСКОВ
# ============================================================================
def compare_runs(run_ids: list, test_id: int = None):
    """Сравнивает несколько запусков"""
    print(f"\n🔬 СРАВНЕНИЕ ЗАПУСКОВ | Индекс Жаккара")
    print(f"{'='*80}")
    print(f"{'Запуск':<8} {'Тест':<20} {'Модель':<15} {'J сред':>10} {'Медиана':>10}")
    print(f"{'-'*80}")

    results = []
    for run_id in run_ids:
        stats = analyze_run(run_id)
        if stats and 'error' not in stats:
            results.append(stats)
            test_name = (stats['test_name'] or 'Unknown')[:19]
            model = (stats['model'] or 'unknown')[:14]
            print(f"#{run_id:<6} {test_name:<20} {model:<15} {stats['mean_jaccard']:>10.3f} {stats['median_jaccard']:>10.3f}")

    print(f"{'='*80}")
    if results:
        best = max(results, key=lambda x: x['mean_jaccard'])
        print(f"🏆 Лучший: #{best['run_id']} — J = {best['mean_jaccard']:.3f}")

    return results


# ============================================================================
# 📋 СПИСОК ЗАПУСКОВ
# ============================================================================
def list_runs(test_id: int = None, limit: int = 10):
    """Показывает список запусков"""
    if test_id:
        runs = get_runs_by_test(test_id, limit=limit)
        test = get_test_by_id(test_id)
        print(f"\n📋 Запуски теста '{test['name']}' (последние {limit}):")
    else:
        runs = get_all_runs(limit=limit)
        print(f"\n📋 Последние запуски ({limit}):")

    if not runs:
        print("   Нет запусков")
        return

    print(f"{'='*80}")
    print(f"{'ID':<6} {'Тест':<20} {'Модель':<15} {'Результат':>12} {'Дата':<20}")
    print(f"{'-'*80}")

    for r in runs:
        test_name = (r.get('test_name') or 'Unknown')[:19]
        model = (r['model_name'] or 'unknown')[:14]
        pct = f"{r['score_percentage']:.1f}%" if r['score_percentage'] else "—"
        date = r['timestamp'][:19] if r['timestamp'] else "—"
        print(f"#{r['id']:<5} {test_name:<20} {model:<15} {pct:>12} {date:<20}")

    print(f"{'='*80}")


# ============================================================================
# 🔍 ПОИСК СЛОЖНЫХ ВОПРОСОВ
# ============================================================================
def find_hard_questions(run_ids: list = None, threshold: float = 0.5, test_id: int = None):
    """Находит вопросы с низким Jaccard"""
    if not run_ids:
        if test_id:
            runs = get_runs_by_test(test_id)
        else:
            runs = get_all_runs(limit=5)
        run_ids = [r['id'] for r in runs]

    hard_questions = []

    for run_id in run_ids:
        stats = analyze_run(run_id, detailed=True)
        if stats and stats.get('details'):
            for q in stats['details']:
                if q['jaccard'] < threshold:
                    hard_questions.append({
                        'run_id': run_id,
                        'test_name': stats['test_name'],
                        'model': stats['model'],
                        **q
                    })

    hard_questions.sort(key=lambda x: x['jaccard'])

    if hard_questions:
        print(f"\n🔍 СЛОЖНЫЕ ВОПРОСЫ (J < {threshold})")
        print(f"{'='*80}")
        for i, q in enumerate(hard_questions[:15], 1):
            print(f"{i:2d}. [#{q['run_id']}] J={q['jaccard']:.2f} | {q['question_text'][:50]}...")
            print(f"    Правильно: {q['correct']} | ИИ: {q['ai_answer']}")
        print(f"{'='*80}\n")
    else:
        print(f"\n✅ Нет вопросов с J < {threshold}")

    return hard_questions


# ============================================================================
# 🎯 MAIN — ТОЧКА ВХОДА
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="📊 MedAITest Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s --list                    — список запусков
  %(prog)s --list --test 1         — запуски конкретного теста
  %(prog)s --run 1                  — анализ запуска #1
  %(prog)s --run 1 -d               — с деталями
  %(prog)s compare 1 2 3           — сравнение запусков
  %(prog)s hard --test 1           — сложные вопросы теста #1
        """
    )

    # Список запусков
    parser.add_argument('--list', action='store_true', help='Список запусков')
    parser.add_argument('--test', type=int, metavar='ID', help='Фильтр по тесту')

    # Анализ
    parser.add_argument('--run', '-r', type=int, help='ID запуска для анализа')
    parser.add_argument('-d', '--detailed', action='store_true', help='Детали')
    parser.add_argument('--json', type=str, help='Экспорт в JSON')

    # Сравнение
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    cmp_p = subparsers.add_parser('compare', help='Сравнить запуски')
    cmp_p.add_argument('runs', type=int, nargs='+', help='ID запусков')

    hard_p = subparsers.add_parser('hard', help='Сложные вопросы')
    hard_p.add_argument('--runs', type=int, nargs='*', help='ID запусков')
    hard_p.add_argument('-t', '--threshold', type=float, default=0.5)
    hard_p.add_argument('--test', type=int, help='Фильтр по тесту')

    args = parser.parse_args()

    init_db()

    # Список запусков
    if args.list:
        list_runs(test_id=args.test)

    # Анализ запуска
    elif args.run:
        stats = analyze_run(args.run, detailed=args.detailed)
        print_analysis(stats, detailed=args.detailed)

        if args.json and stats and 'error' not in stats:
            import json
            export = {k: v for k, v in stats.items() if k != 'details' or args.detailed}
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(export, f, ensure_ascii=False, indent=2)
            print(f"💾 Экспорт: {args.json}")

    # Сравнение
    elif args.command == 'compare':
        compare_runs(args.runs)

    # Сложные вопросы
    elif args.command == 'hard':
        find_hard_questions(run_ids=args.runs, threshold=args.threshold, test_id=args.test)

    else:
        # Показываем помощь и список
        print("📊 MedAITest Analysis")
        print("\nИспользование:")
        print("  python analyze.py --list")
        print("  python analyze.py --run <ID> [-d]")
        print("  python analyze.py compare <ID1> <ID2> ...")
        print("  python analyze.py hard [--test ID]")
        print("\n📚 Доступные тесты:")
        tests = get_all_tests()
        for t in tests[:5]:
            print(f"  #{t['id']} | {t['name']}")
        print("\n📋 Последние запуски:")
        list_runs(limit=5)
