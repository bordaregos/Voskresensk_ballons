"""Хранение вариантов пользовательских разделов конструктора документов --
тот же приём, что title_variants_store.py/intro_variants_store.py/
appendix_variants_store.py, но один общий JSON-файл на ВСЕ такие разделы
(data/custom_section_variants.json), а не один файл на раздел: в отличие от
title/intro/appendix1, у пользовательского раздела нет заранее выделенной
константы-пути -- сам раздел заводится в рантайме
(src/ui/main_window.py, MainWindow._create_section()), заранее завести под
него файл нельзя.

Формат файла -- {"<slot_id>": {"variants": [...]}, ...}, по одному ключу на
раздел (read-modify-write в save_variants(), как и у соседних *_store.py --
запись одного раздела не должна стирать остальные). Встроенных вариантов у
пользовательского раздела не бывает (см. src/config.py,
find_section_template()) -- get_all_variants() поэтому просто алиас
load_variants() с той же сигнатурой, что get_all_title_variants() и её
аналоги (единый вызов из MainWindow._slot_store(slot).get_all_variants(),
не знающий, встроенный это раздел или пользовательский)."""

import json
from pathlib import Path
from typing import Dict, List

from ..config import CUSTOM_SECTION_VARIANTS_FILE
from ..models.title_variant import TitleVariant
from .template_schema import TitleConfig


def _load_raw(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def _save_raw(data: Dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_variants(slot: str, path: Path = CUSTOM_SECTION_VARIANTS_FILE) -> List[TitleVariant]:
    """Загружает варианты раздела slot.

    Если файла ещё нет (первый запуск), или у этого раздела ещё ни одного
    варианта не добавили, возвращает пустой список.
    """
    data = _load_raw(path)
    return [TitleVariant.from_dict(item) for item in data.get(slot, {}).get('variants', [])]


def save_variants(slot: str, variants: List[TitleVariant], path: Path = CUSTOM_SECTION_VARIANTS_FILE) -> None:
    """Сохраняет варианты раздела slot, не трогая записи остальных разделов
    в том же файле."""
    data = _load_raw(path)
    section = data.setdefault(slot, {})
    section['variants'] = [variant.to_dict() for variant in variants]
    _save_raw(data, path)


def get_all_variants(slot: str, path: Path = CUSTOM_SECTION_VARIANTS_FILE) -> Dict[str, TitleConfig]:
    """Варианты раздела slot в виде словаря id -> TitleConfig -- то, чем
    сайдбар конструктора заполняет список вариантов раздела. Встроенных
    вариантов здесь нет (в отличие от get_all_title_variants() и её
    аналогов) -- пользовательский раздел всегда стартует пустым."""
    return {
        variant.id: TitleConfig(document_title=variant.document_title, subtitle_fields=variant.subtitle_fields)
        for variant in load_variants(slot, path)
    }
