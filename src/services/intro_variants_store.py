"""Хранение пользовательских вариантов вводной части конструктора
документов -- тот же приём, что и title_variants_store.py, но отдельный
JSON-файл (data/intro_variants.json): вводная часть -- второй, независимый
от титульного листа слот (см. src/ui/main_window.py), у него свой список
вариантов в сайдбаре и своя область документа.

Каталог плейсхолдеров (id -> подпись) НЕ дублируется здесь -- он общий для
обоих слотов и по-прежнему живёт в title_variants_store.py
(get_all_field_labels()/load_field_catalog()/save_field_catalog()) вместе
со своим файлом (data/title_variants.json): оператор вставляет один и тот
же плейсхолдер что в титульный лист, что во вводную часть, через одно и то
же меню «Вставить плейсхолдер» (см. мокап docs/design/вводная_часть.html,
где fieldCatalog -- одна общая переменная на оба слота)."""

import json
from pathlib import Path
from typing import Dict, List

from ..config import INTRO_VARIANTS_FILE
from ..models.title_variant import TitleVariant
from .template_schema import INTRO_VARIANTS, TitleConfig


def _load_raw(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _save_raw(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_intro_variants(path: Path = INTRO_VARIANTS_FILE) -> List[TitleVariant]:
    """Загружает пользовательские варианты вводной части из JSON.

    Если файла ещё нет (первый запуск, или ни одного варианта ещё не
    добавили), возвращает пустой список.
    """
    data = _load_raw(path)
    return [TitleVariant.from_dict(item) for item in data.get('intro_variants', [])]


def save_intro_variants(variants: List[TitleVariant], path: Path = INTRO_VARIANTS_FILE) -> None:
    """Сохраняет пользовательские варианты вводной части в JSON."""
    data = _load_raw(path)
    data['intro_variants'] = [variant.to_dict() for variant in variants]
    _save_raw(data, path)


def get_all_intro_variants(path: Path = INTRO_VARIANTS_FILE) -> Dict[str, TitleConfig]:
    """Встроенные INTRO_VARIANTS + пользовательские из JSON, в виде единого
    словаря id -> TitleConfig -- то, чем сайдбар конструктора заполняет
    список «Вводная часть»."""
    variants = dict(INTRO_VARIANTS)
    for variant in load_intro_variants(path):
        variants[variant.id] = TitleConfig(
            document_title=variant.document_title, subtitle_fields=variant.subtitle_fields,
        )
    return variants


# Единые имена -- см. их докстринг в title_variants_store.py.
load_variants = load_intro_variants
save_variants = save_intro_variants
get_all_variants = get_all_intro_variants
