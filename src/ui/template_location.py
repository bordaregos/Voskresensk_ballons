"""Выбор пользователем места хранения .docx-заготовки варианта конструктора
документов -- раньше все заготовки жёстко уходили в FRAGMENTS_DIR
(templates/fragments), теперь оператор сам решает, куда сохранить файл.
Тот же приём запоминания выбора, что и у "Открыть с помощью"
(src/ui/open_with.py, PREFERRED_EDITOR_FILE) -- диалог сохранения в
следующий раз стартует в той же папке."""

import json
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QFileDialog, QWidget

from ..config import FRAGMENTS_DIR, PREFERRED_TEMPLATE_DIR_FILE


def _load_remembered_dir() -> Path:
    if PREFERRED_TEMPLATE_DIR_FILE.exists():
        try:
            data = json.loads(PREFERRED_TEMPLATE_DIR_FILE.read_text(encoding="utf-8"))
            dir_path = Path(data.get("dir_path", ""))
            if dir_path.is_dir():
                return dir_path
        except (OSError, json.JSONDecodeError):
            pass
    return FRAGMENTS_DIR


def _remember_dir(dir_path: Path) -> None:
    PREFERRED_TEMPLATE_DIR_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREFERRED_TEMPLATE_DIR_FILE.write_text(
        json.dumps({"dir_path": str(dir_path)}, ensure_ascii=False), encoding="utf-8"
    )


def choose_template_save_path(parent: QWidget, default_filename: str) -> Optional[Path]:
    """Диалог «Сохранить как» для .docx-заготовки варианта конструктора --
    стартует в последней папке, которую выбрал оператор (или в
    FRAGMENTS_DIR при первом запуске), и запоминает новый выбор. None --
    пользователь отменил диалог."""
    start_dir = _load_remembered_dir()
    file_path, _ = QFileDialog.getSaveFileName(
        parent, "Сохранить шаблон как", str(start_dir / default_filename), "Документы Word (*.docx)"
    )
    if not file_path:
        return None
    path = Path(file_path)
    _remember_dir(path.parent)
    return path
