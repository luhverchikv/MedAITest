# MedAITest

**Открытая платформа для тестирования AI-моделей на медицинских экзаменационных вопросах**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![GitHub stars](https://img.shields.io/github/stars/luhverchikv/MedAITest?style=social)

---

## Описание

MedAITest — это open-source платформа для объективной оценки AI-моделей в решении медицинских тестовых задач. Использует **индекс Жаккара** для точной оценки ответов.

### Ключевые возможности

| Функция | Описание |
|---------|----------|
| **Множественные тесты** | Управляйте несколькими тестами одновременно |
| **Обмен тестами** | Экспортируйте и импортируйте тесты в JSON |
| **Сравнение моделей** | Оценивайте разные AI-системы на одних данных |
| **Анализ ошибок** | Находите проблемные вопросы |
| **Индекс Жаккара** | Объективная метрика оценки точности |

---

## Быстрый старт

### 1. Установка

```bash
git clone https://github.com/luhverchikv/MedAITest.git
cd MedAITest
pip install -r requirements.txt
cp .env.example .env
# Добавьте API ключ в .env
```

### 2. Загрузка тестов

```bash
python manage_tests.py --import-folder tests/
```

### 3. Запуск теста

```bash
python run_test.py --test-id 1 -m gemini-2.5-flash-lite
```

### 4. Анализ результатов

```bash
python analyze.py --run 1 -d
```

---

## Структура проекта

```
MedAITest/
├── manage_tests.py        # Управление тестами
├── run_test.py           # Запуск тестов
├── analyze.py             # Анализ результатов
├── find_bad_questions.py   # Поиск проблемных вопросов
├── database.py            # SQLite база данных
├── config.py              # Конфигурация
├── ai_client.py           # AI API клиент
├── parser.py              # Парсинг тестов
├── tests/                 # Папка с тестами
├── logs/                  # Логи запусков
├── docs/                  # Документация
└── requirements.txt
```

---

## CLI команды

### manage_tests.py — Управление тестами

| Команда | Описание |
|---------|----------|
| `--list` | Список всех тестов |
| `--stats` | Статистика базы |
| `--show <id>` | Детали теста |
| `--create` | Создать тест |
| `--import <file>` | Импорт из файла |
| `--import-folder <path>` | Импорт из папки |
| `--export <id>` | Экспорт теста |
| `--delete <id>` | Удалить тест |

### run_test.py — Запуск тестов

| Команда | Описание |
|---------|----------|
| `--test-id <id>` | ID теста |
| `--test-name <name>` | Имя теста |
| `--list-tests` | Список тестов |
| `-m <model>` | Модель AI |
| `-n <num>` | Количество вопросов |

### analyze.py — Анализ

| Команда | Описание |
|---------|----------|
| `--list` | Список запусков |
| `--run <id>` | Анализ запуска |
| `-d` | Детальный вывод |
| `compare <ids>` | Сравнение запусков |
| `hard` | Сложные вопросы |

---

## Добавление собственных тестов

### Текстовый формат (.txt)

Создайте файл `my_test.txt`:

```
Вопрос 1: Какой симптом характерен для гипертонии?
1. Головная боль
2. Кашель
3. Тошнота
Правильный ответ: Головная боль

Вопрос 2: Какие препараты применяются при гипертонии? (несколько)
1. Амлодипин
2. Метформин
3. Индапамид
4. Аспирин
Правильные ответы: Амлодипин, Индапамид
```

Импортируйте:

```bash
python manage_tests.py --import my_test.txt
```

### JSON формат (для обмена)

```json
{
  "format_version": "1.0",
  "test": {
    "name": "Кардиология 2024",
    "description": "Тест по кардиологии",
    "category": "Кардиология",
    "difficulty": "medium",
    "author": "Иванов И.И."
  },
  "questions": [
    {
      "text": "Какой препарат применяется при острой сердечной недостаточности?",
      "is_multiple": false,
      "correct_indices": [2],
      "options": [
        {"index": 1, "text": "Аспирин"},
        {"index": 2, "text": "Дигоксин"},
        {"index": 3, "text": "Метформин"}
      ]
    }
  ]
}
```

---

## Документация

Подробная документация доступна в папке [docs/](docs/):

| Файл | Описание |
|------|----------|
| [01_INSTALL.md](docs/01_INSTALL.md) | Установка и настройка |
| [02_TEST_MANAGEMENT.md](docs/02_TEST_MANAGEMENT.md) | Управление тестами |
| [03_RUNNING_TESTS.md](docs/03_RUNNING_TESTS.md) | Запуск тестов |
| [04_ANALYSIS.md](docs/04_ANALYSIS.md) | Анализ результатов |
| [05_FIND_BAD_QUESTIONS.md](docs/05_FIND_BAD_QUESTIONS.md) | Поиск проблемных вопросов |

---

## Индекс Жаккара

Для оценки качества ответов используется **индекс Жаккара**:

```
J(A, C) = |A ∩ C| / |A ∪ C|
```

- **A** — множество ответов AI
- **C** — множество правильных ответов
- **1.0** = идеальное совпадение
- **0.0** = полное несовпадение

Подробнее: [04_ANALYSIS.md](docs/04_ANALYSIS.md)

---

## Contributing

Мы приветствуем contributions!

1. Fork репозитория
2. Создайте ветку: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Pull Request

---

## Лицензия

MIT License — подробности в [LICENSE](LICENSE)

---

## Отказ от ответственности

> **Важно**: Результаты тестирования предназначены исключительно для исследовательских целей и не должны использоваться для принятия клинических решений без экспертной валидации.

---

## Автор

**luhverchikv** — [GitHub](https://github.com/luhverchikv)

---

**MedAITest** — объективная оценка AI в медицине
