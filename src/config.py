"""Конфигурация приложения: пути к шаблонам, выходным файлам и настройки."""

from pathlib import Path


# Базовая директория проекта
PROJECT_ROOT = Path(__file__).parent.parent

# Папки
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"
BACKUP_DIR = PROJECT_ROOT / "backup"

# Справочник сотрудников — общий для компании, не привязан к конкретному
# отчёту/проекту (см. src/services/employees_store.py). Реальные
# персональные данные, поэтому папка data/ в .gitignore.
DATA_DIR = PROJECT_ROOT / "data"
EMPLOYEES_FILE = DATA_DIR / "employees.json"
KLEISHE_DIR = DATA_DIR / "kleishe"

# Справочник приборов — тот же приём, что и справочник сотрудников: общий
# для компании, не привязан к конкретному отчёту/проекту (см.
# src/services/instruments_store.py).
INSTRUMENTS_FILE = DATA_DIR / "instruments.json"

# Пользовательские варианты титульного листа конструктора документов — тот
# же приём (см. src/services/title_variants_store.py). Встроенные варианты
# (TITLE_VARIANTS) в этот файл не попадают.
TITLE_VARIANTS_FILE = DATA_DIR / "title_variants.json"

# Пользовательские варианты вводной части конструктора документов -- второй,
# независимый слот наравне с титульным листом (см. src/services/
# intro_variants_store.py), отдельный JSON-файл, но переиспользует ту же
# модель TitleVariant (см. src/models/title_variant.py) и общий каталог
# плейсхолдеров title_variants_store.get_all_field_labels() -- ничего
# специфичного для титульного листа в самой модели нет (id/document_title/
# subtitle_fields/template_filename одинаково осмысленны и для вводной
# части), заводить отдельный почти идентичный dataclass не было смысла.
INTRO_VARIANTS_FILE = DATA_DIR / "intro_variants.json"

# Приложение, выбранное пользователем через «Открыть с помощью» для
# редактирования/просмотра .docx-файлов конструктора документов (см.
# src/ui/open_with.py) -- запоминается один раз, дальше open_with_prompt()
# открывает тем же приложением без повторного диалога выбора.
PREFERRED_EDITOR_FILE = DATA_DIR / "preferred_editor.json"

# Схемы НК (Приложение 7, трубопровод) — привязаны к конкретному отчёту
# (хранятся в report_data проекта как имя файла), но физически лежат в
# общей папке data/, как и клише — см. store_kleishe_image().
NK_SCHEME_DIR = DATA_DIR / "nk_schemes"

# График нагружения (Приложение 8, Рисунок 1, трубопровод) — тот же приём,
# что и NK_SCHEME_DIR.
PNEVMO_GRAPH_DIR = DATA_DIR / "pnevmo_graphs"

# Шаблоны
TEMPLATE_WORD = TEMPLATES_DIR / "Шаблон_финал.docx"
TEMPLATE_WORD_OLD = TEMPLATES_DIR / "Шаблон_баллоны_2.docx"
TEMPLATE_WORD_PIPELINE = TEMPLATES_DIR / "Шаблон_трубопровод.docx"

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
    for directory in [
        TEMPLATES_DIR, OUTPUT_DIR, BACKUP_DIR, DATA_DIR, KLEISHE_DIR,
        NK_SCHEME_DIR, PNEVMO_GRAPH_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def get_template_paths():
    """Получить все возможные пути к шаблонам (баллоны, для обратной совместимости)."""
    paths = [TEMPLATE_WORD]
    paths.extend(LEGACY_TEMPLATES)
    return paths


# Пути к шаблону по типу объекта. Новый тип добавляется отдельной записью,
# не меняя порядок поиска для существующих типов.
TEMPLATE_PATHS_BY_TYPE = {
    "balloon": get_template_paths(),
    "pipeline": [TEMPLATE_WORD_PIPELINE],
}


def find_template(equipment_type: str = "balloon"):
    """Найти первый доступный шаблон Word для указанного типа объекта."""
    paths = TEMPLATE_PATHS_BY_TYPE.get(equipment_type)
    if paths is None:
        raise ValueError(f"Неизвестный тип объекта: {equipment_type}")
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Не найден шаблон Word. Попробуйте поместить шаблон в: {TEMPLATES_DIR}"
    )


