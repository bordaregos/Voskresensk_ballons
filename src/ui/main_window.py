"""Главное окно приложения: связывает main_window.ui с расчётными сервисами."""

from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QComboBox,
                             QPushButton, QSpinBox, QDateEdit, QTableWidgetItem, QTableWidget,
                             QMessageBox, QFileDialog, QGroupBox,
                             QTreeWidgetItem, QInputDialog, QMenu, QListWidgetItem,
                             QDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QDialogButtonBox,
                             QLabel, QWidget)
from PyQt6.QtCore import QLocale, Qt, QDate, QPointF, QTimer, QSize
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QPen
from PyQt6.uic import loadUi
from typing import Dict, Union
from pathlib import Path
from uuid import uuid4
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage, RichText

import os
import re
import subprocess
import html
import math

from ..equipment_types import EquipmentType, REGISTRY
from ..services.calculations import (
    calculate_strength,
    calculate_residual_life,
    generate_thickness_measurements,
    generate_ovalness_measurements,
    calculate_hardness_range,
    generate_hardness_measurements,
    find_min_thickness,
    format_year_range,
)
from ..services.formatting import (
    format_ru, format_ru_fixed, parse_ru, format_thickness_block, format_fio_initials,
    number_to_words_ru,
)
from ..services.calculations_pipeline import (
    calculate_pipeline_strength,
    calculate_pipeline_residual_life,
    generate_pipeline_thickness_measurements,
    get_allowable_stress,
    SegmentSpec,
)
from ..services.employees_store import (
    store_kleishe_image, load_employees, resolve_kleishe_path, find_employee_id_by_name,
)
from ..services.docx_layout import float_drawings_behind_text
from ..services import workspace
from ..models.project import Project
from ..config import NK_SCHEME_DIR, PNEVMO_GRAPH_DIR
from .widget_names_pipeline import SEGMENT_TYPES, PROGRAM_DEFAULT_ITEMS, AE_CLASS_TYPES


# Тёмная тема окна конструктора документов -- палитра 1:1 из
# docs/design/constructor_mockup.html (#1c1c1e/#2c2c2e/#0a84ff/#8e8e93/
# #38383a). Применяется ТОЛЬКО к окну конструктора (self.setStyleSheet() в
# __init__ при equipment_type.id == "constructor") -- баллоны и трубопровод
# по-прежнему рендерятся нативным стилем Qt, эта тема их не затрагивает.
# В проекте нет иконочного шрифта/.qrc (см. CLAUDE.md) -- там, где в мокапе
# иконка, здесь текстовые символы (▾/▸, ×) на обычных QPushButton/QLabel.
CONSTRUCTOR_QSS = """
QMainWindow, #constructorCentral { background: #1c1c1e; }
#constructorSidebar { background: #242426; border-right: 0.5px solid #38383a; }
#constructorSidebar QLabel { color: #8e8e93; font-size: 11px; }
#titleGroupToggle {
    background: transparent; border: none; color: #e5e5e7; font-size: 12px;
    font-weight: 500; text-align: left; padding: 6px; border-radius: 5px;
}
#titleGroupToggle:hover { background: #2c2c2e; }
#appendicesSoonLabel { color: #5a5a5c; font-size: 11.5px; padding: 6px; }
QListWidget#availableBlocksList {
    background: transparent; border: none; outline: none; font-size: 11.5px;
}
QListWidget#availableBlocksList::item {
    background: #2c2c2e; border: 0.5px solid #38383a; border-radius: 7px;
    padding: 8px 9px; margin: 2px 0; color: #e5e5e7;
}
QListWidget#availableBlocksList::item:hover { border-color: #0a84ff; }
QListWidget#availableBlocksList::item:selected { background: #2c2c2e; }
QLabel#crumbLabel {
    background: #202022; color: #8e8e93; font-size: 11px; padding: 8px 18px;
    border-bottom: 0.5px solid #2c2c2e;
}
QLabel#documentSectionLabel { color: #8e8e93; font-size: 11px; }
QListWidget#includedBlockList { background: transparent; outline: none; border: none; }
QListWidget#includedBlockList[filled="false"] {
    border: 1.5px dashed #38383a; border-radius: 8px;
}
QListWidget#includedBlockList[filled="true"]::item {
    background: #2c2c2e; border-radius: 8px; padding: 0; margin: 0;
}
QGroupBox#fieldsPanel {
    border: none; margin-top: 14px; padding-top: 8px;
}
QGroupBox#fieldsPanel::title {
    color: #8e8e93; font-size: 11px; subcontrol-origin: margin; left: 0; padding: 0;
}
QGroupBox#fieldsPanel QLabel { color: #c7c7cc; font-size: 12px; }
QGroupBox#fieldsPanel QPlainTextEdit {
    background: #2c2c2e; border: 0.5px solid #38383a; border-radius: 5px;
    color: #e5e5e7; font-size: 12px; padding: 6px 8px;
}
QGroupBox#fieldsPanel QPlainTextEdit:focus { border-color: #0a84ff; }
#constructorBottomBar { background: #1c1c1e; border-top: 0.5px solid #38383a; }
#constructorBottomBar QPushButton {
    background: transparent; border: none; color: #c7c7cc; font-size: 12px;
    padding: 9px; border-left: 0.5px solid #38383a;
}
#constructorBottomBar QPushButton#pushButt_generateWord { border-left: none; }
#constructorBottomBar QPushButton:disabled { color: #5a5a5c; }
"""


