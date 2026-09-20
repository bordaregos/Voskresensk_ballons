"""Контроллер вкладки «Сотрудники» — справочник сотрудников компании.

Не зависит от логики отчёта (get_form_data/STEP_ORDER/Project) — данные
хранятся отдельно, см. src/services/employees_store.py: справочник общий
для компании, не привязан к текущему заключению/проекту. Клише сотрудника
вставляется в .docx через MainWindow._add_specialist_row()/
_specialist_kleishe_image() -- специалистов отчёта выбирают отсюда.
"""

from pathlib import Path
from uuid import uuid4

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QListWidgetItem,
    QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import icons
from ..config import KLEISHE_DIR
from ..models.employee import Employee
from ..services.employees_store import load_employees, save_employees, store_kleishe_image


class EmployeesTabController:
    """Управляет вкладкой «Сотрудники» окна трубопровода."""

    def __init__(self, main_window):
        self.mw = main_window
        self.employees = load_employees()
        self._current_id = None
        self._current_kleishe_filename = None

        self.mw.table_employees.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mw.table_employees.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.mw.table_employees.itemSelectionChanged.connect(self._on_row_selected)
        self.mw.pushButt_newEmployee.clicked.connect(self._new_employee)
        self.mw.pushButt_deleteEmployee.clicked.connect(self._delete_employee)
        self.mw.pushButt_addCertificate.clicked.connect(self._add_certificate)
        self.mw.pushButt_removeCertificate.clicked.connect(self._remove_certificate)
        self.mw.pushButt_chooseKleishe.clicked.connect(self._choose_kleishe)
        self.mw.pushButt_clearKleishe.clicked.connect(self._clear_kleishe)
        self.mw.pushButt_saveEmployee.clicked.connect(self._save_employee)

        # Удостоверение -- одна строка на запись (домен: "№ 0039-33918 от
        # 20.12.2024 г."), но employee_certificate_input -- QPlainTextEdit
        # (та же стилизация, что у остальных полей формы), а не QLineEdit,
        # поэтому по умолчанию Enter вставляет перевод строки вместо
        # отправки записи (расхождение с docs/design/
        # сотрудники_конструктор.html, #certInput onkeydown). Подменяем
        # keyPressEvent конкретного экземпляра -- в .ui это обычный
        # QPlainTextEdit без promoted-подкласса, менять там нечего.
        # Shift+Enter по-прежнему вставляет перевод строки (на случай, если
        # он всё же понадобится).
        input_widget = self.mw.employee_certificate_input
        default_key_press = input_widget.keyPressEvent

        def _certificate_input_key_press(event, _default=default_key_press):
            plain_enter = event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            if plain_enter and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self._add_certificate()
                event.accept()
                return
            _default(event)

        input_widget.keyPressEvent = _certificate_input_key_press

        self._refresh_table()
        self._clear_form()

    def _refresh_table(self):
        """Перерисовывает table_employees из self.employees (тот же порядок,
        что и в списке — строка row однозначно соответствует self.employees[row])."""
        table = self.mw.table_employees
        table.setRowCount(len(self.employees))
        for row, employee in enumerate(self.employees):
            table.setItem(row, 0, QTableWidgetItem(employee.position))
            table.setItem(row, 1, QTableWidgetItem(employee.full_name))
            table.setItem(row, 2, QTableWidgetItem("; ".join(employee.certificates)))
            table.setItem(row, 3, QTableWidgetItem("есть" if employee.kleishe_filename else "—"))

    def _on_row_selected(self):
        row = self.mw.table_employees.currentRow()
        if row < 0 or row >= len(self.employees):
            return
        self._load_employee_into_form(self.employees[row])

    def _load_employee_into_form(self, employee: Employee):
        self._current_id = employee.id
        self.mw.employee_position.setPlainText(employee.position)
        self.mw.employee_fio.setPlainText(employee.full_name)
        # employee_qualification -- только в constructor_window.ui (см.
        # Employee.qualification), у трубопровода этого виджета нет.
        if hasattr(self.mw, "employee_qualification"):
            self.mw.employee_qualification.setPlainText(employee.qualification)

        self.mw.employee_certificates_list.clear()
        for certificate in employee.certificates:
            self.mw.employee_certificates_list.addItem(QListWidgetItem(certificate))

        self._set_kleishe_preview(employee.kleishe_filename)

    def _new_employee(self):
        self.mw.table_employees.clearSelection()
        self._clear_form()

    def _clear_form(self):
        self._current_id = None
        self.mw.employee_position.setPlainText("")
        self.mw.employee_fio.setPlainText("")
        if hasattr(self.mw, "employee_qualification"):
            self.mw.employee_qualification.setPlainText("")
        self.mw.employee_certificates_list.clear()
        self.mw.employee_certificate_input.setPlainText("")
        self._set_kleishe_preview(None)

    def _add_certificate(self):
        # " ".join(...split()) вместо .strip() -- схлопывает и внутренние
        # переводы строк/пробелы тоже (например, из вставки многострочного
        # текста), не только по краям: удостоверение -- одна строка записи.
        text = " ".join(self.mw.employee_certificate_input.toPlainText().split())
        if not text:
            return
        self.mw.employee_certificates_list.addItem(QListWidgetItem(text))
        self.mw.employee_certificate_input.setPlainText("")

    def _remove_certificate(self):
        row = self.mw.employee_certificates_list.currentRow()
        if row >= 0:
            self.mw.employee_certificates_list.takeItem(row)

    def _choose_kleishe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.mw, "Выбрать клише", "", "Изображения (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        filename = store_kleishe_image(Path(file_path))
        self._set_kleishe_preview(filename)

    def _clear_kleishe(self):
        self._set_kleishe_preview(None)

    def _set_kleishe_preview(self, filename):
        self._current_kleishe_filename = filename
        label = self.mw.employee_kleishe_preview
        if not filename:
            label.setPixmap(QPixmap())
            label.setText("нет изображения")
            return

        pixmap = QPixmap(str(KLEISHE_DIR / filename))
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("не удалось загрузить")
            return

        label.setText("")
        label.setPixmap(pixmap.scaled(
            label.width(), label.height(), Qt.AspectRatioMode.KeepAspectRatio,
        ))

    def _save_employee(self):
        position = self.mw.employee_position.toPlainText().strip()
        full_name = self.mw.employee_fio.toPlainText().strip()

        if not position or not full_name:
            self.mw.show_message(
                "Не заполнены поля",
                "Укажите должность и ФИО сотрудника.",
                QMessageBox.Icon.Warning,
            )
            return

        certificates = [
            self.mw.employee_certificates_list.item(i).text()
            for i in range(self.mw.employee_certificates_list.count())
        ]
        qualification = (
            self.mw.employee_qualification.toPlainText().strip()
            if hasattr(self.mw, "employee_qualification") else ""
        )

        if self._current_id is None:
            employee = Employee(
                id=uuid4().hex[:8],
                position=position,
                full_name=full_name,
                qualification=qualification,
                certificates=certificates,
                kleishe_filename=self._current_kleishe_filename,
            )
            self.employees.append(employee)
            self._current_id = employee.id
        else:
            for existing in self.employees:
                if existing.id == self._current_id:
                    existing.position = position
                    existing.full_name = full_name
                    existing.qualification = qualification
                    existing.certificates = certificates
                    existing.kleishe_filename = self._current_kleishe_filename
                    break

        save_employees(self.employees)
        self._refresh_table()
        self._select_row_by_id(self._current_id)

    def _delete_employee(self):
        if self._current_id is None:
            return
        self.employees = [e for e in self.employees if e.id != self._current_id]
        save_employees(self.employees)
        self._refresh_table()
        self._clear_form()

    def _select_row_by_id(self, employee_id):
        for row, employee in enumerate(self.employees):
            if employee.id == employee_id:
                self.mw.table_employees.selectRow(row)
                return


