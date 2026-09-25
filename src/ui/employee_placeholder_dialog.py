"""Редактор сотрудника -- «Создать сотрудника» из ПКМ на чипе плейсхолдера
в реквизитах конструктора документов (см. src/ui/main_window.py,
_show_chip_context_menu()/_create_employee_from_chip_menu()).

Портирован из мокапа (docs/design/редактор_сотрудника.html, финальная,
четвёртая итерация) -- список уже записанных сотрудников слева (читает тот
же общий справочник, что и раздел «Сотрудники», src/services/
employees_store.py; это окно только читает и умеет удалить запись, ничего
не создаёт и не правит -- полное редактирование карточки сотрудника
остаётся в разделе «Сотрудники», см. EmployeesTabController), готовые
плейсхолдеры данных выбранного сотрудника справа
(src/services/employee_placeholders.py, employee_chip_fields() -- статические
EMPLOYEE_DATA_FIELDS плюс динамические представления его удостоверений, по
паре чипов на каждую запись справочника, а не одно общее поле) --
множественный выбор чипов, клик переключает синий/зелёный.

Диалог НЕ пишет привязку сам -- только возвращает employee_id/selected_keys
после exec()==Accepted (или ничего не возвращает, если закрыли крестиком/
Esc, DialogCode.Rejected). На вызывающей стороне, _create_employee_from_chip_menu()
в main_window.py, каждый отмеченный ключ становится ОТДЕЛЬНЫМ новым полем
реквизитов (не одной строкой на все выбранные представления) -- диалог
сам об этом не знает, отдаёт только employee_id и набор ключей."""

from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QLineEdit, QPushButton,
    QScrollArea, QMessageBox, QSizePolicy,
)

from . import icons
from .flow_layout import FlowLayout
from ..models.employee import Employee
from ..services.employee_placeholders import employee_chip_fields, employee_data_value, fio_short
from ..services.employees_store import load_employees, save_employees

_QSS = """
QDialog { background: #1c1c1e; }
QDialog QLabel { color: #c7c7cc; font-size: 12px; }
QLabel#empDlgTitle { color: #e5e5e7; font-size: 13px; font-weight: 600; }
QWidget#empDlgSidebar { background: #202022; border-right: 0.5px solid #38383a; }
QLabel#empDlgSidebarHeader { color: #8e8e93; font-size: 10.5px; font-weight: 500; }
QLineEdit#empDlgSearch {
    background: #1c1c1e; border: 0.5px solid #38383a; border-radius: 6px;
    color: #e5e5e7; font-size: 12px; padding: 6px 8px;
}
QLineEdit#empDlgSearch:focus { border-color: #0a84ff; }
QWidget#empDlgRow { border-radius: 6px; }
QWidget#empDlgRow[empRowActive="true"] { background: rgba(10, 132, 255, 40); }
QLabel#empDlgRowName { color: #e5e5e7; font-size: 11.5px; background: transparent; }
QLabel#empDlgRowPosition { color: #8e8e93; font-size: 10px; background: transparent; }
QLabel#empDlgAvatar {
    background: #38383a; color: #c7c7cc; font-size: 10.5px; font-weight: 600; border-radius: 13px;
}
QWidget#empDlgRow[empRowActive="true"] QLabel#empDlgAvatar { background: #0a84ff; color: #fff; }
QLabel#empDlgEmptyHint { color: #5a5a5c; font-size: 11px; font-style: italic; }
QLabel#empDlgCrumb { color: #8e8e93; font-size: 10.5px; }
QLabel#empDlgSectionTitle { color: #8e8e93; font-size: 10.5px; }
QLabel[empChip="true"] {
    background: rgba(10, 132, 255, 40); color: #5ab4ff;
    border: 1px solid rgba(10, 132, 255, 110); border-radius: 6px;
    padding: 4px 9px; font-size: 11.5px;
}
QLabel[empChip="true"][empChipSelected="true"] {
    background: rgba(48, 209, 88, 40); color: #30d158;
    border: 1px solid rgba(48, 209, 88, 140);
}
"""


