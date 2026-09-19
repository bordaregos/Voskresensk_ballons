"""Хранение пользовательских вариантов титульного листа конструктора
документов: JSON-файл, тот же приём, что employees_store.py/
instruments_store.py -- не зависит от Qt.

Встроенные варианты (TITLE_VARIANTS, src/services/template_schema.py)
живут в коде и через этот стор не редактируются -- get_all_title_variants()
только добавляет к ним пользовательские, id которых генерируется в UI-слое
(uuid4().hex[:8], тот же приём, что src/ui/employees_tab.py) и поэтому не
пересекается с "otchet"/"zaklyuchenie".

Файл хранит ЧЕТЫРЕ независимые секции -- "title_variants" (сами варианты),
"field_catalog" (id -> человекочитаемая подпись поля-плейсхолдера,
переиспользуется между вариантами при вставке через каталог плейсхолдеров,
см. src/ui/main_window.py, _build_placeholder_menu()), "hidden_builtin_fields"
(id встроенных полей TITLE_FIELD_LABELS, скрытых оператором через корзину в
том же меню -- сама константа в коде не трогается, "удаление" встроенного
поля -- это его id в списке-исключении, см. get_all_field_labels()) и
"field_formulas" (id -> {"tokens":.., "decimals":..} -- формула
вычисляемого поля, см. src/services/formula_engine.py и редактор формул,
src/ui/formula_editor_dialog.py; открывается через ПКМ на чипе плейсхолдера
в реквизитах, «Создать формулу»). Формула, как и подпись поля,
привязана к field_id в общем каталоге -- одна формула действует везде, где
встречается этот плейсхолдер (любой слот, любой вариант), а не только там,
где её создали. save_title_variants()/save_field_catalog()/
save_hidden_builtin_fields()/save_field_formulas() поэтому читают-правят-
пишут файл целиком (read-modify-write), а не перезаписывают его слепо
целиком своей секцией -- иначе сохранение одной секции стирало бы другие."""

import json
from pathlib import Path
from typing import Dict, List

from ..config import TITLE_VARIANTS_FILE
from ..models.title_variant import TitleVariant
from .template_schema import TITLE_FIELD_LABELS, TITLE_VARIANTS, TitleConfig


def _load_raw(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _save_raw(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_title_variants(path: Path = TITLE_VARIANTS_FILE) -> List[TitleVariant]:
    """Загружает пользовательские варианты титульного листа из JSON.

    Если файла ещё нет (первый запуск, или ни одного варианта ещё не
    добавили), возвращает пустой список.
    """
    data = _load_raw(path)
    return [TitleVariant.from_dict(item) for item in data.get('title_variants', [])]


def save_title_variants(variants: List[TitleVariant], path: Path = TITLE_VARIANTS_FILE) -> None:
    """Сохраняет пользовательские варианты титульного листа в JSON, не трогая
    соседнюю секцию field_catalog."""
    data = _load_raw(path)
    data['title_variants'] = [variant.to_dict() for variant in variants]
    _save_raw(data, path)


def load_field_catalog(path: Path = TITLE_VARIANTS_FILE) -> Dict[str, str]:
    """Пользовательские поля-плейсхолдеры (id -> подпись), заведённые через
    «+ Новое поле» в редакторе шаблона. Встроенные (TITLE_FIELD_LABELS,
    template_schema.py) сюда не входят -- см. get_all_field_labels()."""
    data = _load_raw(path)
    return dict(data.get('field_catalog', {}))


def save_field_catalog(catalog: Dict[str, str], path: Path = TITLE_VARIANTS_FILE) -> None:
    """Сохраняет каталог пользовательских полей, не трогая секцию
    title_variants."""
    data = _load_raw(path)
    data['field_catalog'] = dict(catalog)
    _save_raw(data, path)


def load_hidden_builtin_fields(path: Path = TITLE_VARIANTS_FILE) -> List[str]:
    """Id встроенных полей (TITLE_FIELD_LABELS), скрытых оператором через
    корзину в меню «Вставить плейсхолдер» (см. src/ui/main_window.py,
    _delete_catalog_field()). Сама константа в коде остаётся нетронутой --
    это просто список-исключение, который get_all_field_labels() вычитает
    при сборке итогового каталога."""
    data = _load_raw(path)
    return list(data.get('hidden_builtin_fields', []))


def save_hidden_builtin_fields(field_ids: List[str], path: Path = TITLE_VARIANTS_FILE) -> None:
    """Сохраняет список скрытых встроенных полей, не трогая секции
    title_variants/field_catalog."""
    data = _load_raw(path)
    data['hidden_builtin_fields'] = list(field_ids)
    _save_raw(data, path)


def load_field_formulas(path: Path = TITLE_VARIANTS_FILE) -> Dict[str, Dict]:
    """field_id -> {"tokens": [...токены...], "decimals": int} -- формулы
    вычисляемых полей (см. src/services/formula_engine.py). Тот же общий
    охват, что и у field_catalog: один каталог формул на оба слота и все
    варианты, не привязан к конкретному варианту/слоту."""
    data = _load_raw(path)
    return dict(data.get('field_formulas', {}))


def save_field_formulas(formulas: Dict[str, Dict], path: Path = TITLE_VARIANTS_FILE) -> None:
    """Сохраняет формулы вычисляемых полей, не трогая остальные секции файла."""
    data = _load_raw(path)
    data['field_formulas'] = dict(formulas)
    _save_raw(data, path)


def get_all_field_labels(path: Path = TITLE_VARIANTS_FILE) -> Dict[str, str]:
    """(Встроенные TITLE_FIELD_LABELS минус hidden_builtin_fields) +
    пользовательский field_catalog, в виде единого словаря id -> подпись --
    источник для выпадающего списка «Вставить плейсхолдер» и для подписей
    в форме реквизитов (src/ui/main_window.py, _render_slot_fields())."""
    hidden = set(load_hidden_builtin_fields(path))
    labels = {field_id: label for field_id, label in TITLE_FIELD_LABELS.items() if field_id not in hidden}
    labels.update(load_field_catalog(path))
    return labels


def get_all_title_variants(path: Path = TITLE_VARIANTS_FILE) -> Dict[str, TitleConfig]:
    """Встроенные TITLE_VARIANTS + пользовательские из JSON, в виде единого
    словаря id -> TitleConfig -- то, чем сайдбар конструктора заполняет
    список «Титульные листы»."""
    variants = dict(TITLE_VARIANTS)
    for variant in load_title_variants(path):
        variants[variant.id] = TitleConfig(
            document_title=variant.document_title, subtitle_fields=variant.subtitle_fields,
        )
    return variants


# Единые имена, одинаковые во всех *_variants_store.py (title/intro/appendix)
# -- src/ui/main_window.py выбирает нужный модуль через _slot_store(slot) и
# дальше зовёт load_variants()/save_variants()/get_all_variants() не зная,
# какой это слот: без этих алиасов пришлось бы на каждом вызове отдельно
# решать, load_title_variants или load_intro_variants (или load_appendix_variants)
# вызвать -- ровно то дублирование, которое этот приём убирает.
load_variants = load_title_variants
save_variants = save_title_variants
get_all_variants = get_all_title_variants
