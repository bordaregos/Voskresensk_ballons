"""Хранение пользовательских вариантов титульного листа конструктора
документов: JSON-файл, тот же приём, что employees_store.py/
instruments_store.py -- не зависит от Qt.

Встроенные варианты (TITLE_VARIANTS, src/services/template_schema.py)
живут в коде и через этот стор не редактируются -- get_all_title_variants()
только добавляет к ним пользовательские, id которых генерируется в UI-слое
(uuid4().hex[:8], тот же приём, что src/ui/employees_tab.py) и поэтому не
пересекается с "otchet"/"zaklyuchenie".

Файл хранит ДВЕ независимые секции -- "title_variants" (сами варианты) и
"field_catalog" (id -> человекочитаемая подпись поля-плейсхолдера,
переиспользуется между вариантами при вставке через каталог плейсхолдеров,
см. src/ui/main_window.py, _build_title_placeholder_catalog()).
save_title_variants()/save_field_catalog()
поэтому читают-правят-пишут файл целиком (read-modify-write), а не
перезаписывают его слепо целиком своей секцией -- иначе сохранение одной
секции стирало бы другую."""

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


def get_all_field_labels(path: Path = TITLE_VARIANTS_FILE) -> Dict[str, str]:
    """Встроенные TITLE_FIELD_LABELS + пользовательский field_catalog, в виде
    единого словаря id -> подпись -- источник для выпадающего списка
    «Вставить плейсхолдер» и для подписей в форме реквизитов
    (src/ui/main_window.py, _render_title_fields())."""
    labels = dict(TITLE_FIELD_LABELS)
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
