# Установка MedAITest

## Системные требования

- **Python**: 3.8 или выше
- **ОС**: Windows, macOS, Linux
- **Интернет**: Для API-запросов к AI-моделям

## Быстрая установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/luhverchikv/MedAITest.git
cd MedAITest
```

### 2. Создание виртуального окружения (рекомендуется)

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env и добавьте ваш API ключ
nano .env  # или любой редактор
```

### 5. Настройка API

Отредактируйте файл `.env`:

```env
# API ключ для VedAI (или другого OpenAI-совместимого сервиса)
VEDAI_API_KEY=your_api_key_here

# URL API (по умолчанию VedAI)
VEDAI_BASE_URL=https://vedai.by/api/v1
```

> Получить API ключ можно на [vedai.by](https://vedai.by) или использовать любой OpenAI-совместимый API.

## Проверка установки

```bash
# Проверка версии Python
python --version  # Должно быть 3.8+

# Проверка зависимостей
python -c "import openai; print('openai OK')"

# Запуск справки
python manage_tests.py --help
```

## Структура файлов после установки

```
MedAITest/
├── .env                 # Ваши настройки (не коммитится!)
├── .env.example         # Пример настроек
├── .gitignore           # Игнорируемые файлы
├── ai_client.py         # Клиент для AI API
├── analyze.py           # Анализ результатов
├── config.py            # Конфигурация приложения
├── database.py          # SQLite база данных
├── find_bad_questions.py # Поиск проблемных вопросов
├── manage_tests.py      # Управление тестами
├── parser.py            # Парсинг тестов
├── run_test.py          # Запуск тестов
├── requirements.txt     # Зависимости Python
├── tests/               # Папка с тестами
│   ├── emergency.txt
│   ├── pharmacology.txt
│   └── ...
└── docs/                # Документация
```

## Устранение проблем

### Ошибка "Module not found"

```bash
pip install -r requirements.txt
```

### Ошибка базы данных

```bash
# Удалите старую базу и создайте заново
rm test_database.sqlite
python manage_tests.py --list  # Создаст новую БД автоматически
```

### Проблемы с кодировкой (Windows)

```bash
# Убедитесь, что используете UTF-8
chcp 65001
set PYTHONIOENCODING=utf-8
```

## Следующие шаги

1. [Управление тестами](02_TEST_MANAGEMENT.md) — загрузка и импорт тестов
2. [Запуск тестов](03_RUNNING_TESTS.md) — тестирование AI-моделей
3. [Анализ результатов](04_ANALYSIS.md) — интерпретация результатов
