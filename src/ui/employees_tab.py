"""Контроллер вкладки «Сотрудники» — справочник сотрудников компании.

Не зависит от логики отчёта (get_form_data/STEP_ORDER/Project) — данные
хранятся отдельно, см. src/services/employees_store.py: справочник общий
для компании, не привязан к текущему заключению/проекту, вставка клише в
.docx пока не реализуется.
"""

from pathlib import Path
from uuid import uuid4

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QListWidgetItem, QMessageBox, QTableWidgetItem,
)

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
        self.mw.employee_certificates_list.clear()
        self.mw.employee_certificate_input.setPlainText("")
        self._set_kleishe_preview(None)

    def _add_certificate(self):
        text = self.mw.employee_certificate_input.toPlainText().strip()
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

        if self._current_id is None:
            employee = Employee(
                id=uuid4().hex[:8],
                position=position,
                full_name=full_name,
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
