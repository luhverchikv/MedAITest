# MedAITest

**Открытая система для тестирования AI-моделей на медицинских экзаменах**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Stars](https://img.shields.io/github/stars/luhverchikv/MedAITest?style=social)

---

## Описание

MedAITest — это open-source платформа для объективной оценки AI-моделей в решении медицинских тестовых задач.

### Ключевые возможности

| Функция | Описание |
|---------|----------|
| **Множественные тесты** | Управляйте несколькими тестами одновременно |
| **Обмен тестами** | Экспортируйте и импортируйте тесты в JSON |
| **Сравнение моделей** | Оценивайте разные AI-системы |
| **Анализ ошибок** | Находите проблемные вопросы |
| **Индекс Жаккара** | Объективная метрика оценки |

---

## Установка

```bash
# Клонирование репозитория
git clone https://github.com/luhverchikv/MedAITest.git
cd MedAITest

# Установка зависимостей
pip install -r requirements.txt

# Настройка
cp .env.example .env
# Добавьте API ключ в .env
```

---

## Быстрый старт

### 1. Загрузка тестов

```bash
# Загрузить все тесты из папки tests/
python manage_tests.py --import-folder tests/

# Или загрузить отдельный файл
python manage_tests.py --import tests/pharmacology.txt
```

### 2. Просмотр тестов

```bash
# Список всех тестов
python manage_tests.py --list

# Статистика базы
python manage_tests.py --stats

# Детали конкретного теста
python manage_tests.py --show 1
```

### 3. Запуск теста

```bash
# Запустить тест по ID
python run_test.py --test-id 1

# Запустить по имени
python run_test.py --test-name "Pharmacology"

# С указанием модели
python run_test.py --test-id 1 -m gemini-2.5-flash-lite
```

### 4. Анализ результатов

```bash
# Анализ запуска
python analyze.py --run 1 -d

# Сравнить запуски
python analyze.py compare 1 2 3

# Найти сложные вопросы
python analyze.py hard --test 1
```

---

## Управление тестами

### Создание тестов

```bash
# Интерактивное создание
python manage_tests.py --create

# Импорт из JSON
python manage_tests.py --import my_test.json
```

### Формат JSON для импорта

```json
{
  "format_version": "1.0",
  "test": {
    "name": "Кардиология 2024",
    "description": "Тест по кардиологии для врачей",
    "category": "Кардиология",
    "difficulty": "medium",
    "author": "Иванов И.И.",
    "source": "Учебник по кардиологии"
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

### Экспорт тестов

```bash
# Экспорт теста в JSON
python manage_tests.py --export 1

# Экспорт в конкретный файл
python manage_tests.py --export 1 -o my_pharmacology.json
```

### Обмен тестами

1. **Экспортируйте** свой тест:
   ```bash
   python manage_tests.py --export 1 -o cardiology_test.json
   ```

2. **Поделитесь** файлом с коллегами

3. **Коллеги импортируют**:
   ```bash
   python manage_tests.py --import cardiology_test.json
   ```

---

## Структура проекта

```
MedAITest/
├── ai_client.py          # Клиент для AI API
├── analyze.py            # Анализ результатов
├── browse_questions.py   # Просмотр вопросов
├── config.py             # Конфигурация
├── database.py           # База данных (SQLite)
├── find_bad_questions.py # Поиск проблемных вопросов
├── manage_tests.py       # Управление тестами ⭐
├── parser.py            # Парсинг тестов
├── run_test.py          # Запуск тестов ⭐
│
├── tests/                # Папка с тестами
│   ├── anaphylaxis.txt
│   ├── pharmacology.txt
│   ├── emergency.txt
│   └── ...
│
├── docs/                 # Документация
└── tests_data/           # Архивные данные
```

---

## CLI команды

### manage_tests.py — Управление тестами

| Команда | Описание |
|---------|----------|
| `--list` | Список всех тестов |
| `--stats` | Статистика базы |
| `--show <ID>` | Детали теста |
| `--create` | Создать тест |
| `--import <file>` | Импорт из файла |
| `--import-folder <path>` | Импорт из папки |
| `--export <ID>` | Экспорт теста |
| `--delete <ID>` | Удалить тест |

### run_test.py — Запуск тестов

| Команда | Описание |
|---------|----------|
| `--test-id <ID>` | ID теста |
| `--test-name <name>` | Имя теста |
| `--list-tests` | Список тестов |
| `-m <model>` | Модель AI |
| `-n <count>` | Количество вопросов |

### analyze.py — Анализ

| Команда | Описание |
|---------|----------|
| `--list` | Список запусков |
| `--run <ID>` | Анализ запуска |
| `-d` | Детальный вывод |
| `compare <ID1> <ID2>` | Сравнение запусков |
| `hard` | Сложные вопросы |

---

## Добавление собственных тестов

### 1. Через текстовый файл (.txt)

Создайте файл `my_test.txt`:

```text
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

Загрузите:
```bash
python manage_tests.py --import my_test.txt
```

### 2. Через JSON (для обмена)

Создайте файл `my_test.json` по формату выше и импортируйте:
```bash
python manage_tests.py --import my_test.json
```

---

## Документация

- [ANALYSIS.md](docs/ANALYSIS.md) — Подробный анализ результатов
- [INSTALL.md](docs/INSTALL.md) — Инструкция по установке
- [USAGE.md](docs/USAGE.md) — Подробное использование

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

## Автор

**luhverchikv**
- GitHub: [@luhverchikv](https://github.com/luhverchikv)

---

**MedAITest** — объективная оценка AI в медицине 🏥