class MainWindow(QMainWindow):
    def __init__(self, equipment_type: EquipmentType = REGISTRY["balloon"]):
        """Инициализация конструктора класса. Пишем все атрибуты,
        что пригодятся нам по коду.

        equipment_type определяет, какой .ui загружать, какие виджеты
        резолвить и в каком порядке требовать шаги расчёта — см.
        src/equipment_types.py. По умолчанию баллоны, чтобы существующие
        вызовы MainWindow() не меняли поведение.
        """
        super().__init__()
        self.data = {}
        self.text = []
        self.s_min_lst = []
        self.file_handler = None
        self._completed_steps = set()
        self._current_document_path = None

        self.equipment_type = equipment_type
        # list(...) -- копия, не ссылка: конструктор документов дописывает
        # сюда имена динамически созданных полей реквизитов в рантайме (см.
        # _render_title_fields()); без копии .append() мутировал бы сам
        # модуль widget_names_constructor.py между запусками окна.
        self.PLAIN_TEXT_EDIT_NAMES = list(equipment_type.widget_names.PLAIN_TEXT_EDIT_NAMES)
        self.COMBO_BOX_NAMES = equipment_type.widget_names.COMBO_BOX_NAMES
        self.DATE_EDIT_NAMES = equipment_type.widget_names.DATE_EDIT_NAMES
        self.BUTTON_NAMES = equipment_type.widget_names.BUTTON_NAMES
        self.SPIN_BOX_NAMES = equipment_type.widget_names.SPIN_BOX_NAMES
        self.TABLE_WIDGET = equipment_type.widget_names.TABLE_WIDGET
        self.STEP_ORDER = equipment_type.step_order
        self.STEP_LABELS = equipment_type.step_labels

        loadUi(str(equipment_type.ui_path), self)

        # Автоматическая инициализация виджетов
        self.init_widgets()

        # Инициализация FileHandler
        self.init_file_handler()

        # Подключение сигналов — общие для всех типов
        self.pushButt_generateWord.clicked.connect(self.calculate)
        self.pushButton_saveProject.clicked.connect(self.save_project)
        self.pushButton_openProject.clicked.connect(self.open_project)

        if equipment_type.id == "balloon":
            self.pushButton_exportCSV.clicked.connect(self.export_csv)
            self.pushButt_amount.clicked.connect(self.fill_table)
            self.pushButt_sMinMin.clicked.connect(self.s_min_min_calc)
            self.pushButton_creatThickness.clicked.connect(self.calc_thick)
            self.pushButton_creatRasschProchn.clicked.connect(self.prochnost)
            self.pushButton_creatOstRes.clicked.connect(self.ost_res)
            self.pushButt_ovalnost.clicked.connect(self.ovalnost_calc)
            self.pushButt_tverdost.clicked.connect(self.tverdost)
            self.pushButton_importCSV.clicked.connect(self.import_csv)
        elif equipment_type.id == "pipeline":
            # Комбобоксы выбора специалиста (Приложения 1-6, 8, 9) --
            # хранят не текст, а индекс строки table_specialists (см.
            # _refresh_specialist_combo()), поэтому не входят ни в один
            # список widget_names_pipeline.py. Из-за этого выбор нигде
            # не попадал в JSON проекта и при открытии всегда откатывался
            # на первую строку -- см. get_form_data()/_fill_ui_from_project()
            # в file_handler.py и _refresh_program_specialist_combo() ниже.
            self.SPECIALIST_COMBO_NAMES = [
                "program_specialist", "act2_specialist", "vik_specialist",
                "thick_specialist", "uzk_specialist", "calc_specialist",
                "pnevmo_specialist", "ae_zakl_specialist",
            ]
            # employee_id сотрудника из справочника «Сотрудники» для каждой
            # строки table_specialists, по порядку строк -- см.
            # _add_specialist_row()/_remove_specialist_row(). Не входит ни в
            # TABLE_WIDGET, ни в один список widget_names_pipeline.py --
            # сохраняется/восстанавливается отдельно, см. file_handler.py.
            self._specialist_employee_ids = []
            # Префиксы плейсхолдеров подписи, для которых в шаблон
            # подставляется клише специалиста (InlineImage), см. calculate()
            # и _specialist_kleishe_image(). lead_specialist -- всегда первая
            # строка table_specialists, остальные 8 -- SPECIALIST_COMBO_NAMES
            # (program_specialist -> programm_specialist_* и т.п., названия
            # плейсхолдеров исторически с двумя "м", см. calculate()).
            self.KLEISHE_ROLE_PREFIXES = [
                "lead_specialist", "programm_specialist", "act2_specialist",
                "vik_specialist", "thick_specialist", "uzk_specialist",
                "calc_specialist", "pnevmo_specialist", "ae_zakl_specialist",
            ]
            self.pushButt_segments.clicked.connect(self.fill_segments_table)
            self.pushButton_genThickness.clicked.connect(self.calc_pipeline_thickness)
            self.pushButton_calcStrength.clicked.connect(self.calc_pipeline_strength_ui)
            self.pushButton_calcResidualLife.clicked.connect(self.calc_pipeline_residual_life_ui)
            self.pushButt_addSpecialist.clicked.connect(self._add_specialist_row)
            self.pushButt_removeSpecialist.clicked.connect(self._remove_specialist_row)
            self.pushButt_addReviewedDoc.clicked.connect(lambda: self._add_table_row(self.table_reviewed_docs))
            self.pushButt_removeReviewedDoc.clicked.connect(lambda: self._remove_table_row(self.table_reviewed_docs))
            self.pushButt_addDocSection5.clicked.connect(lambda: self._add_table_row(self.table_docs_section5))
            self.pushButt_removeDocSection5.clicked.connect(lambda: self._remove_table_row(self.table_docs_section5))
            self.pushButt_addVikVisualRow.clicked.connect(lambda: self._add_table_row(self.table_vik_visual))
            self.pushButt_removeVikVisualRow.clicked.connect(lambda: self._remove_table_row(self.table_vik_visual))
            self.pushButt_addVikMeasureRow.clicked.connect(lambda: self._add_table_row(self.table_vik_measure))
            self.pushButt_removeVikMeasureRow.clicked.connect(lambda: self._remove_table_row(self.table_vik_measure))
            self.pushButt_removeThickDevice.clicked.connect(lambda: self._remove_combo_current_item(self.thick_device))
            self.pushButt_removeUzkDevice.clicked.connect(lambda: self._remove_combo_current_item(self.uzk_device))
            self.pushButt_addUzkRow.clicked.connect(self._add_uzk_row)
            self.pushButt_removeUzkRow.clicked.connect(self._remove_uzk_row)
            self.pushButt_removePnevmoDevice.clicked.connect(lambda: self._remove_combo_current_item(self.pnevmo_device))
            self.pushButt_removeReportTitle.clicked.connect(lambda: self._remove_combo_current_item(self.report_title))
            self.pushButt_addPipeMaterial.clicked.connect(self._add_pipe_material_row)
            self.pushButt_removePipeMaterial.clicked.connect(lambda: self._remove_table_row(self.table_pipe_materials))
            self.p_rab_mpa.textChanged.connect(self._update_p_rab_kgs)
            self.p_rab_mpa.textChanged.connect(self._update_calc_p_rab_display)
            self.p_rab_kgs.textChanged.connect(self._update_pnevmo_pressure)
            self.p_rab_kgs.textChanged.connect(self._fill_pnevmo_stages_table)
            self.work_temp.textChanged.connect(self._update_calc_temp_display)
            self.years_of_operation.textChanged.connect(self._update_calc_years_operation_display)
            self.obj_naznach.textChanged.connect(self._update_pnevmo_obj_naznach_display)
            self.pnevmo_obj_naznach.textChanged.connect(self._update_ae_zakl_obj_control_display)
            self.pnevmo_date.dateChanged.connect(self._update_ae_zakl_date_display)
            self.report_date.dateChanged.connect(self._update_ae_zakl_report_date_display)
            self.pnevmo_pressure.textChanged.connect(self._update_pnevmo_pressure_hint)
            self.pnevmo_pressure.textChanged.connect(self._update_result_76_pressure)
            self.final_years_allowed.textChanged.connect(self._update_final_deadline_date)
            self.report_year.textChanged.connect(self._update_final_deadline_date)
            self.report_year.textChanged.connect(self._update_years_of_operation_display)
            self.year_start.textChanged.connect(self._update_years_of_operation_display)
            self.pushButt_addProgramItem.clicked.connect(self._add_program_item_row)
            self.pushButt_addProgramSubitem.clicked.connect(self._add_program_subitem_row)
            self.pushButt_removeProgramRow.clicked.connect(self._remove_program_row)
            self._seed_program_table_defaults()
            self.pushButt_chooseNkScheme.clicked.connect(self._choose_nk_scheme)
            self.pushButt_clearNkScheme.clicked.connect(self._clear_nk_scheme)
            self.pushButt_fillPnevmoAeTable.clicked.connect(self._fill_pnevmo_ae_table)
            self.pushButt_addPnevmoAeRow.clicked.connect(self._add_pnevmo_ae_row)
            self.pushButt_removePnevmoAeRow.clicked.connect(lambda: self._remove_table_row(self.table_pnevmo_ae))
            self.pushButt_addPnevmoStageRow.clicked.connect(lambda: self._add_table_row(self.table_pnevmo_stages))
            self.pushButt_removePnevmoStageRow.clicked.connect(lambda: self._remove_table_row(self.table_pnevmo_stages))
            self.pushButt_choosePnevmoGraph.clicked.connect(self._choose_pnevmo_graph)
            self.pushButt_clearPnevmoGraph.clicked.connect(self._clear_pnevmo_graph)

            from .employees_tab import EmployeesTabController
            self.employees_tab = EmployeesTabController(self)

            from .instruments_tab import InstrumentsTabController
            self.instruments_tab = InstrumentsTabController(self)

            from .orgdocs_tab import OrgDocsTabController
            self.orgdocs_tab = OrgDocsTabController(self)

            # Сайдбар: переключатели «Сотрудники»/«Приборы»/«Документы» —
            # общие справочники компании, не часть текущего отчёта: кнопки
            # генерации Word и работы с проектом там неуместны, см.
            # _update_report_buttons_visibility(). Дерево объектов/
            # документов (objectsTree) — навигация внутри "document".
            self.sidebarBtn_employees.clicked.connect(lambda: self._switch_view("employees"))
            self.sidebarBtn_instruments.clicked.connect(lambda: self._switch_view("instruments"))
            self.sidebarBtn_orgdocs.clicked.connect(lambda: self._switch_view("orgdocs"))
            self._current_view = "document"

            # Дерево "объект (папка) -> документ (.json внутри неё)" --
            # см. src/services/workspace.py. Клик по документу открывает
            # его (см. _open_document()); клик по объекту — стандартное
            # разворачивание/сворачивание QTreeWidget, ничего сверху не
            # навешено.
            self.sidebarBtn_createObject.clicked.connect(self._create_object_dialog)
            self.sidebarBtn_createDocument.clicked.connect(self._create_document_dialog)
            self.sidebarBtn_templates.clicked.connect(self._show_templates_menu)
            self.objectsTree.itemClicked.connect(self._on_objects_tree_item_clicked)
            self.objectsTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.objectsTree.customContextMenuRequested.connect(self._show_objects_tree_context_menu)
            self._refresh_objects_tree()
            self.sidebarSearchBox.textChanged.connect(self._filter_objects_tree)
            self._sidebar_collapsed = False
            # mainSplitter -- три ребёнка (revealStrip, sidebar, viewStack,
            # Фаза 7), sizes должен покрывать все три -- список короче
            # count() даёт непредсказуемое распределение (найдено
            # реальным багом: sidebar защёлкивался на maximumWidth=400
            # вместо заданных 240, потому что setSizes([240, 760]) на
            # трёх виджетах интерпретировался не так, как рассчитывали).
            self._sidebar_expanded_sizes = [0, 240, 760]
            self.sidebarBtn_collapse.clicked.connect(self._toggle_sidebar)
            self.sidebarBtn_expand.clicked.connect(self._toggle_sidebar)
            # sidebarBtn_pin -- чисто визуальный тумблер, как и в
            # референсе (togglePin() там тоже только перекрашивает
            # иконку, без функционального эффекта): checkable=true +
            # QPushButton:checked в styleSheet (.ui) уже даёт нужный вид
            # сам, без единой строки кода здесь.

            # Оглавление документа (Фаза 6): вложено в objectsTree как
            # дочерние строки открытого документа -- список groupbox'ов
            # статичен (не зависит от того, какой документ открыт,
            # форма всегда одна и та же), берётся из самой ленты
            # tab_document, а не хардкодится -- если разделы переставят
            # в Designer'е, список подстроится сам. Клики по строкам TOC
            # идут через тот же objectsTree.itemClicked, что и по
            # объектам/документам -- см. _on_objects_tree_item_clicked().
            self._suppress_toc_spy = False
            self._toc_groupboxes = self._collect_toc_groupboxes()
            self._current_toc_items = []
            self._current_toc_active_item = None
            self._toc_check_icon = self._make_check_icon()
            self._toc_circle_icon = self._make_circle_icon()
            self._toc_lock_icon = self._make_lock_icon()
            self.tab_document_scroll.verticalScrollBar().valueChanged.connect(self._on_document_scrolled)

            # Индикатор несохранённых изменений (Фаза 5.4) -- точка на
            # строке текущего документа в objectsTree.
            self._document_dirty = False
            self._dirty_icon = self._make_dot_icon("#e0983c")
            self._connect_dirty_tracking()

            # Ширина сайдбара задаётся кодом: .ui-формат не умеет
            # сериализовать QSplitter.sizes (нет XML-типа под QList<int>).
            # Диапазон перетаскивания ограничен minimumSize/maximumSize
            # самого sidebar (180..400 px в .ui). Индексы -- по составу
            # mainSplitter после Фазы 7: 0=revealStrip, 1=sidebar,
            # 2=viewStack; растягивается при изменении размера окна
            # только форма (индекс 2), сайдбар держит выставленную
            # ширину.
            self.mainSplitter.setSizes(self._sidebar_expanded_sizes)
            self.mainSplitter.setStretchFactor(0, 0)
            self.mainSplitter.setStretchFactor(1, 0)
            self.mainSplitter.setStretchFactor(2, 1)
            # Ручка перетаскивания шире дефолтной (~3-4px) -- за неё
            # неудобно было попасть мышью, отсюда и ощущение, что
            # ширину нельзя менять руками.
            self.mainSplitter.setHandleWidth(6)

            # Нижняя панель -- три равные колонки, как в референсе.
            # <property name="stretch"> в .ui не сработал бы: uic.loadUi()
            # (в отличие от кодогенератора pyuic6) не умеет разбирать
            # строку "1,1,1" для QHBoxLayout.setStretch(), падает на
            # старте (проверено headless-тестом) -- выставляется кодом.
            for i in range(self.bottom_buttons.count()):
                self.bottom_buttons.setStretch(i, 1)

            # Устанавливает начальный вид -- при запуске ни один документ
            # ещё не открыт (_current_document_path is None), TOC-строк
            # в дереве нет (появляются в _open_document()).
            self._switch_view("document")
            self.breadcrumbLabel.setOpenExternalLinks(False)
            self.breadcrumbLabel.linkActivated.connect(self._on_breadcrumb_link_activated)
            self._update_breadcrumb()
        elif equipment_type.id == "constructor":
            # Перетаскивание между списками настроено декларативно в самом
            # .ui (dragEnabled/acceptDrops/dragDropMode) -- Qt по умолчанию
            # кодирует все роли item'а (включая UserRole) в MIME при
            # перетаскивании между двумя QListWidget, так что специального
            # кода на сам drag не нужно. pushButt_generateWord уже
            # подключена к self.calculate выше (общая кнопка для всех
            # типов) -- она же и «Собрать документ» для конструктора.
            self.setStyleSheet(CONSTRUCTOR_QSS)
            self._dynamic_field_names = []

            self._refresh_available_blocks_list()
            self.availableBlocksList.itemClicked.connect(self._on_available_block_clicked)
            self.availableBlocksList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.availableBlocksList.customContextMenuRequested.connect(
                self._show_available_block_context_menu
            )

            self.titleGroupToggle.toggled.connect(self._toggle_title_group)

            # В списке ровно один блок (Phase 1, см. _process_block_drop()) --
            # родная линия-подсказка Qt "вставить выше/ниже" вводит в
            # заблуждение при замене (выглядит так, будто можно вставить
            # второй блок рядом), хотя реально всегда остаётся один. Сама
            # вставка above/below при этом всё равно у Qt происходит --
            # обрабатывается в _process_block_drop() независимо от того,
            # видна эта линия или нет.
            self.includedBlockList.setDropIndicatorShown(False)
            self.includedBlockList.model().rowsInserted.connect(self._on_block_dropped)
            self.pushButt_generateWord.setEnabled(False)
            self._show_included_block_placeholder()

    def init_file_handler(self):
        """Инициализация FileHandler для импорта/экспорта."""
        from .file_handler import FileHandler
        self.file_handler = FileHandler(self)

    def init_widgets(self):
        """Автоматически инициализирует все виджеты из UI"""
        # Инициализация QPlainTextEdit
        for name in self.PLAIN_TEXT_EDIT_NAMES:
            widget = self.findChild(QPlainTextEdit, name)
            if widget is None:
                raise ValueError(f"Не найден QPlainTextEdit с именем {name}")
            setattr(self, name, widget)

        # Инициализация QComboBox
        for name in self.COMBO_BOX_NAMES:
            widget = self.findChild(QComboBox, name)
            if widget is None:
                raise ValueError(f"Не найден QComboBox с именем {name}")
            setattr(self, name, widget)

        # Инициализация QPushButton
        for name in self.BUTTON_NAMES:
            widget = self.findChild(QPushButton, name)
            if widget is None:
                raise ValueError(f"Не найден QPushButton с именем {name}")
            setattr(self, name, widget)

        # Инициализация QSpinBox
        for name in self.SPIN_BOX_NAMES:
            widget = self.findChild(QSpinBox, name)
            if widget is None:
                raise ValueError(f"Не найден QSpinBox с именем {name}")
            setattr(self, name, widget)

        # Инициализация QDateEdit
        for name in self.DATE_EDIT_NAMES:
            widget = self.findChild(QDateEdit, name)
            if widget is None:
                raise ValueError(f"Не найден QDateEdit с именем {name}")
            setattr(self, name, widget)

        # Инициализация QTableWidget.
        for name in self.TABLE_WIDGET:
            widget = self.findChild(QTableWidget, name)
            if widget is None:
                raise ValueError(f"Не найден QTableWidget с именем {name}")
            setattr(self, name, widget)

    def get_form_data(self) -> Dict[str, Union[str, float]]:
        """Возвращает все данные формы в виде словаря"""

        # Получаем текст из всех QPlainTextEdit
        for name in self.PLAIN_TEXT_EDIT_NAMES:
            widget = getattr(self, name)
            self.data[name] = widget.toPlainText()

        # Получаем текущий текст из QComboBox
        for name in self.COMBO_BOX_NAMES:
            widget = getattr(self, name)
            self.data[name] = widget.currentText()

        # Комбобоксы выбора специалиста (только трубопровод) -- хранят
        # индекс строки table_specialists (currentData()), а не текст,
        # поэтому не в COMBO_BOX_NAMES. Сохраняем отдельно, иначе выбор
        # не переживает "Сохранить проект" -> "Открыть проект" и после
        # открытия откатывается на первую строку, см.
        # FileHandler._fill_ui_from_project()/_refresh_program_specialist_combo().
        for name in getattr(self, "SPECIALIST_COMBO_NAMES", []):
            widget = getattr(self, name)
            self.data[name] = widget.currentData()

        # Получаем текст из QSpinBox.
        for name in self.SPIN_BOX_NAMES:
            widget = getattr(self, name)
            self.data[name] = widget.value()

        # Получаем даты из QDateEdit.
        for name in self.DATE_EDIT_NAMES:
            widget = getattr(self, name)
            date = widget.date()
            if date.isValid():
                locale = QLocale('ru_RU')
                # Суффикс "г." -- только для трубопровода: в его шаблоне
                # везде, кроме final_deadline_date, дата стоит "голой"
                # (Дата проведения контроля {{ ... }}, титул {{ report_date
                # }}) -- эталонный документ TD_720291 везде добавляет "г.".
                # final_deadline_date -- исключение: за ним в шаблоне уже
                # стоит своё литеральное "года" (8.2, 8.4.1), суффикс
                # задвоил бы "г. года". Баллонный шаблон не проверялся на
                # такое же дублирование, поэтому его не трогаем.
                is_pipeline = self.equipment_type.id == "pipeline"
                suffix = " г." if (is_pipeline and name != "final_deadline_date") else ""
                if name == "report_date":
                    # Дата отчёта на титульном листе -- день в кавычках-ёлочках
                    # по канцелярской традиции: «15» ноября 2024. Текст в
                    # одинарных кавычках в формате QLocale выводится буквально.
                    self.data[name] = locale.toString(date, "'«'dd'»' MMMM yyyy") + suffix
                else:
                    # Формат: dd MMMM yyyy (пробелы, месяц в родительном падеже на русском)
                    self.data[name] = locale.toString(date, 'dd MMMM yyyy') + suffix
            else:
                self.data[name] = ""

        # Получаем текст из QTableWidget. Ячейка может быть обычным
        # QTableWidgetItem или виджетом (например, QComboBox -- см.
        # table_segments), поэтому при отсутствии item проверяем cellWidget.
        for name in self.TABLE_WIDGET:
            widget = getattr(self, name)
            table_data = []
            for row in range(widget.rowCount()):
                row_data = []
                for col in range(widget.columnCount()):
                    item = widget.item(row, col)
                    if item is not None:
                        row_data.append(item.text())
                    else:
                        cell_widget = widget.cellWidget(row, col)
                        if isinstance(cell_widget, QComboBox):
                            row_data.append(cell_widget.currentText())
                        else:
                            row_data.append("")
                table_data.append(row_data)
            self.data[name] = table_data

        return self.data

    def calculate(self):
        """Обработчик нажатия кнопки генерации Word с улучшенной обработкой ошибок"""
        if self.equipment_type.id == "constructor":
            # Конструктор собирает документ из перетащенных блоков, а не из
            # одного большого статического шаблона -- рендер устроен
            # совсем иначе (см. _calculate_constructor()), чем у
            # balloon/pipeline ниже, поэтому отдельная ветка, а не третий
            # elif в теле этого метода.
            self._calculate_constructor()
            return

        missing = [step for step in self.STEP_ORDER if step not in self._completed_steps]
        if missing:
            missing_labels = ", ".join(self.STEP_LABELS[step] for step in missing)
            self.show_message(
                "Не выполнены обязательные шаги",
                f"Перед генерацией документа выполните: {missing_labels}.",
                QMessageBox.Icon.Warning,
            )
            return

        try:
            # 1. Проверка заполненности полей
            if not all(
                getattr(self, name).toPlainText().strip()
                for name in self.equipment_type.required_fields
            ):
                raise ValueError("Не все обязательные поля заполнены")

            # 2. Получаем данные формы
            if self.equipment_type.id == "pipeline":
                # specialists -- список словарей для {% for %} в шаблоне;
                # table_specialists (список списков "как есть") тоже
                # попадёт в form_data ниже через get_form_data() -- нужен
                # для сохранения/восстановления проекта.
                # Колонки таблицы: 0 -- Должность, 1 -- ФИО, 2 -- Удостоверение
                # (полное, только для Таблицы 2), 3 -- Удостоверение (кратко,
                # для подписей после каждого из 9 приложений, см. ниже).
                self.data["specialists"] = self._table_to_dicts(
                    self.table_specialists,
                    ["position", "name", "cert_number", "cert_number_short"]
                )
                # name_initials -- "И. О. Фамилия" для таблицы подписи после
                # раздела 8 (Таблица 2 продолжает использовать полное "name").
                # employee_id -- сотрудник справочника «Сотрудники», из
                # которого взята эта строка (см. _add_specialist_row()),
                # нужен ниже для подстановки клише (InlineImage) в каждое из
                # 9 мест подписи, см. _specialist_kleishe_image(). Если связи
                # нет (строка вписана вручную или сохранена в project.json
                # до появления привязки к справочнику) -- пробуем найти
                # сотрудника по точному совпадению ФИО, иначе документы,
                # набранные раньше этой доработки, никогда не получили бы
                # клише, хотя вписанное ФИО совпадает с сотрудником в
                # справочнике буква в букву.
                roster = load_employees()
                for row, specialist in enumerate(self.data["specialists"]):
                    specialist["name_initials"] = format_fio_initials(specialist["name"])
                    employee_id = (
                        self._specialist_employee_ids[row]
                        if row < len(self._specialist_employee_ids) else None
                    )
                    if not employee_id:
                        employee_id = find_employee_id_by_name(roster, specialist["name"])
                    specialist["employee_id"] = employee_id

                # Таблица подписи после раздела 8 -- подписывает только один
                # (первый по списку) специалист, не цикл по всем; см.
                # template_schema.py. Явные плоские поля вместо {{
                # specialists[0]... }} в шаблоне -- Jinja упал бы на пустом
                # списке, а так ошибка ловится здесь с понятным текстом.
                if not self.data["specialists"]:
                    raise ValueError(
                        "Добавьте хотя бы одного специалиста в Таблице 2 "
                        "(1.3 Сведения о специалистах) -- он подписывает Отчёт"
                    )
                lead_specialist = self.data["specialists"][0]
                self.data["lead_specialist_position"] = lead_specialist["position"]
                self.data["lead_specialist_name_initials"] = lead_specialist["name_initials"]
                self.data["lead_specialist_cert_number"] = lead_specialist["cert_number_short"]
                self.data["lead_specialist_employee_id"] = lead_specialist["employee_id"]

                # "Программу составил" (Приложение 1) -- специалиста выбирает
                # оператор через program_specialist (индекс строки Таблицы 2),
                # а не жёстко первая строка, как у lead_specialist_* выше.
                programm_specialist_idx = self.program_specialist.currentData()
                if (
                    programm_specialist_idx is None
                    or programm_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Программу составил» "
                        "(Приложение 1) -- источник вариантов: Таблица 2 (1.3)"
                    )
                programm_specialist = self.data["specialists"][programm_specialist_idx]
                self.data["programm_specialist_position"] = programm_specialist["position"]
                self.data["programm_specialist_name_initials"] = programm_specialist["name_initials"]
                self.data["programm_specialist_cert_number"] = programm_specialist["cert_number_short"]
                self.data["programm_specialist_employee_id"] = programm_specialist["employee_id"]

                # "Анализ документации провёл" (Приложение 2) -- тот же
                # паттерн, что и "Программу составил" выше.
                act2_specialist_idx = self.act2_specialist.currentData()
                if (
                    act2_specialist_idx is None
                    or act2_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Анализ документации провёл» "
                        "(Приложение 2) -- источник вариантов: Таблица 2 (1.3)"
                    )
                act2_specialist = self.data["specialists"][act2_specialist_idx]
                self.data["act2_specialist_position"] = act2_specialist["position"]
                self.data["act2_specialist_name_initials"] = act2_specialist["name_initials"]
                self.data["act2_specialist_cert_number"] = act2_specialist["cert_number_short"]
                self.data["act2_specialist_employee_id"] = act2_specialist["employee_id"]

                # "Контроль провёл" (Приложение 3) -- тот же паттерн.
                vik_specialist_idx = self.vik_specialist.currentData()
                if (
                    vik_specialist_idx is None
                    or vik_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Контроль провёл» "
                        "(Приложение 3) -- источник вариантов: Таблица 2 (1.3)"
                    )
                vik_specialist = self.data["specialists"][vik_specialist_idx]
                self.data["vik_specialist_position"] = vik_specialist["position"]
                self.data["vik_specialist_name_initials"] = vik_specialist["name_initials"]
                self.data["vik_specialist_cert_number"] = vik_specialist["cert_number_short"]
                self.data["vik_specialist_employee_id"] = vik_specialist["employee_id"]

                # "Измерение провёл" (Приложение 4) -- тот же паттерн.
                thick_specialist_idx = self.thick_specialist.currentData()
                if (
                    thick_specialist_idx is None
                    or thick_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Измерение провёл» "
                        "(Приложение 4) -- источник вариантов: Таблица 2 (1.3)"
                    )
                thick_specialist = self.data["specialists"][thick_specialist_idx]
                self.data["thick_specialist_position"] = thick_specialist["position"]
                self.data["thick_specialist_name_initials"] = thick_specialist["name_initials"]
                self.data["thick_specialist_cert_number"] = thick_specialist["cert_number_short"]
                self.data["thick_specialist_employee_id"] = thick_specialist["employee_id"]

                # "Измерение провёл" (Приложение 5) -- тот же паттерн.
                uzk_specialist_idx = self.uzk_specialist.currentData()
                if (
                    uzk_specialist_idx is None
                    or uzk_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Измерение провёл» "
                        "(Приложение 5) -- источник вариантов: Таблица 2 (1.3)"
                    )
                uzk_specialist = self.data["specialists"][uzk_specialist_idx]
                self.data["uzk_specialist_position"] = uzk_specialist["position"]
                self.data["uzk_specialist_name_initials"] = uzk_specialist["name_initials"]
                self.data["uzk_specialist_cert_number"] = uzk_specialist["cert_number_short"]
                self.data["uzk_specialist_employee_id"] = uzk_specialist["employee_id"]

                # "Расчёт выполнил" (Приложение 6) -- тот же паттерн.
                calc_specialist_idx = self.calc_specialist.currentData()
                if (
                    calc_specialist_idx is None
                    or calc_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Расчёт выполнил» "
                        "(Приложение 6) -- источник вариантов: Таблица 2 (1.3)"
                    )
                calc_specialist = self.data["specialists"][calc_specialist_idx]
                self.data["calc_specialist_position"] = calc_specialist["position"]
                self.data["calc_specialist_name_initials"] = calc_specialist["name_initials"]
                self.data["calc_specialist_cert_number"] = calc_specialist["cert_number_short"]
                self.data["calc_specialist_employee_id"] = calc_specialist["employee_id"]

                # "Контроль выполнил" (Приложение 8) -- тот же паттерн.
                pnevmo_specialist_idx = self.pnevmo_specialist.currentData()
                if (
                    pnevmo_specialist_idx is None
                    or pnevmo_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Контроль выполнил» "
                        "(Приложение 8) -- источник вариантов: Таблица 2 (1.3)"
                    )
                pnevmo_specialist = self.data["specialists"][pnevmo_specialist_idx]
                self.data["pnevmo_specialist_position"] = pnevmo_specialist["position"]
                self.data["pnevmo_specialist_name_initials"] = pnevmo_specialist["name_initials"]
                self.data["pnevmo_specialist_cert_number"] = pnevmo_specialist["cert_number_short"]
                self.data["pnevmo_specialist_employee_id"] = pnevmo_specialist["employee_id"]

                # "Заключение составил" (Приложение 9) -- тот же паттерн.
                ae_zakl_specialist_idx = self.ae_zakl_specialist.currentData()
                if (
                    ae_zakl_specialist_idx is None
                    or ae_zakl_specialist_idx >= len(self.data["specialists"])
                ):
                    raise ValueError(
                        "Выберите специалиста в поле «Заключение составил» "
                        "(Приложение 9) -- источник вариантов: Таблица 2 (1.3)"
                    )
                ae_zakl_specialist = self.data["specialists"][ae_zakl_specialist_idx]
                self.data["ae_zakl_specialist_position"] = ae_zakl_specialist["position"]
                self.data["ae_zakl_specialist_name_initials"] = ae_zakl_specialist["name_initials"]
                self.data["ae_zakl_specialist_cert_number"] = ae_zakl_specialist["cert_number_short"]
                self.data["ae_zakl_specialist_employee_id"] = ae_zakl_specialist["employee_id"]

                # Таблица 1 (Приложение 8, п.11) -- список словарей под
                # {%tr for %} в шаблоне; колонки: 0 -- ПАЭ №, 1 -- Нагрузка,
                # 2 -- Класс источника (см. table_pnevmo_ae, AE_CLASS_TYPES).
                self.data["pnevmo_ae_results"] = self._table_to_dicts(
                    self.table_pnevmo_ae, ["paje_num", "nagruzka", "klass"]
                )

                # 8.2 -- "5 (пять) лет": число прописью в скобках рядом с цифрой.
                years_allowed_text = self.final_years_allowed.toPlainText().strip()
                try:
                    years_allowed_int = int(years_allowed_text)
                except ValueError:
                    raise ValueError(
                        f"«Разрешённый срок дальнейшей эксплуатации» должен быть "
                        f"целым числом лет: {years_allowed_text!r}"
                    )
                self.data["final_years_allowed_words"] = number_to_words_ru(years_allowed_int)

                # Приложение 8, п.1 -- дата контроля числом (15.08.2024), а не
                # текстом (pnevmo_date остаётся текстовым везде, где уже
                # используется, включая Приложение 9 -- см. отчёт о сравнении).
                self.data["pnevmo_date_numeric"] = self.pnevmo_date.date().toString("dd.MM.yyyy")
            # Копия, а не self.data напрямую: ниже в form_data пишутся
            # InlineImage (держат ссылку на DocxTemplate/дерево .docx) и
            # RichText (_apply_line_breaks) -- одноразовые объекты только
            # для рендера. self.get_form_data() возвращает self.data по
            # ссылке; без copy() эти объекты оседали бы в self.data
            # навсегда и следующее "Сохранить проект" падало бы с
            # RecursionError на dataclasses.asdict() -> copy.deepcopy()
            # лежащего в них lxml-дерева документа.
            form_data = dict(self.get_form_data())
            if self.equipment_type.id == "pipeline":
                self._apply_line_breaks(form_data)
            print("Данные для Word:", form_data)

            # 3. Проверяем наличие шаблона (используем config.py)
            from ..config import find_template, OUTPUT_DIR
            template_path = find_template(self.equipment_type.id)

            # 4. Загружаем и заполняем шаблон
            doc = DocxTemplate(template_path)

            if self.equipment_type.id == "pipeline":
                # Приложение 7 -- Схема НК: картинка не обязательна, при
                # отсутствии на месте {{ nk_scheme_image }} остаётся пусто.
                nk_scheme_filename = self.data.get("nk_scheme_filename")
                if nk_scheme_filename:
                    form_data["nk_scheme_image"] = InlineImage(
                        doc, str(NK_SCHEME_DIR / nk_scheme_filename), width=Mm(150)
                    )
                else:
                    form_data["nk_scheme_image"] = ""

                # Приложение 8 -- Рисунок 1 (график нагружения): тот же
                # приём, картинка не обязательна.
                pnevmo_graph_filename = self.data.get("pnevmo_graph_filename")
                if pnevmo_graph_filename:
                    form_data["pnevmo_graph_image"] = InlineImage(
                        doc, str(PNEVMO_GRAPH_DIR / pnevmo_graph_filename), width=Mm(150)
                    )
                else:
                    form_data["pnevmo_graph_image"] = ""

                # Клише специалиста (картинка из справочника «Сотрудники»,
                # см. EmployeesTabController) в каждое из 9 мест подписи --
                # тот же приём, не обязательно (сотрудник мог не загрузить
                # клише, а специалист может быть не найден в справочнике
                # даже через find_employee_id_by_name() выше). roster --
                # тот же справочник, что уже читали выше для employee_id.
                # kleishe_paths_used -- для _float_kleishe_drawings_behind_
                # text() ниже, после рендера.
                kleishe_paths_used = set()
                for prefix in self.KLEISHE_ROLE_PREFIXES:
                    form_data[f"{prefix}_kleishe"] = self._specialist_kleishe_image(
                        doc, roster, self.data.get(f"{prefix}_employee_id"), kleishe_paths_used
                    )

            doc.render(form_data)

            if self.equipment_type.id == "pipeline":
                # Клише должно быть "за текстом" (Word: Обтекание текстом ->
                # За текстом), а не обычной инлайн-картинкой, растягивающей
                # ячейку -- docxtpl не умеет вставлять плавающие картинки
                # напрямую, поэтому уже отрисованный XML патчится постфактум,
                # см. src/services/docx_layout.py. Размер (<wp:extent>) при
                # этом не меняется -- переносится тот же узел, а не пересоздаётся.
                self._float_kleishe_drawings_behind_text(doc, kleishe_paths_used)

            # 5. Генерируем имя файла
            if self.equipment_type.id == "balloon":
                output_filename = (
                    f"закл_{self.zakl_number.toPlainText().strip()}_"
                    f"рег-{self.reg_number.toPlainText().strip()}_"
                    f"р-{self.p_rab.toPlainText().strip()}_"
                    f"{self.rab_sreda.currentText()}_"
                    f"кбХиммаш_{self.amount.value()}шт.docx"
                )
            else:
                # Реальные номера отчётов часто содержат "/" (напр.
                # "681/24") -- недопустимо в имени файла, заменяем на "-".
                safe_report_number = self.report_number.toPlainText().strip().replace("/", "-")
                output_filename = (
                    f"отчёт_{safe_report_number}_"
                    f"рег-{self.reg_number.toPlainText().strip()}_"
                    f"р-{self.p_rab_mpa.toPlainText().strip()}_"
                    f"{self.work_medium.currentText()}.docx"
                )

            # 6. Место сохранения и имя файла -- оператор может изменить
            # и то, и другое; output_filename выше только подсказка по
            # умолчанию.
            output_dir = str(OUTPUT_DIR)
            os.makedirs(output_dir, exist_ok=True)
            default_path = os.path.join(output_dir, output_filename)

            output_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить документ", default_path, "Документы Word (*.docx)"
            )
            if not output_path:
                return  # отменено пользователем -- не ошибка

            doc.save(output_path)

            # 7. Уведомление об успехе
            self.show_message(
                "Готово!",
                f"Документ успешно сохранён:\n{output_path}",
                QMessageBox.Icon.Information  # PyQt6 использует QMessageBox.Icon
            )
            print(f"Документ успешно сохранён: {output_path}")

        except ValueError as ve:
            self.show_message("Ошибка ввода", str(ve), QMessageBox.Icon.Warning)
        except FileNotFoundError as fe:
            self.show_message("Файл не найден", str(fe), QMessageBox.Icon.Critical)
        except PermissionError:
            self.show_message(
                "Ошибка доступа",
                "Нет прав для записи в указанную папку",
                QMessageBox.Icon.Critical
            )
        except Exception as e:
            self.show_message(
                "Ошибка генерации",
                f"Неизвестная ошибка: {str(e)}",
                QMessageBox.Icon.Critical
            )

    def _calculate_constructor(self):
        """Сборка документа конструктора (equipment_type == "constructor").

        Phase 1: ровно один блок -- титульный лист, перетащенный из
        availableBlocksList в includedBlockList (id варианта -- в
        Qt.ItemDataRole.UserRole каждого item'а, см. _add_available_blocks()).
        Рендер -- тот же однократный DocxTemplate(path).render(data) +
        .save(path), что и в calculate() (строки 659-740) для balloon/
        pipeline, просто на маленьком файле-фрагменте вместо большого шаблона.
        Склейка нескольких блоков в один .docx появится в Phase 2, когда
        блоков в includedBlockList станет больше одного."""
        if self.includedBlockList.count() == 0:
            self.show_message(
                "Нечего собирать",
                "Перетащите титульный лист из списка слева в основную область.",
                QMessageBox.Icon.Warning,
            )
            return

        variant_id = self.includedBlockList.item(0).data(Qt.ItemDataRole.UserRole)

        try:
            from ..config import OUTPUT_DIR, find_title_template

            form_data = self.get_form_data()
            tpl = DocxTemplate(find_title_template(variant_id))
            tpl.render(form_data)

            doc_number_widget = getattr(self, "doc_number", None)
            safe_doc_number = (
                doc_number_widget.toPlainText().strip().replace("/", "-") if doc_number_widget else ""
            )
            output_filename = f"констр_{safe_doc_number or 'документ'}.docx"

            output_dir = str(OUTPUT_DIR)
            os.makedirs(output_dir, exist_ok=True)
            default_path = os.path.join(output_dir, output_filename)

            output_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить документ", default_path, "Документы Word (*.docx)"
            )
            if not output_path:
                return  # отменено пользователем -- не ошибка

            tpl.save(output_path)

            self.show_message(
                "Готово!", f"Документ успешно сохранён:\n{output_path}", QMessageBox.Icon.Information,
            )
            print(f"Документ успешно сохранён: {output_path}")

        except FileNotFoundError as fe:
            self.show_message("Файл не найден", str(fe), QMessageBox.Icon.Critical)
        except PermissionError:
            self.show_message(
                "Ошибка доступа", "Нет прав для записи в указанную папку", QMessageBox.Icon.Critical,
            )
        except Exception as e:
            self.show_message("Ошибка генерации", f"Неизвестная ошибка: {str(e)}", QMessageBox.Icon.Critical)

    # -- Конструктор документов: сайдбар «Титульные листы» -------------------

    ADD_VARIANT_MARKER = "__add__"
    INCLUDED_BLOCK_PLACEHOLDER = "__empty__"

    def _toggle_title_group(self, expanded: bool):
        """Сворачивание/разворачивание группы «Титульные листы» -- сам
        QListWidget прячется/показывается, кнопка-заголовок меняет текст
        (▾/▸ -- в проекте нет иконочного шрифта, см. CONSTRUCTOR_QSS)."""
        self.availableBlocksList.setVisible(expanded)
        arrow = "▾" if expanded else "▸"
        self.titleGroupToggle.setText(f"{arrow}  Титульные листы")

    ITEM_CHARS_PER_LINE = 18  # см. _set_wrapped_item_size_hint()

    def _set_wrapped_item_size_hint(self, item: QListWidgetItem):
        """QListWidget не пересчитывает высоту item'а под перенесённый на
        несколько строк текст сам по себе -- реальная отрисованная высота
        строки (QSS font-size, паддинг item'а) оказалась заметно больше,
        чем даёт QFontMetrics/QLabel.sizeHint() при замере до полного
        применения стиля (проверено: даже нарочно завышенная в 2 раза
        оценка не спасала от обрезки многоточием). Вместо хрупкого замера
        шрифтом -- грубая, но надёжная оценка по числу символов: пусть
        лучше немного лишнего пустого места снизу, чем обрезанный текст.

        QSize с отрицательной шириной Qt считает невалидным и тихо
        игнорирует весь setSizeHint() целиком (проверено) -- ширину нельзя
        оставить «как есть» через -1, нужно явное значение."""
        width = self.availableBlocksList.viewport().width() or 200
        lines = max(1, math.ceil(len(item.text()) / self.ITEM_CHARS_PER_LINE))
        item.setSizeHint(QSize(width, lines * 22 + 20))

    def _refresh_available_blocks_list(self):
        """Перестраивает availableBlocksList из get_all_title_variants()
        (встроенные TITLE_VARIANTS + пользовательские из JSON) + сентинел
        «+ Добавить» последним item'ом -- вызывается при старте и после
        любой правки списка вариантов (добавление/удаление)."""
        from ..services.title_variants_store import get_all_title_variants

        self.availableBlocksList.clear()
        for variant_id, title_config in get_all_title_variants().items():
            item = QListWidgetItem(title_config.document_title)
            item.setData(Qt.ItemDataRole.UserRole, variant_id)
            self.availableBlocksList.addItem(item)

        add_item = QListWidgetItem("+  Добавить")
        add_item.setData(Qt.ItemDataRole.UserRole, self.ADD_VARIANT_MARKER)
        add_item.setFlags(add_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
        add_item.setForeground(QColor("#0a84ff"))
        self.availableBlocksList.addItem(add_item)

        # Пересчёт высоты -- следующим тиком цикла событий: во время
        # заполнения (в т.ч. при старте, до первого show()) viewport() ещё
        # не имеет окончательной геометрии, ширина под перенос текста и
        # суммарная высота item'ов посчитались бы неверно.
        QTimer.singleShot(0, self._resize_available_blocks_list_to_content)

    def _resize_available_blocks_list_to_content(self):
        """QListWidget с vsizetype=Maximum (.ui) сам по себе не растягивает
        sizeHint() под сумму высот item'ов -- без этого список обрезался бы
        внутренним скроллом даже когда под содержимое хватает места в
        сайдбаре."""
        list_widget = self.availableBlocksList
        for i in range(list_widget.count()):
            self._set_wrapped_item_size_hint(list_widget.item(i))
        total_height = sum(
            list_widget.item(i).sizeHint().height() for i in range(list_widget.count())
        )
        list_widget.setFixedHeight(total_height + 4)

    def _on_available_block_clicked(self, item: QListWidgetItem):
        """Клик по обычному варианту ничего не делает (выбор -- через
        drag-and-drop, см. _on_block_dropped()); клик по сентинелу «+
        Добавить» открывает модалку создания нового варианта."""
        if item.data(Qt.ItemDataRole.UserRole) == self.ADD_VARIANT_MARKER:
            self._open_add_title_variant_dialog()

    def _open_add_title_variant_dialog(self):
        """Модалка «Новый вариант титульного листа» -- сохраняет только
        метаданные (id + текст заголовка) в JSON, как справочники
        сотрудников/приборов; .docx-заготовку под новый id оператор
        генерирует отдельно через CLI (find_title_template() уже подсказывает
        точную команду, если заготовки ещё нет)."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Новый вариант титульного листа")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Заголовок:"))
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Например, Протокол по результатам контроля")
        layout.addWidget(line_edit)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text = line_edit.text().strip()
        if not text:
            return

        from ..models.title_variant import TitleVariant
        from ..services.template_schema import DEFAULT_TITLE_SUBTITLE_FIELDS
        from ..services.title_variants_store import load_title_variants, save_title_variants

        variants = load_title_variants()
        variants.append(TitleVariant(
            id=uuid4().hex[:8], document_title=text, subtitle_fields=DEFAULT_TITLE_SUBTITLE_FIELDS,
        ))
        save_title_variants(variants)
        self._refresh_available_blocks_list()

    def _show_available_block_context_menu(self, pos):
        """Правый клик по варианту -- «Удалить», только для пользовательских
        вариантов (встроенные TITLE_VARIANTS через UI не удаляются)."""
        from ..services.template_schema import TITLE_VARIANTS

        item = self.availableBlocksList.itemAt(pos)
        if item is None:
            return
        variant_id = item.data(Qt.ItemDataRole.UserRole)
        if variant_id in (None, self.ADD_VARIANT_MARKER) or variant_id in TITLE_VARIANTS:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("Удалить")
        if menu.exec(self.availableBlocksList.mapToGlobal(pos)) == delete_action:
            self._delete_title_variant(variant_id, item.text())

    def _delete_title_variant(self, variant_id: str, label: str):
        answer = QMessageBox.question(
            self, "Удалить вариант", f"Удалить вариант «{label}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        from ..services.title_variants_store import load_title_variants, save_title_variants

        variants = [v for v in load_title_variants() if v.id != variant_id]
        save_title_variants(variants)
        self._refresh_available_blocks_list()

        included = self.includedBlockList
        if included.count() and included.item(0).data(Qt.ItemDataRole.UserRole) == variant_id:
            self._clear_included_block()

    # -- Конструктор документов: область документа ---------------------------

    def _on_block_dropped(self, parent, first, last):
        """Реагирует на успешный drop в includedBlockList. rowsInserted
        стреляет ДО того, как Qt успевает заполнить данные нового item'а
        (проверено: text() и UserRole внутри этого сигнала ещё пустые,
        заполняются через мгновение уже после dropMimeData()) -- поэтому
        сама обработка отложена на следующий тик цикла событий через
        QTimer.singleShot(0, ...), где item уже полностью готов."""
        QTimer.singleShot(0, self._process_block_drop)

    def _process_block_drop(self):
        """Реагирует на успешный drop в includedBlockList (Qt сам создаёт
        item со всеми ролями исходного, включая UserRole, при перетаскивании
        между двумя QListWidget -- см. план). В документе ровно один
        титульный лист (Phase 1) -- второй drop оставляет только последний
        добавленный item.

        rowsInserted стреляет и на программные addItem() (см.
        _show_included_block_placeholder() -- вызывается при старте и при
        очистке, не только на реальный drag-and-drop), поэтому плейсхолдер
        сначала исключается из рассмотрения, а не только последний item --
        Qt может вставить перетащенный item и ПЕРЕД плейсхолдером/старым
        item'ом (см. ниже), не только после."""
        block_list = self.includedBlockList
        real_indices = [
            i for i in range(block_list.count())
            if block_list.item(i).data(Qt.ItemDataRole.UserRole) != self.INCLUDED_BLOCK_PLACEHOLDER
        ]
        if not real_indices:
            return  # в списке только сам плейсхолдер -- нечего обрабатывать

        # При замене (два реальных item'а: старый + новый перетащенный, или
        # первый drop -- плейсхолдер + новый) Qt сам решает, вставить ли
        # новый item ДО или ПОСЛЕ уже лежащего, в зависимости от того, в
        # верхнюю или нижнюю половину курсор попал при drop'е
        # (DropIndicatorPosition AboveItem/BelowItem) -- порядок в списке не
        # гарантирован. Раньше код слепо брал последний item -- если Qt
        # вставлял новый ПЕРЕД старым, последним оставался старый item с
        # уже стёртым text() (см. item.setText("") ниже, из предыдущей
        # обработки) -- отсюда пустая строка вместо названия при повторной
        # замене. Новый item опознаётся по отсутствию itemWidget: его
        # выставляет только эта функция, а Qt при перетаскивании копирует
        # роли исходного item'а (текст, UserRole), но не itemWidget.
        keep_index = next(
            (i for i in real_indices if block_list.itemWidget(block_list.item(i)) is None),
            real_indices[-1],
        )
        for i in reversed(range(block_list.count())):
            if i != keep_index:
                block_list.takeItem(i)

        item = block_list.item(0)
        variant_id = item.data(Qt.ItemDataRole.UserRole)
        label_text = item.text()
        # Текст item'а показывает не нативная отрисовка делегата, а сам row
        # (QLabel ниже) -- иначе поверх setItemWidget() проступает
        # оригинальный текст item'а вторым, наложенным слоем. sizeHint тоже
        # сбрасываем -- Qt копирует роли (включая SizeHintRole) исходного
        # item'а при перетаскивании, из-за чего сюда попадала многострочная
        # высота карточки в availableBlocksList вместо компактной строки.
        item.setText("")
        item.setSizeHint(QSize(block_list.viewport().width() or 200, 42))

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 8, 6, 8)
        # WA_TransparentForMouseEvents -- клики по тексту должны доходить до
        # row.mousePressEvent (сворачивание/разворачивание реквизитов, см.
        # _toggle_fields_panel()), а не гаситься самим QLabel (мышиные
        # события Qt не всплывают от ребёнка к родителю сами по себе, в
        # отличие от event bubbling в DOM).
        text_label = QLabel(label_text)
        text_label.setWordWrap(True)
        text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row_layout.addWidget(text_label, stretch=1)
        self.includedBlockChevron = QLabel("▾")
        self.includedBlockChevron.setStyleSheet("color: #8e8e93; font-size: 11px;")
        self.includedBlockChevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row_layout.addWidget(self.includedBlockChevron)
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setFlat(True)
        remove_btn.clicked.connect(self._clear_included_block)
        row_layout.addWidget(remove_btn)
        # QPushButton остаётся обычным (не прозрачным для мыши) -- его
        # собственный клик по-прежнему обрабатывается им самим, до row
        # не долетает, поэтому отдельный stopPropagation тут не нужен.
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.mousePressEvent = self._toggle_fields_panel
        block_list.setItemWidget(item, row)
        self._set_included_block_filled(True)

        # Список без этого остаётся высотой под старый maximumSize из .ui
        # (под пустое состояние с текстом-подсказкой) -- карточка внутри
        # тогда болтается с зазором сверху/снизу вместо того, чтобы
        # заполнять всю площадь блока.
        block_list.setFixedHeight(
            item.sizeHint().height() + 2 * block_list.frameWidth() + 4
        )

        self._render_title_fields(variant_id)
        self.crumbLabel.setText(f"Конструктор документов / {label_text}")
        self.fieldsPanel.setVisible(True)
        self.pushButt_generateWord.setEnabled(True)

    def _set_included_block_filled(self, filled: bool):
        """Переключает QSS-состояние includedBlockList через динамическое
        свойство ("filled" в CONSTRUCTOR_QSS) -- пунктирная рамка только в
        пустом состоянии, у заполненной карточки своя (сплошной фон,
        никакой рамки у самого списка) -- иначе рамка списка и фон
        item'а никогда не совпадают точь-в-точь (зазоры/наплывы по краям,
        не совпадающие радиусы), что и было исходной проблемой."""
        block_list = self.includedBlockList
        block_list.setProperty("filled", filled)
        block_list.style().unpolish(block_list)
        block_list.style().polish(block_list)

    def _show_included_block_placeholder(self):
        """Пустое состояние includedBlockList -- ненажимаемый item-подсказка
        вместо пустого списка без текста (Qt не даёт «placeholder-текст» у
        QListWidget нативно)."""
        block_list = self.includedBlockList
        block_list.clear()

        placeholder = QListWidgetItem("Перетащите титульный лист сюда")
        placeholder.setData(Qt.ItemDataRole.UserRole, self.INCLUDED_BLOCK_PLACEHOLDER)
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        placeholder.setForeground(QColor("#5a5a5c"))
        placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # AlignCenter центрирует текст только внутри РЕАЛЬНОЙ высоты item'а
        # (без явного sizeHint это естественная высота одной строки, ~20px),
        # а не внутри всех 56px box'а -- без этого текст залипает у верхнего
        # края с пустотой снизу. frameShape=NoFrame (.ui) -- inner-высота
        # виджета совпадает с его maximumSize, поэтому 56 без поправок.
        placeholder.setSizeHint(QSize(block_list.viewport().width() or 200, 56))
        block_list.addItem(placeholder)
        self._set_included_block_filled(False)
        block_list.setFixedHeight(56)

    def _clear_included_block(self):
        self._show_included_block_placeholder()
        self.fieldsPanel.setVisible(False)
        self.crumbLabel.setText("Конструктор документов / без титульного листа")
        self.pushButt_generateWord.setEnabled(False)

    def _toggle_fields_panel(self, event):
        """Левый клик по перетащенному блоку в includedBlockList сворачивает/
        разворачивает fieldsPanel (реквизиты титульного листа) -- см. мокап
        docs/design/constructor_mockup.html, toggleFields(). Клик по
        remove_btn ("×") сюда не долетает (см. _process_block_drop())."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        visible = not self.fieldsPanel.isVisible()
        self.fieldsPanel.setVisible(visible)
        self.includedBlockChevron.setText("▾" if visible else "▸")

    def _render_title_fields(self, variant_id: str):
        """Перестраивает titleFieldsLayout под набор полей конкретного
        варианта (get_all_title_variants()[variant_id].subtitle_fields) --
        поля разные у разных вариантов (напр. «Отчёт» -- 8 полей, остальные
        -- 4), поэтому строятся в рантайме, а не заранее в .ui.

        Динамически созданные виджеты регистрируются в self.PLAIN_TEXT_EDIT_NAMES
        -- том же списке, что уже читают get_form_data()/init_widgets() --
        вместо отдельного пути сохранения/чтения данных для конструктора."""
        from ..services.template_schema import TITLE_FIELD_LABELS
        from ..services.title_variants_store import get_all_title_variants

        for name in self._dynamic_field_names:
            if name in self.PLAIN_TEXT_EDIT_NAMES:
                self.PLAIN_TEXT_EDIT_NAMES.remove(name)
        self._dynamic_field_names = []

        layout = self.titleFieldsLayout
        while layout.rowCount():
            layout.removeRow(0)

        field_ids = get_all_title_variants()[variant_id].subtitle_fields
        for field_id in field_ids:
            widget = QPlainTextEdit()
            widget.setMaximumHeight(32)
            widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            layout.addRow(TITLE_FIELD_LABELS.get(field_id, field_id), widget)
            setattr(self, field_id, widget)
            self.PLAIN_TEXT_EDIT_NAMES.append(field_id)
            self._dynamic_field_names.append(field_id)

    def show_message(self, title, text, icon=QMessageBox.Icon.Information):
        """Универсальный метод показа сообщений"""
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def _check_prerequisite(self, step: str) -> bool:
        """Проверяет, что предыдущий шаг из STEP_ORDER выполнен.

        Если нет — показывает предупреждение вместо тихого сбоя
        (см. STEP_ORDER) и возвращает False.
        """
        idx = self.STEP_ORDER.index(step)
        if idx == 0:
            return True
        prev = self.STEP_ORDER[idx - 1]
        if prev not in self._completed_steps:
            self.show_message(
                "Нарушен порядок действий",
                f"Сначала выполните шаг {self.STEP_LABELS[prev]}.",
                QMessageBox.Icon.Warning,
            )
            return False
        return True

    # --- Методы импорта/экспорта ---

    def import_csv(self):
        """Импорт баллонов из CSV файла."""
        if self.file_handler:
            self.file_handler.import_csv_balloon_list()

    def export_csv(self):
        """Экспорт баллонов в CSV файл."""
        if self.file_handler:
            self.file_handler.export_csv_balloon_list()

    def save_project(self):
        """Сохранение проекта в JSON файл."""
        if self.file_handler:
            self.file_handler.save_project_json()

    def open_project(self):
        """Загрузка проекта из JSON файла."""
        if self.file_handler:
            self.file_handler.open_project_json()

    def fill_table(self):
        """Заполнение таблицы баллонов. Заполняется 1й столбец!!!"""
        self.text = (self.zav_nums.toPlainText()).split(', ')
        amount = self.amount.value()
        table = self.table_ballons
        if len(self.text) == amount:
            table.setRowCount(amount)
            for row, zav_num in enumerate(self.text):
                item = QTableWidgetItem(zav_num)
                table.setItem(row, 0, item)
            self._completed_steps.add("amount")

        else:
            print(f"Кол-во баллонов {amount} не совпадает с введёными зав. №№ {len(self.text)}")

        self.data.update({"tables": [{"num": str(i + 1)} for i in range(len(self.text))]})

    def s_min_min_calc(self):
        """Вычисляет минимальное значение из второго столбца и выводит в QPlainTextEdit"""
        if not self._check_prerequisite("s_min_min"):
            return

        self.s_min_lst = []
        years_min_max_lst = []
        table = self.table_ballons

        # Проверка наличия данных в self.text
        if not self.text:
            print("Ошибка: список заводских номеров пуст. Нажмите кнопку 'Количество'")
            self.s_min_total.setPlainText("Нет данных")
            return

        # Собираем все числовые значения из второго столбца
        for row in range(table.rowCount()):
            item = table.item(row, 1)
            if item is not None and item.text():
                try:
                    self.s_min_lst.append(parse_ru(item.text()))
                except ValueError:
                    print(f"Пропуск нечислового значения в строке {row}")
                    continue

        # Вычисляем минимум (если есть данные)
        try:
            min_result = find_min_thickness(self.s_min_lst)
        except ValueError:
            self.s_min_total.setPlainText("Нет данных")
            self.zav_s_min.setPlainText("Нет данных")
            print("Ошибка: нет числовых данных для вычисления минимума")
        else:
            self.s_min_total.setPlainText(format_ru(min_result.s_min))
            if min_result.s_min_index < len(self.text):
                self.zav_s_min.setPlainText(self.text[min_result.s_min_index])
            else:
                print(f"Ошибка: индекс {min_result.s_min_index} выходит за пределы списка {len(self.text)}")
                self.zav_s_min.setPlainText("Нет данных")
            self._completed_steps.add("s_min_min")

        # Собираем все года из третьего столбца.
        for row in range(table.rowCount()):
            item = table.item(row, 2)
            if item is not None and item.text():
                try:
                    years_min_max_lst.append(int(item.text()))
                except ValueError:
                    print(f"Пропуск нечислового значения в строке {row}")
                    continue

        # Вычисляем диапазон годов изготовления и добавляем в словарь data на вывод в ворд.
        self.data.update({"min_year": format_year_range(years_min_max_lst)})

    def calc_thick(self):
        """Функция - генератор толщин."""
        if not self._check_prerequisite("thickness"):
            return

        thick_table = self.table_thick
        amount = self.amount.value()
        tolshiny_lst = []

        # Устанавливаем высоту строки (вызовите это один раз при инициализации)
        thick_table.verticalHeader().setDefaultSectionSize(100)

        if len(self.text) != amount:
            # Обработка несоответствия количества элементов
            thick_table.setRowCount(0)
            return

        thick_table.setRowCount(amount)

        for row, zav_num in enumerate(self.text):
            # Устанавливаем заводской номер в первый столбец
            item = QTableWidgetItem(zav_num)
            thick_table.setItem(row, 0, item)

            table = self.table_ballons
            s_min_item = table.item(row, 1)
            g_i_bal_item = table.item(row, 2)
            massa_item = table.item(row, 3)

            # Получаем значения из ячеек
            s_min = s_min_item.text() if s_min_item else ""
            g_i_bal = g_i_bal_item.text() if g_i_bal_item else ""
            massa = massa_item.text() if massa_item else ""

            tolshiny_dict = {
                "zav": zav_num,
                "s_min": s_min,
                "g_i_bal": g_i_bal,
                "massa": massa
            }

            # Проверяем, что есть данные в self.s_min_lst
            if row < len(self.s_min_lst):
                try:
                    nums = float(self.s_min_lst[row])

                    # Генерируем 20 замеров толщины вокруг измеренного минимума
                    res_thick = generate_thickness_measurements(nums)

                    # Добавляем значения в словарь
                    for i, value in enumerate(res_thick, 1):
                        tolshiny_dict[f"s{i}"] = format_ru_fixed(value)

                    # Форматируем в 5 строк по 4 числа
                    res_thick_str = format_thickness_block(res_thick)

                    # Устанавливаем значения во второй столбец
                    item2 = QTableWidgetItem(res_thick_str)
                    thick_table.setItem(row, 1, item2)
                    tolshiny_lst.append(tolshiny_dict)

                except (ValueError, TypeError) as e:
                    print(f"Ошибка обработки данных для строки {row}: {e}")
                    continue

        self.data.update({"ballony": tolshiny_lst})
        self._completed_steps.add("thickness")

    def s_max_lst(self):
        """Собираем все макс толщины в список."""
        s_max_lst = []
        table = self.table_ballons

        for row in range(table.rowCount()):
            item = table.item(row, 2)
            if item is not None and item.text():
                try:
                    s_max_lst.append(float(item.text().replace(',', '.')))
                except ValueError:
                    print(f"Пропуск нечислового значения в строке {row}")
                    continue
        print(s_max_lst)

    def ovalnost_calc(self):
        """Расчёт овальности."""
        if not self._check_prerequisite("ovalness"):
            return

        bal_oval = []

        for zav in self.text:
            bal_oval_dict = {
                "z_n": zav
            }
            for i, m in enumerate(generate_ovalness_measurements(count=3)):
                bal_oval_dict.update({
                    f"d_max_rand{i}": f'{m.d_max}',
                    f"d_min_rand{i}": f'{m.d_min}',
                    f"oval{i}": f'{m.ovalness}'
                })

            bal_oval.append(bal_oval_dict)
        self.data.update({"bal_oval": bal_oval})
        self._completed_steps.add("ovalness")

    def tverdost(self) -> None:
        """Расчёт твёрдости и подготовка данных для Word."""
        if not self._check_prerequisite("hardness"):
            return
        try:
            # 1. Получаем предел прочности (Rm) из интерфейса — то же поле,
            # что уже вводится оператором для расчёта прочности в prochnost().
            rm = parse_ru(self.vrem_sopr_min.toPlainText())

            # 2. Расчёт минимальной и максимальной твёрдости по ГОСТ
            hb_range = calculate_hardness_range(rm)

            # 3. Генерация значений для каждого баллона (если нужно)
            tverdost_data = []

            for zav in self.text:
                tverdost_dict = {
                    "zav": zav
                }
                measurements = generate_hardness_measurements(hb_range.hb_min, hb_range.hb_max)
                for i, hb_random in enumerate(measurements, 1):
                    tverdost_dict.update({f"hb_{i}": f"{hb_random}"})
                tverdost_data.append(tverdost_dict)

            # 4. Формируем словарь для плейсхолдеров Word
            self.data.update({
                "hb_min": format_ru(hb_range.hb_min),
                "hb_max": format_ru(hb_range.hb_max),
                "tverdost_data": tverdost_data  # Список для цикла в Word
            })
            self._completed_steps.add("hardness")

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.show_message("Ошибка ввода", str(e), QMessageBox.Icon.Warning)

    def prochnost(self):
        if not self._check_prerequisite("strength"):
            return
        try:
            # Получаем данные из полей
            pred_tek_min = parse_ru(self.pred_tek_min.toPlainText())
            vrem_sopr_min = parse_ru(self.vrem_sopr_min.toPlainText())
            p_rab_MPa = parse_ru(self.p_rab_MPa.toPlainText())
            p_gidro = parse_ru(self.p_gidro.toPlainText())
            d_vnutr = parse_ru(self.d_vnutr.toPlainText())
            s_isp = parse_ru(self.s_isp.toPlainText())
            p_pnevma = parse_ru(self.p_pnevma.toPlainText())
            p_rab = parse_ru(self.p_rab.toPlainText())

            # Расчёт на прочность по ГОСТ 34233.1
            result = calculate_strength(
                pred_tek_min, vrem_sopr_min, p_rab_MPa, p_gidro,
                d_vnutr, s_isp, p_pnevma, p_rab,
            )

            # Давление для этапов пневматического испытания.
            self.data.update({"p_rab_025": f"{result.p_rab_025}"})
            self.data.update({"p_rab_05": f"{result.p_rab_05}"})
            self.data.update({"p_rab_075": f"{result.p_rab_075}"})

            # Вывод в QPlainTextEdit
            self.sigma.setPlainText(format_ru(result.sigma))
            self.sigma_gidro.setPlainText(format_ru(result.sigma_gidro))
            self.s_rasch.setPlainText(format_ru(result.s_rasch))
            self.s_rasch_gidro.setPlainText(format_ru(result.s_rasch_gidro))
            self.s_max_rasch.setPlainText(format_ru(result.s_max_rasch))
            self.p_pnevma_kgs.setPlainText(format_ru(result.p_pnevma_kgs))
            self.p_dop.setPlainText(format_ru(result.p_dop))
            self._completed_steps.add("strength")

        except ValueError as e:
            print(f"Ошибка ввода: {e}")
            self.sigma.setPlainText("Ошибка")
            self.sigma_gidro.setPlainText("Ошибка")
            self.s_max_rasch.setPlainText("Ошибка")

    def ost_res(self):
        if not self._check_prerequisite("residual_life"):
            return
        try:
            # Получаем данные из полей с проверкой на пустые значения
            s_isp = parse_ru(self.s_isp.toPlainText()) if self.s_isp.toPlainText() else 0.0
            c0_plus_dop = parse_ru(self.c0_plus_dop.toPlainText()) if self.c0_plus_dop.toPlainText() else 0.0
            s_min_total = parse_ru(self.s_min_total.toPlainText()) if self.s_min_total.toPlainText() else 0.0
            years_of_operation = parse_ru(self.yearsOfExpluatation.toPlainText()) \
                if self.yearsOfExpluatation.toPlainText() else 0.0

            # Получаем s_max_rasch (если это QPlainTextEdit)
            s_max_rasch = parse_ru(self.s_max_rasch.toPlainText()) if hasattr(self,
                                                                               's_max_rasch') and self.s_max_rasch.toPlainText() else 0.0

            # Расчёт скорости коррозии и остаточного ресурса
            # (raises ValueError, если срок эксплуатации равен нулю)
            result = calculate_residual_life(s_isp, c0_plus_dop, s_min_total, years_of_operation, s_max_rasch)

            # Вывод результатов
            self.a_corr.setPlainText(format_ru(result.corrosion_rate))
            self.tk_years.setPlainText(format_ru(result.remaining_years))
            self.tk_just.setPlainText(result.comment)
            self._completed_steps.add("residual_life")

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.a_corr.setPlainText("Ошибка")
            self.tk_years.setPlainText("Ошибка")

    # --- Методы для трубопровода (ГОСТ 32388-2013) ---

    def _install_segment_type_combo(self, table, row, current_text=SEGMENT_TYPES[0]):
        """Устанавливает выпадающий список типа элемента в ячейку (row, 1)
        таблицы участков трассы -- вместо свободного ввода текста."""
        combo = QComboBox()
        combo.addItems(SEGMENT_TYPES)
        if current_text not in SEGMENT_TYPES:
            combo.addItem(current_text)
        combo.setCurrentText(current_text)
        table.setCellWidget(row, 1, combo)

    def _install_ae_class_combo(self, table, row, current_text=AE_CLASS_TYPES[0]):
        """Устанавливает выпадающий список "Класс источника" в ячейку
        (row, 2) table_pnevmo_ae (Приложение 8, Таблица 1) -- тот же приём,
        что и _install_segment_type_combo(), фиксированный список
        AE_CLASS_TYPES."""
        combo = QComboBox()
        combo.addItems(AE_CLASS_TYPES)
        if current_text not in AE_CLASS_TYPES:
            combo.addItem(current_text)
        combo.setCurrentText(current_text)
        table.setCellWidget(row, 2, combo)

    def _install_uzk_segment_combo(self, table, row, current_text=None):
        """Устанавливает выпадающий список "Участок" (номер участка на
        схеме) в ячейку (row, 1) table_uzk (Приложение 5) -- вместо
        свободного ввода текста, только номера от 1 до segments_count
        (Приложение 4, "Количество участков") включительно, тот же приём,
        что и _install_segment_type_combo(). При смене выбора синхронизирует
        колонку "Типоразмер" той же строки (см. _on_uzk_segment_changed)."""
        options = [str(n) for n in range(1, self.segments_count.value() + 1)]
        combo = QComboBox()
        combo.addItems(options)
        if current_text and current_text not in options:
            combo.addItem(current_text)
        if current_text:
            combo.setCurrentText(current_text)
        combo.currentTextChanged.connect(lambda _=None, c=combo: self._on_uzk_segment_changed(c))
        table.setCellWidget(row, 1, combo)

    def _uzk_typorazmer_for_segment(self, segment_number_text):
        """Значение "Типоразмер" из table_segments (Приложение 4, "Участки
        трассы (ввод)") для строки с номером участка segment_number_text --
        поиск по значению колонки "№" (не по индексу строки, строки могли
        быть пересозданы через fill_segments_table())."""
        table = self.table_segments
        for row in range(table.rowCount()):
            number_item = table.item(row, 0)
            if number_item is not None and number_item.text().strip() == segment_number_text:
                size_item = table.item(row, 2)
                return size_item.text() if size_item else ""
        return ""

    def _sync_uzk_row_size(self, table, row):
        """Проставляет в (row, 2) table_uzk "Типоразмер" выбранного в (row,
        1) участка -- то же значение, что в одноимённой колонке
        table_segments для этого номера участка."""
        combo = table.cellWidget(row, 1)
        segment_number = combo.currentText() if combo else ""
        table.setItem(row, 2, QTableWidgetItem(self._uzk_typorazmer_for_segment(segment_number)))

    def _on_uzk_segment_changed(self, combo):
        """Реакция на смену номера участка в table_uzk -- находит строку
        комбобокса по факту (не по захваченному при подключении сигнала
        индексу: он "протухает" при удалении строк выше) и пересинхронизирует
        "Типоразмер" этой строки."""
        table = self.table_uzk
        for row in range(table.rowCount()):
            if table.cellWidget(row, 1) is combo:
                self._sync_uzk_row_size(table, row)
                return

    def _renumber_uzk_rows(self):
        """Колонка "№" table_uzk -- сквозная нумерация по позиции строки,
        та же логика, что и в fill_segments_table() (Приложение 4)."""
        table = self.table_uzk
        for row in range(table.rowCount()):
            table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

    def _add_uzk_row(self):
        """Добавляет одну пустую строку в table_uzk (Приложение 5) с
        выпадающим списком номера участка в колонке 1, авто-номером в
        колонке 0 и подставленным "Типоразмер" в колонке 2."""
        table = self.table_uzk
        row = table.rowCount()
        table.insertRow(row)
        self._install_uzk_segment_combo(table, row)
        self._renumber_uzk_rows()
        self._sync_uzk_row_size(table, row)

    def _remove_uzk_row(self):
        """Удаляет выбранную строку table_uzk и перенумеровывает колонку
        "№" оставшихся строк (см. _renumber_uzk_rows)."""
        self._remove_table_row(self.table_uzk)
        self._renumber_uzk_rows()

    def _add_pnevmo_ae_row(self):
        """Добавляет одну пустую строку в table_pnevmo_ae (Приложение 8,
        Таблица 1) с выпадающим списком "Класс источника" в колонке 2 --
        для точечной правки поверх _fill_pnevmo_ae_table()."""
        table = self.table_pnevmo_ae
        row = table.rowCount()
        table.insertRow(row)
        self._install_ae_class_combo(table, row)

    def _fill_pnevmo_ae_table(self):
        """Заполняет table_pnevmo_ae (Приложение 8, Таблица 1) по числу
        датчиков (pnevmo_sensors_count, п.7): группами по 5 строк на
        каждый ПАЭ со стандартными ступенями нагрузки. Полностью
        перезаписывает таблицу -- как fill_segments_table(), кнопка не
        добавляет, а пересобирает. Дальше строки редактируются вручную
        (класс источника, нагрузка) или добавляются/удаляются по одной."""
        stages = ["0,3 Рразр", "0,6 Рразр", "Рразр", "Рисп.", "Рразр"]
        table = self.table_pnevmo_ae
        table.setRowCount(0)
        for paje_num in range(1, self.pnevmo_sensors_count.value() + 1):
            for stage in stages:
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(str(paje_num)))
                table.setItem(row, 1, QTableWidgetItem(stage))
                self._install_ae_class_combo(table, row)

    def _update_pnevmo_mirrors(self):
        """Зеркалит в read-only поля Приложения 8 (пункт 3) значения,
        введённые оператором ранее в других местах формы -- обязательное
        требование задачи "заполняются автоматически в read-only". Сами
        поля-зеркала (pnevmo_*_display) не входят в widget_names_pipeline.py
        и в шаблон .docx не попадают -- шаблон использует исходные ключи
        (obj_naznach, reg_number и т.п.), см. _update_calc_temp_display().
        pnevmo_obj_naznach/ae_zakl_obj_control сюда не входят -- они теперь
        самостоятельные редактируемые поля, см.
        _update_pnevmo_obj_naznach_display()/_update_ae_zakl_obj_control_display().
        ae_zakl_date_display и ae_zakl_report_date_display тоже сюда не
        входят -- обновляются сразу по dateChanged (pnevmo_date и
        report_date соответственно), см. _update_ae_zakl_date_display()/
        _update_ae_zakl_report_date_display() (раньше ждали переключения
        вкладки, из-за чего показывали старую дату)."""
        self.pnevmo_reg_number_display.setPlainText(self.reg_number.toPlainText())
        self.pnevmo_year_start_display.setPlainText(self.year_start.toPlainText())
        self.pnevmo_p_rab_display.setPlainText(self.p_rab_kgs.toPlainText())
        self.pnevmo_work_medium_display.setPlainText(self.work_medium.currentText())
        self.pnevmo_steel_grade_display.setPlainText(self._first_pipe_material_value(4))
        self.pnevmo_pipe_size_display.setPlainText(self._first_pipe_material_value(3))

        # Приложение 9 -- те же исходные значения, тот же приём зеркал.
        self.ae_zakl_reg_number_display.setPlainText(self.reg_number.toPlainText())
        self.ae_zakl_location_display.setPlainText(self.obj_location.toPlainText())

    def _update_ae_zakl_date_display(self):
        """Зеркалит pnevmo_date (Приложение 8, "Дата проведения") в
        read-only ae_zakl_date_display (Приложение 9, "Дата проведения
        контроля") сразу при изменении даты -- раньше обновлялось только
        при переключении вкладки (_update_pnevmo_mirrors()), из-за чего
        после правки даты в Приложении 8 тут держалась старая дата (по
        умолчанию 01.01.2000) до следующего переключения вкладки."""
        self.ae_zakl_date_display.setPlainText(self.pnevmo_date.date().toString("dd.MM.yyyy"))

    def _update_ae_zakl_report_date_display(self):
        """Зеркалит report_date (титульный лист, "Дата отчёта") в
        read-only ae_zakl_report_date_display (Приложение 9, "Дата
        отчёта (к «УТВЕРЖДАЮ»)") сразу при изменении даты -- тот же
        баг и тот же приём, что и в _update_ae_zakl_date_display(): без
        прямой подписки на dateChanged поле держало дату по умолчанию
        (01.01.2000) до переключения вкладки, из-за чего дата отчёта в
        Приложении 9 расходилась с титульным листом, хотя оба места
        рендерятся из одного и того же report_date в шаблоне .docx."""
        self.ae_zakl_report_date_display.setPlainText(self.report_date.date().toString("dd.MM.yyyy"))

    def _update_pnevmo_obj_naznach_display(self):
        """Подсказка pnevmo_obj_naznach (Приложение 8, п.3 "Трубопровод
        (наименование)") значением obj_naznach (раздел 2) -- поле
        редактируемое, см. _sync_mirror_field()."""
        self._sync_mirror_field(
            self.pnevmo_obj_naznach, self.obj_naznach.toPlainText(),
            "_pnevmo_obj_naznach_auto_value",
        )

    def _update_ae_zakl_obj_control_display(self):
        """Подсказка ae_zakl_obj_control (Приложение 9, "Объект контроля")
        значением pnevmo_obj_naznach (Приложение 8, "Трубопровод
        (наименование)") -- общий по смыслу плейсхолдер для обоих полей, см.
        _sync_mirror_field()."""
        self._sync_mirror_field(
            self.ae_zakl_obj_control, self.pnevmo_obj_naznach.toPlainText(),
            "_ae_zakl_obj_control_auto_value",
        )

    def _first_pipe_material_value(self, col):
        """Значение колонки col первой строки table_pipe_materials (Таблица
        6 -- Сведения о трубах) или "" если таблица пуста. Типоразмер и
        марка стали больше не отдельные поля формы -- вводятся один раз в
        Таблице 6, остальные места документа (участки трассы, расчёт на
        прочность) берут значение оттуда, из первого (представительного)
        элемента."""
        table = self.table_pipe_materials
        if table.rowCount() == 0:
            return ""
        item = table.item(0, col)
        if item is not None:
            return item.text().strip()
        cell_widget = table.cellWidget(0, col)
        # NB: "if cell_widget" была бы неверна -- пустой QComboBox (без
        # добавленных пунктов, только с введённым текстом) в Python ложный
        # (__len__() == 0), хотя currentText() при этом валиден.
        if isinstance(cell_widget, QComboBox):
            return cell_widget.currentText().strip()
        return ""

    def fill_segments_table(self):
        """Заполнение таблицы участков трассы. STEP_ORDER: 'segments'.

        Идемпотентно: повторное нажатие (например, чтобы заново отметить
        шаг выполненным после открытия сохранённого проекта -- см.
        FileHandler) не затирает уже введённые тип элемента и типоразмер
        существующих строк значениями по умолчанию, только достраивает
        новые строки при увеличении segments_count."""
        count = self.segments_count.value()
        default_size = self._first_pipe_material_value(3) or "-"
        table = self.table_segments
        existing_rows = table.rowCount()
        table.setRowCount(count)
        for row in range(count):
            table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            if row < existing_rows:
                type_combo = table.cellWidget(row, 1)
                current_type = type_combo.currentText() if type_combo else SEGMENT_TYPES[0]
                size_item = table.item(row, 2)
                current_size = size_item.text() if size_item and size_item.text() else default_size
            else:
                current_type = SEGMENT_TYPES[0]
                current_size = default_size
            self._install_segment_type_combo(table, row, current_type)
            table.setItem(row, 2, QTableWidgetItem(current_size))
        self._completed_steps.add("segments")
        self._update_toc_progress()

    def _read_segments(self):
        """Читает участки трассы из table_segments в список SegmentSpec."""
        table = self.table_segments
        segments = []
        for row in range(table.rowCount()):
            number_item = table.item(row, 0)
            size_item = table.item(row, 2)
            if number_item is None or not number_item.text():
                continue
            type_combo = table.cellWidget(row, 1)
            element_type = type_combo.currentText() if type_combo else SEGMENT_TYPES[0]
            segments.append(SegmentSpec(
                number=int(number_item.text()),
                element_type=element_type,
                size=size_item.text() if size_item and size_item.text() else "",
            ))
        return segments

    def calc_pipeline_thickness(self):
        """Синтетическая генерация замеров толщины по участкам. STEP_ORDER: 'thickness'."""
        if not self._check_prerequisite("thickness"):
            return
        try:
            s_min = parse_ru(self.thick_seed_min.toPlainText())
            segments = self._read_segments()
            if not segments:
                raise ValueError("Сначала заполните участки трассы")

            measurements = generate_pipeline_thickness_measurements(segments, s_min)

            table = self.table_thick_pipeline
            table.setRowCount(len(measurements))
            for row, m in enumerate(measurements):
                table.setItem(row, 0, QTableWidgetItem(str(m.number)))
                table.setItem(row, 1, QTableWidgetItem(m.element_type))
                table.setItem(row, 2, QTableWidgetItem(m.size))
                table.setItem(row, 3, QTableWidgetItem(format_ru_fixed(m.thickness, 2)))

            self.data.update({"segments": [
                {
                    "number": m.number, "element_type": m.element_type,
                    "size": m.size, "thickness": format_ru_fixed(m.thickness, 2),
                }
                for m in measurements
            ]})

            # Фактическая минимальная толщина -- минимум из сгенерированных
            # замеров, автоматически подставляется как вход для расчёта на
            # прочность (calc_sf), как Sф в контрольном примере из отчёта.
            s_fact_min = min(m.thickness for m in measurements)
            self.calc_sf.setPlainText(format_ru_fixed(s_fact_min, 2))

            self._completed_steps.add("thickness")
            self._update_toc_progress()

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.show_message("Ошибка ввода", str(e), QMessageBox.Icon.Warning)

    def calc_pipeline_strength_ui(self):
        """Расчёт на прочность по ГОСТ 32388-2013. STEP_ORDER: 'strength'."""
        if not self._check_prerequisite("strength"):
            return
        try:
            p_working = parse_ru(self.p_rab_mpa.toPlainText())
            d_outer = parse_ru(self.calc_da.toPlainText())
            temp = parse_ru(self.calc_temp.toPlainText())
            phi = parse_ru(self.calc_phi.toPlainText())
            c2 = parse_ru(self.calc_c2.toPlainText())
            s_actual = parse_ru(self.calc_sf.toPlainText())
            steel_grade = self._first_pipe_material_value(4)
            if not steel_grade:
                raise ValueError(
                    "Сначала заполните марку стали в Таблице 6 (Сведения о трубах)"
                )
            self.calc_steel_grade.setPlainText(steel_grade)

            try:
                allowable_stress = get_allowable_stress(steel_grade, temp)
                self.calc_sigma_allow.setPlainText(format_ru(allowable_stress))
            except (KeyError, ValueError) as e:
                manual_value = self.calc_sigma_allow.toPlainText().strip()
                if not manual_value:
                    raise ValueError(
                        f"{e} Введите [σ] вручную в поле «Допускаемое "
                        "напряжение [σ], МПа»."
                    )
                allowable_stress = parse_ru(manual_value)

            result = calculate_pipeline_strength(
                p_working=p_working, d_outer=d_outer, allowable_stress=allowable_stress,
                s_actual=s_actual, c2=c2, phi=phi,
            )

            self.calc_sr.setPlainText(format_ru(result.s_calc))
            self.calc_s_reject.setPlainText(format_ru(result.s_reject))
            self.calc_p_allow.setPlainText(format_ru(result.p_allow))
            self.calc_strength_conclusion.setPlainText(
                "Условие прочности выполняется" if result.strength_ok
                else "Условие прочности не выполняется"
            )
            self._completed_steps.add("strength")
            self._update_toc_progress()

        except (ValueError, KeyError) as e:
            print(f"Ошибка ввода данных: {e}")
            self.show_message("Ошибка ввода", str(e), QMessageBox.Icon.Warning)

    def calc_pipeline_residual_life_ui(self):
        """Остаточный ресурс по скорости коррозии. STEP_ORDER: 'residual_life'."""
        if not self._check_prerequisite("residual_life"):
            return
        try:
            s_nominal = parse_ru(self.calc_sn.toPlainText())
            s_actual = parse_ru(self.calc_sf.toPlainText())
            s_reject = parse_ru(self.calc_s_reject.toPlainText())
            years = parse_ru(self.calc_years_operation.toPlainText())
            k = parse_ru(self.calc_k.toPlainText()) if self.calc_k.toPlainText().strip() else 1.0

            # calc_corrosion_rate редактируется вручную: если поле уже
            # заполнено (расчётом или инженером), его текущее значение
            # берётся как есть, а не перезаписывается формулой -- иначе
            # правка терялась бы при каждом повторном нажатии кнопки.
            corrosion_text = self.calc_corrosion_rate.toPlainText().strip()
            corrosion_override = parse_ru(corrosion_text) if corrosion_text else None

            result = calculate_pipeline_residual_life(
                s_nominal=s_nominal, s_actual=s_actual, s_reject=s_reject,
                years_of_operation=years, k=k, corrosion_rate_override=corrosion_override,
            )

            self.calc_corrosion_rate.setPlainText(format_ru(result.corrosion_rate))
            self.calc_remaining_years.setPlainText(format_ru(result.remaining_years))
            # calc_residual_comment -- вывод формулируется инженером текстом
            # вручную (как thick_conclusion/uzk_conclusion), кнопка его не
            # перезаписывает -- иначе правки в UI терялись бы при каждом
            # повторном расчёте.

            # final_years_allowed (раздел 8) -- подсказка расчётным остаточным
            # ресурсом, только если поле ещё пустое: инженер вправе утвердить
            # меньший регламентный срок, повторный расчёт его правку не сотрёт.
            # setPlainText ниже сам вызовет _update_final_deadline_date() через
            # textChanged (см. подключение сигнала в __init__).
            if not self.final_years_allowed.toPlainText().strip():
                self.final_years_allowed.setPlainText(str(int(result.remaining_years)))

            self._completed_steps.add("residual_life")
            self._update_toc_progress()

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.show_message("Ошибка ввода", str(e), QMessageBox.Icon.Warning)

    def _add_table_row(self, table):
        """Добавляет пустую строку в конец таблицы -- рассмотренные
        документы, элементы ВИК. Свободный ввод, не расчётный шаг -- не
        входит в STEP_ORDER. Специалисты используют отдельный
        _add_specialist_row() -- их ячейки не свободный текст, а
        редактируемые выпадающие списки."""
        table.insertRow(table.rowCount())

    def _remove_table_row(self, table):
        """Удаляет выбранную строку таблицы (если строка выбрана). Работает
        одинаково для ячеек-текста и ячеек-виджетов (комбобоксов)."""
        row = table.currentRow()
        if row >= 0:
            table.removeRow(row)

    def _remove_combo_current_item(self, combo):
        """Удаляет из выпадающего списка текущий пункт (толщиномер,
        дефектоскоп, аппаратура АЭ и т.п. -- редактируемые комбобоксы, куда
        новые варианты добавляются вводом текста)."""
        index = combo.currentIndex()
        if index >= 0:
            combo.removeItem(index)
        else:
            combo.clearEditText()

    def _install_growable_combo(self, table, row, col, current_text=""):
        """Устанавливает редактируемый выпадающий список в ячейку (row, col)
        произвольной таблицы -- вместо свободного ввода текста. В отличие от
        _install_segment_type_combo() (фиксированный SEGMENT_TYPES), список
        здесь растёт вводом оператора (как thick_device и т.п.) и изначально
        собирается из уже введённых значений этой же колонки в других
        строках -- чтобы повторно использовать ранее введённые значения
        (ФИО/должности/удостоверения в специалистах, марки стали/ГОСТы в
        трубах и т.п.) через выпадающий список."""
        combo = QComboBox()
        combo.setEditable(True)
        seen = []
        for r in range(table.rowCount()):
            if r == row:
                continue
            existing = table.cellWidget(r, col)
            if isinstance(existing, QComboBox):
                text = existing.currentText()
                if text and text not in seen:
                    seen.append(text)
        combo.addItems(seen)
        if current_text and current_text not in seen:
            combo.addItem(current_text)
        combo.setCurrentText(current_text)
        table.setCellWidget(row, col, combo)

    def _add_specialist_row(self):
        """Добавляет строку в table_specialists -- специалиста выбирают из
        справочника «Сотрудники» (EmployeesTabController), а не вводят
        текстом: так подтвердил пользователь, весь состав специалистов
        отчёта должен идти через справочник (иначе для строки не с кем
        связать клише -- см. _specialist_kleishe_image()). Если нужного
        человека нет в справочнике -- его сначала заводят на вкладке
        «Сотрудники».

        4 ячейки по-прежнему QComboBox (редактируемый, как и раньше --
        _cell_text()/_table_to_dicts() рассчитаны именно на этот тип), но
        предзаполненные из Employee, а не пустые."""
        employees = load_employees()
        if not employees:
            self.show_message(
                "Справочник пуст",
                "Сначала добавьте сотрудников на вкладке «Сотрудники» -- "
                "специалисты отчёта выбираются оттуда.",
                QMessageBox.Icon.Warning,
            )
            return

        labels = [f"{e.position} — {e.full_name}" for e in employees]
        label, ok = QInputDialog.getItem(
            self, "Выбор специалиста", "Сотрудник:", labels, editable=False
        )
        if not ok:
            return
        employee = employees[labels.index(label)]

        cert_full = ""
        cert_short = ""
        if employee.certificates:
            cert_full = employee.certificates[0]
            if len(employee.certificates) > 1:
                cert_full, ok = QInputDialog.getItem(
                    self, "Выбор удостоверения", "Удостоверение:",
                    employee.certificates, editable=False,
                )
                if not ok:
                    cert_full = employee.certificates[0]
            match = re.search(r"№\s*\S+", cert_full)
            cert_short = match.group(0) if match else cert_full

        table = self.table_specialists
        row = table.rowCount()
        table.insertRow(row)
        for col, text in enumerate((employee.position, employee.full_name, cert_full, cert_short)):
            self._install_growable_combo(table, row, col, text)
        self._specialist_employee_ids.append(employee.id)
        self._refresh_program_specialist_combo()

    def _remove_specialist_row(self):
        """Удаляет выбранную строку table_specialists, синхронно убирает её
        employee_id из _specialist_employee_ids (см. _add_specialist_row()) и
        обновляет комбобоксы выбора специалиста (program_specialist и
        т.п.) -- раньше эти комбобоксы обновлялись только при переключении
        вкладки, теперь вкладок нет, обновление дергается прямо из точек,
        где меняется table_specialists, см. _refresh_program_specialist_combo()."""
        row = self.table_specialists.currentRow()
        if row >= 0 and row < len(self._specialist_employee_ids):
            self._specialist_employee_ids.pop(row)
        self._remove_table_row(self.table_specialists)
        self._refresh_program_specialist_combo()

    def _specialist_kleishe_image(self, doc, employees, employee_id, used_paths):
        """InlineImage клише сотрудника для подстановки в form_data (см.
        calculate(), KLEISHE_ROLE_PREFIXES) -- тот же приём, что и
        nk_scheme_image/pnevmo_graph_image: пустая строка, если клише нет
        (сотрудник не выбран, не привязан к справочнику или не загрузил
        клише), без ошибки рендера. Путь к файлу резолвит
        resolve_kleishe_path() (src/services/employees_store.py).

        used_paths -- set, куда добавляется путь картинки, если она
        подставлена -- после doc.render() по нему находим rId вставленных
        картинок для _float_kleishe_drawings_behind_text() (картинка клише
        должна плавать "за текстом", а не как схема НК/график нагружения,
        см. calculate()).

        width/height не заданы намеренно -- InlineImage тогда берёт
        реальный размер картинки (пиксели + DPI из самого файла, см.
        docx.image.image.Image.width/height), а не произвольно
        подогнанный -- раньше здесь стоял фиксированный width=Mm(30),
        из-за чего клише в документе не совпадало по размеру с исходным
        файлом."""
        path = resolve_kleishe_path(employees, employee_id)
        if not path:
            return ""
        used_paths.add(path)
        return InlineImage(doc, str(path))

    def _float_kleishe_drawings_behind_text(self, doc, used_paths):
        """После doc.render() переводит уже вставленные картинки клише из
        обычного инлайн-положения в плавающее "за текстом" (Word:
        Обтекание текстом -> За текстом) -- без изменения размера. Только
        клише -- схема НК/график нагружения (тоже InlineImage) не
        затрагиваются, т.к. их rId в used_paths не попадают.

        rId картинок определяем через get_or_add_image() -- она дедуплицирует
        по содержимому так же, как это уже сделал docxtpl при рендере (см.
        docx.parts.story.StoryPart.get_or_add_image()), поэтому для уже
        вставленной картинки метод просто возвращает тот же rId, без
        побочных эффектов."""
        if not used_paths:
            return
        target_rids = {doc.part.get_or_add_image(str(path))[0] for path in used_paths}
        float_drawings_behind_text(doc.docx, target_rids)

    def _add_pipe_material_row(self):
        """Добавляет строку в table_pipe_materials (Таблица 6 -- Сведения о
        трубах): № проставляется автоматически, колонки "Наименование
        элемента", "Марка стали, ГОСТ или ТУ" и "Трубы, ГОСТ или ТУ" --
        растущие выпадающие списки (см. _install_growable_combo()),
        "Количество" и "Типоразмер" остаются свободным текстом."""
        table = self.table_pipe_materials
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(f"{row + 1}."))
        self._install_growable_combo(table, row, 1)
        self._install_growable_combo(table, row, 4)
        self._install_growable_combo(table, row, 5)

    def _seed_program_table_defaults(self):
        """Предзаполняет table_program (Приложение 1 -- Программа) стандартным
        составом работ из PROGRAM_DEFAULT_ITEMS -- только если таблица ещё
        пустая (не перетирает восстановленный из проекта или уже
        отредактированный оператором список). Дальше строки полностью
        редактируются/удаляются/добавляются через UI, как обычные строки."""
        if self.table_program.rowCount() > 0:
            return
        table = self.table_program
        for level, text in PROGRAM_DEFAULT_ITEMS:
            row = table.rowCount()
            table.insertRow(row)
            number_item = QTableWidgetItem("")
            number_item.setData(Qt.ItemDataRole.UserRole, level)
            table.setItem(row, 0, number_item)
            table.setItem(row, 1, QTableWidgetItem(text))
        self._renumber_program_table()

    def _add_program_item_row(self):
        """Добавляет пункт верхнего уровня в table_program -- № вида "N.",
        см. _renumber_program_table()."""
        self._insert_program_row(level=0)

    def _add_program_subitem_row(self):
        """Добавляет подпункт в table_program -- № вида "N.M." под текущим
        (последним) пунктом верхнего уровня, см. _renumber_program_table()."""
        self._insert_program_row(level=1)

    def _insert_program_row(self, level):
        """Общая часть _add_program_item_row()/_add_program_subitem_row():
        строка всегда добавляется в конец таблицы (как и все остальные
        таблицы в проекте -- ни у одной сейчас нет reorder/insert-в-середину),
        уровень хранится в Qt.ItemDataRole.UserRole на item(row, 0)."""
        table = self.table_program
        row = table.rowCount()
        table.insertRow(row)
        number_item = QTableWidgetItem("")
        number_item.setData(Qt.ItemDataRole.UserRole, level)
        table.setItem(row, 0, number_item)
        table.setItem(row, 1, QTableWidgetItem(""))
        self._renumber_program_table()

    def _remove_program_row(self):
        """Удаляет выбранную строку table_program и пересчитывает номера --
        обычный _remove_table_row() номера не трогает."""
        self._remove_table_row(self.table_program)
        self._renumber_program_table()

    def _renumber_program_table(self):
        """Пересчитывает колонку "№ п/п" в table_program по уровням: level 0
        -> "N.", level 1 -> "N.M." под текущим top-level пунктом. Уровень
        читается из Qt.ItemDataRole.UserRole на item(row, 0); если он не
        выставлен (например, после восстановления проекта из JSON -- Project
        хранит только текст ячеек, см. src/ui/file_handler.py), определяется
        эвристикой по уже отображённому номеру ("1.1." -> подпункт, иначе --
        пункт верхнего уровня), чтобы повторное открытие сохранённого
        проекта не расплющивало уже сохранённую иерархию при следующем
        добавлении строки. Подпункт раньше первого пункта верхнего уровня
        трактуется как пункт верхнего уровня (без "0.1.")."""
        table = self.table_program
        top = 0
        sub = 0
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is None:
                item = QTableWidgetItem("")
                table.setItem(row, 0, item)
            level = item.data(Qt.ItemDataRole.UserRole)
            if level is None:
                level = 1 if item.text().strip(".").count(".") >= 1 else 0
            if level != 0 and top == 0:
                level = 0
            item.setData(Qt.ItemDataRole.UserRole, level)
            if level == 0:
                top += 1
                sub = 0
                item.setText(f"{top}.")
            else:
                sub += 1
                item.setText(f"{top}.{sub}.")

    def _refresh_program_specialist_combo(self, saved_indices=None):
        """Обновляет списки в program_specialist (поле "Программу составил",
        Приложение 1), act2_specialist (поле "Анализ документации провёл",
        Приложение 2), vik_specialist (поле "Контроль провёл", Приложение 3),
        thick_specialist (поле "Измерение провёл", Приложение 4),
        uzk_specialist (поле "Измерение провёл", Приложение 5),
        calc_specialist (поле "Расчёт выполнил", Приложение 6),
        pnevmo_specialist (поле "Контроль выполнил", Приложение 8) и
        ae_zakl_specialist (поле "Заключение составил", Приложение 9).
        Источник вариантов для всех один и тот же: table_specialists (1.3
        Сведения о специалистах, Таблица 2) -- вызывается прямо из точек,
        где меняется эта таблица (_add_specialist_row/_remove_specialist_row),
        плюс после загрузки проекта (см. file_handler.py) -- раньше
        обновление держалось на переключении вкладки "Приложения"/"Расчёты",
        вкладок больше нет. Ни один из комбобоксов не входит ни в один
        список widget_names_pipeline.py (как pnevmo_pressure_hint) -- каждый
        даёт индекс строки специалиста, а не текст для .docx напрямую,
        итоговые плейсхолдеры собирает calculate(). Заодно обновляет
        read-only зеркала пункта 3 Приложения 8, см. _update_pnevmo_mirrors().

        saved_indices -- необязательный dict {имя_комбобокса: индекс},
        восстановленный из report_data при загрузке проекта (см.
        FileHandler.open_project_json()/MainWindow._open_document()).
        Перекрывает обычную логику "сохранить текущий выбор" в
        _refresh_specialist_combo() -- для только что открытого документа
        combo.currentData() всегда None (комбобоксы ещё не заполнены),
        без этого выбор специалиста откатывался на первую строку."""
        saved_indices = saved_indices or {}
        for name in self.SPECIALIST_COMBO_NAMES:
            self._refresh_specialist_combo(getattr(self, name), saved_indices.get(name))
        self._update_pnevmo_mirrors()

    def _refresh_specialist_combo(self, combo, desired=None):
        """Перезаполняет один комбобокс-выбор специалиста вариантами из
        table_specialists, сохраняя выбор (по индексу строки), если он
        всё ещё существует -- общая логика для program_specialist и
        act2_specialist, см. _refresh_program_specialist_combo().

        desired -- индекс строки, который нужно выставить явно (при
        загрузке проекта, когда живого текущего выбора в ещё не
        заполненном комбобоксе нет); по умолчанию берётся
        combo.currentData() -- обычный случай live-редактирования
        таблицы специалистов, когда выбор уже стоит в комбобоксе."""
        previous = desired if desired is not None else combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for row in range(self.table_specialists.rowCount()):
            position = self._cell_text(self.table_specialists, row, 0)
            name = self._cell_text(self.table_specialists, row, 1)
            label = " — ".join(part for part in (position, name) if part) or f"Специалист {row + 1}"
            combo.addItem(label, row)
        if previous is not None:
            index = combo.findData(previous)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _switch_view(self, view):
        """Переключает viewStack между документом и общими справочниками
        (Сотрудники/Приборы/Документы)."""
        page = {
            "document": self.tab_document,
            "employees": self.tab_employees,
            "instruments": self.tab_instruments,
            "orgdocs": self.tab_orgdocs,
        }[view]
        self.viewStack.setCurrentWidget(page)
        self._current_view = view
        self._update_report_buttons_visibility()

    def _reset_form(self):
        """Очищает форму под новый/другой документ -- обратная операция к
        get_form_data()/_fill_ui_from_project(), проходит по тем же
        спискам виджетов (widget_names_pipeline.py и т.п.), только очищая
        вместо чтения. Раньше такой возможности не было вообще -- "начать
        заново" означало перезапустить приложение; нужна для переключения
        между документами дерева объектов без перезапуска.

        Комбобоксы намеренно НЕ .clear() -- это стёрло бы предзаполненные
        варианты (у work_medium это единственный источник выбора: азот/
        воздух/кислород/гелий/аргон, не растится вводом). setCurrentIndex(0)
        воспроизводит тот же вид, что при самом первом запуске окна (ни у
        одного из комбобоксов currentIndex в .ui не выставлен явно, Qt по
        умолчанию показывает первый пункт).

        _current_document_path обнуляется ДО очистки виджетов, а не после
        -- сама очистка (setPlainText(""), setCurrentIndex(0) и т.п.)
        дёргает те же сигналы, что и правки оператора, и без этого
        _mark_dirty() успел бы ложно пометить грязным только что
        сохранённый документ, который мы покидаем (см. Фаза 5.4)."""
        self._current_document_path = None
        for name in self.PLAIN_TEXT_EDIT_NAMES:
            getattr(self, name).setPlainText("")
        for name in self.COMBO_BOX_NAMES:
            getattr(self, name).setCurrentIndex(0)
        for name in self.DATE_EDIT_NAMES:
            getattr(self, name).setDate(QDate.currentDate())
        for name in self.SPIN_BOX_NAMES:
            widget = getattr(self, name)
            widget.setValue(widget.minimum())
        for name in self.TABLE_WIDGET:
            getattr(self, name).setRowCount(0)

        self.data = {}
        self._completed_steps = set()

        if self.equipment_type.id == "pipeline":
            self._seed_program_table_defaults()
            self._specialist_employee_ids = []
            self._current_toc_items = []
            self._current_toc_active_item = None
            self._update_breadcrumb()

    def _refresh_objects_tree(self):
        """Перестраивает objectsTree с нуля из файловой системы (см.
        src/services/workspace.py) -- объекты как раскрывающиеся строки
        верхнего уровня, документы внутри как дочерние, путь к файлу
        документа лежит в Qt.ItemDataRole.UserRole. Вызывается при
        старте и сразу после создания объекта/документа -- построение
        дешёвое (десятки папок/файлов, не тысячи), отдельный кэш не
        заводится."""
        self.objectsTree.clear()
        for object_name in workspace.list_objects():
            object_item = QTreeWidgetItem([object_name])
            self.objectsTree.addTopLevelItem(object_item)
            object_dir = workspace.OUTPUT_DIR / object_name
            for path, label in workspace.list_documents(object_dir, self.equipment_type.id):
                doc_item = QTreeWidgetItem([label])
                doc_item.setData(0, Qt.ItemDataRole.UserRole, path)
                object_item.addChild(doc_item)
            object_item.setExpanded(True)

        # objectsTree.clear() выше уничтожает и дочерние строки
        # оглавления под строкой текущего документа (см.
        # _populate_document_toc()), а _current_toc_items/
        # _current_toc_active_item эти QTreeWidgetItem не сбрасывает --
        # без восстановления это висячие ссылки на удалённые C++
        # объекты (падение "wrapped C/C++ object of type QTreeWidgetItem
        # has been deleted" при следующем _update_breadcrumb()/
        # _on_document_scrolled()). Отстраиваем TOC текущего документа
        # заново, если он есть в новом дереве.
        if self._current_document_path is not None:
            doc_item = self._find_document_tree_item(self._current_document_path)
            if doc_item is not None:
                self._populate_document_toc(doc_item)

    def _filter_objects_tree(self, text):
        """Фильтр по вводу в sidebarSearchBox. Документ виден, если текст
        совпал с ним самим ИЛИ с именем его объекта-папки (иначе поиск по
        имени объекта прятал бы все документы внутри). Пустая строка --
        показывает всё."""
        text = text.strip().lower()
        for i in range(self.objectsTree.topLevelItemCount()):
            object_item = self.objectsTree.topLevelItem(i)
            object_match = text in object_item.text(0).lower()
            any_child_match = False
            for j in range(object_item.childCount()):
                doc_item = object_item.child(j)
                doc_match = text in doc_item.text(0).lower()
                doc_item.setHidden(bool(text) and not object_match and not doc_match)
                any_child_match = any_child_match or doc_match
            object_item.setHidden(bool(text) and not object_match and not any_child_match)

    def _toggle_sidebar(self):
        """Сворачивает/разворачивает сайдбар (Фаза 7, как в референсе) --
        весь sidebar прячется целиком, вместо него показывается узкая
        полоса revealStrip (22px) с одной кнопкой разворота. Оба виджета
        -- постоянные дети mainSplitter (Фаза 4.3), переключается только
        видимость -- QSplitter сам схлопывает скрытого ребёнка до 0 при
        пересчёте раскладки, отдельно двигать min/maxWidth не нужно.
        childrenCollapsible=false защищает только от случайного
        схлопывания перетаскиванием мышью, программному setVisible() не
        мешает."""
        self._sidebar_collapsed = not self._sidebar_collapsed
        self.sidebar.setVisible(not self._sidebar_collapsed)
        self.revealStrip.setVisible(self._sidebar_collapsed)
        if self._sidebar_collapsed:
            self._sidebar_expanded_sizes = self.mainSplitter.sizes()
        else:
            self.mainSplitter.setSizes(self._sidebar_expanded_sizes)
            self._switch_view(self._current_view)

    def _on_objects_tree_item_clicked(self, item, column):
        """Клик по строке objectsTree -- три вида строк, различаются
        глубиной вложенности. Объект (папка, верхний уровень,
        item.parent() is None) -- ничего не делаем, QTreeWidget сам
        разворачивает/сворачивает. Документ (2-й уровень, UserRole --
        путь к файлу) -- открываем его, см. _open_document(). Раздел
        оглавления (3-й уровень, дочерний у документа, UserRole -- сам
        groupbox, см. Фаза 6) -- скроллим к разделу, см.
        _scroll_to_toc_item()."""
        parent = item.parent()
        if parent is None:
            return
        if parent.parent() is None:
            path = item.data(0, Qt.ItemDataRole.UserRole)
            self._open_document(path)
        else:
            self._scroll_to_toc_item(item)

    def _show_objects_tree_context_menu(self, pos):
        """ПКМ по objectsTree (Фаза 8) -- вид меню зависит от глубины
        строки под курсором, как и в _on_objects_tree_item_clicked():
        объект -> _show_folder_context_menu(), документ ->
        _show_document_context_menu(), раздел TOC -- меню нет, там
        нечем управлять."""
        item = self.objectsTree.itemAt(pos)
        if item is None:
            return
        parent = item.parent()
        if parent is None:
            self._show_folder_context_menu(item, pos)
        elif parent.parent() is None:
            self._show_document_context_menu(item, pos)

    def _show_document_context_menu(self, item, pos):
        """ПКМ по строке документа. «Переименовать» из референсного
        мокапа (docs/design/pipeline_sidebar_mockup.html) отдельным
        пунктом меню не реализовано -- ярлык документа это имя файла
        (path.stem, см. workspace.list_documents()), а переименование
        уже доступно через «Сохранить проект»: диалог всегда просит имя
        файла (FileHandler._prompt_document_path()), и при вводе
        другого имени старый файл удаляется, а не остаётся сиротой
        (см. FileHandler.save_project_json())."""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction("Дублировать", lambda: self._duplicate_document(path))
        menu.addAction("Показать в Finder", lambda: self._reveal_in_finder(path))
        menu.addSeparator()
        menu.addAction("Удалить", lambda: self._delete_document(path))
        menu.exec(self.objectsTree.mapToGlobal(pos))

    def _show_folder_context_menu(self, item, pos):
        """ПКМ по строке объекта (папки)."""
        object_dir = workspace.OUTPUT_DIR / item.text(0)
        menu = QMenu(self)
        menu.addAction("Создать документ здесь", lambda: self._create_document_in_object(object_dir.name))
        menu.addSeparator()
        menu.addAction("Переименовать объект", lambda: self._rename_object_dialog(object_dir))
        menu.addAction("Показать в Finder", lambda: self._reveal_in_finder(object_dir))
        menu.addSeparator()
        menu.addAction("Удалить объект", lambda: self._delete_object_dialog(object_dir))
        menu.exec(self.objectsTree.mapToGlobal(pos))

    def _reveal_in_finder(self, path):
        """Открывает Finder с выделенным файлом/папкой -- macOS-
        специфично (`open -R`), как и сам пункт меню в референсе
        ("Показать в Finder"): приложение не претендует на
        кроссплатформенность."""
        subprocess.run(["open", "-R", str(path)])

    def _duplicate_document(self, path):
        """«Дублировать» -- копирует .json документа в той же папке
        под новым именем (см. workspace.duplicate_document())."""
        workspace.duplicate_document(path)
        self._refresh_objects_tree()

    def _delete_document(self, path):
        """«Удалить» документ -- необратимо, с подтверждением. Если
        удаляется текущий открытый документ, форма сбрасывается
        (как при старте, документов больше нет для показа)."""
        reply = QMessageBox.question(
            self, "Удалить документ",
            f"Удалить документ «{path.stem}»? Это необратимо.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if path == self._current_document_path:
            self._reset_form()
            self._switch_view("document")
        path.unlink(missing_ok=True)
        self._refresh_objects_tree()
        self._update_breadcrumb()

    def _create_document_in_object(self, object_name):
        """«Создать документ здесь» из меню папки -- то же самое, что
        обычное «Создать документ», но без диалога выбора объекта: он
        уже известен из того, по какой строке кликнули ПКМ."""
        object_dir = workspace.create_object(object_name)
        doc_path = workspace.create_document(object_dir, self.equipment_type.id)
        self._refresh_objects_tree()
        self._open_document(doc_path)

    def _rename_object_dialog(self, object_dir):
        """«Переименовать объект» -- в отличие от документа, у объекта
        реальное имя ровно совпадает с именем папки на диске, так что
        переименование осмысленно и видно в дереве сразу."""
        new_name, ok = QInputDialog.getText(
            self, "Переименовать объект", "Новое название:", text=object_dir.name,
        )
        if not ok or not new_name.strip():
            return
        new_dir = workspace.rename_object(object_dir, new_name)
        if self._current_document_path is not None and self._current_document_path.parent == object_dir:
            self._current_document_path = new_dir / self._current_document_path.name
        self._refresh_objects_tree()
        self._update_breadcrumb()

    def _delete_object_dialog(self, object_dir):
        """«Удалить объект» -- необратимо, удаляет папку целиком со
        всеми документами внутри, число которых показывается в
        подтверждении, чтобы не удалить что-то по ошибке."""
        doc_count = len(list(object_dir.glob("*.json")))
        reply = QMessageBox.question(
            self, "Удалить объект",
            f"Удалить объект «{object_dir.name}» и все документы внутри ({doc_count})? Это необратимо.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self._current_document_path is not None and self._current_document_path.parent == object_dir:
            self._reset_form()
            self._switch_view("document")
        workspace.delete_object(object_dir)
        self._refresh_objects_tree()
        self._update_breadcrumb()

    def _open_document(self, path):
        """Открывает документ дерева. Если это уже открытый документ --
        просто переключает вид, не трогая форму (иначе несохранённые
        правки терялись бы). Иначе: тихо сохраняет текущий документ (если
        он был), сбрасывает форму и наполняет данными выбранного —
        порядок как в _reset_form()/_fill_ui_from_project(), см. план
        Фазы 2."""
        if path == self._current_document_path:
            self._switch_view("document")
            return

        if self._current_document_path is not None:
            try:
                self.file_handler._save_current_project()
            except Exception as e:
                print(f"Не удалось автосохранить текущий документ: {e}")
            # Оглавление уходящего документа -- дочерние строки под его
            # строкой в дереве -- снимается: статус разделов считается
            # по живым виджетам формы, а они сейчас переиспользуются под
            # другой документ (см. _reset_form()).
            old_item = self._find_document_tree_item(self._current_document_path)
            if old_item is not None:
                old_item.takeChildren()

        self._reset_form()
        project = Project.load_from_file(path)
        self.file_handler._fill_ui_from_project(project)
        self._current_document_path = path
        self._document_dirty = False
        self._update_dirty_indicator()
        saved_indices = {
            name: project.report_data.get(name) for name in self.SPECIALIST_COMBO_NAMES
        }
        self._refresh_program_specialist_combo(saved_indices)
        self._switch_view("document")
        doc_item = self._find_document_tree_item(path)
        if doc_item is not None:
            self._populate_document_toc(doc_item)
        self._update_breadcrumb()

    def _find_document_tree_item(self, path):
        """Ищет строку objectsTree, чей UserRole -- искомый путь к
        файлу. Дерево небольшое (десятки строк), полный обход на каждый
        вызов дешевле, чем держать отдельный кэш path->item в
        синхронизации с _refresh_objects_tree()."""
        for i in range(self.objectsTree.topLevelItemCount()):
            object_item = self.objectsTree.topLevelItem(i)
            for j in range(object_item.childCount()):
                doc_item = object_item.child(j)
                if doc_item.data(0, Qt.ItemDataRole.UserRole) == path:
                    return doc_item
        return None

    def _update_breadcrumb(self):
        """Обновляет breadcrumbLabel над лентой документа: объект /
        документ / текущий раздел оглавления. Ярлык документа берётся
        готовым из строки дерева (там уже имя файла из
        workspace.list_documents()), а не пересчитывается заново.

        Объект и документ -- кликабельные ссылки (Фаза 11, как revealFolder()/
        revealDoc() в референсе, docs/design/pipeline_sidebar_mockup.html)
        через встроенную поддержку rich-text гиперссылок в QLabel
        (setOpenExternalLinks(False) + сигнал linkActivated, см.
        _on_breadcrumb_link_activated()) -- три отдельных виджета под
        три сегмента заводить не пришлось. Раздел -- не ссылка, как и в
        референсе (там у него нет своего reveal-обработчика)."""
        if self._current_document_path is None:
            self.breadcrumbLabel.setText("")
            self.breadcrumbLabel.setVisible(False)
            return
        object_name = Path(self._current_document_path).parent.name
        doc_item = self._find_document_tree_item(self._current_document_path)
        doc_label = doc_item.text(0) if doc_item is not None else ""
        section = self._current_toc_active_item.text(0) if self._current_toc_active_item is not None else ""
        parts = []
        if object_name:
            parts.append(f'<a href="object" style="color:inherit; text-decoration:none;">{html.escape(object_name)}</a>')
        if doc_label:
            parts.append(f'<a href="document" style="color:inherit; text-decoration:none;">{html.escape(doc_label)}</a>')
        if section:
            parts.append(html.escape(section))
        self.breadcrumbLabel.setText(" / ".join(parts))
        self.breadcrumbLabel.setVisible(True)

    def _on_breadcrumb_link_activated(self, href):
        """Клик по сегменту breadcrumb -- разворачивает сайдбар (если
        свёрнут), раскрывает нужную строку дерева и на мгновение
        подсвечивает её (см. revealFolder()/revealDoc() в референсе)."""
        if self._sidebar_collapsed:
            self._toggle_sidebar()
        if href == "document":
            item = self._find_document_tree_item(self._current_document_path)
        else:
            object_name = Path(self._current_document_path).parent.name
            item = None
            for i in range(self.objectsTree.topLevelItemCount()):
                top_item = self.objectsTree.topLevelItem(i)
                if top_item.text(0) == object_name:
                    item = top_item
                    break
        if item is None:
            return
        if item.parent() is not None:
            item.parent().setExpanded(True)
        item.setExpanded(True)
        self.objectsTree.scrollToItem(item)
        self._flash_tree_item(item)

    def _flash_tree_item(self, item):
        """Кратковременная подсветка строки дерева (700ms, как
        folder-flash/doc-flash в референсе) -- в отличие от
        _set_toc_active_item(), это одноразовая вспышка (взгляду
        помочь найти строку после клика по breadcrumb), а не постоянная
        подсветка "текущий раздел"."""
        flash_color = QColor("#0a84ff")
        flash_color.setAlpha(38)
        item.setBackground(0, flash_color)
        QTimer.singleShot(700, lambda: item.setData(0, Qt.ItemDataRole.BackgroundRole, None))

    def _make_dot_icon(self, color):
        """Рисует маленький закрашенный кружок как QIcon -- в проекте нет
        инфраструктуры иконок-ресурсов (.qrc), проще нарисовать пиксмап
        на лету (см. также _make_check_icon()/_make_circle_icon()/
        _make_lock_icon() -- тот же приём для иконок TOC, Фаза 6)."""
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 8, 8)
        painter.end()
        return QIcon(pixmap)

    def _connect_dirty_tracking(self):
        """Подключает _mark_dirty к сигналу изменения на каждом виджете
        формы -- по тем же спискам, что _reset_form()/get_form_data(),
        так что набор отслеживаемых полей не может разойтись с реальным
        составом документа."""
        for name in self.PLAIN_TEXT_EDIT_NAMES:
            getattr(self, name).textChanged.connect(self._mark_dirty)
        for name in self.COMBO_BOX_NAMES:
            getattr(self, name).currentIndexChanged.connect(self._mark_dirty)
        for name in self.DATE_EDIT_NAMES:
            getattr(self, name).dateChanged.connect(self._mark_dirty)
        for name in self.SPIN_BOX_NAMES:
            getattr(self, name).valueChanged.connect(self._mark_dirty)
        for name in self.TABLE_WIDGET:
            getattr(self, name).itemChanged.connect(self._mark_dirty)

    def _mark_dirty(self, *args):
        """Слот на любое изменение поля формы. Срабатывает и во время
        программного заполнения формы при открытии документа
        (_fill_ui_from_project() дёргает те же сигналы) -- в этот момент
        _current_document_path ещё None (сбрасывается в _reset_form() до
        заполнения), поэтому ложных срабатываний нет.

        Помимо самого факта "документ изменён" (once-флаг, дальше не
        трогается до сохранения/переоткрытия), пересчитывает иконки
        ✓/○/🔒 у TOC текущего документа на КАЖДОЕ изменение, не только
        первое -- для 18 из 20 разделов (не завязанных на кнопку шага
        STEP_ORDER) статус "готово" определяется именно заполненностью
        полей (см. _groupbox_done()), а значит должен обновляться
        живьём по мере ввода, а не только по клику кнопки расчёта."""
        if self._current_document_path is None:
            return
        if not self._document_dirty:
            self._document_dirty = True
            self._update_dirty_indicator()
        self._update_toc_progress()

    def _update_dirty_indicator(self):
        """Ставит/снимает точку-иконку у строки текущего документа в
        objectsTree."""
        item = self._find_document_tree_item(self._current_document_path)
        if item is None:
            return
        item.setIcon(0, self._dirty_icon if self._document_dirty else QIcon())

    def _create_object_dialog(self):
        """«Создать объект»: спрашивает название, создаёт папку, сразу
        обновляет дерево, чтобы новый объект стало видно."""
        name, ok = QInputDialog.getText(self, "Новый объект", "Название объекта:")
        if not ok or not name.strip():
            return
        workspace.create_object(name)
        self._refresh_objects_tree()

    def _create_document_dialog(self):
        """«Создать документ» -- всплывающее меню от кнопки: список
        существующих объектов + «Новый объект…» снизу (соответствует
        шагу 1 референсного мокапа, docs/design/pipeline_sidebar_mockup.html,
        #stepObject). Шаг 2 референса ("Использовать шаблон"/"Создать
        новый шаблон") сознательно не реализован -- реальной
        инфраструктуры нескольких шаблонов на equipment_type нет
        (find_template() захардкожен на один файл в config.py), а
        generate_template() -- разовая операция подготовки заготовки
        под ручную правку в Word (см. template_generator.py), не
        предназначенная запускаться при каждом создании документа.
        Фиктивный шаг выбора шаблона, который ничего не переключает,
        хуже, чем его отсутствие."""
        menu = QMenu(self)
        for object_name in workspace.list_objects():
            menu.addAction(object_name, lambda name=object_name: self._create_document_in_object(name))
        if menu.actions():
            menu.addSeparator()
        menu.addAction("Новый объект…", self._create_document_in_new_object)
        button = self.sidebarBtn_createDocument
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _create_document_in_new_object(self):
        """«Новый объект…» в меню «Создать документ» -- спрашивает имя,
        создаёт объект и сразу документ внутри него за один шаг (в
        отличие от отдельной кнопки «Создать объект», после которой
        пришлось бы ещё раз открывать это же меню)."""
        name, ok = QInputDialog.getText(self, "Новый объект", "Название объекта:")
        if not ok or not name.strip():
            return
        self._create_document_in_object(name)

    def _show_templates_menu(self):
        """«Мои шаблоны» -- показывает реально существующий шаблон
        (find_template() поддерживает ровно один файл на equipment_type,
        см. TEMPLATE_PATHS_BY_TYPE в config.py -- инфраструктуры выбора
        между несколькими шаблонами в проекте нет). Пункт
        информационный, недоступен для клика -- переключать нечего,
        пока шаблон один; помечать его "по умолч." было бы обманчиво,
        раз альтернативы не существует."""
        from ..config import find_template
        menu = QMenu(self)
        try:
            template_path = find_template(self.equipment_type.id)
            action = menu.addAction(template_path.stem)
        except FileNotFoundError:
            action = menu.addAction("Шаблон не найден")
        action.setEnabled(False)
        button = self.sidebarBtn_templates
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _collect_toc_groupboxes(self):
        """Собирает top-level QGroupBox'ы ленты tab_document в порядке
        компоновки -- статический список, форма всегда одна и та же
        независимо от того, какой документ открыт (в отличие от
        _current_toc_items, дочерних строк дерева, которые заново
        строятся под каждым открываемым документом, см.
        _populate_document_toc())."""
        layout = self.tab_document_scrollContent.layout()
        groupboxes = []
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if isinstance(widget, QGroupBox):
                groupboxes.append(widget)
        return groupboxes

    def _populate_document_toc(self, doc_item):
        """Строит оглавление как дочерние строки под строкой документа в
        objectsTree (Фаза 6) -- по одной на каждый groupbox из
        _toc_groupboxes, в том же порядке. Только для ТЕКУЩЕГО открытого
        документа: статус разделов считается по живым виджетам формы
        (см. _groupbox_done()), а данные другого документа в них не
        загружены. Вызывается из _open_document() после заполнения
        формы; TOC уходящего документа снимается там же через
        item.takeChildren()."""
        self._current_toc_items = []
        for groupbox in self._toc_groupboxes:
            item = QTreeWidgetItem([groupbox.title()])
            item.setData(0, Qt.ItemDataRole.UserRole, groupbox)
            doc_item.addChild(item)
            self._current_toc_items.append(item)
        doc_item.setExpanded(True)
        self._current_toc_active_item = None
        self._update_toc_progress()

    def _scroll_to_toc_item(self, item):
        """Клик по строке оглавления в дереве -- скроллит
        tab_document_scroll так, чтобы верх выбранного раздела оказался
        у верха видимой области (не ensureWidgetVisible(): для разделов
        выше высоты вьюпорта он подтянул бы минимальным движением, а не
        встык к началу раздела). Заблокированные строки (см.
        _toc_lock_reason()) не скроллят -- у них уже снят
        Qt.ItemFlag.ItemIsEnabled в _update_toc_item_style(), но клик
        может дойти и до отключённого item'а, проверка дублируется."""
        groupbox = item.data(0, Qt.ItemDataRole.UserRole)
        if self._toc_lock_reason(groupbox) is not None:
            return
        self._suppress_toc_spy = True
        self.tab_document_scroll.verticalScrollBar().setValue(groupbox.y())
        self._set_toc_active_item(item)
        self._suppress_toc_spy = False
        self._update_breadcrumb()

    def _on_document_scrolled(self, value):
        """Скролл-спай: при ручной прокрутке ленты подсвечивает строку
        последнего раздела, чей верх уже проскроллен (groupbox.y() <=
        value), в оглавлении текущего открытого документа. Отключается
        на время программного скролла по клику (_suppress_toc_spy),
        иначе клик спорил бы сам с собой."""
        if self._suppress_toc_spy or not self._current_toc_items:
            return
        current = 0
        for i, groupbox in enumerate(self._toc_groupboxes):
            if groupbox.y() <= value:
                current = i
        self._set_toc_active_item(self._current_toc_items[current])
        self._update_breadcrumb()

    def _set_toc_active_item(self, item):
        """Полная заливка активной строки TOC синим, как в референсе
        (docs/design/pipeline_sidebar_mockup.html, .toc-active) -- через
        setBackground()/setForeground() напрямую на item, а не через
        нативное выделение QTreeWidget: нативная подсветка платформенно
        по-разному ведёт себя в фокусе/без фокуса окна, а тут нужна
        подсветка "текущий раздел", не зависящая от фокуса. Сброс роли в
        None (не просто прозрачный цвет) возвращает предыдущему item'у
        подлинный вид по умолчанию."""
        if self._current_toc_active_item is not None:
            self._current_toc_active_item.setData(0, Qt.ItemDataRole.BackgroundRole, None)
            self._current_toc_active_item.setData(0, Qt.ItemDataRole.ForegroundRole, None)
        item.setBackground(0, QColor("#0a84ff"))
        item.setForeground(0, QColor("#ffffff"))
        self._current_toc_active_item = item

    # Пункты оглавления, у которых есть осмысленное понятие "выполнено" из
    # реальной кнопки-расчёта -- только эти два groupbox'а физически
    # содержат кнопки шагов из equipment_types.py STEP_ORDER
    # (segments/thickness -> thick_group, strength/residual_life ->
    # calc_appendix_group). У остальных 18 разделов такой кнопки нет --
    # для них статус считает _groupbox_done() по заполненности полей.
    TOC_PROGRESS_GROUPS = {
        "thick_group": {"segments", "thickness"},
        "calc_appendix_group": {"strength", "residual_life"},
    }

    def _groupbox_done(self, groupbox):
        """"Готово" для раздела оглавления. Для thick_group/
        calc_appendix_group -- точная семантика STEP_ORDER (см.
        TOC_PROGRESS_GROUPS): у них есть настоящая кнопка-расчёт, это
        строго более надёжный сигнал, чем заполненность полей, трогать
        не нужно. Для остальных 18 разделов, где такой кнопки нет --
        обобщённая проверка: все виджеты формы внутри groupbox'а (те же
        типы, что в _reset_form()/get_form_data()) заполнены.

        QDateEdit и QComboBox намеренно не проверяются. У даты всегда
        есть значение (по умолчанию сегодняшнее) -- "пустой" даты, в
        отличие от текстового поля, не бывает. У комбобоксов currentIndex()
        == 0 НЕ значит "не заполнено": report_title -- редактируемый
        комбобокс ровно с одним пунктом (реальный дефолтный текст, не
        плейсхолдер-заглушка), work_medium -- 5 реальных веществ без
        пустого варианта; для обоих индекс 0 -- уже осмысленный выбор,
        который оператор имеет полное право оставить как есть (проверено
        headless-тестом: report_title.count() == 1 в свежесозданном
        документе -- проверка "index == 0 -> пусто" там попросту неверна)."""
        steps = self.TOC_PROGRESS_GROUPS.get(groupbox.objectName())
        if steps is not None:
            return steps <= self._completed_steps
        for edit in groupbox.findChildren(QPlainTextEdit):
            if not edit.toPlainText().strip():
                return False
        for spin in groupbox.findChildren(QSpinBox):
            if spin.value() == spin.minimum():
                return False
        for table in groupbox.findChildren(QTableWidget):
            if table.rowCount() == 0:
                return False
        return True

    def _toc_lock_reason(self, groupbox):
        """Возвращает заголовок блокирующего раздела, если groupbox
        заблокирован (🔒), иначе None. Единственная реальная зависимость
        в данных этого приложения: calc_appendix_group (шаги
        strength/residual_life) требует thick_group (шаги
        segments/thickness) выполненным целиком -- тот же порядок, что
        и в _check_prerequisite(). Другие 18 разделов никогда не
        блокируются -- в реальной модели STEP_ORDER больше зависимостей
        нет; выдумывать их ради сходства с иллюстрацией в референсе не
        нужно (референсный "Приложение 8 заблокировано Приложением 6" --
        условный пример для мокапа, не основанный на реальных данных
        этого приложения)."""
        if groupbox.objectName() == "calc_appendix_group" and not self._groupbox_done(self.thick_group):
            return self.thick_group.title()
        return None

    def _update_toc_item_style(self, item, groupbox):
        """Ставит иконку ✓/○/🔒 и тултип у одной строки TOC."""
        lock_reason = self._toc_lock_reason(groupbox)
        if lock_reason:
            item.setIcon(0, self._toc_lock_icon)
            item.setToolTip(0, f"Сначала завершите «{lock_reason}»")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        else:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
            item.setToolTip(0, "")
            item.setIcon(0, self._toc_check_icon if self._groupbox_done(groupbox) else self._toc_circle_icon)

    def _update_toc_progress(self):
        """Обновляет иконки ✓/○/🔒 у всех строк TOC текущего открытого
        документа. Единая точка входа после любого изменения, влияющего
        на статус разделов -- клика по кнопке шага STEP_ORDER (см. 4
        вызова ниже) или правки любого поля формы (см. _mark_dirty()).
        Безопасно вызывать и когда документ не открыт -- _current_toc_items
        тогда пуст, zip() ничего не делает."""
        for item, groupbox in zip(self._current_toc_items, self._toc_groupboxes):
            self._update_toc_item_style(item, groupbox)

    def _make_check_icon(self):
        """✓ готово -- зелёный кружок с белой галочкой (аналог
        ti-circle-check из референса). Рисуется на лету тем же приёмом,
        что и _make_dot_icon()."""
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#30d158"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(1, 1, 12, 12)
        pen = QPen(QColor("#ffffff"))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(QPointF(4, 7.2), QPointF(6.2, 9.5))
        painter.drawLine(QPointF(6.2, 9.5), QPointF(10, 4.7))
        painter.end()
        return QIcon(pixmap)

    def _make_circle_icon(self):
        """○ не готово -- серый контур кружка (аналог ti-circle)."""
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#8e8e93"))
        pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 10, 10)
        painter.end()
        return QIcon(pixmap)

    def _make_lock_icon(self):
        """🔒 заблокировано -- серый замок, тело + дужка (аналог
        ti-lock)."""
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#8e8e93")
        pen = QPen(color)
        pen.setWidthF(1.6)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(3, 1, 8, 8, 0, 180 * 16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(2, 6, 10, 7, 2, 2)
        painter.end()
        return QIcon(pixmap)

    def _update_report_buttons_visibility(self):
        """Скрывает кнопки "Выгрузить в Word"/"Сохранить проект"/"Открыть
        проект", пока открыты "Сотрудники"/"Приборы"/"Документы" -- это
        общие справочники компании, не часть текущего отчёта (см.
        EmployeesTabController, InstrumentsTabController,
        OrgDocsTabController), эти действия к ним не относятся."""
        is_directory_view = self._current_view in ("employees", "instruments", "orgdocs")
        self.pushButt_generateWord.setVisible(not is_directory_view)
        self.pushButton_saveProject.setVisible(not is_directory_view)
        self.pushButton_openProject.setVisible(not is_directory_view)

    def _cell_text(self, table, row, col):
        """Текст ячейки (row, col) независимо от того, обычный это
        QTableWidgetItem или виджет (QComboBox, см. _install_growable_combo())."""
        item = table.item(row, col)
        if item is not None:
            return item.text()
        cell_widget = table.cellWidget(row, col)
        if isinstance(cell_widget, QComboBox):
            return cell_widget.currentText()
        return ""

    def _update_p_rab_kgs(self):
        """Автоматически пересчитывает "Давление, кгс/см2" из "Давление,
        МПа" (1 МПа = 1/0,0980665 кгс/см2, точный коэффициент перевода) --
        p_rab_kgs доступно только для чтения (см. .ui), оператор вводит
        давление один раз в МПа."""
        try:
            mpa = parse_ru(self.p_rab_mpa.toPlainText())
        except ValueError:
            self.p_rab_kgs.setPlainText("")
            return
        self.p_rab_kgs.setPlainText(format_ru_fixed(mpa / 0.0980665, 1))

    def _sync_mirror_field(self, target, source_text, state_attr):
        """Копирует source_text в target, пока оператор не ввёл в target
        своё значение. "Тронуто" определяется не через "непусто" (иначе при
        обычном посимвольном наборе в source-поле target подхватил бы
        только самый первый введённый символ и на этом застрял бы -- после
        него target уже "непусто", хотя это ещё чисто автоподстановка) -- а
        через сравнение текущего текста target с последним значением,
        которое сюда же поставила именно эта автоподстановка (state_attr,
        хранится на self). Если оператор изменил target -- текст разойдётся
        с state_attr, и подстановка остановится."""
        current = target.toPlainText()
        if current and current != getattr(self, state_attr, None):
            return
        target.setPlainText(source_text)
        setattr(self, state_attr, source_text)

    # Пары (target, source, state_attr) для _sync_mirror_field() -- вынесены
    # сюда одним списком, чтобы завести его один раз и переиспользовать и в
    # сигналах __init__ (через свои _update_*_display()), и в
    # _seed_mirror_states_after_load() ниже.
    MIRROR_FIELD_PAIRS = (
        ("calc_temp", "work_temp", "_calc_temp_auto_value"),
        ("pnevmo_obj_naznach", "obj_naznach", "_pnevmo_obj_naznach_auto_value"),
        ("ae_zakl_obj_control", "pnevmo_obj_naznach", "_ae_zakl_obj_control_auto_value"),
        ("calc_years_operation", "years_of_operation", "_calc_years_operation_auto_value"),
    )

    def _seed_mirror_states_after_load(self):
        """Восстанавливает state_attr у "зеркал, пока не тронутых"
        (_sync_mirror_field(): calc_temp/pnevmo_obj_naznach/
        ae_zakl_obj_control/calc_years_operation) сразу после загрузки
        проекта (FileHandler._fill_ui_from_project()) -- единственный
        признак "не тронуто" там -- current-текст target совпадает с
        state_attr, а на свежем окне state_attr всегда None. Без этого
        восстановленное из JSON непустое значение target (даже если оно
        никогда не редактировалось вручную и просто совпадает с source)
        навсегда воспринималось бы как "оператор его трогал" -- дальше
        правки в source-поле (например years_of_operation, раздел 6)
        переставали подхватываться в target (calc_years_operation,
        Приложение 6), хотя раньше, до сохранения/открытия проекта,
        подхватывались нормально.

        Сеем состояние только когда target совпадает с source -- если они
        разошлись (оператор реально переопределил target перед
        сохранением), это и есть корректное "тронуто", трогать не нужно."""
        for target_name, source_name, state_attr in self.MIRROR_FIELD_PAIRS:
            target = getattr(self, target_name)
            source = getattr(self, source_name)
            if target.toPlainText() == source.toPlainText():
                setattr(self, state_attr, target.toPlainText())

        # years_of_operation -- отдельный случай: источник не одно
        # текстовое поле, а вычисление report_year - year_start, см.
        # _update_years_of_operation_display(). Та же логика "seed только
        # если совпадает с вычисленным значением".
        try:
            computed = str(
                int(parse_ru(self.report_year.toPlainText()))
                - int(parse_ru(self.year_start.toPlainText()))
            )
        except ValueError:
            computed = None
        if computed is not None and self.years_of_operation.toPlainText() == computed:
            self._years_of_operation_auto_value = computed

    def _update_years_of_operation_display(self):
        """Подсказка years_of_operation (раздел 6, "Срок эксплуатации,
        лет") -- по умолчанию год составления отчёта (report_year,
        раздел 1) минус год ввода в эксплуатацию (year_start, раздел 6),
        но поле редактируемое: инженер может исправить вручную (например,
        если объект фактически простаивал часть срока), см.
        _sync_mirror_field()."""
        try:
            report_year = int(parse_ru(self.report_year.toPlainText()))
            year_start = int(parse_ru(self.year_start.toPlainText()))
        except ValueError:
            return
        self._sync_mirror_field(
            self.years_of_operation, str(report_year - year_start),
            "_years_of_operation_auto_value",
        )

    def _update_calc_temp_display(self):
        """Подсказка calc_temp (Приложение 6) значением work_temp (1. Общие
        данные) -- по умолчанию температура стенки принимается равной
        рабочей температуре среды, но поле редактируемое: дальше значение
        полностью в руках оператора, см. _sync_mirror_field()."""
        self._sync_mirror_field(self.calc_temp, self.work_temp.toPlainText(), "_calc_temp_auto_value")

    def _update_calc_years_operation_display(self):
        """Подсказка calc_years_operation (Приложение 6, "Остаточный
        ресурс -- исходные данные") значением years_of_operation (раздел 6)
        -- по умолчанию срок эксплуатации для расчёта остаточного ресурса
        равен сроку эксплуатации объекта, но поле редактируемое, см.
        _sync_mirror_field()."""
        self._sync_mirror_field(
            self.calc_years_operation, self.years_of_operation.toPlainText(),
            "_calc_years_operation_auto_value",
        )

    def _update_calc_p_rab_display(self):
        """Зеркалит p_rab_mpa (1. Общие данные) в read-only
        calc_p_rab_display (Приложение 6) -- само это поле не резолвится
        через widget_names_pipeline.py и в шаблон .docx не попадает, это
        чисто UI-подсказка (тот же приём, что и pnevmo_pressure_hint)."""
        self.calc_p_rab_display.setPlainText(self.p_rab_mpa.toPlainText())

    def _update_pnevmo_pressure(self):
        """Автоматически пересчитывает "Испытательное давление"
        (pnevmo_pressure, Приложения 8-9) из "Давление, кгс/см2"
        (p_rab_kgs, 1. Общие данные) по формуле p_rab_kgs * 1,25 --
        срабатывает при каждом изменении p_rab_kgs, перезаписывая
        прежнее значение поля (тот же принцип, что и у
        _update_final_deadline_date)."""
        try:
            p_rab_kgs = parse_ru(self.p_rab_kgs.toPlainText())
        except ValueError:
            self.pnevmo_pressure.setPlainText("")
            return
        self.pnevmo_pressure.setPlainText(format_ru_fixed(p_rab_kgs * 1.25, 1))

    def _fill_pnevmo_stages_table(self):
        """Автозаполнение table_pnevmo_stages (Приложение 8, "Этапы
        пневматического испытания трубопровода") -- 5 строк, ступени
        давления от p_rab_kgs (0,3 / 0,6 / 1,0 / 1,25 и само значение),
        время выдержки по методике (10 мин на первых трёх ступенях, 15 на
        четвёртой, для пятой -- прочерк). Срабатывает при каждом изменении
        p_rab_kgs, полностью перезаписывая таблицу (тот же принцип, что и у
        _update_pnevmo_pressure())."""
        table = self.table_pnevmo_stages
        try:
            p_rab_kgs = parse_ru(self.p_rab_kgs.toPlainText())
        except ValueError:
            table.setRowCount(0)
            return
        stages = [
            (format_ru_fixed(p_rab_kgs * 0.3, 1), "10"),
            (format_ru_fixed(p_rab_kgs * 0.6, 1), "10"),
            (format_ru_fixed(p_rab_kgs * 1.0, 1), "10"),
            (format_ru_fixed(p_rab_kgs * 1.25, 1), "15"),
            (self.p_rab_kgs.toPlainText(), "-"),
        ]
        table.setRowCount(len(stages))
        for row, (pressure, hold_time) in enumerate(stages):
            table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            table.setItem(row, 1, QTableWidgetItem(pressure))
            table.setItem(row, 2, QTableWidgetItem(hold_time))

    def _update_pnevmo_pressure_hint(self):
        """Зеркалит "Испытательное давление" (pnevmo_pressure, Приложения
        8-9) в read-only pnevmo_pressure_hint рядом с result_76 (раздел
        7.6). Плейсхолдеры не вкладываются друг в друга, поэтому текст 7.6
        оставляет пробел "P=__________ кгс/см2" под ручное заполнение --
        это поле только подсказывает уже введённое оператором значение,
        само оно в шаблон .docx не попадает."""
        self.pnevmo_pressure_hint.setPlainText(self.pnevmo_pressure.toPlainText())

    def _update_result_76_pressure(self):
        """Подставляет введённое испытательное давление вместо заглушки
        "P=__________" в свободном тексте result_76 (раздел 7.6) -- работает,
        только пока заглушка ещё не тронута оператором, иначе правку текста
        не перезаписывает (тот же принцип, что и у final_years_allowed/
        final_deadline_date)."""
        text = self.result_76.toPlainText()
        if "P=__________" in text:
            self.result_76.setPlainText(
                text.replace("P=__________", f"P={self.pnevmo_pressure.toPlainText()}")
            )

    def _update_final_deadline_date(self):
        """Дата из report_year + final_years_allowed (раздел 8.4.1) -- год
        отчёта плюс разрешённый срок эксплуатации в годах, день/месяц
        берутся из report_date (при его отсутствии -- текущая дата).
        Пересчитывается при каждом изменении final_years_allowed или
        report_year, перезаписывая прежнее значение поля."""
        try:
            years = int(parse_ru(self.final_years_allowed.toPlainText()))
            report_year = int(parse_ru(self.report_year.toPlainText()))
        except ValueError:
            return
        day_month_source = self.report_date.date()
        if day_month_source == QDate(2000, 1, 1):
            day_month_source = QDate.currentDate()
        base = QDate(report_year, day_month_source.month(), day_month_source.day())
        if not base.isValid():
            base = QDate(report_year, day_month_source.month(), 28)
        self.final_deadline_date.setDate(base.addYears(years))

    def _choose_nk_scheme(self):
        """Загрузка изображения схемы НК (Приложение 7). Тот же приём, что
        и клише сотрудника (src/ui/employees_tab.py) -- копия файла в
        общую папку под uuid-именем, само имя лежит в self.data и едет в
        Project.report_data при сохранении/открытии проекта."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать схему НК", "", "Изображения (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        filename = store_kleishe_image(Path(file_path), dest_dir=NK_SCHEME_DIR)
        self.data["nk_scheme_filename"] = filename
        self._set_nk_scheme_preview(filename)

    def _clear_nk_scheme(self):
        self.data["nk_scheme_filename"] = None
        self._set_nk_scheme_preview(None)

    def _set_nk_scheme_preview(self, filename):
        label = self.nk_scheme_preview
        if not filename:
            label.setPixmap(QPixmap())
            label.setText("нет изображения")
            return

        pixmap = QPixmap(str(NK_SCHEME_DIR / filename))
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("не удалось загрузить")
            return

        label.setText("")
        label.setPixmap(pixmap.scaled(
            label.width(), label.height(), Qt.AspectRatioMode.KeepAspectRatio,
        ))

    def _choose_pnevmo_graph(self):
        """Загрузка изображения графика нагружения (Приложение 8, Рисунок
        1) -- полная копия _choose_nk_scheme() (Приложение 7) под новую
        папку PNEVMO_GRAPH_DIR."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать график нагружения", "", "Изображения (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        filename = store_kleishe_image(Path(file_path), dest_dir=PNEVMO_GRAPH_DIR)
        self.data["pnevmo_graph_filename"] = filename
        self._set_pnevmo_graph_preview(filename)

    def _clear_pnevmo_graph(self):
        self.data["pnevmo_graph_filename"] = None
        self._set_pnevmo_graph_preview(None)

    def _set_pnevmo_graph_preview(self, filename):
        label = self.pnevmo_graph_preview
        if not filename:
            label.setPixmap(QPixmap())
            label.setText("нет изображения")
            return

        pixmap = QPixmap(str(PNEVMO_GRAPH_DIR / filename))
        if pixmap.isNull():
            label.setPixmap(QPixmap())
            label.setText("не удалось загрузить")
            return

        label.setText("")
        label.setPixmap(pixmap.scaled(
            label.width(), label.height(), Qt.AspectRatioMode.KeepAspectRatio,
        ))

    def _table_to_dicts(self, table, keys):
        """Конвертирует QTableWidget (по столбцам, слева направо) в
        list[dict] по переданным keys -- для полей, которые в self.data
        должны попасть списком словарей под Jinja-цикл {% for %}, а не
        списком списков "как есть" (см. get_form_data(), TABLE_WIDGET).
        Ячейка может быть обычным QTableWidgetItem или виджетом (см.
        table_specialists -- редактируемые комбобоксы), поэтому при
        отсутствии item проверяем cellWidget."""
        rows = []
        for row in range(table.rowCount()):
            item_dict = {}
            for col, key in enumerate(keys):
                item = table.item(row, col)
                if item is not None:
                    item_dict[key] = item.text()
                else:
                    cell_widget = table.cellWidget(row, col)
                    if isinstance(cell_widget, QComboBox):
                        item_dict[key] = cell_widget.currentText()
                    else:
                        item_dict[key] = ""
            rows.append(item_dict)
        return rows

    # Поля, чей плейсхолдер в шаблоне трубопровода использует докстпл-синтаксис
    # {{r field }} (сырой XML, не экранированный текст) -- см. _apply_line_breaks().
    # Список должен буквально совпадать с тем, что реально помечено {{r %}
    # в templates/Шаблон_трубопровод.docx -- {{r %} требует RichText-совместимое
    # значение ВСЕГДА (даже однострочное: RichText("текст") без \n -- валидный
    # <w:r><w:t>текст</w:t></w:r>), иначе докстпл вставляет голый текст мимо
    # <w:t>, и Word/python-docx его теряют -- проверено эмпирически на
    # org_activity_scope (однострочное значение, {{r %} без RichText → пропало).
    RICH_TEXT_FIELDS = frozenset({
        "intro_text", "result_71", "result_72", "result_73", "result_74",
        "result_75", "result_76", "result_77", "act2_intro_text",
        "vik_guidance_docs", "thick_guidance_docs", "uzk_guidance_docs",
        "uzk_evaluation_text", "calc_gost_basis", "calc_residual_methodology_note",
        "calc_residual_formula_text", "calc_corrosion_formula_text",
        "calc_worked_example_note", "ae_zakl_sources_text",
        "ae_zakl_evaluation_text", "org_activity_scope",
        "pnevmo_sensor_placement_note", "org_license_issuer",
    })

    # Поля из RICH_TEXT_FIELDS, чей плейсхолдер-run в шаблоне помечен italic
    # -- RichText не наследует форматирование run'а, который заменяет (см.
    # _apply_line_breaks), поэтому курсив нужно проставлять явно, иначе он
    # тихо теряется при рендере (эмпирически найдено на org_activity_scope).
    RICH_TEXT_ITALIC_FIELDS = frozenset({"org_activity_scope"})

    @classmethod
    def _apply_line_breaks(cls, form_data: dict) -> None:
        """Заменяет в form_data (на месте) значения полей из RICH_TEXT_FIELDS
        на docxtpl.RichText с настоящими переносами строк (<w:br/> между
        строками, без новых <w:p> -- так же устроены реальные переносы в
        эталонном документе). Применяется КО ВСЕМ полям из списка, а не
        только к содержащим '\\n' -- их плейсхолдер в шаблоне уже помечен
        {{r %} (сырой XML), и без RichText-обёртки даже однострочное
        значение теряется при рендере (см. RICH_TEXT_FIELDS)."""
        for key in cls.RICH_TEXT_FIELDS:
            value = form_data.get(key)
            if not isinstance(value, str):
                continue
            italic = key in cls.RICH_TEXT_ITALIC_FIELDS
            rt = RichText()
            lines = value.split("\n")
            for i, line in enumerate(lines):
                if i > 0:
                    rt.xml += "<w:r><w:br/></w:r>"
                rt.add(line, italic=italic)
            form_data[key] = rt


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
