"""Пакет сервисов бизнес-логики."""

from .calculations import (
    CalculationsService,
    StrengthResults,
    CorrosionResults,
    OvalnessResult,
)

__all__ = [
    "CalculationsService",
    "StrengthResults",
    "CorrosionResults",
    "OvalnessResult",
]
