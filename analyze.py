#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze.py — Анализ результатов тестирования AI моделей
Умный подсчёт баллов с учётом частичных совпадений
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from config import DB_PATH

# Режимы подсчёта баллов
SCORING_MODES = {
    'strict': 'Строгий (0 или 1)',
    'partial': 'Частичный (пропорциональный)',
    'balanced': 'Сбалансированный (штраф за ошибки)',
    'jaccard': 'Индекс Жаккара'
}

def get_db_connection():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_score(
    ai_indices: List[int],
    correct_indices: List[int],
    mode: str = 'balanced'
) -> float:
    """
    Вычисляет оценку за ответ с учётом режима.

    Modes:
    - strict: 1.0 если полностью верно, иначе 0.0
    - partial: доля угаданных правильных ответов (|intersection| / |correct|)
    - balanced: |intersection| / (|correct| + |wrong|)
    - jaccard: |intersection| / |union|
    """
    ai_set = set(ai_indices)
    correct_set = set(correct_indices)

    if not correct_set:
        return 0.0

    intersection = ai_set & correct_set

    if mode == 'strict':
        return 1.0 if ai_set == correct_set else 0.0

    elif mode == 'partial':
        # Доля правильно выбранных ответов
        return len(intersection) / len(correct_set)

    elif mode == 'balanced':
        # Штраф за лишние выборы
        total = len(correct_set) + len(ai_set - correct_set)
        if total == 0:
            return 0.0
        return len(intersection) / total

    elif mode == 'jaccard':
        # Индекс Жаккара: пересечение / объединение
        union = ai_set | correct_set
        if not union:
            return 0.0
        return len(intersection) / len(union)

    return 0.0

def get_run_results(run_id: int) -> List[Dict]:
    """Получает результаты теста с дополнительной информацией"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, q.text as question_text, q.is_multiple, q.correct_indices
        FROM results r
        JOIN questions q ON r.question_id = q.id
        WHERE r.run_id = ?
        ORDER BY r.question_id
    """, (run_id,))

    results = []
    for row in cursor.fetchall():
        results.append({
            'result_id': row['id'],
            'run_id': row['run_id'],
            'question_id': row['question_id'],
            'question_text': row['question_text'],
            'is_multiple': bool(row['is_multiple']),
            'correct_indices': [int(x) for x in row['correct_indices'].split(',')],
            'ai_indices': [int(x) for x in row['ai_selected_indices'].split(',')] if row['ai_selected_indices'] else [],
            'original_score': row['score']
        })

    conn.close()
    return results