# Фрагменты-блоки конструктора документов (equipment_type == "constructor") --
# в отличие от TEMPLATE_PATHS_BY_TYPE, каждый файл тут маленький,
# самостоятельный кусок документа, а не целый отчёт. Phase 1: только
# варианты титульного листа (см. TITLE_VARIANTS, src/services/template_schema.py);
# Phase 2 добавит рядом такой же словарь под приложения.
FRAGMENTS_DIR = TEMPLATES_DIR / "fragments"


def find_title_template(variant_id: str):
    """Найти .docx-заготовку варианта титульного листа конструктора --
    встроенного (TITLE_VARIANTS) или пользовательского (title_variants_store,
    data/title_variants.json).

    Пользовательские варианты с этой версии не бывают "осиротевшими": их
    заготовка генерируется автоматически при создании («Добавить»,
    src/ui/main_window.py, _open_add_title_variant_dialog()) и как сеть
    безопасности при добавлении плейсхолдера, если файл пропал
    (_ensure_title_fragment_exists()), а не вручную через CLI.
    FileNotFoundError здесь теперь означает реальную поломку (файл удалили
    с диска руками), а не штатное "заготовку ещё не сгенерировали"."""
    # Импорт внутри функции: services/__init__.py эагерно тянет
    # calculations.py, а тот импортирует config.py -- импорт template_schema
    # на верхнем уровне этого модуля дал бы циклический импорт.
    from .services.template_schema import TITLE_VARIANTS
    from .services.title_variants_store import load_title_variants

    is_builtin = variant_id in TITLE_VARIANTS
    is_custom = any(v.id == variant_id for v in load_title_variants())
    if not is_builtin and not is_custom:
        raise ValueError(f"Неизвестный вариант титульного листа: {variant_id}")

    path = FRAGMENTS_DIR / f"title_{variant_id}.docx"
    if path.exists():
        return path
    if is_builtin:
        raise FileNotFoundError(
            f"Не найдена заготовка титульного листа «{variant_id}». Сгенерируйте её: "
            f"python scripts/template_tool.py generate-title {variant_id}"
        )
    raise FileNotFoundError(
        f"Не найдена заготовка титульного листа «{variant_id}» -- похоже, файл "
        f"{path} удалили вручную. Откройте вариант на редактирование и сохраните "
        f"ещё раз, чтобы перегенерировать заготовку."
    )


def find_intro_template(variant_id: str):
    """Найти .docx-заготовку варианта вводной части конструктора -- та же
    логика, что у find_title_template(), но со своим реестром (INTRO_VARIANTS)
    и своим пользовательским стором (intro_variants_store, data/
    intro_variants.json), а фрагмент лежит в FRAGMENTS_DIR под префиксом
    "intro_" вместо "title_"."""
    from .services.template_schema import INTRO_VARIANTS
    from .services.intro_variants_store import load_intro_variants

    is_builtin = variant_id in INTRO_VARIANTS
    is_custom = any(v.id == variant_id for v in load_intro_variants())
    if not is_builtin and not is_custom:
        raise ValueError(f"Неизвестный вариант вводной части: {variant_id}")

    path = FRAGMENTS_DIR / f"intro_{variant_id}.docx"
    if path.exists():
        return path
    if is_builtin:
        raise FileNotFoundError(
            f"Не найдена заготовка вводной части «{variant_id}». Сгенерируйте её: "
            f"python scripts/template_tool.py generate-intro {variant_id}"
        )
    raise FileNotFoundError(
        f"Не найдена заготовка вводной части «{variant_id}» -- похоже, файл "
        f"{path} удалили вручную. Откройте вариант на редактирование и сохраните "
        f"ещё раз, чтобы перегенерировать заготовку."
    )
