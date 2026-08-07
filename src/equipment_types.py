"""Реестр типов объектов освидетельствования.

Каждый тип объекта (баллон, трубопровод, ...) — запись с данными: свой
.ui-файл, свои списки виджетов, свой порядок обязательных шагов расчёта.
MainWindow остаётся одним классом и параметризуется записью из REGISTRY
при создании — никакого отдельного класса-окна или контроллера на тип.
"""

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Dict, List

from .ui import widget_names, widget_names_pipeline

DESIGNER_DIR = Path(__file__).resolve().parent / "ui" / "designer"


@dataclass(frozen=True)
class EquipmentType:
    id: str
    label: str
    ui_path: Path
    widget_names: ModuleType
    step_order: List[str]
    step_labels: Dict[str, str]
    required_fields: List[str]


BALLOON = EquipmentType(
    id="balloon",
    label="Баллоны высокого давления",
    ui_path=DESIGNER_DIR / "main_window.ui",
    widget_names=widget_names,
    step_order=[
        "amount", "s_min_min", "thickness", "strength",
        "residual_life", "ovalness", "hardness",
    ],
    step_labels={
        "amount": "«Кол-во баллонов»",
        "s_min_min": "«Smin-min»",
        "thickness": "«Расчитать толщины»",
        "strength": "«Расчёт на прочность»",
        "residual_life": "«Остаточный ресурс»",
        "ovalness": "«Расчёт овальности»",
        "hardness": "«Расчёт твёрдости»",
    },
    required_fields=["zakl_number", "reg_number", "p_rab"],
)

PIPELINE = EquipmentType(
    id="pipeline",
    label="Трубопроводы технологические",
    ui_path=DESIGNER_DIR / "pipeline_window.ui",
    widget_names=widget_names_pipeline,
    step_order=["segments", "thickness", "strength", "residual_life"],
    step_labels={
        "segments": "«Участки трассы»",
        "thickness": "«Замерить толщины»",
        "strength": "«Расчёт на прочность»",
        "residual_life": "«Остаточный ресурс»",
    },
    required_fields=["report_number", "reg_number", "p_rab_mpa"],
)

REGISTRY: Dict[str, EquipmentType] = {"balloon": BALLOON, "pipeline": PIPELINE}