def get_all_runs() -> List[Dict]:
    """Получает список всех запусков"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_runs ORDER BY id DESC")
    runs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return runs

def analyze_run(
    run_id: int,
    scoring_mode: str = 'balanced',
    verbose: bool = True
) -> Dict:
    """
    Анализирует результаты запуска с выбранным режимом подсчёта.
    """
    results = get_run_results(run_id)

    if not results:
        return None

    # Получаем информацию о запуске
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_runs WHERE id = ?", (run_id,))
    run_info = dict(cursor.fetchone())
    conn.close()

    # Анализ по каждому вопросу
    analysis = []
    total_score = 0.0
    perfect_count = 0
    zero_count = 0
    partial_count = 0

    single_total = 0
    single_score = 0.0
    multiple_total = 0
    multiple_score = 0.0

    for r in results:
        score = calculate_score(r['ai_indices'], r['correct_indices'], scoring_mode)
        r['calculated_score'] = score
        total_score += score

        if score == 1.0:
            perfect_count += 1
        elif score == 0.0:
            zero_count += 1
        else:
            partial_count += 1

        if r['is_multiple']:
            multiple_total += 1
            multiple_score += score
        else:
            single_total += 1
            single_score += score

        # Определяем тип ошибки
        ai_set = set(r['ai_indices'])
        correct_set = set(r['correct_indices'])
        missed = correct_set - ai_set  # Пропущенные
        extra = ai_set - correct_set  # Лишние

        r['missed'] = list(missed)
        r['extra'] = list(extra)

        analysis.append(r)

    total = len(results)

    # Статистика
    stats = {
        'run_id': run_id,
        'model_name': run_info['model_name'],
        'timestamp': run_info['timestamp'],
        'scoring_mode': scoring_mode,
        'total_questions': total,
        'perfect': perfect_count,
        'partial': partial_count,
        'zero': zero_count,
        'total_score': total_score,
        'average_score': total_score / total if total > 0 else 0,
        'by_type': {
            'single': {
                'count': single_total,
                'score': single_score,
                'average': single_score / single_total if single_total > 0 else 0
            },
            'multiple': {
                'count': multiple_total,
                'score': multiple_score,
                'average': multiple_score / multiple_total if multiple_total > 0 else 0
            }
        },
        'results': analysis
    }

    if verbose:
        print_analysis(stats)

    return stats

def print_analysis(stats: Dict):
    """Красиво выводит результаты анализа"""
    print(f"\n{'='*70}")
    print(f"📊 АНАЛИЗ ЗАПУСКА #{stats['run_id']}")
    print(f"{'='*70}")
    print(f"🤖 Модель: {stats['model_name']}")
    print(f"📅 Дата: {stats['timestamp']}")
    print(f"📐 Режим: {SCORING_MODES.get(stats['scoring_mode'], stats['scoring_mode'])}")
    print()

    print(f"📈 ИТОГО:")
    print(f"   Вопросов: {stats['total_questions']}")
    print(f"   ✅ Идеально: {stats['perfect']} ({stats['perfect']/stats['total_questions']*100:.1f}%)")
    print(f"   🔶 Частично: {stats['partial']} ({stats['partial']/stats['total_questions']*100:.1f}%)")
    print(f"   ❌ Неверно: {stats['zero']} ({stats['zero']/stats['total_questions']*100:.1f}%)")
    print(f"   🏆 Средний балл: {stats['average_score']:.3f}")
    print()

    print(f"📋 ПО ТИПУ ВОПРОСОВ:")
    single = stats['by_type']['single']
    multiple = stats['by_type']['multiple']
    print(f"   🔘 С одним ответом ({single['count']} шт): {single['average']:.3f}")
    print(f"   🔀 С несколькими ответами ({multiple['count']} шт): {multiple['average']:.3f}")
    print(f"{'='*70}")

def compare_runs(run_ids: List[int], scoring_mode: str = 'balanced') -> List[Dict]:
    """Сравнивает несколько запусков"""
    results = []
    for run_id in run_ids:
        stats = analyze_run(run_id, scoring_mode=scoring_mode, verbose=False)
        if stats:
            results.append(stats)

    if not results:
        print("❌ Нет данных для сравнения")
        return []

    print(f"\n{'='*80}")
    print(f"📊 СРАВНЕНИЕ ЗАПУСКОВ (режим: {SCORING_MODES.get(scoring_mode, scoring_mode)})")
    print(f"{'='*80}")
    print(f"{'ID':<5} {'Модель':<30} {'Балл':>8} {'Идеально':>10} {'Частично':>10} {'Ошибки':>8}")
    print(f"{'-'*80}")

    # Сортировка по среднему баллу
    results.sort(key=lambda x: x['average_score'], reverse=True)

    for r in results:
        name = r['model_name'][:28]
        print(f"{r['run_id']:<5} {name:<30} {r['average_score']:>8.3f} {r['perfect']:>9} {r['partial']:>9} {r['zero']:>7}")

    print(f"{'-'*80}")
    return results

def find_hard_questions(run_ids: List[int] = None, limit: int = 10) -> List[Dict]:
    """Находит вопросы на которые модель(и) чаще всего отвечала неверно"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if run_ids:
        placeholders = ','.join('?' * len(run_ids))
        cursor.execute(f"""
            SELECT r.question_id, q.text, q.is_multiple, q.correct_indices,
                   COUNT(*) as attempts,
                   SUM(CASE WHEN r.score < 1.0 THEN 1 ELSE 0 END) as failures
            FROM results r
            JOIN questions q ON r.question_id = q.id
            WHERE r.run_id IN ({placeholders})
            GROUP BY r.question_id
            ORDER BY failures DESC, attempts DESC
            LIMIT ?
        """, run_ids + [limit])
    else:
        cursor.execute("""
            SELECT r.question_id, q.text, q.is_multiple, q.correct_indices,
                   COUNT(*) as attempts,
                   SUM(CASE WHEN r.score < 1.0 THEN 1 ELSE 0 END) as failures
            FROM results r
            JOIN questions q ON r.question_id = q.id
            GROUP BY r.question_id
            ORDER BY failures DESC, attempts DESC
            LIMIT ?
        """, (limit,))

    hard_questions = []
    for row in cursor.fetchall():
        hard_questions.append({
            'question_id': row['question_id'],
            'text': row['text'][:80] + '...' if len(row['text']) > 80 else row['text'],
            'is_multiple': bool(row['is_multiple']),
            'correct_indices': row['correct_indices'],
            'attempts': row['attempts'],
            'failures': row['failures'],
            'failure_rate': row['failures'] / row['attempts'] if row['attempts'] > 0 else 0
        })

    conn.close()

    print(f"\n{'='*70}")
    print(f"🔴 САМЫЕ СЛОЖНЫЕ ВОПРОСЫ (топ {len(hard_questions)})")
    print(f"{'='*70}")
    for i, q in enumerate(hard_questions, 1):
        print(f"\n{i}. Вопрос #{q['question_id']} ({q['attempts']} попыток, {q['failures']} ошибок)")
        print(f"   📝 {q['text']}")
        print(f"   ❌ Неудач: {q['failure_rate']*100:.0f}%")

    return hard_questions

