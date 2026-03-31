# run_test.py — ОБНОВЛЁННАЯ ВЕРСИЯ С ЛОГИРОВАНИЕМ
import time
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from database import (
    init_db, get_all_questions, get_options_by_question_id,
    create_test_run, save_result, calculate_score, 
    get_run_summary, get_run_results
)
from ai_client import OpenAICompatibleClient  # Универсальный клиент
from config import (
    VEDAI_API_KEY, VEDAI_BASE_URL, MODELS_TO_TEST,
    MAX_QUESTIONS, SAVE_PROGRESS_EVERY, REQUEST_DELAY,
    TEMPERATURE, MAX_TOKENS
)

# ============================================================================
# 🪵 НАСТРОЙКА ЛОГИРОВАНИЯ
# ============================================================================

def setup_logging(run_id: int, log_dir: str = "logs", console_output: bool = True):
    """
    Настраивает логирование в файл и (опционально) в консоль
    
    Args:
        run_id: ID запуска теста (для имени файла)
        log_dir: Папка для логов
        console_output: Дублировать ли в консоль
    
    Returns:
        logger: Настроенный логгер
    """
    # Создаём папку для логов
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Имя файла лога
    log_file = log_path / f"run_{run_id}.log"
    
    # Создаём/настраиваем логгер
    logger = logging.getLogger(f"run_{run_id}")
    logger.setLevel(logging.DEBUG)  # Записываем всё в файл
    
    # Очищаем старые хендлеры (чтобы не дублировать)
    logger.handlers.clear()
    
    # 📁 Файловый хендлер (всё в файл)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', 
                                    datefmt='%H:%M:%S')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # 🖥️ Консольный хендлер (только важное)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # Только INFO и выше
        console_format = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    return logger, log_file


def log_question_details(logger, q_num: int, question: dict, options: list, 
                         ai_indices: list, correct_indices: list, score: float, 
                         error: str = None):
    """Детально логирует один вопрос для последующего анализа"""
    
    if error:
        logger.error(f"Q{q_num:03d} ❌ API ERROR: {error}")
        return
    
    status = "✅" if score == 1.0 else "❌"
    question_short = question['text'][:100].replace('\n', ' ')
    
    # Основная строка
    logger.info(f"Q{q_num:03d} {status} \"{question_short}...\"")
    
    # Детали (на уровне DEBUG)
    logger.debug(f"  → Варианты: {options}")
    logger.debug(f"  → Правильно: {correct_indices}")
    logger.debug(f"  → Ответ ИИ:  {ai_indices}")
    logger.debug(f"  → Score: {score}")
    
    # Если ответ неверный — логируем подробнее на INFO уровне
    if score < 1.0:
        logger.info(f"     ⚠️  Ошибка: ожидалось {correct_indices}, получено {ai_indices}")


# ============================================================================
# 🧪 ФУНКЦИИ ТЕСТИРОВАНИЯ
# ============================================================================