def _employee_initials(full_name: str) -> str:
    """Инициалы для аватара-кружка в карточке (docs/design/
    сотрудники_конструктор.html, initials()) -- первые буквы первых двух
    "слов" ФИО, в верхнем регистре. Терпимо к пустому/однословному имени
    (аватар тогда с одной буквой или пустой, не падает)."""
    parts = full_name.split()
    letters = (part[0] for part in parts[:2])
    return "".join(letters).upper()


class ConstructorEmployeesTabController(EmployeesTabController):
    """Тот же общий справочник и та же CRUD-логика, что и
    EmployeesTabController (сохранение/удаление/сертификаты/клише -- ни
    один из этих методов здесь не переопределён), только отрисовка списка
    и карточки сотрудника -- под визуал конструктора документов (docs/design/
    сотрудники_конструктор.html): карточки с аватаром-инициалами вместо
    строк таблицы с шапкой, хлебная крошка "Сотрудники / <ФИО>" вместо
    заголовка группы, кнопка «Удалить» скрыта, пока не выбран существующий
    сотрудник. Пайплайн (EmployeesTabController напрямую) этот класс не
    использует и не затрагивается его изменениями."""

    def __init__(self, main_window):
        table = main_window.table_employees
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        for col in (1, 2, 3):
            table.setColumnHidden(col, True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        super().__init__(main_window)
        main_window.employeeSearchBox.textChanged.connect(self.filter_employees)
        # В мокапе (docs/design/сотрудники_конструктор.html) удаление
        # удостоверения -- крестик у самой строки (_wrap_certificate_item()
        # ниже), отдельной кнопки нет. Сама pushButt_removeCertificate не
        # удалена из .ui и остаётся подключена к _remove_certificate() --
        # EmployeesTabController.__init__ коннектит её безусловно, а
        # трубопровод (EmployeesTabController напрямую) по-прежнему
        # показывает её как есть.
        main_window.pushButt_removeCertificate.setVisible(False)

    def _refresh_table(self):
        table = self.mw.table_employees
        table.setRowCount(len(self.employees))
        for row, employee in enumerate(self.employees):
            table.setRowHeight(row, 44)
            table.setCellWidget(row, 0, self._build_employee_card(employee))

    def _build_employee_card(self, employee: Employee) -> QWidget:
        card = QWidget()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        avatar = QLabel(_employee_initials(employee.full_name))
        avatar.setObjectName("employeeCardAvatar")
        avatar.setFixedSize(26, 26)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name_label = QLabel(employee.full_name)
        name_label.setObjectName("employeeCardName")
        position_label = QLabel(employee.position)
        position_label.setObjectName("employeeCardPosition")
        text_col.addWidget(name_label)
        text_col.addWidget(position_label)
        layout.addLayout(text_col, 1)

        return card

    # Потолок высоты employee_certificates_list (px) -- дальше появляется
    # внутренняя прокрутка вместо разрастания на всю оставшуюся площадь
    # панели (см. _sync_certificates_list_height()).
    CERT_LIST_MAX_HEIGHT = 150
    CERT_ROW_HEIGHT = 30

    def _load_employee_into_form(self, employee: Employee):
        super()._load_employee_into_form(employee)
        self._wrap_all_certificate_items()
        self.mw.employeeCrumbLabel.setText(f"Сотрудники / {employee.full_name}")
        self.mw.pushButt_deleteEmployee.setVisible(True)

    def _clear_form(self):
        super()._clear_form()
        self._sync_certificates_list_height()
        self.mw.employeeCrumbLabel.setText("Сотрудники / Новый сотрудник")
        self.mw.pushButt_deleteEmployee.setVisible(False)

    def _add_certificate(self):
        """Как EmployeesTabController._add_certificate(), плюс построчный
        крестик удаления на добавленном элементе (см. _wrap_certificate_item())."""
        list_widget = self.mw.employee_certificates_list
        count_before = list_widget.count()
        super()._add_certificate()
        if list_widget.count() > count_before:
            self._wrap_certificate_item(list_widget.item(count_before))
            self._sync_certificates_list_height()

    def _wrap_all_certificate_items(self):
        list_widget = self.mw.employee_certificates_list
        for row in range(list_widget.count()):
            self._wrap_certificate_item(list_widget.item(row))
        self._sync_certificates_list_height()

    def _sync_certificates_list_height(self):
        """Высота списка -- под фактическое число строк (компактно, как
        .cert-list в docs/design/сотрудники_конструктор.html), а не под
        Preferred/Maximum-потолок из .ui сразу: тот декларирует лишь верхнюю
        границу, реальная высота считается здесь на каждое изменение
        списка (загрузка карточки, добавление/удаление удостоверения)."""
        list_widget = self.mw.employee_certificates_list
        height = max(list_widget.count(), 1) * self.CERT_ROW_HEIGHT + 6
        list_widget.setMaximumHeight(min(height, self.CERT_LIST_MAX_HEIGHT))

    def _remove_certificate_row(self, item: QListWidgetItem):
        list_widget = self.mw.employee_certificates_list
        list_widget.takeItem(list_widget.row(item))
        self._sync_certificates_list_height()

    def _wrap_certificate_item(self, item: QListWidgetItem):
        """Подменяет стандартный текстовый рендер QListWidgetItem компактной
        строкой с крестиком удаления -- docs/design/сотрудники_конструктор.html,
        .cert-row + .remove-btn. Строка одна на удостоверение (CERT_ROW_HEIGHT
        в _sync_certificates_list_height() это предполагает), поэтому
        встроенные переводы строк схлопываются -- на новые записи их уже не
        пропускает _add_certificate(), но для удостоверений, сохранённых до
        этой правки (или основного EmployeesTabController.employee_certificate_input,
        общего с трубопроводом), это чинит отображение и сам item.text() тут
        же, при открытии карточки. _save_employee() (базовый, не переопределён,
        читает список через item(i).text()) от этого не страдает -- сохранит
        уже нормализованный текст."""
        list_widget = self.mw.employee_certificates_list

        normalized_text = " ".join(item.text().split())
        if normalized_text != item.text():
            item.setText(normalized_text)

        row = QWidget()
        # setItemWidget() накладывает row поверх ячейки как дочерний
        # виджет, а не заменяет отрисовку -- у прозрачного QWidget без
        # своего фона сквозь него всё равно видно исходный item.text(),
        # нарисованный делегатом списка ПОД ним (двоящийся текст). objectName
        # + непрозрачный фон в CONSTRUCTOR_QSS (см. QWidget#certRow) это
        # перекрывает.
        row.setObjectName("certRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 0, 6, 0)
        layout.setSpacing(8)

        label = QLabel(normalized_text)
        label.setObjectName("certRowLabel")
        layout.addWidget(label, 1)

        remove_btn = QPushButton()
        remove_btn.setObjectName("certRowRemoveBtn")
        remove_btn.setIcon(icons.icon("x", "#8e8e93", 12))
        remove_btn.setIconSize(QSize(12, 12))
        remove_btn.setFixedSize(20, 20)
        remove_btn.setToolTip("Удалить")
        remove_btn.clicked.connect(lambda: self._remove_certificate_row(item))
        layout.addWidget(remove_btn)

        item.setSizeHint(QSize(0, 30))
        list_widget.setItemWidget(item, row)

    def filter_employees(self, text: str):
        """Живой поиск по сайдбару (employeeSearchBox) -- прячет строки
        table_employees, не совпавшие по ФИО или должности, тем же приёмом,
        что и _filter_objects_tree() у objectsTree."""
        needle = text.strip().lower()
        table = self.mw.table_employees
        for row, employee in enumerate(self.employees):
            match = (
                not needle
                or needle in employee.full_name.lower()
                or needle in employee.position.lower()
            )
            table.setRowHidden(row, not match)
