#!/usr/bin/env python3
"""
MedAITest — Генератор графика прохождения теста
Строит график: X = количество вопросов, Y = процент правильных ответов (накопительный)
"""

import sqlite3
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path

# Настройка для кириллицы
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
matplotlib.rcParams['axes.unicode_minus'] = False

def get_db_path():
    """Получает путь к базе данных"""
    return Path(__file__).parent / "test_database.sqlite"

def load_run_results(run_id: int, db_path: str = None):
    """Загружает результаты запуска и вычисляет накопительный процент"""

    if db_path is None:
        db_path = get_db_path()

    if not Path(db_path).exists():
        print(f"❌ База данных не найдена: {db_path}")
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем информацию о запуске
    cursor.execute('''
        SELECT tr.id, tr.test_id, tr.model_name, tr.timestamp,
               tr.total_questions, tr.correct_answers, tr.score_percentage,
               t.name as test_name
        FROM test_runs tr
        LEFT JOIN tests t ON tr.test_id = t.id
        WHERE tr.id = ?
    ''', (run_id,))

    run_info = cursor.fetchone()
    if not run_info:
        print(f"❌ Запуск #{run_id} не найден")
        conn.close()
        return None

    # Получаем все результаты в порядке вопросов
    cursor.execute('''
        SELECT r.id, r.question_id, r.score, q.text, q.correct_indices
        FROM results r
        JOIN questions q ON r.question_id = q.id
        WHERE r.run_id = ?
        ORDER BY r.id
    ''', (run_id,))

    results = cursor.fetchall()
    conn.close()

    if not results:
        print(f"❌ Нет результатов для запуска #{run_id}")
        return None

    # Вычисляем накопительный процент
    cumulative_correct = 0
    cumulative_percentages = []
    question_numbers = []

    for i, result in enumerate(results, 1):
        if result[2] == 1.0:  # score = 1.0 означает правильный ответ
            cumulative_correct += 1

        cumulative_pct = (cumulative_correct / i) * 100
        cumulative_percentages.append(cumulative_pct)
        question_numbers.append(i)

    return {
        'run_id': run_info[0],
        'test_id': run_info[1],
        'model_name': run_info[2],
        'timestamp': run_info[3],
        'total_questions': run_info[4],
        'correct_answers': run_info[5],
        'final_percentage': run_info[6],
        'test_name': run_info[7],
        'question_numbers': question_numbers,
        'cumulative_percentages': cumulative_percentages
    }

def generate_chart(data: dict, output_file: str = None, show_final_line: bool = True):
    """Генерирует и сохраняет график"""

    if data is None:
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    # Основная линия
    ax.plot(data['question_numbers'],
            data['cumulative_percentages'],
            color='#2E86AB',
            linewidth=2.5,
            label='Точность ИИ')

    # Заливка под графиком
    ax.fill_between(data['question_numbers'],
                    data['cumulative_percentages'],
                    alpha=0.3,
                    color='#2E86AB')

    # Горизонтальная линия финального результата
    if show_final_line:
        ax.axhline(y=data['final_percentage'],
                   color='#E94F37',
                   linestyle='--',
                   linewidth=2,
                   label=f'Финальный результат: {data["final_percentage"]:.1f}%')

    # Точка старта
    ax.scatter([1], [data['cumulative_percentages'][0]],
               color='#44AF69', s=100, zorder=5, label='Старт')

    # Точка финиша
    ax.scatter([data['total_questions']], [data['final_percentage']],
               color='#E94F37', s=150, zorder=5, marker='*',
               label=f'Финиш ({data["final_percentage"]:.1f}%)')

    # Настройка осей
    ax.set_xlabel('Количество вопросов', fontsize=12, fontweight='bold')
    ax.set_ylabel('Процент правильных ответов (%)', fontsize=12, fontweight='bold')

    # Заголовок
    title = f"Прохождение теста: {data['test_name']}\n"
    title += f"Модель: {data['model_name']} | "
    title += f"Дата: {data['timestamp'][:10]}"
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    # Сетка
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_xlim(0, data['total_questions'] + 5)
    ax.set_ylim(0, 100)

    # Легенда
    ax.legend(loc='lower right', fontsize=10)

    # Статистика в углу
    stats_text = (f"Всего вопросов: {data['total_questions']}\n"
                  f"Правильных: {data['correct_answers']}\n"
                  f"Точность: {data['final_percentage']:.1f}%")

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✅ График сохранён: {output_file}")

    plt.close()

    # Вывод в терминал
    print(f"\n📊 Статистика запуска #{data['run_id']}:")
    print(f"   Тест: {data['test_name']}")
    print(f"   Модель: {data['model_name']}")
    print(f"   Вопросов: {data['total_questions']}")
    print(f"   Правильных: {data['correct_answers']}")
    print(f"   Точность: {data['final_percentage']:.1f}%")
    print(f"   Начальная точность: {data['cumulative_percentages'][0]:.1f}%")
    print(f"   Конечная точность: {data['cumulative_percentages'][-1]:.1f}%")

def list_available_runs(db_path: str = None):
    """Показывает список доступных запусков"""

    if db_path is None:
        db_path = get_db_path()

    if not Path(db_path).exists():
        print(f"❌ База данных не найдена: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT tr.id, t.name, tr.model_name, tr.timestamp,
               tr.total_questions, tr.correct_answers, tr.score_percentage
        FROM test_runs tr
        LEFT JOIN tests t ON tr.test_id = t.id
        ORDER BY tr.id DESC
        LIMIT 10
    ''')

    runs = cursor.fetchall()
    conn.close()

    if not runs:
        print("❌ Нет запусков в базе данных")
        return

    print("\n📋 Последние запуски:")
    print("-" * 100)
    print(f"{'ID':<4} {'Тест':<20} {'Модель':<25} {'Дата':<12} {'Вопр.':<6} {'Прав.':<6} {'%':<6}")
    print("-" * 100)

    for run in runs:
        print(f"{run[0]:<4} {run[1][:18]:<20} {run[2][:23]:<25} "
              f"{run[3][:10]:<12} {run[4]:<6} {run[5]:<6} {run[6]:.1f}%")

    print("-" * 100)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Генератор графика прохождения теста MedAITest')
    parser.add_argument('--run-id', '-r', type=int, default=2,
                        help='ID запуска (по умолчанию: 2)')
    parser.add_argument('--db', '-d', type=str, default=None,
                        help='Путь к базе данных')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Путь для сохранения графика')
    parser.add_argument('--list', '-l', action='store_true',
                        help='Показать список доступных запусков')

    args = parser.parse_args()

    if args.list:
        list_available_runs(args.db)
        return

    # Загружаем данные
    data = load_run_results(args.run_id, args.db)

    if data is None:
        print("\n💡 Используйте --list для просмотра доступных запусков")
        return

    # Генерируем график
    output_file = args.output
    if output_file is None:
        output_file = f"chart_run_{args.run_id}.png"

    generate_chart(data, output_file)

if __name__ == '__main__':
    main()
