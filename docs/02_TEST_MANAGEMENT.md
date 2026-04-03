# Управление тестами

## Обзор

`manage_tests.py` — CLI-инструмент для управления тестами в базе данных.

```bash
python manage_tests.py [команда]
```

## Команды

### Просмотр тестов

```bash
# Список всех тестов
python manage_tests.py --list

# Статистика базы данных
python manage_tests.py --stats

# Детали конкретного теста
python manage_tests.py --show 1
```

### Импорт тестов

```bash
# Импорт одного файла
python manage_tests.py --import tests/emergency.txt

# Импорт из JSON
python manage_tests.py --import my_test.json

# Импорт всех файлов из папки
python manage_tests.py --import-folder tests/
```

### Экспорт тестов

```bash
# Экспорт по ID
python manage_tests.py --export 1

# Экспорт в конкретный файл
python manage_tests.py --export 1 -o backup.json
```

### Управление тестами

```bash
# Создать новый тест (интерактивно)
python manage_tests.py --create

# Удалить тест (с подтверждением)
python manage_tests.py --delete 1

# Удалить навсегда
python manage_tests.py --delete 1 --permanent
```

## Форматы файлов

### Текстовый формат (.txt)

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

### JSON формат

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

## Обмен тестами

### Экспорт и передача

1. Экспортируйте тест:
   ```bash
   python manage_tests.py --export 1 -o cardiology.json
   ```

2. Поделитесь файлом `cardiology.json` с коллегами

### Импорт от коллег

```bash
python manage_tests.py --import cardiology.json
```

> JSON-файлы включают MD5-checksum для проверки целостности.

## Структура базы данных

```
tests/
├── id (INTEGER PRIMARY KEY)
├── name (TEXT)
├── description (TEXT)
├── source (TEXT)
├── author (TEXT)
├── category (TEXT)
├── difficulty (TEXT)
├── is_active (BOOLEAN)
└── created_at (TIMESTAMP)

questions/
├── id (INTEGER PRIMARY KEY)
├── test_id (INTEGER FK)
├── text (TEXT)
├── is_multiple (BOOLEAN)
├── correct_indices (TEXT)
├── external_id (TEXT)
└── explanation (TEXT)

options/
├── id (INTEGER PRIMARY KEY)
├── question_id (INTEGER FK)
├── index (INTEGER)
└── text (TEXT)
```

## Устранение проблем

### Ошибка "database is locked"

```bash
# Закройте другие процессы, использующие базу
# Или увеличьте timeout в config.py
```

### Неверный формат файла

```bash
# Проверьте кодировку файла (должна быть UTF-8)
file my_test.txt

# Конвертируйте, если нужно
iconv -f CP1251 -t UTF-8 old.txt > new.txt
```
