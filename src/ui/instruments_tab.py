"""Контроллер вкладки «Приборы» — справочник приборов компании.

Не зависит от логики отчёта (get_form_data/STEP_ORDER/Project) — данные
хранятся отдельно, см. src/services/instruments_store.py: справочник общий
для компании, не привязан к текущему заключению/проекту.
"""

from uuid import uuid4

from PyQt6.QtWidgets import (
    QAbstractItemView, QListWidgetItem, QMessageBox, QTableWidgetItem,
)

from ..models.instrument import Instrument
from ..services.instruments_store import load_instruments, save_instruments


class InstrumentsTabController:
    """Управляет вкладкой «Приборы» окна трубопровода."""

    def __init__(self, main_window):
        self.mw = main_window
        self.instruments = load_instruments()
        self._current_id = None

        self.mw.table_instruments.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mw.table_instruments.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.mw.table_instruments.itemSelectionChanged.connect(self._on_row_selected)
        self.mw.pushButt_newInstrument.clicked.connect(self._new_instrument)
        self.mw.pushButt_deleteInstrument.clicked.connect(self._delete_instrument)
        self.mw.pushButt_addDocument.clicked.connect(self._add_document)
        self.mw.pushButt_removeDocument.clicked.connect(self._remove_document)
        self.mw.pushButt_saveInstrument.clicked.connect(self._save_instrument)

        self._refresh_table()
        self._clear_form()

    def _refresh_table(self):
        """Перерисовывает table_instruments из self.instruments (тот же
        порядок, что и в списке — строка row однозначно соответствует
        self.instruments[row])."""
        table = self.mw.table_instruments
        table.setRowCount(len(self.instruments))
        for row, instrument in enumerate(self.instruments):
            table.setItem(row, 0, QTableWidgetItem(instrument.name))
            table.setItem(row, 1, QTableWidgetItem(instrument.serial_number))
            table.setItem(row, 2, QTableWidgetItem(instrument.cert_number))
            table.setItem(row, 3, QTableWidgetItem("; ".join(instrument.documents)))

    def _on_row_selected(self):
        row = self.mw.table_instruments.currentRow()
        if row < 0 or row >= len(self.instruments):
            return
        self._load_instrument_into_form(self.instruments[row])

    def _load_instrument_into_form(self, instrument: Instrument):
        self._current_id = instrument.id
        self.mw.instrument_name.setPlainText(instrument.name)
        self.mw.instrument_serial_number.setPlainText(instrument.serial_number)
        self.mw.instrument_cert_number.setPlainText(instrument.cert_number)

        self.mw.instrument_documents_list.clear()
        for document in instrument.documents:
            self.mw.instrument_documents_list.addItem(QListWidgetItem(document))

    def _new_instrument(self):
        self.mw.table_instruments.clearSelection()
        self._clear_form()

    def _clear_form(self):
        self._current_id = None
        self.mw.instrument_name.setPlainText("")
        self.mw.instrument_serial_number.setPlainText("")
        self.mw.instrument_cert_number.setPlainText("")
        self.mw.instrument_documents_list.clear()
        self.mw.instrument_document_input.setPlainText("")

    def _add_document(self):
        text = self.mw.instrument_document_input.toPlainText().strip()
        if not text:
            return
        self.mw.instrument_documents_list.addItem(QListWidgetItem(text))
        self.mw.instrument_document_input.setPlainText("")

    def _remove_document(self):
        row = self.mw.instrument_documents_list.currentRow()
        if row >= 0:
            self.mw.instrument_documents_list.takeItem(row)

    def _save_instrument(self):
        name = self.mw.instrument_name.toPlainText().strip()
        serial_number = self.mw.instrument_serial_number.toPlainText().strip()
        cert_number = self.mw.instrument_cert_number.toPlainText().strip()

        if not name:
            self.mw.show_message(
                "Не заполнены поля",
                "Укажите наименование прибора.",
                QMessageBox.Icon.Warning,
            )
            return

        documents = [
            self.mw.instrument_documents_list.item(i).text()
            for i in range(self.mw.instrument_documents_list.count())
        ]

        if self._current_id is None:
            instrument = Instrument(
                id=uuid4().hex[:8],
                name=name,
                serial_number=serial_number,
                cert_number=cert_number,
                documents=documents,
            )
            self.instruments.append(instrument)
            self._current_id = instrument.id
        else:
            for existing in self.instruments:
                if existing.id == self._current_id:
                    existing.name = name
                    existing.serial_number = serial_number
                    existing.cert_number = cert_number
                    existing.documents = documents
                    break

        save_instruments(self.instruments)
        self._refresh_table()
        self._select_row_by_id(self._current_id)

    def _delete_instrument(self):
        if self._current_id is None:
            return
        self.instruments = [i for i in self.instruments if i.id != self._current_id]
        save_instruments(self.instruments)
        self._refresh_table()
        self._clear_form()

    def _select_row_by_id(self, instrument_id):
        for row, instrument in enumerate(self.instruments):
            if instrument.id == instrument_id:
                self.mw.table_instruments.selectRow(row)
                return