def list_runs():
    """Показывает список всех запусков"""
    runs = get_all_runs()

    if not runs:
        print("❌ Нет сохранённых запусков")
        return []

    print(f"\n📋 ВСЕ ЗАПУСКИ ({len(runs)} шт)")
    print("=" * 70)
    for run in runs:
        print(f"  #{run['id']}: {run['model_name']} — {run['timestamp']}")

    print("=" * 70)
    return runs

def show_detailed_results(run_id: int, scoring_mode: str = 'balanced', limit: int = None):
    """Показывает детальные результаты с объяснением оценок"""
    stats = analyze_run(run_id, scoring_mode=scoring_mode, verbose=False)

    if not stats:
        print(f"❌ Нет результатов для запуска #{run_id}")
        return

    print(f"\n{'='*80}")
    print(f"📋 ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ЗАПУСКА #{run_id}")
    print(f"{'='*80}")

    results = stats['results']
    if limit:
        results = results[:limit]

    for r in results:
        score = r['calculated_score']
        is_multiple = r['is_multiple']

        if score == 1.0:
            status = "✅"
        elif score == 0.0:
            status = "❌"
        else:
            status = "🔶"

        print(f"\n{status} Вопрос #{r['question_id']} (балл: {score:.2f})")
        print(f"   📝 {r['question_text'][:70]}...")

        if is_multiple:
            correct = r['correct_indices']
            ai = r['ai_indices']
            missed = r['missed']
            extra = r['extra']

            print(f"   Ожидалось: {correct}")
            print(f"   Получено:  {ai}")

            if missed:
                print(f"   ❌ Пропущено: {missed}")
            if extra:
                print(f"   ⚠️ Лишние: {extra}")
        else:
            expected = r['correct_indices'][0] if r['correct_indices'] else "?"
            got = r['ai_indices'][0] if r['ai_indices'] else "?"
            print(f"   Ожидалось: {expected}, получено: {got}")

    if limit and len(stats['results']) > limit:
        print(f"\n... и ещё {len(stats['results']) - limit} вопросов")
        print(f"💡 Используйте: python analyze.py {run_id} --all для полного вывода")

    print(f"\n{'='*80}")
    print(f"📊 Итого: {stats['average_score']:.3f} баллов")

