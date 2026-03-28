# parser.py
import re
from typing import List, Dict, Tuple

# Глобальный список для сбора вопросов с частичными совпадениями
_partial_matches_log: List[Dict] = []


def normalize_text(text: str) -> str:
    """Приводит текст к единому виду для надежного сравнения"""
    text = text.strip().lower()
    text = re.sub(r'[.,;:!?]+$', '', text)  # Убираем пунктуацию в конце
    text = re.sub(r'\s+', ' ', text)  # Заменяем множественные пробелы на один
    return text


def _find_match(correct_text: str, options: List[str], allow_partial: bool = False) -> Tuple[List[int], List[Dict]]:
    """
    Ищет совпадение текста правильного ответа с вариантами.
    
    Параметры:
        correct_text: текст для поиска
        options: список вариантов ответа
        allow_partial: если True, допускает поиск подстроки (частичное совпадение)
    
    Возвращает:
        (list_of_matched_indices, list_of_partial_match_details)
    """
    options_normalized = [(i+1, normalize_text(opt)) for i, opt in enumerate(options)]
    correct_norm = normalize_text(correct_text)
    
    matched_indices = []
    partial_details = []
    
    # 1. Точное совпадение
    for idx, opt_norm in options_normalized:
        if correct_norm == opt_norm:
            matched_indices.append(idx)
            return matched_indices, partial_details
    
    # 2. Частичное совпадение (только если разрешено и текст достаточно длинный)
    if allow_partial and len(correct_norm) >= 15:
        for idx, opt_norm in options_normalized:
            if correct_norm in opt_norm or opt_norm in correct_norm:
                # Оцениваем качество совпадения
                overlap = len(correct_norm) / max(len(opt_norm), len(correct_norm))
                if overlap >= 0.75:  # Требуем минимум 75% перекрытия
                    matched_indices.append(idx)
                    partial_details.append({
                        'correct_text': correct_text,
                        'matched_option_idx': idx,
                        'matched_option_text': options[idx-1],
                        'overlap_ratio': round(overlap, 2)
                    })
                    return matched_indices, partial_details
    
    # 3. Не найдено
    if allow_partial:
        partial_details.append({
            'correct_text': correct_text,
            'matched_option_idx': None,
            'matched_option_text': None,
            'error': 'NOT_FOUND'
        })
    
    return matched_indices, partial_details


def parse_tests_file(filepath: str, verbose: bool = True) -> List[Dict]:
    """
    Парсит файл с вопросами по улучшенной логике.
    
    Алгоритм:
    1. Если в правильном ответе НЕТ запятых → один ответ → точное сравнение
    2. Если ЕСТЬ запятые:
       а) Сначала пробуем точное совпадение ВСЕЙ строки (один ответ с запятой внутри)
       б) Если не нашли → разбиваем по запятой и ищем каждый ответ отдельно
    """
    global _partial_matches_log
    _partial_matches_log = []
    
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
            continue
        
        question_text = header_match.group(1).strip()
        question_id_match = re.search(r'Вопрос\s*(\d+)', lines[0])
        question_num = question_id_match.group(1) if question_id_match else "?"
        
        # === Ищем строку с правильными ответами ===
        correct_line_idx = None
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if line_lower.startswith('правильный ответ:') or line_lower.startswith('правильные ответы:'):
                correct_line_idx = i
                break
        
        if correct_line_idx is None:
            continue
        
        # === Извлекаем варианты ответов ===
        options_lines = lines[1:correct_line_idx]
        options = [opt for opt in options_lines if opt and not opt.lower().startswith('вопрос')]
        
        if not options:
            continue
        
        # === Парсим правильные ответы ===
        correct_line = lines[correct_line_idx]
        correct_part = correct_line.split(':', 1)[1].strip()
        
        correct_indices = []
        question_partial_matches = []
        
        # ═══════════════════════════════════════════════════════
        # НОВАЯ ЛОГИКА: определяем стратегию по наличию запятой
        # ═══════════════════════════════════════════════════════
        
        if ',' not in correct_part:
            # ── СЛУЧАЙ 1: Нет запятых → точно один правильный ответ ──
            # Пробуем только точное совпадение
            indices, _ = _find_match(correct_part, options, allow_partial=False)
            
            if indices:
                correct_indices = indices
            else:
                # Если точное не сработало — пробуем частичное (на случай опечаток/пробелов)
                indices, matches = _find_match(correct_part, options, allow_partial=True)
                correct_indices = indices
                question_partial_matches = matches
                
        else:
            # ── СЛУЧАЙ 2: Есть запятые ──
            # Шаг А: Сначала пробуем точное совпадение ВСЕЙ строки целиком
            # (на случай, если это один ответ, содержащий запятую)
            indices, _ = _find_match(correct_part, options, allow_partial=False)
            
            if indices:
                # Успех! Это один ответ с запятой внутри
                correct_indices = indices
            else:
                # Не нашли целиком → значит ответов несколько, разбиваем по запятой
                candidates = [c.strip() for c in correct_part.split(',') if c.strip()]
                
                for candidate in candidates:
                    # Для каждого кандидата: сначала точное, потом частичное
                    indices, matches = _find_match(candidate, options, allow_partial=False)
                    if indices:
                        correct_indices.extend(indices)
                    else:
                        # Пробуем частичное совпадение
                        indices, matches = _find_match(candidate, options, allow_partial=True)
                        if indices:
                            correct_indices.extend(indices)
                            question_partial_matches.extend(matches)
                        else:
                            # Совсем не нашли
                            question_partial_matches.extend(matches)
        
        # Пропускаем вопрос, если не удалось сопоставить ни один ответ
        if not correct_indices:
            if verbose:
                print(f"  ❌ Вопрос #{question_num}: не удалось сопоставить правильные ответы")
            continue
        
        is_multiple = len(correct_indices) > 1
        
        # Если были частичные совпадения — добавляем в лог для отчёта
        if question_partial_matches:
            _partial_matches_log.append({
                'question_num': question_num,
                'question_text': question_text,
                'matches': question_partial_matches,
                'options': options,
                'correct_indices': sorted(correct_indices)
            })
            
            if verbose:
                print(f"  ⚠ Вопрос #{question_num}: '{question_text[:60]}...'")
                for m in question_partial_matches:
                    if m.get('error') == 'NOT_FOUND':
                        print(f"     ❌ Не найдено: '{m['correct_text']}'")
                    else:
                        opt_preview = m['matched_option_text'][:50]
                        ratio = f" ({m.get('overlap_ratio', 100)}%)" if 'overlap_ratio' in m else ""
                        print(f"     🔸 '{m['correct_text']}' → Вариант {m['matched_option_idx']}: '{opt_preview}...'{ratio}")
        
        questions.append({
            'text': question_text,
            'options': options,
            'correct_indices': sorted(correct_indices),
            'is_multiple': is_multiple
        })
    
    # === Выводим сводный отчёт в конце ===
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
    """Возвращает список вопросов с частичными совпадениями для экспорта"""
    return _partial_matches_log


def clear_partial_matches_log():
    """Очищает лог частичных совпадений"""
    global _partial_matches_log
    _partial_matches_log = []

