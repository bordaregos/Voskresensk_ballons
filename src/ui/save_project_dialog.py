"""Диалог «Сохранить проект» -- имя файла + выбор папки.

Портирован из docs/design/вводная_часть.html (#saveProjectModal): один
плоский выпадающий список ВСЕХ папок дерева (произвольная вложенность, см.
src/services/workspace.py:list_all_folders()) с отступом по глубине, плюс
пункт «+ Новая папка…», раскрывающий поле для её названия -- новая папка
всегда создаётся на верхнем уровне дерева, вложенность при желании
настраивается потом вручную в самой «Базе документов» (ПКМ по папке ->
«Новая подпапка»), см. комментарий у #saveProjectModal в мокапе.

Общий для трубопровода и конструктора документов (оба используют одно и то
же дерево "папка -> документ", см. FileHandler._prompt_document_path()) --
без принудительной тёмной темы конструктора (CONSTRUCTOR_QSS в
main_window.py применяется только к самому окну конструктора, не глобально
на QApplication), красить этот диалог под неё было бы неверно для
трубопровода, у которого нативная тема Qt.
"""

from pathlib import Path
from typing import Optional, Tuple

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QLabel,
)

from ..services import workspace

_NEW_FOLDER_SENTINEL = object()


class SaveProjectDialog(QDialog):
    def __init__(self, parent, default_folder: Path, default_filename: str,
                 current_path: Optional[Path] = None):
        super().__init__(parent)
        self.setWindowTitle("Сохранить проект")
        self._current_path = current_path
        self._result_folder: Optional[Path] = None
        self._result_filename: Optional[str] = None

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Сохраняется JSON со всеми введёнными данными -- проект можно "
            "будет открыть заново и продолжить."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        layout.addLayout(form)

        self.name_edit = QLineEdit(default_filename)
        form.addRow("Имя файла:", self.name_edit)

        self.folder_combo = QComboBox()
        default_index = 0
        # workspace.OUTPUT_DIR передаётся явно (а не через дефолт
        # list_all_folders()) -- он читается здесь свежим значением
        # атрибута модуля на каждый вызов, а не однажды связывается как
        # аргумент по умолчанию функции при импорте (та самая ловушка:
        # переприсваивание workspace.OUTPUT_DIR в тестах не долетело бы
        # до уже связанного default-параметра).
        for i, (folder_path, depth) in enumerate(workspace.list_all_folders(workspace.OUTPUT_DIR)):
            self.folder_combo.addItem("    " * depth + folder_path.name, folder_path)
            if folder_path == default_folder:
                default_index = i
        self.folder_combo.addItem("+ Новая папка…", _NEW_FOLDER_SENTINEL)
        self.folder_combo.setCurrentIndex(default_index)
        form.addRow("Папка:", self.folder_combo)

        self.new_folder_label = QLabel("Название новой папки:")
        self.new_folder_edit = QLineEdit()
        self.new_folder_edit.setPlaceholderText("Например, название объекта/заказчика")
        form.addRow(self.new_folder_label, self.new_folder_edit)
        self._update_new_folder_visibility()
        self.folder_combo.currentIndexChanged.connect(self._update_new_folder_visibility)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #c0392b;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_new_folder_visibility(self):
        is_new = self.folder_combo.currentData() is _NEW_FOLDER_SENTINEL
        self.new_folder_label.setVisible(is_new)
        self.new_folder_edit.setVisible(is_new)

    def _show_error(self, text: str):
        self.error_label.setText(text)
        self.error_label.setVisible(True)

    def _on_accept(self):
        filename = self.name_edit.text().strip()
        if not filename:
            self._show_error("Введите имя файла.")
            return

        folder_data = self.folder_combo.currentData()
        if folder_data is _NEW_FOLDER_SENTINEL:
            new_name = self.new_folder_edit.text().strip()
            if not new_name:
                self._show_error("Введите название новой папки.")
                return
            folder_dir = workspace.create_object(new_name, base_dir=workspace.OUTPUT_DIR)
        else:
            folder_dir = folder_data

        new_path = folder_dir / f"{workspace.sanitize_object_name(filename)}.json"
        # Тот же путь, что уже открыт -- это повторное сохранение под тем
        # же именем, а не конфликт с чужим файлом.
        if new_path != self._current_path and new_path.exists():
            self._show_error(
                f"В папке «{folder_dir.name}» уже есть файл «{new_path.name}» -- выберите другое имя."
            )
            return

        self._result_folder = folder_dir
        self._result_filename = filename
        self.accept()

    def result_values(self) -> Optional[Tuple[Path, str]]:
        """None, если диалог отменён; иначе (папка, имя_файла_без_расширения)."""
        if self._result_folder is None:
            return None
        return self._result_folder, self._result_filename
