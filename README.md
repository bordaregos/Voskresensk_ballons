# Генератор заключений на баллоны

Приложение для генерации заключений на баллоны с автоматическим расчётом параметров и формированием документов Word и CSV.

## 🏗️ Архитектура проекта

```
voskresensk_ballons/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Конфигурация (пути, настройки)
│   ├── models/                   # Модели данных
│   │   ├── __init__.py
│   │   ├── balloon.py            # Баллон, его параметры
│   │   └── project.py            # Проект (сохранение/загрузка)
│   ├── services/                 # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── calculations.py       # Расчёты (толщина, прочность, овальность)
│   │   ├── generator.py          # Генерация Word/CSV документов
│   │   ├── importer.py           # Импорт данных (CSV/JSON)
│   │   └── exporter.py           # Экспорт данных (CSV/JSON)
│   ├── ui/                       # UI layer
│   │   ├── __init__.py
│   │   ├── designer/             # UI designer files
│   │   │   └── main_window.ui    # Главное окно (Qt Designer)
│   │   └── file_handler.py       # Обработчик файлов (импорт/экспорт)
│   └── utils/                    # Утилиты
│       ├── __init__.py
│       ├── validators.py         # Валидация входных данных
│       └── date_formatter.py     # Форматирование дат
├── templates/                    # Шаблоны Word
│   ├── Плейсхолдеры_шаблона.docx
│   ├── Шаблон_баллоны_2.docx
│   └── Шаблон_финал.docx
├── output/                       # Выходные файлы
├── Dockerfile                    # Docker конфигурация
├── docker-compose.yml            # Docker Compose конфигурация
├── .gitignore                    # Git игнорируемые файлы
├── .dockerignore                 # Docker игнорируемые файлы
├── ui_logic.py                   # UI logic (использует src/ui/designer)
├── main.py                       # Точка входа
└── requirements.txt              # Зависимости
```

## 📋 Описание слоёв

### 1. **Models** (Модели данных)
- `Balloon` - модель баллона с параметрами
- `Report` - модель заключения на баллоны
- `Project` - модель проекта для сохранения/загрузки

### 2. **Services** (Бизнес-логика)
- `CalculationsService` - расчёты прочности, толщины, овальности, твёрдости
- `DocumentGenerator` - генерация Word и CSV документов
- `CSVImporter/JSONImporter` - импорт данных
- `Exporter` - экспорт данных

### 3. **Utils** (Утилиты)
- `InputValidator` - валидация входных данных
- `format_russian_date` - форматирование дат в русский формат

### 4. **UI** (Графический интерфейс)
- `FileHandler` - обработчик файлов (импорт/экспорт)
- `MainWindow` - главное окно приложения
- Связывает модели и сервисы

## 🚀 Установка

### Вариант 1: Через Docker (рекомендуется)

```bash
# Сборка образа
docker-compose build

# Запуск
docker-compose up

# Или в фоновом режиме
docker-compose up -d

# Остановка
docker-compose down

# Логи
docker-compose logs -f
```

### Вариант 2: Локальная установка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск приложения
python main.py
```

## 📝 Структура данных

### Поля формы
- **Номер заключения**, **Регистрационный номер**
- **Данные о секции**: название, дата ввода, среда
- **Геометрия**: диаметр, длина, толщина
- **Параметры**: давление, материал, ГОСТ
- **Таблица баллонов**: заводские номера, толщина, годы

### Расчёты
1. **Прочность** - напряжения, расчётные толщины
2. **Овальность** - проверка формы баллона
3. **Твёрдость** - по ГОСТ
4. **Коррозия** - скорость и остаточный ресурс

### Документы
- **Word** - заключение по шаблону
- **CSV** - таблица с данными баллонов

## 📂 Импорт/Экспорт данных

### CSV импорт
Загрузка баллонов из CSV файла:

```csv
зав№;Sмин;Sмакс;Год изготовления
001;26.5;28.0;2024
002;26.3;27.8;2024
```

Кнопка: **"Импорт CSV"** → загружает данные в таблицу баллонов

### CSV экспорт
Сохранение баллонов в CSV файл:

Кнопка: **"Экспорт CSV"** → сохраняет данные из таблицы

### JSON проект
Сохранение/загрузка полного состояния проекта:

Кнопки:
- **"Сохранить проект"** → сохраняет всё в JSON
- **"Открыть проект"** → загружает проект из JSON

Сохраняет:
- Все поля формы
- Таблицу баллонов
- Настройки

## 🛠️ Использование новых сервисов

### Расчёты
```python
from src.services.calculations import CalculationsService

