"""Хранение пользовательских вариантов «Приложения 1» конструктора
документов -- тот же приём, что и title_variants_store.py/intro_variants_store.py,
но отдельный JSON-файл (data/appendix_variants.json): «Приложение 1» --
третий, независимый от титульного листа и вводной части слот (см.
src/ui/main_window.py), у него свой список вариантов в сайдбаре и своя
область документа.

Каталог плейсхолдеров (id -> подпись) НЕ дублируется здесь -- он общий для
всех слотов и по-прежнему живёт в title_variants_store.py
(get_all_field_labels()/load_field_catalog()/save_field_catalog()) вместе
со своим файлом (data/title_variants.json)."""

import json
from pathlib import Path
from typing import Dict, List

from ..config import APPENDIX_VARIANTS_FILE
from ..models.title_variant import TitleVariant
from .template_schema import APPENDIX_VARIANTS, TitleConfig


def _load_raw(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _save_raw(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_appendix_variants(path: Path = APPENDIX_VARIANTS_FILE) -> List[TitleVariant]:
    """Загружает пользовательские варианты приложения 1 из JSON.

    Если файла ещё нет (первый запуск, или ни одного варианта ещё не
    добавили), возвращает пустой список.
    """
    data = _load_raw(path)
    return [TitleVariant.from_dict(item) for item in data.get('appendix_variants', [])]


def save_appendix_variants(variants: List[TitleVariant], path: Path = APPENDIX_VARIANTS_FILE) -> None:
    """Сохраняет пользовательские варианты приложения 1 в JSON."""
    data = _load_raw(path)
    data['appendix_variants'] = [variant.to_dict() for variant in variants]
    _save_raw(data, path)


def get_all_appendix_variants(path: Path = APPENDIX_VARIANTS_FILE) -> Dict[str, TitleConfig]:
    """Встроенные APPENDIX_VARIANTS + пользовательские из JSON, в виде
    единого словаря id -> TitleConfig -- то, чем сайдбар конструктора
    заполняет список «Приложение 1»."""
    variants = dict(APPENDIX_VARIANTS)
    for variant in load_appendix_variants(path):
        variants[variant.id] = TitleConfig(
            document_title=variant.document_title, subtitle_fields=variant.subtitle_fields,
        )
    return variants


# Единые имена -- см. их докстринг в title_variants_store.py.
load_variants = load_appendix_variants
save_variants = save_appendix_variants
get_all_variants = get_all_appendix_variants