def run_single_model_test(
    model_name: str, 
    display_name: str = None,
    max_questions: int = None, 
    verbose: bool = True,
    log_to_file: bool = True
) -> dict:
    """
    Запускает тестирование для одной модели с логированием
    
    Returns:
        dict с результатами и путём к логу
    """
    init_db()
    
    questions = get_all_questions()
    if not questions:
        msg = "❌ Нет вопросов в базе. Загрузите вопросы через load_data.py"
        print(msg)
        return {"error": msg}

    # Ограничиваем количество вопросов
    if max_questions:
        questions = questions[:max_questions]
    elif MAX_QUESTIONS:
        questions = questions[:MAX_QUESTIONS]

    # Создаём запись запуска ДО настройки логов (чтобы получить run_id)
    run_id = create_test_run(display_name or model_name)
    
    # Настраиваем логирование
    logger = None
    log_file = None
    if log_to_file:
        logger, log_file = setup_logging(run_id, console_output=verbose)
        logger.info(f"🚀 ЗАПУСК ТЕСТА | Модель: {display_name or model_name}")
        logger.info(f"📊 Вопросов: {len(questions)} | API: {VEDAI_BASE_URL}")
        logger.info(f"⚙️  Параметры: temperature={TEMPERATURE}, max_tokens={MAX_TOKENS}")
        logger.info("-" * 80)
    
    if verbose and not logger:
        print(f"\n🚀 Тестирование: {display_name or model_name}")
        print(f"   Вопросов: {len(questions)} | Запуск #{run_id}")

    # Инициализация AI-клиента
    client = OpenAICompatibleClient(
        api_key=VEDAI_API_KEY,
        base_url=VEDAI_BASE_URL,
        model=model_name,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )

    # Проверка подключения
    success, msg = client.test_connection()
    if not success:
        error_msg = f"❌ Ошибка подключения: {msg}"
        if logger:
            logger.error(error_msg)
        else:
            print(error_msg)
        return {"model": model_name, "error": msg, "success": False, "run_id": run_id}
    
    if logger:
        logger.info(f"✅ Подключение: {msg}")
    elif verbose:
        print(f"✅ {msg}")

    # Статистика
    correct = 0
    errors = 0
    start_time = time.time()
    question_times = []  # Для анализа скорости

    # 🔄 Главный цикл
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

        q_elapsed = time.time() - q_start
        question_times.append(q_elapsed)

        # Обработка ответа
        if not ai_success:
            errors += 1
            log_question_details(logger, i, q, options, [], correct_indices, 0.0, error_msg)
            save_result(run_id, question_id, [], 0.0)
            continue

        # Оценка и сохранение
        score = calculate_score(ai_indices, correct_indices)
        if score == 1.0:
            correct += 1
            
        save_result(run_id, question_id, ai_indices, score)
        log_question_details(logger, i, q, options, ai_indices, correct_indices, score)

        # Прогресс (каждые 5 вопросов или последний)
        if verbose and (i % 5 == 0 or i == len(questions)):
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            remaining = (len(questions) - i) * avg_time
            pct = correct/i*100
            
            progress_msg = f"📊 {i}/{len(questions)} | ✅ {correct} ({pct:.1f}%) | ⏱ {remaining:.0f}с"
            if logger:
                logger.info(progress_msg)
            else:
                print(progress_msg)

        # Сохранение прогресса
        if SAVE_PROGRESS_EVERY and i % SAVE_PROGRESS_EVERY == 0:
            if logger:
                logger.info(f"💾 Прогресс сохранён (вопрос #{i})")

        # Задержка между запросами
        time.sleep(REQUEST_DELAY)

    # 🏁 Итоги
    total_time = time.time() - start_time
    summary = get_run_summary(run_id)
    
    # Статистика времени
    avg_time_per_q = sum(question_times) / len(question_times) if question_times else 0
    min_time = min(question_times) if question_times else 0
    max_time = max(question_times) if question_times else 0
    
    result = {
        "run_id": run_id,
        "model": model_name,
        "display_name": display_name,
        "success": True,
        "log_file": str(log_file) if log_file else None,
        "total_questions": summary['total_questions'],
        "correct_answers": summary['correct_answers'],
        "score_percentage": summary['score_percentage'],
        "errors": errors,
        "time_seconds": round(total_time, 1),
        "avg_time_per_question": round(avg_time_per_q, 2),
        "min_time": round(min_time, 2),
        "max_time": round(max_time, 2),
    }
    
    # Финальный лог
    if logger:
        logger.info("-" * 80)
        logger.info(f"🏁 ТЕСТ ЗАВЕРШЁН")
        logger.info(f"✅ Правильно: {result['correct_answers']}/{result['total_questions']}")
        logger.info(f"📈 Точность: {result['score_percentage']}%")
        logger.info(f"⚠️  Ошибок API: {errors}")
        logger.info(f"⏱ Время: {result['time_seconds']}с (среднее: {avg_time_per_q:.2f}с/вопрос)")
        logger.info(f"📄 Лог-файл: {log_file}")
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"🏁 {display_name or model_name} — ЗАВЕРШЕНО")
        print(f"{'='*60}")
        print(f" ✅ Правильно: {result['correct_answers']}/{result['total_questions']}")
        print(f" 📈 Точность: {result['score_percentage']}%")
        print(f" ⚠️  Ошибок API: {errors}")
        print(f" ⏱ Время: {result['time_seconds']}с")
        if log_file:
            print(f" 📄 Лог: {log_file}")
        print(f"{'='*60}\n")

    return result


# ============================================================================
# 🎯 MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="🏥 MedAITest — Тестирование медицинских вопросов")
    parser.add_argument("run_id", nargs="?", type=int, help="Показать результаты запуска по ID")
    
    parser.add_argument("--model", type=str, help="Запустить тест для конкретной модели")
    parser.add_argument("-n", "--questions", type=int, help="Количество вопросов для теста")
    parser.add_argument("--no-log", action="store_true", help="Отключить логирование в файл")
    parser.add_argument("--quiet", action="store_true", help="Минимальный вывод в консоль")
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    log_to_file = not args.no_log
    max_q = args.questions
    
        
        
    # Одна модель
    if args.model:
        run_single_model_test(
            model_name=args.model,
            max_questions=max_q,
            verbose=verbose,
            log_to_file=log_to_file
        )
        
    # По умолчанию — сравнение
    else:
        run_single_model_test(
            model_name="gpt-5-nano",
            max_questions=None,
            verbose=verbose,
            log_to_file=log_to_file
        )

