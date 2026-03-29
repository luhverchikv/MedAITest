#!/usr/bin/env python3
# analyze.py — Интерактивный анализатор вопросов из базы данных

import sqlite3
from config import DB_PATH


def get_db_connection():
    """Возвращает соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def list_questions(limit: int = 20):
    """Выводит список последних вопросов для быстрого выбора"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, text, is_multiple, correct_indices 
        FROM questions 
        ORDER BY id 
        LIMIT ?
    """, (limit,))
    
    questions = cursor.fetchall()
    conn.close()
    
    if not questions:
        print("⚪ База данных пуста")
        return []
    
    print(f"\n📋 Последние {len(questions)} вопросов:")
    print("-" * 70)
    for q in questions:
        q_type = "🔀" if q['is_multiple'] else "🔘"
        correct = q['correct_indices'].split(',')
        print(f"{q_type} #{q['id']}: {q['text'][:60]}...")
        print(f"   Правильные: {correct} | Всего вариантов: ?")
    
    print("-" * 70)
    return questions


def get_question_by_id(question_id: int):
    """Получает вопрос с вариантами ответов по ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем вопрос
    cursor.execute("""
        SELECT id, text, is_multiple, correct_indices 
        FROM questions WHERE id = ?
    """, (question_id,))
    
    question = cursor.fetchone()
    if not question:
        conn.close()
        return None
    
    # Получаем варианты ответов
    cursor.execute("""
        SELECT option_index, text 
        FROM options 
        WHERE question_id = ? 
        ORDER BY option_index
    """, (question_id,))
    
    options = cursor.fetchall()
    conn.close()
    
    return {
        'id': question['id'],
        'text': question['text'],
        'is_multiple': bool(question['is_multiple']),
        'correct_indices': [int(x) for x in question['correct_indices'].split(',')],
        'options': [(opt['option_index'], opt['text']) for opt in options]
    }


def display_question(q_ dict, show_answers: bool = True):
    """Красиво выводит вопрос для анализа"""
    print(f"\n{'='*80}")
    print(f"❓ ВОПРОС #{q_data['id']}")
    print(f"{'='*80}")
    
    # Тип вопроса
    q_type = "🔀 НЕСКОЛЬКО ПРАВИЛЬНЫХ ОТВЕТОВ" if q_data['is_multiple'] else "🔘 ОДИН ПРАВИЛЬНЫЙ ОТВЕТ"
    print(f"Тип: {q_type}\n")
    
    # Текст вопроса
    print(f"📝 {q_data['text']}\n")
    
    # Варианты ответов
    print("📋 Варианты ответов:")
    print("-" * 40)
    for idx, text in q_data['options']:
        # Если показываем ответы — помечаем правильные
        if show_answers and idx in q_data['correct_indices']:
            print(f"  ✅ {idx}. {text}")
        else:
            print(f"     {idx}. {text}")
    print("-" * 40)
    
    # Правильные ответы (если включено отображение)
    if show_answers:
        correct_texts = [
            q_data['options'][i-1][1] 
            for i in q_data['correct_indices'] 
            if i <= len(q_data['options'])
        ]
        print(f"\n🎯 Правильный ответ(ы) ({len(q_data['correct_indices'])}):")
        for i, idx in enumerate(q_data['correct_indices'], 1):
            print(f"   {i}. Вариант #{idx}: {correct_texts[i-1][:100]}{'...' if len(correct_texts[i-1]) > 100 else ''}")
    
    print(f"\n{'='*80}")


