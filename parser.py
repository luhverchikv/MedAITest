# parser.py
import re
from typing import List, Dict, Optional

# Глобальный список для сбора вопросов с частичными совпадениями
_partial_matches_log: List[Dict] = []


def normalize_text(text: str) -> str:
    """Приводит текст к единому виду для надежного сравнения"""
    text = text.strip().lower()
    text = re.sub(r'[.,;:!?]+$', '', text)  # Убираем пунктуацию в конце
    text = re.sub(r'\s+', ' ', text)  # Заменяем множественные пробелы на один
    return text


def parse_tests_file(filepath: str, verbose: bool = True) -> List[Dict]:
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
    
    Параметры:
        verbose: если True, выводит только вопросы с частичными совпадениями
    
    Возвращает список словарей:
    [
        {
            'text': 'Текст вопроса',
            'options': ['Вариант 1', 'Вариант 2', ...],
            'correct_indices': [1, 3],
            'is_multiple': False
        },
        ...
    ]
    """
    global _partial_matches_log
    _partial_matches_log = []  # Сбрасываем лог при новом запуске
    
    questions = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разбиваем на блоки по шаблону "Вопрос N:"
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
            continue  # Тихо пропускаем блоки без заголовка
        
        question_text = header_match.group(1).strip()
        question_id_match = re.search(r'Вопрос\s*(\d+)', lines[0])
        question_num = question_id_match.group(1) if question_id_match else "?"
        
        # === Ищем строку с правильными ответами ===
        correct_line_idx = None
        for i, line in enumerate(lines):
            if line.lower().startswith('правильный ответ:') or line.lower().startswith('правильные ответы:'):
                correct_line_idx = i
                break
        
        if correct_line_idx is None:
            continue  # Пропускаем вопросы без правильных ответов
        
        # === Извлекаем варианты ответов (между вопросом и правильным ответом) ===
        options_lines = lines[1:correct_line_idx]
        options = [opt for opt in options_lines if opt and not opt.lower().startswith('вопрос')]
        
        if not options:
            continue  # Пропускаем вопросы без вариантов
        
        # === Парсим правильные ответы ===
        correct_line = lines[correct_line_idx]
        correct_part = correct_line.split(':', 1)[1].strip()
        
        # Разбиваем на отдельные ответы (по запятой или точке с запятой)
        correct_texts_raw = re.split(r'[,;]', correct_part)
        correct_texts = [normalize_text(ct) for ct in correct_texts_raw if ct.strip()]
        
        # === Сопоставляем тексты правильных ответов с индексами вариантов ===
        correct_indices = []
        options_normalized = [(i+1, normalize_text(opt)) for i, opt in enumerate(options)]
        
        # Локальный список частичных совпадений для этого вопроса
        question_partial_matches = []
        
        for correct_text in correct_texts:
            found = False
            
            # 1. Сначала ищем ТОЧНОЕ совпадение
            for idx, opt_norm in options_normalized:
                if correct_text == opt_norm:
                    correct_indices.append(idx)
                    found = True
                    break
            
            # 2. Если не нашли — ищем ЧАСТИЧНОЕ совпадение
            if not found:
                for idx, opt_norm in options_normalized:
                    if correct_text in opt_norm or opt_norm in correct_text:
                        correct_indices.append(idx)
                        question_partial_matches.append({
                            'correct_text': correct_text,
                            'matched_option_idx': idx,
                            'matched_option_text': options[idx-1]  # оригинальный текст варианта
                        })
                        found = True
                        break
            
            # 3. Если вообще не нашли — логируем как ошибку
            if not found:
                question_partial_matches.append({
                    'correct_text': correct_text,
                    'matched_option_idx': None,
                    'matched_option_text': None,
                    'error': 'NOT_FOUND'
                })
        
        if not correct_indices:
            continue  # Пропускаем вопросы, где не удалось сопоставить ответы
        
        is_multiple = len(correct_indices) > 1
        
        # Если были частичные совпадения — добавляем в глобальный лог
        if question_partial_matches:
            _partial_matches_log.append({
                'question_num': question_num,
                'question_text': question_text,
                'matches': question_partial_matches,
                'options': options,
                'correct_indices': sorted(correct_indices)
            })
            
            # Мгновенный вывод при парсинге (если verbose)
            if verbose:
                print(f"  ⚠ Вопрос #{question_num}: '{question_text[:60]}...'")
                for m in question_partial_matches:
                    if m.get('error') == 'NOT_FOUND':
                        print(f"     ❌ Не найдено: '{m['correct_text']}'")
                    else:
                        opt_preview = m['matched_option_text'][:50]
                        print(f"     🔸 '{m['correct_text']}' → Вариант {m['matched_option_idx']}: '{opt_preview}...'")
        
        questions.append({
            'text': question_text,
            'options': options,
            'correct_indices': sorted(correct_indices),
            'is_multiple': is_multiple
        })
    
    # === Выводим сводный список в конце (если verbose и есть совпадения) ===
    if verbose and _partial_matches_log:
        _print_summary_report()
    
    return questions


def _print_summary_report():
    """Печатает сводный отчёт по вопросам с частичными совпадениями"""
    print(f"\n{'='*80}")
    print(f"📋 СПИСОК ВОПРОСОВ С ЧАСТИЧНЫМИ СОВПАДЕНИЯМИ (требуют проверки)")
    print(f"{'='*80}")
    
    for item in _partial_matches_log:
        print(f"\n🔴 Вопрос #{item['question_num']}: {item['question_text']}")
        print(f"   └─ Варианты ответов:")
        for i, opt in enumerate(item['options'], 1):
            marker = "✓" if i in item['correct_indices'] else " "
            print(f"      {marker} {i}. {opt}")
        
        print(f"   └─ Частичные совпадения:")
        for m in item['matches']:
            if m.get('error') == 'NOT_FOUND':
                print(f"      ❌ '{m['correct_text']}' — НЕ НАЙДЕН среди вариантов")
            else:
                print(f"      🔸 '{m['correct_text']}' → Вариант #{m['matched_option_idx']}")
    
    print(f"\n{'='*80}")
    print(f"📊 Всего вопросов с частичными совпадениями: {len(_partial_matches_log)}")
    print(f"{'='*80}\n")


def get_partial_matches_log() -> List[Dict]:
    """
    Возвращает список вопросов с частичными совпадениями.
    Полезно для экспорта в файл или дальнейшей обработки.
    """
    return _partial_matches_log


def clear_partial_matches_log():
    """Очищает лог частичных совпадений"""
    global _partial_matches_log
    _partial_matches_log = []

