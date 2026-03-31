# run_test.py — УПРОЩЁННАЯ ВЕРСИЯ С ЛОГИРОВАНИЕМ В ФАЙЛ
import time
import logging
import sys
from pathlib import Path
from datetime import datetime

from database import (
    init_db, get_all_questions, get_options_by_question_id,
    create_test_run, save_result, calculate_score, get_run_summary
)
from ai_client import OpenAICompatibleClient  # ✅ Универсальный клиент
from config import (
    VEDAI_API_KEY, VEDAI_BASE_URL, DEFAULT_MODEL,
    MAX_QUESTIONS, SAVE_PROGRESS_EVERY, REQUEST_DELAY,
    TEMPERATURE, MAX_TOKENS
)


def setup_logger(run_id: int, log_dir: str = "logs", console: bool = True):
    """Настраивает логгер: файл + опционально консоль"""
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    logger = logging.getLogger(f"run_{run_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # избегаем дублирования
    
    # 📁 Файл: пишем ВСЁ (DEBUG и выше)
    file_handler = logging.FileHandler(log_path / f"run_{run_id}.log", 
                                       mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-7s | %(message)s', 
        datefmt='%H:%M:%S'
    ))
    logger.addHandler(file_handler)
    
    # 🖥️ Консоль: только важное (INFO и выше)
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(console_handler)
    
    return logger


def run_test(
    model_name: str = None, 
    max_questions: int = None, 
    verbose: bool = True,
    log_to_file: bool = True
):
    """
    Запускает тестирование AI на вопросах из базы данных
    
    Returns:
        run_id: ID запуска (для поиска лога)
    """
    # 1️⃣ Инициализация БД
    init_db()
    
    # 2️⃣ Загрузка вопросов
    questions = get_all_questions()
    if not questions:
        print("❌ Нет вопросов в базе. Загрузите через load_data.py")
        return None
    
    if max_questions:
        questions = questions[:max_questions]
    elif MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]
    
    # 3️⃣ Создаём запись запуска (чтобы получить run_id для имени лога)
    model = model_name or DEFAULT_MODEL
    run_id = create_test_run(model)
    
    # 4️⃣ Настраиваем логирование
    logger = None
    if log_to_file:
        logger = setup_logger(run_id, console=verbose)
        logger.info(f"🚀 ЗАПУСК | Модель: {model} | Вопросов: {len(questions)}")
        logger.info(f"🌐 API: {VEDAI_BASE_URL} | Temp: {TEMPERATURE} | Tokens: {MAX_TOKENS}")
        logger.info("-" * 70)
    elif verbose:
        print(f"\n🚀 Запуск: {model} | {len(questions)} вопросов | Запуск #{run_id}")
    
    # 5️⃣ Инициализация AI-клиента (универсальный для VedAI)
    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=model,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )
    
    # 6️⃣ Проверка подключения
    success, msg = client.test_connection()
    if not success:
        error = f"❌ Ошибка подключения: {msg}"
        if logger:
            logger.error(error)
        else:
            print(error)
        return None
    
    if logger:
        logger.info(f"✅ Подключение: {msg}")
    elif verbose:
        print(f"✅ {msg}")
    
    # 7️⃣ Статистика
    correct = 0
    errors = 0
    start_time = time.time()
    
    # 8️⃣ 🔁 Главный цикл
    for i, q in enumerate(questions, 1):
        q_start = time.time()
        
        question_id = q['id']
        question_text = q['text']
        is_multiple = bool(q['is_multiple'])
        correct_indices = [int(x) for x in q['correct_indices'].split(',')]
        options = get_options_by_question_id(question_id)
        
        # Запрос к ИИ
        ai_success, ai_indices, error_msg = client.get_answer(
            question_text, options, is_multiple
        )
        
        q_time = time.time() - q_start
        
        # Обработка ошибки API
        if not ai_success:
            errors += 1
            if logger:
                logger.error(f"Q{i:03d} ❌ API ERROR: {error_msg}")
            elif verbose:
                print(f" ❌ В#{i}: {error_msg}")
            save_result(run_id, question_id, [], 0.0)
            continue
        
        # Оценка и сохранение
        score = calculate_score(ai_indices, correct_indices)
        if score == 1.0:
            correct += 1
        
        save_result(run_id, question_id, ai_indices, score)
        
        # Детальный лог каждого вопроса (на уровне DEBUG)
        if logger:
            status = "✅" if score == 1.0 else "❌"
            q_short = question_text[:80].replace('\n', ' ')
            logger.info(f"Q{i:03d} {status} \"{q_short}...\" → {ai_indices} (score: {score}) [{q_time:.2f}с]")
            
            # Если неверно — логируем подробнее на INFO
            if score < 1.0:
                logger.info(f"      ⚠️ Ошибка: ожидалось {correct_indices}, получено {ai_indices}")
        
        # Прогресс в консоль
        if verbose and (i % 5 == 0 or i == len(questions)):
            elapsed = time.time() - start_time
            avg = elapsed / i
            remaining = (len(questions) - i) * avg
            pct = correct / i * 100
            print(f" 📊 {i}/{len(questions)} | ✅ {correct} ({pct:.1f}%) | ⏱ {remaining:.0f}с")
        
        # Сохранение прогресса
        if SAVE_PROGRESS_EVERY and i % SAVE_PROGRESS_EVERY == 0:
            if logger:
                logger.info(f"💾 Прогресс сохранён (#{i})")
            elif verbose:
                print(f" 💾 Сохранено {i} результатов...")
        
        # Задержка между запросами
        time.sleep(REQUEST_DELAY)
    
    # 9️⃣ 🏁 Итоги
    total_time = time.time() - start_time
    summary = get_run_summary(run_id)
    
    # Формируем итоговый отчёт
    result_msg = (
        f"\n{'='*60}\n"
        f"🏁 ТЕСТ ЗАВЕРШЁН\n"
        f"{'='*60}\n"
        f" Модель: {summary['model_name']}\n"
        f" Всего вопросов: {summary['total_questions']}\n"
        f" Правильных ответов: {summary['correct_answers']}\n"
        f" Процент: {summary['score_percentage']}%\n"
        f" Ошибок API: {errors}\n"
        f" Время: {total_time:.1f}с\n"
        f"{'='*60}"
    )
    
    if logger:
        logger.info(result_msg)
        logger.info(f"📄 Лог-файл: logs/run_{run_id}.log")
    else:
        print(result_msg)
    
    return run_id


if __name__ == "__main__":
    # Простой запуск без аргументов
    run_test()

