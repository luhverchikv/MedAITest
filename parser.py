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


def _find_match_by_options(correct_text: str, options: List[str]) -> Tuple[List[int], List[Dict]]:
    """
    Новый алгоритм сопоставления ответов.

    Логика:
    1. Берем все варианты и перебираем в цикле
    2. Сравниваем с правильным ответом целыми строками
    3. Если есть совпадение → только один вариант ответа, мы его нашли
    4. Если совпадения нет → берем часть варианта и ищем в правильном ответе
    5. Если нашли → записываем как правильный и продолжаем перебирать варианты

    Returns:
        (list_of_matched_indices, list_of_match_details)
    """
    matched_indices = []
    match_details = []

    correct_norm = normalize_text(correct_text)

    # Первый проход: точное совпадение любого варианта с правильным ответом
    for i, option in enumerate(options):
        opt_norm = normalize_text(option)
        if opt_norm == correct_norm:
            # Нашли точное совпадение - это один единственный правильный ответ
            matched_indices.append(i + 1)  # 1-based индекс
            match_details.append({
                'option_idx': i + 1,
                'option_text': option,
                'match_type': 'exact'
            })
            return matched_indices, match_details

    # Второй проход: ищем фрагменты вариантов в правильном ответе
    for i, option in enumerate(options):
        opt_norm = normalize_text(option)

        # Пропускаем, если уже нашли точное совпадение (не должно случиться)
        if (i + 1) in matched_indices:
            continue

        # Ищем, содержится ли вариант в правильном ответе
        if opt_norm in correct_norm:
            matched_indices.append(i + 1)
            match_details.append({
                'option_idx': i + 1,
                'option_text': option,
                'match_type': 'contained'
            })
            continue

        # Пробуем обратное: правильный ответ содержится в варианте
        if correct_norm in opt_norm and len(correct_norm) >= 10:
            matched_indices.append(i + 1)
            match_details.append({
                'option_idx': i + 1,
                'option_text': option,
                'match_type': 'reverse_containment'
            })
            continue

        # Частичное совпадение по словам (для длинных вариантов)
        if len(opt_norm) >= 15:
            # Разбиваем вариант на слова и ищем их в правильном ответе
            words = opt_norm.split()
            if len(words) >= 2:
                matched_words = 0
                for word in words:
                    if len(word) >= 4 and word in correct_norm:
                        matched_words += 1

                # Если более 70% слов найдено
                if matched_words / len(words) >= 0.7:
                    matched_indices.append(i + 1)
                    match_details.append({
                        'option_idx': i + 1,
                        'option_text': option,
                        'match_type': 'partial_word_match',
                        'matched_words': matched_words,
                        'total_words': len(words)
                    })

    return matched_indices, match_details


def parse_tests_file(filepath: str, verbose: bool = True) -> List[Dict]:
    """
    Парсит файл с вопросами.

    Алгоритм (новая логика):
    1. Берем все варианты и перебираем в цикле
    2. Сравниваем с правильным ответом целыми строками
    3. Если есть совпадение → только один вариант ответа
    4. Если совпадения нет → ищем фрагменты вариантов в правильном ответе
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

        # ═══════════════════════════════════════════════════════
        # НОВЫЙ АЛГОРИТМ: ищем варианты внутри правильного ответа
        # ═══════════════════════════════════════════════════════

        correct_indices, match_details = _find_match_by_options(correct_part, options)

        # Проверяем, нашли ли все
        if not correct_indices:
            if verbose:
                print(f"  ❌ Вопрос #{question_num}: не удалось сопоставить правильные ответы")
                print(f"     Правильный ответ: '{correct_part}'")
                print(f"     Варианты: {options}")
            continue

        # Проверяем на частичные совпадения
        partial_matches = [m for m in match_details if m['match_type'] != 'exact']
        if partial_matches and verbose:
            print(f"  ⚠ Вопрос #{question_num}: '{question_text[:60]}...'")
            for m in match_details:
                match_type_icon = '✓' if m['match_type'] == 'exact' else '🔸'
                match_type_label = {
                    'exact': 'точное',
                    'contained': 'фрагмент',
                    'reverse_containment': 'содержит',
                    'partial_word_match': 'частичное'
                }.get(m['match_type'], m['match_type'])
                print(f"     {match_type_icon} Вариант {m['option_idx']} ({match_type_label}): '{m['option_text'][:50]}...'")

        # Логируем для статистики
        if partial_matches:
            _partial_matches_log.append({
                'question_num': question_num,
                'question_text': question_text,
                'correct_answer': correct_part,
                'matches': match_details,
                'options': options,
                'correct_indices': sorted(correct_indices)
            })

        is_multiple = len(correct_indices) > 1

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
    print(f"📋 СПИСОК ВОПРОСОВ С ЧАСТИЧНЫМИ СОВПАДЕНИЯМИ")
    print(f"{'='*80}")

    for item in _partial_matches_log:
        print(f"\n🔴 Вопрос #{item['question_num']}: {item['question_text']}")
        print(f"   └─ Правильный ответ: {item['correct_answer']}")
        print(f"   └─ Варианты ответов:")
        for i, opt in enumerate(item['options'], 1):
            marker = "✓" if i in item['correct_indices'] else " "
            print(f"      {marker} {i}. {opt}")
        print(f"   └─ Совпадения:")
        for m in item['matches']:
            match_type_label = {
                'exact': 'точное',
                'contained': 'фрагмент',
                'reverse_containment': 'содержит',
                'partial_word_match': 'частичное'
            }.get(m['match_type'], m['match_type'])
            print(f"      🔸 Вариант #{m['option_idx']} ({match_type_label}): '{m['option_text']}'")

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