# Расчёт прочности
results = CalculationsService.calculate_strength(
    working_pressure=39.0,
    hydro_test_pressure=59.0,
    pneumatic_test_pressure=45.0,
    inner_diameter=411.0,
    min_yield_strength=898.0,
    min_ultimate_strength=981.0,
    wall_thickness=28.0
)

print(f"Расчётное напряжение: {results.sigma}")
print(f"Расчётная толщина: {results.s_rasch}")
```

### Генерация документов
```python
from src.services.generator import DocumentGenerator
from src.models.balloon import Report, Balloon

# Создание заключения
report = Report(
    report_number="001",
    registration_number="63761",
    working_pressure=39.0,
    # ...
)

# Генерация
generator = DocumentGenerator()
output_path = generator.generate_report(report, output_dir="output")
print(f"Документ сохранён: {output_path}")
```

### Импорт/Экспорт
```python
from src.services.importer import import_balloon_list_from_csv
from src.services.exporter import export_balloon_list_to_csv
from src.models.project import Project

# Импорт CSV
balloons = import_balloon_list_from_csv(Path("balloons.csv"))

# Экспорт CSV
export_balloon_list_to_csv(balloons, Path("output.csv"))

# Сохранение проекта
project = Project(report_data=data, balloons_data=balloons)
project.save_to_file(Path("project.json"))

# Загрузка проекта
project = Project.load_from_file(Path("project.json"))
```

## 📊 Преимущества новой архитектуры

| Критерий | Было | Стало |
|----------|------|-------|
| Тестируемость | ❌ | ✅ Юнит-тесты сервисов |
| Поддерживаемость | ❌ Смешанная логика | ✅ Разделение ответственности |
| Расширяемость | ❌ | ✅ Легко добавлять сервисы |
| Перес используемость | ❌ Дублирование | ✅ Общие сервисы |
| Читаемость | ❌ 90+ строк в одном файле | ✅ Каждый файл ~200-300 строк |

## 📂 Старый код

Старый код сохранён в `ui_logic.py` для совместимости. Он использует новые сервисы из `src/` и загружает UI из `src/ui/designer/main_window.ui`.

## 📂 Перемещение UI файлов

Версия 5.3 (текущая):
- UI файлы вынесены в отдельный модуль `src/ui/designer/`
- Текущий UI: `src/ui/designer/main_window.ui`
- Удалены старые версии UI файлов
- Удалены пустые `tests/` и `backup/` директории

## 🐳 Docker

Проект поддерживает Docker для изоляции зависимостей и простоты развёртывания.

### Структура Docker

- `Dockerfile` - конфигурация образа с PyQt6 и X11
- `docker-compose.yml` - compose файл для удобного запуска
- `.dockerignore` - игнорируемые файлы при сборке
- `docker-start.sh` - скрипт запуска с поддержкой X11

### Использование

```bash
# Сборка образа
docker-compose build

# Запуск контейнера
docker-compose up

# Запуск в фоновом режиме
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f

# Пересборка после изменений
docker-compose up --build
```

### Использование с GUI (X11 forwarding)

Для работы с GUI нужно:
1. Установить XQuartz на macOS или X11 на Linux
2. Запустить с X11 forwarding:

```bash
# macOS с XQuartz
docker-compose run --rm -e DISPLAY=host.docker.internal:0 ballons

# Linux с X11
docker-compose run --rm -e DISPLAY=$DISPLAY ballons
```

### Монтирование томов

- `./templates` - шаблоны Word (только чтение)
- `./output` - выходные файлы (чтение/запись)
- `.` - исходный код (для разработки)

## 🔮 Планы развития

- [ ] Добавить юнит-тесты для всех сервисов
- [ ] Рефакторинг UI в новую архитектуру
- [ ] Добавить графики и визуализацию
- [ ] История заключений
- [ ] Логирование ошибок
- [ ] Экспорт в PDF

## 📄 Лицензия

Proprietary - Voskresensk Ballons

## 👨‍💻 Автор

Разработано для ОАО "Химмаш"
