# parser.py
import re
from typing import List, Dict, Optional

def normalize_text(text: str) -> str:
    """Приводит текст к единому виду для надежного сравнения"""
    # Убираем лишние пробелы, приводим к нижнему регистру, убираем знаки препинания в конце
    text = text.strip().lower()
    text = re.sub(r'[.,;:!?]+$', '', text)  # Убираем пунктуацию в конце
    text = re.sub(r'\s+', ' ', text)  # Заменяем множественные пробелы на один
    return text

def parse_tests_file(filepath: str) -> List[Dict]:
    """
    Парсит файл с вопросами в вашем формате.
    
    Формат входных данных:
    Вопрос 19: Текст вопроса:
    Вариант 1
    Вариант 2
    Вариант 3
    Правильный ответ: Текст варианта
    ИЛИ
    Правильные ответы: Текст1, Текст2
    
    Возвращает список словарей:
    [
        {
            'text': 'Текст вопроса',
            'options': ['Вариант 1', 'Вариант 2', ...],
            'correct_texts': ['Правильный вариант'],
            'is_multiple': False
        },
        ...
    ]
    """
    questions = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разбиваем на блоки по шаблону "Вопрос N:"
    # Используем regex с захватом номера вопроса
    question_blocks = re.split(r'\n(?=Вопрос\s*\d+\s*:)', content.strip())
    
    for block in question_blocks:
        block = block.strip()
        if not block:
            continue
        
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue
        
        # === Парсим заголовок вопроса ===
        header_match = re.match(r'Вопрос\s*\d+\s*:\s*(.+)', lines[0], re.IGNORECASE)
        if not header_match:
            print(f"⚠ Пропущен блок (нет заголовка): {block[:50]}...")
            continue
        
        question_text = header_match.group(1).strip()
        
        # === Ищем строку с правильными ответами ===
        correct_line_idx = None
        correct_prefix = None
        
        for i, line in enumerate(lines):
            if line.lower().startswith('правильный ответ:'):
                correct_line_idx = i
                correct_prefix = 'правильный ответ:'
                break
            elif line.lower().startswith('правильные ответы:'):
                correct_line_idx = i
                correct_prefix = 'правильные ответы:'
                break
        
        if correct_line_idx is None:
            print(f"⚠ Пропущен вопрос '{question_text[:30]}...': не найдена строка с правильным ответом")
            continue
        
        # === Извлекаем варианты ответов (между вопросом и правильным ответом) ===
        options_lines = lines[1:correct_line_idx]
        # Фильтруем пустые строки и строки, похожие на заголовки
        options = [opt for opt in options_lines if opt and not opt.lower().startswith('вопрос')]
        
        if not options:
            print(f"⚠ Пропущен вопрос '{question_text[:30]}...': не найдены варианты ответов")
            continue
        
        # === Парсим правильные ответы ===
        correct_line = lines[correct_line_idx]
        correct_part = correct_line.split(':', 1)[1].strip()
        
        # Разбиваем на отдельные ответы (по запятой или точке с запятой)
        correct_texts_raw = re.split(r'[,;]', correct_part)
        correct_texts = [normalize_text(ct) for ct in correct_texts_raw if ct.strip()]
        
        # === Сопоставляем тексты правильных ответов с индексами вариантов ===
        correct_indices = []
        options_normalized = [(i+1, normalize_text(opt)) for i, opt in enumerate(options)]
        
        for correct_text in correct_texts:
            found = False
            for idx, opt_norm in options_normalized:
                if correct_text == opt_norm:
                    correct_indices.append(idx)
                    found = True
                    break
            if not found:
                # Попытка найти по частичному совпадению (на случай опечаток)
                for idx, opt_norm in options_normalized:
                    if correct_text in opt_norm or opt_norm in correct_text:
                        correct_indices.append(idx)
                        print(f"  ℹ Найдено частичное совпадение для '{correct_text}' -> вариант {idx}")
                        found = True
                        break
            if not found:
                print(f"  ⚠ Не найден вариант для правильного ответа: '{correct_text}'")
                print(f"    Доступные варианты: {[opt for _, opt in options_normalized]}")
        
        if not correct_indices:
            print(f"⚠ Пропущен вопрос '{question_text[:30]}...': не удалось сопоставить правильные ответы")
            continue
        
        is_multiple = len(correct_indices) > 1
        
        questions.append({
            'text': question_text,
            'options': options,
            'correct_indices': sorted(correct_indices),
            'is_multiple': is_multiple
        })
        
        #print(f"✓ Спаршен вопрос #{len(questions)}: '{question_text[:40]}...' ({'мультивыбор' if is_multiple else 'один ответ'})")
    
    return questions

