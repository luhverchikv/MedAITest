# analyze.py
"""
📊 MedAITest — Анализ результатов тестирования
Режим оценки: Индекс Жаккара (Jaccard Similarity Coefficient)
"""

import sys
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from database import get_run_results, get_run_info, get_all_runs
from config import DB_PATH


# ============================================================================
# 🧮 ИНДЕКС ЖАККАРА — ЕДИНСТВЕННАЯ МЕТРИКА
# ============================================================================

def jaccard_score(ai_indices: list[int], correct_indices: list[int]) -> float:
    """
    Вычисляет индекс Жаккара для оценки ответа ИИ.
    
    Формула:
        J(A, C) = |A ∩ C| / |A ∪ C|
    
    Где:
        A — множество ответов ИИ
        C — множество правильных ответов
        |A ∩ C| — количество совпадений (true positives)
        |A ∪ C| — количество уникальных элементов в объединении
    
    Возвращает:
        float от 0.0 (полное несовпадение) до 1.0 (полное совпадение)
    """
    # Преобразуем в множества для операций
    A = set(ai_indices)
    C = set(correct_indices)
    
    # Пустые множества = идеальное совпадение (оба ничего не выбрали)
    if not A and not C:
        return 1.0
    
    # Считаем пересечение и объединение
    intersection = len(A & C)  # |A ∩ C|
    union = len(A | C)         # |A ∪ C|
    
    # Избегаем деления на ноль (если объединение пусто, но это уже обработано выше)
    if union == 0:
        return 0.0
    
    return intersection / union


# ============================================================================
# 📊 АНАЛИЗ ОДНОГО ЗАПУСКА
# ============================================================================

