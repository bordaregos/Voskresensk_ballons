"""Контроллер вкладки «Документы» — архив документов организации.

Не зависит от логики отчёта (get_form_data/STEP_ORDER/Project) — как
и «Сотрудники»/«Приборы», справочник общий для компании, см.
src/services/org_docs_store.py. Проще двух остальных вкладок
намеренно: у записи нет отдельной формы редактирования полей, только
таблица + загрузка/удаление файла целиком — так же, как в референсном
мокапе (docs/design/pipeline_sidebar_mockup.html, #panel-orgdocs).
"""

from datetime import date
from pathlib import Path
from uuid import uuid4

from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QInputDialog, QMessageBox, QTableWidgetItem,
)

from ..models.org_doc import OrgDoc
from ..services.org_docs_store import (
    ORG_DOCS_FILES_DIR, load_org_docs, save_org_docs, store_org_doc_file,
)


class OrgDocsTabController:
    """Управляет вкладкой «Документы» окна трубопровода."""

    def __init__(self, main_window):
        self.mw = main_window
        self.org_docs = load_org_docs()

        self.mw.table_org_docs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mw.table_org_docs.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.mw.pushButt_addOrgDoc.clicked.connect(self._add_org_doc)
        self.mw.pushButt_removeOrgDoc.clicked.connect(self._remove_org_doc)

        self._refresh_table()

    def _refresh_table(self):
        """Перерисовывает table_org_docs из self.org_docs -- строка row
        однозначно соответствует self.org_docs[row], как и в
        InstrumentsTabController._refresh_table()."""
        table = self.mw.table_org_docs
        table.setRowCount(len(self.org_docs))
        for row, doc in enumerate(self.org_docs):
            table.setItem(row, 0, QTableWidgetItem(doc.title))
            table.setItem(row, 1, QTableWidgetItem(doc.doc_type))
            table.setItem(row, 2, QTableWidgetItem(doc.date))

    def _add_org_doc(self):
        """«Загрузить документ» -- в референсе у этой кнопки нет
        обработчика вовсе (декоративна), но программа должна
        отрабатывать функционал по-настоящему: выбор файла ->
        название/тип текстом (два коротких QInputDialog, не отдельная
        форма -- у записи архива нет ничего сложнее) -> копия файла в
        ORG_DOCS_FILES_DIR (см. store_org_doc_file()) -> запись в
        манифест с сегодняшней датой."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.mw, "Выберите документ", "", "Все файлы (*.*)",
        )
        if not file_path:
            return
        source = Path(file_path)
        title, ok = QInputDialog.getText(self.mw, "Документ организации", "Название:", text=source.stem)
        if not ok or not title.strip():
            return
        doc_type, ok = QInputDialog.getText(self.mw, "Документ организации", "Тип (например, Лицензия):")
        if not ok:
            return
        filename = store_org_doc_file(source)
        self.org_docs.append(OrgDoc(
            id=uuid4().hex, title=title.strip(), doc_type=doc_type.strip(),
            date=date.today().strftime("%d.%m.%Y"), filename=filename,
        ))
        save_org_docs(self.org_docs)
        self._refresh_table()

    def _remove_org_doc(self):
        """«Удалить» -- по выбранной строке таблицы, с подтверждением
        (необратимо, как и удаление документа/объекта в дереве, см.
        MainWindow._delete_document())."""
        row = self.mw.table_org_docs.currentRow()
        if row < 0 or row >= len(self.org_docs):
            return
        doc = self.org_docs[row]
        reply = QMessageBox.question(
            self.mw, "Удалить документ",
            f"Удалить «{doc.title}» из архива? Это необратимо.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        (ORG_DOCS_FILES_DIR / doc.filename).unlink(missing_ok=True)
        del self.org_docs[row]
        save_org_docs(self.org_docs)
        self._refresh_table()