def export_to_json(run_id: int, filepath: str = None, scoring_mode: str = 'balanced'):
    """Экспортирует результаты в JSON"""
    stats = analyze_run(run_id, scoring_mode=scoring_mode, verbose=False)

    if not stats:
        return False

    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"analysis_run_{run_id}_{timestamp}.json"

    # Сериализуем для JSON
    export_data = {
        'run_id': stats['run_id'],
        'model_name': stats['model_name'],
        'timestamp': stats['timestamp'],
        'scoring_mode': stats['scoring_mode'],
        'summary': {
            'total_questions': stats['total_questions'],
            'perfect_count': stats['perfect'],
            'partial_count': stats['partial'],
            'zero_count': stats['zero'],
            'average_score': round(stats['average_score'], 4),
            'by_type': {
                'single_answer': {
                    'count': stats['by_type']['single']['count'],
                    'average': round(stats['by_type']['single']['average'], 4)
                },
                'multiple_answer': {
                    'count': stats['by_type']['multiple']['count'],
                    'average': round(stats['by_type']['multiple']['average'], 4)
                }
            }
        },
        'results': [
            {
                'question_id': r['question_id'],
                'is_multiple': r['is_multiple'],
                'correct_indices': r['correct_indices'],
                'ai_indices': r['ai_indices'],
                'score': round(r['calculated_score'], 4),
                'missed': r.get('missed', []),
                'extra': r.get('extra', [])
            }
            for r in stats['results']
        ]
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Результаты экспортированы в: {filepath}")
    return True

# === CLI ===
if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        print("""
🔍 ANALYZER — Анализ результатов тестирования AI моделей

Использование:
  python analyze.py                      — показать список запусков
  python analyze.py <id>                — анализ запуска (сбалансированный)
  python analyze.py <id> --detailed     — детальные результаты
  python analyze.py <id> --json [file]  — экспорт в JSON
  python analyze.py <id> --mode strict  — режим: strict/partial/balanced/jaccard
  python analyze.py compare <id1> <id2> [id3...] — сравнить запуски
  python analyze.py hard                — топ сложных вопросов
  python analyze.py hard <id1> <id2>    — сложные вопросы для конкретных запусков

Примеры:
  python analyze.py 1
  python analyze.py 1 --detailed
  python analyze.py 1 --mode partial
  python analyze.py compare 1 2 3
  python analyze.py hard 1 2
""")
    else:
        args = sys.argv[1:]

        if args[0] == 'compare':
            # Сравнение запусков
            if len(args) < 2:
                print("❌ Укажите ID запусков: compare <id1> <id2> ...")
            else:
                run_ids = [int(x) for x in args[1:]]
                mode = 'balanced'
                if '--mode' in args:
                    idx = args.index('--mode')
                    if idx + 1 < len(args):
                        mode = args[idx + 1]
                compare_runs(run_ids, scoring_mode=mode)

        elif args[0] == 'hard':
            # Сложные вопросы
            run_ids = None
            if len(args) > 1:
                try:
                    run_ids = [int(x) for x in args[1:] if x.isdigit()]
                except:
                    pass
            find_hard_questions(run_ids=run_ids)

        elif args[0].isdigit():
            # Анализ конкретного запуска
            run_id = int(args[0])

            if '--detailed' in args or '-d' in args:
                show_detailed_results(run_id)

            elif '--json' in args or '--export' in args:
                idx = args.index('--json') if '--json' in args else args.index('--export')
                filepath = args[idx + 1] if idx + 1 < len(args) and not args[idx + 1].startswith('--') else None
                mode = 'balanced'
                if '--mode' in args:
                    idx = args.index('--mode')
                    if idx + 1 < len(args):
                        mode = args[idx + 1]
                export_to_json(run_id, filepath, scoring_mode=mode)

            else:
                mode = 'balanced'
                if '--mode' in args:
                    idx = args.index('--mode')
                    if idx + 1 < len(args):
                        mode = args[idx + 1]
                analyze_run(run_id, scoring_mode=mode)

        else:
            list_runs()