def analyze_run(run_id: int, detailed: bool = False) -> dict:
    """
    Анализирует результаты запуска с использованием индекса Жаккара.
    
    Args:
        run_id: ID запуска в базе данных
        detailed: Если True, показывает детали по каждому вопросу
    
    Returns:
        dict со статистикой анализа
    """
    # Загружаем информацию о запуске
    run_info = get_run_info(run_id)
    if not run_info:
        print(f"❌ Запуск #{run_id} не найден в базе {DB_PATH}")
        return {}
    
    # Загружаем результаты по вопросам
    results = get_run_results(run_id)
    if not results:
        print(f"⚠️ Нет результатов для запуска #{run_id}")
        return {"run_id": run_id, "error": "no_results"}
    
    # 🔄 Считаем Jaccard для каждого вопроса
    scores = []
    question_details = []
    
    for r in results:
        ai_indices = [int(x) for x in r['ai_selected_indices'].split(',')] if r['ai_selected_indices'] else []
        correct_indices = [int(x) for x in r['correct_indices'].split(',')]
        
        # Вычисляем индекс Жаккара
        score = jaccard_score(ai_indices, correct_indices)
        scores.append(score)
        
        # Сохраняем детали для отчёта
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
    
    # 📈 Сводная статистика
    n = len(scores)
    stats = {
        'run_id': run_id,
        'model': run_info['model_name'],
        'timestamp': run_info.get('timestamp', 'unknown'),
        'total_questions': n,
        
        # Основные метрики Jaccard
        'mean_jaccard': sum(scores) / n if n > 0 else 0,
        'median_jaccard': sorted(scores)[n // 2] if n > 0 else 0,
        'min_jaccard': min(scores) if scores else 0,
        'max_jaccard': max(scores) if scores else 0,
        
        # Распределение по диапазонам
        'perfect': sum(1 for s in scores if s == 1.0),           # J = 1.0
        'high': sum(1 for s in scores if 0.67 <= s < 1.0),       # J ≥ 2/3
        'medium': sum(1 for s in scores if 0.33 <= s < 0.67),    # 1/3 ≤ J < 2/3
        'low': sum(1 for s in scores if 0 < s < 0.33),           # 0 < J < 1/3
        'zero': sum(1 for s in scores if s == 0.0),              # J = 0
        
        # По типу вопросов
        'single_questions': [s for i, s in enumerate(scores) if not question_details[i]['is_multiple']],
        'multiple_questions': [s for i, s in enumerate(scores) if question_details[i]['is_multiple']],
        
        # Детали (если нужно)
        'details': question_details if detailed else None
    }
    
    # Вычисляем средние по типам вопросов
    stats['single_avg'] = sum(stats['single_questions']) / len(stats['single_questions']) if stats['single_questions'] else 0
    stats['multiple_avg'] = sum(stats['multiple_questions']) / len(stats['multiple_questions']) if stats['multiple_questions'] else 0
    
    return stats


# ============================================================================
# 🖨️ ВЫВОД ОТЧЁТА
# ============================================================================

def print_analysis(stats: dict, detailed: bool = False):
    """Выводит отчёт по анализу в консоль"""
    
    if not stats or 'error' in stats:
        return
    
    print(f"\n{'='*70}")
    print(f"📊 АНАЛИЗ ЗАПУСКА #{stats['run_id']} | Индекс Жаккара")
    print(f"{'='*70}")
    print(f"🤖 Модель: {stats['model']}")
    print(f"📅 Дата: {stats['timestamp']}")
    print(f"📐 Метрика: J(A,C) = |A∩C| / |A∪C|")
    print(f"{'-'*70}")
    
    # 📈 Основные результаты
    n = stats['total_questions']
    print(f"📋 Всего вопросов: {n}")
    print(f"\n🎯 СРЕДНИЙ ИНДЕКС ЖАККАРА: {stats['mean_jaccard']:.3f}")
    print(f"   Медиана: {stats['median_jaccard']:.3f}")
    print(f"   Диапазон: [{stats['min_jaccard']:.3f} — {stats['max_jaccard']:.3f}]")
    
    # 📊 Распределение
    print(f"\n📈 РАСПРЕДЕЛЕНИЕ РЕЗУЛЬТАТОВ:")
    print(f"   ✅ Идеально (J=1.00):     {stats['perfect']:3d} ({stats['perfect']/n*100:5.1f}%)")
    print(f"   🔷 Высокий (J≥0.67):      {stats['high']:3d} ({stats['high']/n*100:5.1f}%)")
    print(f"   🔶 Средний (0.33≤J<0.67): {stats['medium']:3d} ({stats['medium']/n*100:5.1f}%)")
    print(f"   🔸 Низкий (0<J<0.33):     {stats['low']:3d} ({stats['low']/n*100:5.1f}%)")
    print(f"   ❌ Нулевой (J=0.00):      {stats['zero']:3d} ({stats['zero']/n*100:5.1f}%)")
    
    # 🔘 По типу вопросов
    if stats['single_questions'] or stats['multiple_questions']:
        print(f"\n📋 ПО ТИПУ ВОПРОСОВ:")
        if stats['single_questions']:
            sn = len(stats['single_questions'])
            sa = sum(stats['single_questions']) / sn
            print(f"   🔘 С одним ответом ({sn:2d} шт): средний J = {sa:.3f}")
        if stats['multiple_questions']:
            mn = len(stats['multiple_questions'])
            ma = sum(stats['multiple_questions']) / mn
            print(f"   🔀 С несколькими ({mn:2d} шт): средний J = {ma:.3f}")
    
    # 🔍 Детали по вопросам (если запрошено)
    if detailed and stats['details']:
        print(f"\n{'='*70}")
        print(f"🔍 ДЕТАЛИ ПО ВОПРОСАМ (первые 20):")
        print(f"{'='*70}")
        
        for q in stats['details'][:20]:
            status = "✅" if q['jaccard'] == 1.0 else "❌" if q['jaccard'] == 0 else "🔶"
            print(f"\n{status} Q#{q['question_id']:3d} | J={q['jaccard']:.2f} | {q['question_text']}...")
            print(f"      Правильно: {q['correct']} | ИИ: {q['ai_answer']}")
            if q['jaccard'] < 1.0:
                inter = q['intersection']
                union = q['union']
                print(f"      ∩={inter}, ∪={union} → {inter}/{union} = {q['jaccard']:.2f}")
        
        if len(stats['details']) > 20:
            print(f"\n   ... и ещё {len(stats['details']) - 20} вопросов")
    
    print(f"\n{'='*70}\n")


# ============================================================================
# 🔄 СРАВНЕНИЕ НЕСКОЛЬКИХ ЗАПУСКОВ
# ============================================================================

def compare_runs(run_ids: list[int]):
    """Сравнивает несколько запусков по индексу Жаккара"""
    
    print(f"\n🔬 СРАВНЕНИЕ ЗАПУСКОВ | Индекс Жаккара")
    print(f"{'='*70}")
    print(f"{'Запуск':<8} {'Модель':<22} {'Вопросов':>9} {'Средний J':>12} {'Медиана':>10}")
    print(f"{'-'*70}")
    
    results = []
    
    for run_id in run_ids:
        stats = analyze_run(run_id)
        if stats and 'error' not in stats:
            results.append(stats)
            model_short = (stats['model'] or 'unknown')[:21]
            print(f"#{run_id:<6} {model_short:<22} {stats['total_questions']:>9} {stats['mean_jaccard']:>12.3f} {stats['median_jaccard']:>10.3f}")
    
    print(f"{'='*70}")
    
    if results:
        # Лучший по среднему Jaccard
        best = max(results, key=lambda x: x['mean_jaccard'])
        print(f"🏆 Лучший результат: #{best['run_id']} — J = {best['mean_jaccard']:.3f}")
    
    print()
    return results


# ============================================================================
# 🔍 ПОИСК СЛОЖНЫХ ВОПРОСОВ
# ============================================================================

def find_hard_questions(run_ids: list[int] = None, threshold: float = 0.5):
    """Находит вопросы, где индекс Жаккара ниже порога"""
    
    if run_ids is None:
        # Берём все запуски
        all_runs = get_all_runs()
        run_ids = [r['id'] for r in all_runs[:5]]  # Последние 5
    
    hard_questions = []
    
    for run_id in run_ids:
        stats = analyze_run(run_id, detailed=True)
        if stats and stats.get('details'):
            for q in stats['details']:
                if q['jaccard'] < threshold:
                    hard_questions.append({
                        'run_id': run_id,
                        'model': stats['model'],
                        **q
                    })
    
    # Сортируем по возрастанию Jaccard (самые сложные первые)
    hard_questions.sort(key=lambda x: x['jaccard'])
    
    if hard_questions:
        print(f"\n🔍 СЛОЖНЫЕ ВОПРОСЫ (J < {threshold})")
        print(f"{'='*70}")
        
        for i, q in enumerate(hard_questions[:15], 1):  # Показываем топ-15
            print(f"{i:2d}. [#{q['run_id']}] J={q['jaccard']:.2f} | {q['question_text'][:60]}...")
            print(f"    Правильно: {q['correct']} | ИИ: {q['ai_answer']} | ∩={q['intersection']}, ∪={q['union']}")
        
        if len(hard_questions) > 15:
            print(f"\n   ... и ещё {len(hard_questions) - 15}")
        print(f"{'='*70}\n")
    else:
        print(f"\n✅ Нет вопросов с J < {threshold} в выбранных запусках")
    
    return hard_questions


# ============================================================================
# 🎯 MAIN — ТОЧКА ВХОДА
# ============================================================================
# ============================================================================
# 🎯 MAIN — ИСПРАВЛЕННЫЙ ARGPARSE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="📊 MedAITest Analysis — Индекс Жаккара",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  %(prog)s --run 1                    — анализ запуска #1
  %(prog)s --run 1 -d                 — с деталями по вопросам
  %(prog)s compare 1 2 3              — сравнение трёх запусков
  %(prog)s hard                       — найти сложные вопросы (J < 0.5)
  %(prog)s hard --runs 1 2 -t 0.3     — сложные вопросы в запусках 1,2
        """
    )
    
    # 🔹 Используем ФЛАГ --run вместо позиционного аргумента
    parser.add_argument('--run', '-r', type=int, help='ID запуска для анализа')
    parser.add_argument('-d', '--detailed', action='store_true', help='Детали по вопросам')
    parser.add_argument('--json', type=str, help='Экспорт в JSON-файл')
    
    # Субкоманды
    subparsers = parser.add_subparsers(dest='command', help='Дополнительные команды')
    
    # compare: сравнение запусков
    cmp_p = subparsers.add_parser('compare', help='Сравнить несколько запусков')
    cmp_p.add_argument('runs', type=int, nargs='+', help='ID запусков для сравнения')
    
    # hard: поиск сложных вопросов
    hard_p = subparsers.add_parser('hard', help='Найти вопросы с низким Jaccard')
    hard_p.add_argument('--runs', '-R', type=int, nargs='*', help='ID запусков (опционально)')
    hard_p.add_argument('-t', '--threshold', type=float, default=0.5, help='Порог Jaccard')
    
    args = parser.parse_args()
    
    # 🔹 Обработка команд
    if args.command == 'compare':
        if not hasattr(args, 'runs') or not args.runs:
            print("❌ Укажите ID запусков: python analyze.py compare 1 2 3")
        else:
            compare_runs(args.runs)
            
    elif args.command == 'hard':
        runs = args.runs if hasattr(args, 'runs') and args.runs else None
        find_hard_questions(runs, threshold=args.threshold)
        
    elif args.run:
        # Анализ одного запуска по флагу --run
        stats = analyze_run(args.run, detailed=args.detailed)
        print_analysis(stats, detailed=args.detailed)
        
        # Экспорт в JSON
        if args.json and stats and 'error' not in stats:
            import json
            export = {k: v for k, v in stats.items() if k != 'details' or args.detailed}
            with open(args.json, 'w', encoding='utf-8') as f:
                json.dump(export, f, ensure_ascii=False, indent=2)
            print(f"💾 Экспорт: {args.json}")
            
    else:
        # Нет аргументов — показать справку и последние запуски
        print("📊 MedAITest Analysis — Индекс Жаккара")
        print("Использование:")
        print("  python analyze.py --run <ID> [-d] [--json file]")
        print("  python analyze.py compare <ID1> <ID2> ...")
        print("  python analyze.py hard [--runs ID1 ID2] [-t порог]")
        print("  python analyze.py --help")
        
        # Показать последние запуски
        runs = get_all_runs(limit=5)
        if runs:
            print(f"\n📋 Последние запуски:")
            for r in runs:
                print(f"  #{r['id']} | {r['model_name']} | {r['timestamp']}")
            print(f"\n💡 Пример: python analyze.py --run {runs[0]['id']}")