class _ChipLabel(QLabel):
    """Один чип «Готовых плейсхолдеров» -- клик переключает выбор (синий <->
    зелёный), см. докстринг модуля. Не про click-to-copy (в отличие от
    QLabel[titleChip="true"] в реквизитах, _copy_chip()) -- множественный
    выбор, состояние держится, пока диалог открыт."""

    def __init__(self, key: str, text: str, on_toggle):
        super().__init__(text or "—")
        self._key = key
        self._on_toggle = on_toggle
        self.setProperty("empChip", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWordWrap(True)

    def mousePressEvent(self, event):
        self._on_toggle(self._key, self)

    def set_selected(self, selected: bool):
        self.setProperty("empChipSelected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class EmployeePlaceholderDialog(QDialog):
    """См. докстринг модуля. Результат читается ПОСЛЕ exec(), только если
    вернул QDialog.DialogCode.Accepted: employee_id/selected_keys -- id
    выбранного сотрудника и множество отмеченных ключей
    employee_chip_fields(). Пустой selected_keys (сотрудник выбран, но ни
    один чип не отмечен) -- вызывающая сторона тогда не трогает строку
    реквизита, см. _create_employee_from_chip_menu()."""

    def __init__(self, existing_binding: Optional[Dict] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор сотрудника")
        self.setStyleSheet(_QSS)
        self.resize(600, 460)
        self.setMinimumSize(520, 400)

        self._employees: List[Employee] = load_employees()
        self._current_id: Optional[str] = (existing_binding or {}).get("employee_id")
        self._selected_keys: Set[str] = set((existing_binding or {}).get("keys", []))
        if self._current_id not in {e.id for e in self._employees}:
            self._current_id = None
            self._selected_keys = set()

        self.employee_id: Optional[str] = None
        self.selected_keys: Set[str] = set()

        self._build_ui()
        self._render_list()
        self._render_placeholders()

    # -- Построение диалога --------------------------------------------------
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(16, 14, 16, 12)
        right.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("Редактор сотрудника")
        title.setObjectName("empDlgTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        right.addLayout(header_row)

        self._crumb_label = QLabel("Выберите сотрудника")
        self._crumb_label.setObjectName("empDlgCrumb")
        right.addWidget(self._crumb_label)
        right.addSpacing(4)

        section_title = QLabel("Готовые плейсхолдеры")
        section_title.setObjectName("empDlgSectionTitle")
        right.addWidget(section_title)

        self._chips_container = QWidget()
        FlowLayout(self._chips_container, margin=0, spacing=6)
        policy = self._chips_container.sizePolicy()
        policy.setHeightForWidth(True)
        self._chips_container.setSizePolicy(policy)
        right.addWidget(self._chips_container)
        right.addStretch(1)

        footer = QHBoxLayout()
        self._delete_btn = QPushButton("Удалить")
        self._delete_btn.setIcon(icons.icon("trash", "#ff453a", 12))
        self._delete_btn.setStyleSheet(
            "QPushButton{background:transparent; border:0.5px solid rgba(255,69,58,.5); "
            "color:#ff453a; font-size:12px; padding:6px 12px; border-radius:6px;} "
            "QPushButton:hover{background:rgba(255,69,58,.12);}"
        )
        self._delete_btn.clicked.connect(self._on_delete_employee)
        self._delete_btn.setVisible(False)
        footer.addWidget(self._delete_btn)
        footer.addStretch(1)
        done_btn = QPushButton("Готово")
        done_btn.setStyleSheet(
            "QPushButton{background:#0a84ff; border:none; color:#fff; font-weight:500; "
            "padding:6px 13px; border-radius:6px;} QPushButton:hover{background:#3391ff;}"
        )
        done_btn.clicked.connect(self._on_done)
        footer.addWidget(done_btn)
        right.addLayout(footer)

        root.addLayout(right, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("empDlgSidebar")
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(6)

        header = QLabel("Сотрудники")
        header.setObjectName("empDlgSidebarHeader")
        layout.addWidget(header, 0, Qt.AlignmentFlag.AlignLeft)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("empDlgSearch")
        self._search_input.setPlaceholderText("Поиск по ФИО")
        self._search_input.textChanged.connect(self._render_list)
        layout.addWidget(self._search_input)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch(1)
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

        return sidebar

    # -- Список сотрудников ---------------------------------------------------
    def _render_list(self):
        needle = self._search_input.text().strip().lower()
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # hide() -- обязателен, не только deleteLater(): реальное
                # удаление откладывается до следующего прохода цикла
                # событий, а до тех пор виджет остаётся видимым, как был, и
                # просвечивает из-под свежевставленных строк того же списка
                # (тот же приём/тот же баг, что и в _clear_layout()
                # formula_editor_dialog.py).
                widget.hide()
                widget.deleteLater()

        matches = [
            e for e in self._employees
            if not needle or needle in e.full_name.lower() or needle in e.position.lower()
        ]
        if not matches:
            hint = QLabel("Справочник пуст" if not self._employees else "Ничего не найдено")
            hint.setObjectName("empDlgEmptyHint")
            hint.setContentsMargins(10, 4, 10, 4)
            self._list_layout.insertWidget(0, hint)
            return

        for index, employee in enumerate(matches):
            self._list_layout.insertWidget(index, self._build_employee_row(employee))

    def _build_employee_row(self, employee: Employee) -> QWidget:
        row = QWidget()
        row.setObjectName("empDlgRow")
        row.setProperty("empRowActive", employee.id == self._current_id)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        avatar_text = fio_short(employee.full_name)[:1] or "?"
        avatar = QLabel(avatar_text.upper())
        avatar.setObjectName("empDlgAvatar")
        avatar.setFixedSize(24, 24)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name_label = QLabel(fio_short(employee.full_name))
        name_label.setObjectName("empDlgRowName")
        position_label = QLabel(employee.position)
        position_label.setObjectName("empDlgRowPosition")
        text_col.addWidget(name_label)
        text_col.addWidget(position_label)
        layout.addLayout(text_col, 1)

        row.mousePressEvent = lambda event, eid=employee.id: self._select_employee(eid)
        return row

    def _select_employee(self, employee_id: Optional[str]):
        self._current_id = employee_id
        self._selected_keys = set()
        self._render_list()
        self._render_placeholders()

    # -- Готовые плейсхолдеры выбранного сотрудника ---------------------------
    def _current_employee(self) -> Optional[Employee]:
        return next((e for e in self._employees if e.id == self._current_id), None)

    def _render_placeholders(self):
        layout = self._chips_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

        employee = self._current_employee()
        self._delete_btn.setVisible(employee is not None)
        if employee is None:
            self._crumb_label.setText("Выберите сотрудника слева")
            hint = QLabel("Выберите сотрудника слева, чтобы получить готовые плейсхолдеры его данных")
            hint.setObjectName("empDlgEmptyHint")
            hint.setWordWrap(True)
            layout.addWidget(hint)
            return

        self._crumb_label.setText(fio_short(employee.full_name))
        for field in employee_chip_fields(employee):
            value = employee_data_value(employee, field.key)
            chip = _ChipLabel(field.key, value, self._toggle_chip)
            chip.set_selected(field.key in self._selected_keys)
            chip.setToolTip(field.label)
            chip.setParent(self._chips_container)
            chip.show()
            layout.addWidget(chip)

    def _toggle_chip(self, key: str, chip: _ChipLabel):
        if key in self._selected_keys:
            self._selected_keys.discard(key)
        else:
            self._selected_keys.add(key)
        chip.set_selected(key in self._selected_keys)

    # -- Удаление сотрудника из справочника ------------------------------------
    def _on_delete_employee(self):
        employee = self._current_employee()
        if employee is None:
            return
        answer = QMessageBox.question(
            self, "Удалить сотрудника",
            f"Удалить сотрудника «{fio_short(employee.full_name)}» из справочника?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._employees = [e for e in self._employees if e.id != employee.id]
        save_employees(self._employees)
        self._select_employee(None)

    # -- Завершение -------------------------------------------------------------
    def _on_done(self):
        self.employee_id = self._current_id
        self.selected_keys = set(self._selected_keys)
        self.accept()
