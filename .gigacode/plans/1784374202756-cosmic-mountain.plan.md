# Архитектура проекта: Генератор заключений на баллоны

## Текущее состояние

Проект представляет собой desktop-приложение на Python/PyQt6 для генерации заключений на баллоны:
- **ui_logic.py** - основной GUI с 90+ строками кода, смешивающая логику интерфейса и бизнес-логику
- **common/** - устаревшая CLI-версия с функциями генерации данных
- **Шаблон_финал.docx** - Word-шаблон для документации

### Проблемы текущей архитектуры

1. **Смешение ответственности** - UI логика, расчёты и генерация документов в одном классе
2. **Отсутствие модульности** - функции分布在 по разным файлам без чёткой структуры
3. **Сложность тестирования** - невозможно юнит-тестировать расчёты без запуска GUI
4. **Дублирование кода** - логика есть и в `common/main.py` и в `ui_logic.py`
5. **Отсутствие валидации** - нет проверки корректности входных данных
6. **Hardcoded пути** - шаблоны и выходные файлы без конфигурации

---

## Предлагаемая архитектура (Layered Architecture)

```
voskresensk_ballons/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Конфигурация (пути, настройки)
│   ├── models/                   # Модели данных
│   │   ├── __init__.py
│   │   ├── balloon.py            # Баллон, его параметры
│   │   └── report.py             # Заключение
│   ├── services/                 # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── calculations.py       # Расчёты (толщина, прочность, овальность)
│   │   └── generator.py          # Генерация Word/CSV документов
│   ├── ui/                       # UI layer
│   │   ├── __init__.py
│   │   ├── main_window.py        # Главное окно (связывает модели и сервисы)
│   │   └── widgets.py            # Кастомные виджеты
│   └── utils/                    # Утилиты
│       ├── __init__.py
│       ├── validators.py         # Валидация входных данных
│       └── date_formatter.py     # Форматирование дат
├── tests/
│   ├── __init__.py
│   ├── test_calculations.py      # Юнит-тесты расчётов
│   └── test_generator.py         # Тесты генерации
├── templates/
│   ├── Шаблон_финал.docx
│   └── (другие шаблоны)
├── requirements.txt
└── main.py                       # Точка входа
```

---

## Детальное описание слоёв

### 1. **Models (Модели данных)**

```python
# src/models/balloon.py
@dataclass
class Balloon:
    """Модель баллона"""
    serial_number: str
    min_thickness: float
    max_thickness: float
    year_of_manufacture: int
    measurements: List[float] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Валидация данных баллона"""
        pass
```

```python
# src/models/report.py
@dataclass
class Report:
    """Модель заключения"""
    report_number: str
    registration_number: str
    balloons: List[Balloon]
    operating_pressure: float
    test_pressure: float
    # ... другие поля
```

### 2. **Services (Бизнес-логика)**

```python
# src/services/calculations.py
class CalculationsService:
    """Сервис расчётов"""
    
    @staticmethod
    def calculate_min_thickness(thickness_measurements: List[float]) -> float:
        """Расчёт минимальной толщины"""
        return min(thickness_measurements)
    
    @staticmethod
    def calculate_strength(
        working_pressure: float,
        hydro_test_pressure: float,
        inner_diameter: float,
        material_yield: float,
        material_ultimate: float,
        wall_thickness: float
    ) -> StrengthResults:
        """Расчёт прочности"""
        pass
    
    @staticmethod
    def calculate_ovalness(d_min: float, d_max: float) -> float:
        """Расчёт овальности"""
        pass
    
    @staticmethod
    def calculate_hardness(ultimate_strength: float) -> Tuple[float, float]:
        """Расчёт твёрдости по ГОСТ"""
        pass
    
    @staticmethod
    def calculate_corrosion_rate(
        current_thickness: float,
        original_thickness: float,
        corrosion_allowance: float,
        years_of_operation: float
    ) -> CorrosionResults:
        """Расчёт скорости коррозии и остаточного ресурса"""
        pass
```

```python
# src/services/generator.py
class DocumentGenerator:
    """Генератор документов"""
    
    def __init__(self, template_path: str):
        self.template_path = template_path
    
    def generate_report(self, report: Report, output_path: str) -> str:
        """Генерация Word-документа"""
        pass
    
    def generate_csv(self, report: Report, output_path: str) -> str:
        """Генерация CSV-файла"""
        pass
```

### 3. **UI Layer**

```python
# src/ui/main_window.py
class MainWindow(QMainWindow):
    def __init__(self, 
                 calculations_service: CalculationsService,
                 generator: DocumentGenerator):
        self.calculations_service = calculations_service
        self.generator = generator
        # Инициализация UI
    
    def on_generate_clicked(self):
        """Обработка генерации заключения"""
        try:
            # Валидация
            data = self.validate_input()
            
            # Создание модели
            report = self.build_report(data)
            
            # Расчёты
            results = self.calculations_service.calculate_all(report)
            
            # Генерация
            output_path = self.generator.generate_report(report, self.config.output_dir)
            
            self.show_success(output_path)
        except ValidationException as e:
            self.show_error(str(e))
```

### 4. **Utils**

```python
# src/utils/validators.py
class InputValidator:
    """Валидатор входных данных"""
    
    @staticmethod
    def validate_non_empty(value: str, field_name: str) -> None:
        pass
    
    @staticmethod
    def validate_positive_number(value: str, field_name: str) -> float:
        pass
    
    @staticmethod
    def validate_thickness_range(thickness: float, min_allowed: float, max_allowed: float) -> None:
        pass
```

---

## План рефакторинга

### Etап 1: Базовая структура
1. Создать `src/` с подпапками
2. Создать `src/config.py` с настройками
3. Создать `src/models/` с базовыми классами
4. Создать `requirements.txt`

### Этап 2: Модели данных
1. `src/models/balloon.py` - класс Balloon
2. `src/models/report.py` - класс Report
3. Добавить dataclass-декораторы

### Этап 3: Бизнес-логика
1. `src/services/calculations.py` - вынести расчёты из ui_logic.py
2. `src/services/generator.py` - вынести генерацию документов
3. Сделать функции статическими/методами классов

### Этап 4: UI layer
1. `src/ui/main_window.py` - рефакторинг ui_logic.py
2. Внедрить зависимости (calculations_service, generator)
3. Добавить валидацию через `InputValidator`

### Этап 5: Утилиты и тесты
1. `src/utils/validators.py` - валидация
2. `src/utils/date_formatter.py` - форматирование дат
3. `tests/test_calculations.py` - юнит-тесты
4. `main.py` - точка входа

### Этап 6: Документация
1. README.md с инструкциями
2. CHANGELOG.md для версий
3. Документация по API

---

## Преимущества новой архитектуры

| Критерий | Было | Стало |
|----------|------|-------|
| Тестируемость | ❌ Нет юнит-тестов | ✅ Юнит-тесты сервисов |
| Поддерживаемость | ❌ Смешанная логика | ✅ Разделение ответственности |
| Расширяемость | ❌ Тяжело добавлять функции | ✅ Легко добавлять сервисы |
| Перес используемость | ❌ CLI и GUI дублируют логику | ✅ Общие сервисы |
| Читаемость | ❌ 90+ строк в одном файле | ✅ Каждый файл ~200-300 строк |

---

## Пример миграции кода

**Было (ui_logic.py):**
```python
def prochnost(self):
    try:
        pred_tek_min = float(self.pred_tek_min.toPlainText().replace(",", "."))
        # ... 50+ строк
```

**Стало (src/services/calculations.py):**
```python
@dataclass
class StrengthResults:
    sigma: float
    sigma_gidro: float
    s_rasch: float
    s_rasch_gidro: float
    s_max_rasch: float
    p_dop: float

class CalculationsService:
    @staticmethod
    def calculate_strength(
        working_pressure: float,
        hydro_test_pressure: float,
        pneumatic_test_pressure: float,
        inner_diameter: float,
        min_yield_strength: float,
        min_ultimate_strength: float,
        wall_thickness: float
    ) -> StrengthResults:
        """Расчёт прочности баллона"""
        sigma = 1.0 * min(min_yield_strength / 1.5, min_ultimate_strength / 2.4)
        sigma_gidro = min_yield_strength / 1.1
        
        s_rasch = round(((inner_diameter + (wall_thickness * 2)) * working_pressure) / 
                       (2 * sigma + working_pressure), 1)
        # ... остальные расчёты
```

---

## Следующие шаги

1. **Утвердить архитектуру** - согласовать структуру
2. **Создать базовую структуру** - папки и заглушки
3. **Мигрировать расчёты** - вынести логику в services
4. **Рефакторить UI** - использовать новые сервисы
5. **Добавить тесты** - покрыть критичные расчёты
6. **Документировать** - написать README

---

## Вопросы для уточнения

1. **Генерация CSV** - используется ли эта функциональность? В `ui_logic.py` есть `generate_csv()` но она пустая.

2. **Весы (tests.py)** - используется ли класс `Scales`? Похож на тестовый пример, но может быть полезен.

3. **Графики/отчёты** - планируется ли добавление визуализации результатов (графики толщины, коррозии)?

4. **База данных** - нужна ли история заключений или только одиночные генерации?

5. **Логирование** - нужно ли логирование ошибок в файл?