def interactive_mode():
    """Основной интерактивный цикл"""
    print("🔍 АНАЛИЗАТОР ВОПРОСОВ — MedAITest")
    print("Введите номер вопроса для просмотра, или команду:\n")
    print("  list  — показать список вопросов")
    print("  all N — показать вопросы с 1 по N")
    print("  exit  — выход")
    print("  help  — эта справка\n")
    
    while True:
        try:
            user_input = input("\n➤ Введите номер вопроса или команду: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Выход")
            break
        
        if not user_input:
            continue
        
        cmd = user_input.lower()
        
        # === Команды ===
        if cmd in ('exit', 'quit', 'q', 'выход'):
            print("👋 До свидания!")
            break
        
        elif cmd in ('help', 'h', 'справка'):
            print("""
📖 СПРАВКА:
  <число>     — показать вопрос с этим номером
  list        — показать последние 20 вопросов
  all N       — показать вопросы с 1 по N (для массового просмотра)
  hide N      — показать вопрос БЕЗ подсветки правильных ответов (для самопроверки)
  exit        — выйти из программы
            """)
            continue
        
        elif cmd == 'list':
            list_questions()
            continue
        
        elif cmd.startswith('all '):
            try:
                limit = int(cmd.split()[1])
                questions = list_questions(limit)
                # Показать первые 3 для примера
                if questions:
                    print(f"\n💡 Подсказка: введите номер вопроса для детального просмотра")
            except (IndexError, ValueError):
                print("❌ Используйте: all <число>")
            continue
        
        elif cmd.startswith('hide '):
            # Показать вопрос без ответов (для самопроверки)
            try:
                q_id = int(cmd.split()[1])
                q_data = get_question_by_id(q_id)
                if q_
                    display_question(q_data, show_answers=False)
                    print("💡 Подсказка: правильные ответы скрыты. Введите 'show <номер>' чтобы увидеть.")
                else:
                    print(f"❌ Вопрос #{q_id} не найден")
            except (IndexError, ValueError):
                print("❌ Используйте: hide <номер_вопроса>")
            continue
        
        elif cmd.startswith('show '):
            # Показать вопрос с ответами
            try:
                q_id = int(cmd.split()[1])
                q_data = get_question_by_id(q_id)
                if q_
                    display_question(q_data, show_answers=True)
                else:
                    print(f"❌ Вопрос #{q_id} не найден")
            except (IndexError, ValueError):
                print("❌ Используйте: show <номер_вопроса>")
            continue
        
        # === Номер вопроса ===
        try:
            q_id = int(user_input)
            q_data = get_question_by_id(q_id)
            
            if q_
                display_question(q_data, show_answers=True)
                
                # Быстрая статистика
                total_opts = len(q_data['options'])
                correct_count = len(q_data['correct_indices'])
                print(f"📊 Статистика: {correct_count} правильный(ых) из {total_opts} вариантов")
                
            else:
                print(f"❌ Вопрос #{q_id} не найден в базе")
                print("💡 Введите 'list' чтобы увидеть доступные номера")
                
        except ValueError:
            print(f"❌ Не распознано: '{user_input}'. Введите 'help' для справки")


def export_question_to_text(q_id: int, filepath: str = None):
    """Экспортирует вопрос в текстовый формат (для отчётов)"""
    q_data = get_question_by_id(q_id)
    if not q_data:
        return False
    
    lines = [
        f"Вопрос {q_data['id']}: {q_data['text']}",
        ""
    ]
    
    for idx, text in q_data['options']:
        marker = "[ПРАВИЛЬНЫЙ] " if idx in q_data['correct_indices'] else ""
        lines.append(f"{marker}Вариант {idx}: {text}")
    
    lines.append("")
    correct_nums = ",".join(map(str, q_data['correct_indices']))
    lines.append(f"Правильный ответ: {correct_nums}")
    
    content = "\n".join(lines)
    
    if filepath:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Вопрос экспортирован в: {filepath}")
    else:
        print(content)
    
    return True


if __name__ == "__main__":
    import sys
    
    # Режим командной строки: один вопрос и выход
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit():
            q_id = int(sys.argv[1])
            q_data = get_question_by_id(q_id)
            if q_
                display_question(q_data)
            else:
                print(f"❌ Вопрос #{q_id} не найден")
                sys.exit(1)
        elif sys.argv[1] == '--export' and len(sys.argv) == 4:
            export_question_to_text(int(sys.argv[2]), sys.argv[3])
        elif sys.argv[1] in ('--list', '-l'):
            list_questions()
        else:
            print("Использование:")
            print("  python analyze.py <номер_вопроса>     — показать один вопрос")
            print("  python analyze.py --export <id> <file> — экспортировать вопрос в файл")
            print("  python analyze.py --list              — список вопросов")
            print("  python analyze.py                     — интерактивный режим")
    else:
        # Интерактивный режим
        interactive_mode()

