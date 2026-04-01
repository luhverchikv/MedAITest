# MedAITest

**Открытая система для тестирования AI-моделей на медицинских экзаменах**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Stars](https://img.shields.io/github/stars/luhverchikv/MedAITest?style=social)

---

## Описание

MedAITest — это open-source инструмент для объективной оценки качества AI-моделей в решении медицинских тестовых задач.

Проект позволяет:
- Тестировать различные AI-модели на медицинских вопросах
- Сравнивать производительность разных моделей
- Находить проблемные вопросы в тестах
- Использовать модульную систему категорий

**Основная метрика:** Индекс Жаккара (Jaccard Index) — математически строгий показатель точности ответов.

---

## Возможности

| Функция | Описание |
|---------|----------|
| **Тестирование** | Запуск AI-моделей на медицинских вопросах |
| **Сравнение** | Сравнение результатов нескольких моделей |
| **Анализ ошибок** | Поиск вопросов с низким качеством ответов |
| **Модульные тесты** | Гибкая система категорий — добавляйте/удаляйте темы |
| **Экспорт** | JSON-экспорт результатов для анализа |
| **Jaccard Index** | Объективная метрика оценки ответов |

---

## Поддерживаемые категории

Система использует модульную структуру — вы можете загружать только нужные категории:

- Анафилаксия и шок
- Клиническая фармакология
- Неотложная помощь (реанимация, CPR)
- Медицина катастроф
- Биоэтика и медицинская этика
- Кардиология
- Токсикология
- Инфекционные болезни
- Доказательная медицина

**Хотите добавить свою категорию?** Это просто — создайте файл в формате `tests/*.txt`.

---

## Быстрый старт

### 1. Установка

```bash
# Клонирование репозитория
git clone https://github.com/luhverchikv/MedAITest.git
cd MedAITest

# Создание виртуального окружения (рекомендуется)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
```

### 2. Настройка API

Отредактируйте файл `.env`:

```env
VEDAI_API_KEY=your_api_key_here
VEDAI_BASE_URL=https://vedai.by/api/v1
```

> **Где взять API ключ?**
> Проект использует VedAI API (OpenAI-compatible). Вы можете использовать любой OpenAI-compatible endpoint.

### 3. Загрузка тестов

```bash
# Загрузить все тесты в базу данных
python load_data.py

# Посмотреть доступные категории
python load_data.py --list-categories

# Загрузить только определённые категории
python load_data.py --categories pharmacology emergency
```

### 4. Запуск теста

```bash
# Тест с моделью по умолчанию (50 вопросов)
python run_test.py

# Указать модель и количество вопросов
python run_test.py -m gemini-2.5-flash-lite -n 100

# Быстрый режим (без задержек)
python run_test.py -m gpt-5-nano -n 50 --fast
```

### 5. Анализ результатов

```bash
# Базовый анализ
python analyze.py --run 1

# Детальный анализ
python analyze.py --run 1 -d

# Сравнить несколько моделей
python analyze.py compare 1 2 3

# Найти сложные вопросы
python analyze.py hard -t 0.5
```

---

## Использование

### CLI — Основные команды

```bash
# Запуск теста
python run_test.py [OPTIONS]

# Опции:
#   -m, --model      Название модели (по умолчанию: gemma-3-27b-it:free)
#   -n, --questions  Количество вопросов (по умолчанию: все)
#   --fast           Режим без задержек

# Примеры:
python run_test.py -m gpt-5-mini -n 100
python run_test.py -m llama-4-maverick -n 50 --fast
```

### CLI — Анализ

```bash
# Анализ одного запуска
python analyze.py --run <ID> [-d]

# Сравнение запусков
python analyze.py compare <ID1> <ID2> ...

# Поиск сложных вопросов
python analyze.py hard [--threshold 0.5] [--runs ID1 ID2]

# Экспорт в JSON
python analyze.py --run 1 --json results.json
```

### CLI — Поиск подозрительных вопросов

```bash
# Найти вопросы, где все модели ошиблись одинаково
python find_bad_questions.py 1 2 3

# Сниженный порог (50% моделей)
python find_bad_questions.py 1 2 3 4 -t 0.5

# Детальный анализ конкретного вопроса
python find_bad_questions.py --detail 42 --runs 1 2 3
```

### CLI — Просмотр вопросов

```bash
# Список вопросов
python browse_questions.py -l 20

# Детали конкретного вопроса
python browse_questions.py -q 42

# Навигация по страницам
python browse_questions.py -l 10 -o 50
```

---

## Архитектура проекта

```
MedAITest/
├── ai_client.py          # Универсальный клиент для AI API
├── analyze.py            # Анализ результатов тестирования
├── browse_questions.py   # Просмотр вопросов в базе
├── config.py             # Конфигурация проекта
├── database.py           # Работа с SQLite базой данных
├── find_bad_questions.py  # Поиск проблемных вопросов
├── load_data.py          # Загрузка тестов в базу
├── parser.py             # Парсинг медицинских тестов
├── run_test.py           # Запуск AI на тестах
│
├── tests/                # Тестовые вопросы по категориям
│   ├── anaphylaxis.txt
│   ├── pharmacology.txt
│   └── ...
│
├── docs/                 # Документация
│   └── ANALYSIS.md       # Подробный анализ результатов
│
├── requirements.txt      # Python зависимости
├── .env.example          # Пример конфигурации
└── LICENSE              # MIT лицензия
```

---

## Индекс Жаккара — метрика оценки

Проект использует **индекс Жаккара** для объективной оценки качества ответов AI-моделей.

```
J(A, C) = |A ∩ C| / |A ∪ C|
```

Где:
- **A** — множество ответов AI
- **C** — множество правильных ответов
- **|A ∩ C|** — количество совпадений
- **|A ∪ C|** — количество уникальных элементов

### Интерпретация результатов

| Значение J | Значение |
|------------|---------|
| 1.0 | Идеальный ответ |
| 0.67 — 0.99 | Высокое совпадение |
| 0.33 — 0.66 | Среднее совпадение |
| 0.01 — 0.32 | Низкое совпадение |
| 0.0 | Полное несовпадение |

Подробнее: [ANALYSIS.md](docs/ANALYSIS.md)

---

## Добавление новых категорий

### 1. Создайте файл тестов

```bash
mkdir -p tests
touch tests/my_category.txt
```

### 2. Формат файла

```text
Вопрос 1: Какой симптом характерен для данного состояния?
1. Первый вариант ответа
2. Второй вариант ответа
3. Третий вариант ответа
4. Четвёртый вариант ответа
Правильный ответ: Второй вариант ответа

Вопрос 2: Какие симптомы наблюдаются? (несколько ответов)
1. Симптом А
2. Симптом Б
3. Симптом В
4. Симптом Г
Правильные ответы: Симптом А, Симптом Б
```

### 3. Загрузите в базу

```bash
python load_data.py --categories my_category
```

---

## Конфигурация

### Переменные окружения (.env)

```env
# VedAI API (обязательно)
VEDAI_API_KEY=your_api_key_here
VEDAI_BASE_URL=https://vedai.by/api/v1

# Опционально: другие настройки
MAX_QUESTIONS=100
REQUEST_DELAY=0.5
TEMPERATURE=0.3
```

### config.py

```python
# Основные настройки
DB_PATH = "test_database.sqlite"     # Путь к базе данных
INPUT_FILE = "tests_data.txt"        # Файл с тестами

# API настройки
VEDAI_API_KEY = ""                   # API ключ
VEDAI_BASE_URL = "https://vedai.by/api/v1"

# Модели для тестирования
DEFAULT_MODEL = "gemma-3-27b-it:free"

# Настройки тестирования
MAX_QUESTIONS = None                 # None = все вопросы
REQUEST_DELAY = 0.5                  # Задержка между запросами (сек)
TEMPERATURE = 0.3                    # Температура генерации
```

---

## Документация

- [ANALYSIS.md](docs/ANALYSIS.md) — Подробный анализ результатов
- [INSTALL.md](docs/INSTALL.md) — Инструкция по установке
- [USAGE.md](docs/USAGE.md) — Подробное использование

---

## Contributing

Мы приветствуем contributions! Пожалуйста, ознакомьтесь с [CONTRIBUTING.md](CONTRIBUTING.md).

### Как внести вклад

1. **Fork** репозитория
2. **Clone** вашу версию: `git clone https://github.com/YOUR_USERNAME/MedAITest.git`
3. **Создайте ветку**: `git checkout -b feature/amazing-feature`
4. **Commit** изменения: `git commit -m 'Add amazing feature'`
5. **Push** в ветку: `git push origin feature/amazing-feature`
6. **Откройте Pull Request**

### Типы contributions

- 🐛 Сообщения об ошибках
- 💡 Предложения новых функций
- 📚 Добавление тестовых вопросов
- 📖 Улучшение документации
- 🔧 Исправления в коде

---

## Лицензия

Проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).

```
MIT License

Copyright (c) 2026 luhverchikv

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Автор

**luhverchikv**
- GitHub: [@luhverchikv](https://github.com/luhverchikv)
- Repository: [https://github.com/luhverchikv/MedAITest](https://github.com/luhverchikv/MedAITest)

---

## Благодарности

- [VedAI](https://vedai.by) — за предоставление OpenAI-compatible API
- Сообщество open-source Python за вдохновение

---

**MedAITest** — объективная оценка AI в медицине 🏥
