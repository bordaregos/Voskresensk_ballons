"""Конфигурация приложения: пути к шаблонам, выходным файлам и настройки."""

from pathlib import Path


# Базовая директория проекта
PROJECT_ROOT = Path(__file__).parent.parent

# Папки
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"
BACKUP_DIR = PROJECT_ROOT / "backup"

# Шаблоны
TEMPLATE_WORD = TEMPLATES_DIR / "Шаблон_финал.docx"
TEMPLATE_WORD_OLD = TEMPLATES_DIR / "Шаблон_баллоны_2.docx"

# Пути к старым шаблонам (для совместимости)
LEGACY_TEMPLATES = [
    PROJECT_ROOT / "Рыба" / "Шаблон_баллоны_2.docx",
]

# Настройки по умолчанию
DEFAULT_SETTINGS = {
    "working_pressure": 39.0,  # МПа
    "hydro_test_pressure": 59.0,  # МПа
    "pneumatic_test_pressure": 45.0,  # МПа
    "coefficient_safety_yield": 1.5,
    "coefficient_safety_ultimate": 2.4,
    "coefficient_hydro": 1.1,
    "max_ovalness": 0.005,  # 0.5%
    "corrosion_allowance_min": 0.0,
    "corrosion_allowance_max": 2.0,
    "min_thickness_for_recalc": 1.0,
}

# Настройки форматирования
FORMAT_SETTINGS = {
    "decimal_separator": ".",
    "date_format": "%d.%m.%Y",
    "russian_date_format": '"{day}" {month} {year}г.',
    "csv_delimiter": ";",
    "csv_encoding": "utf-8-sig",
}

# Мapped constants (для ГОСТ)
GOST_RMC_RANGE = {
    "min": 898,  # МПа
    "max": 981,  # МПа
}

GOST_HARDNESS_COEFFICIENT = 2.7
GOST_HARDNESS_ALLOWANCE = 20


def ensure_directories():
    """Создание необходимых директорий, если их нет."""
    for directory in [TEMPLATES_DIR, OUTPUT_DIR, BACKUP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_template_paths():
    """Получить все возможные пути к шаблонам."""
    paths = [TEMPLATE_WORD]
    paths.extend(LEGACY_TEMPLATES)
    return paths


def find_template():
    """Найти первый доступный шаблон."""
    for path in get_template_paths():
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Не найден шаблон Word. Попробуйте поместить шаблон в: {TEMPLATES_DIR}"
    )
