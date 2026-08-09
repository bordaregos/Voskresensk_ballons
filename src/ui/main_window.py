"""Главное окно приложения: связывает main_window.ui с расчётными сервисами."""

from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QComboBox,
                             QPushButton, QSpinBox, QDateEdit, QTableWidgetItem, QTableWidget,
                             QMessageBox, QFileDialog)
from PyQt6.QtCore import QLocale, Qt
from PyQt6.uic import loadUi
from typing import Dict, Union
from docxtpl import DocxTemplate

import os

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
from .widget_names_pipeline import SEGMENT_TYPES, PROGRAM_DEFAULT_ITEMS


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

        self.equipment_type = equipment_type
        self.PLAIN_TEXT_EDIT_NAMES = equipment_type.widget_names.PLAIN_TEXT_EDIT_NAMES
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
            self.pushButt_segments.clicked.connect(self.fill_segments_table)
            self.pushButton_genThickness.clicked.connect(self.calc_pipeline_thickness)
            self.pushButton_calcStrength.clicked.connect(self.calc_pipeline_strength_ui)
            self.pushButton_calcResidualLife.clicked.connect(self.calc_pipeline_residual_life_ui)
            self.pushButt_addSpecialist.clicked.connect(self._add_specialist_row)
            self.pushButt_removeSpecialist.clicked.connect(lambda: self._remove_table_row(self.table_specialists))
            self.pushButt_addReviewedDoc.clicked.connect(lambda: self._add_table_row(self.table_reviewed_docs))
            self.pushButt_removeReviewedDoc.clicked.connect(lambda: self._remove_table_row(self.table_reviewed_docs))
            self.pushButt_addVikRow.clicked.connect(lambda: self._add_table_row(self.table_vik))
            self.pushButt_removeVikRow.clicked.connect(lambda: self._remove_table_row(self.table_vik))
            self.pushButt_removeThickDevice.clicked.connect(lambda: self._remove_combo_current_item(self.thick_device))
            self.pushButt_removeUzkDevice.clicked.connect(lambda: self._remove_combo_current_item(self.uzk_device))
            self.pushButt_removePnevmoDevice.clicked.connect(lambda: self._remove_combo_current_item(self.pnevmo_device))
            self.pushButt_removeReportTitle.clicked.connect(lambda: self._remove_combo_current_item(self.report_title))
            self.pushButt_addPipeMaterial.clicked.connect(self._add_pipe_material_row)
            self.pushButt_removePipeMaterial.clicked.connect(lambda: self._remove_table_row(self.table_pipe_materials))
            self.p_rab_mpa.textChanged.connect(self._update_p_rab_kgs)
            self.pnevmo_pressure.textChanged.connect(self._update_pnevmo_pressure_hint)
            self.pushButt_addProgramItem.clicked.connect(self._add_program_item_row)
            self.pushButt_addProgramSubitem.clicked.connect(self._add_program_subitem_row)
            self.pushButt_removeProgramRow.clicked.connect(self._remove_program_row)
            self.tabWidget.currentChanged.connect(self._refresh_program_specialist_combo)
            self._seed_program_table_defaults()

            from .employees_tab import EmployeesTabController
            self.employees_tab = EmployeesTabController(self)

            # «Сотрудники» — общий справочник компании, не часть текущего
            # отчёта: кнопки генерации Word и работы с проектом там неуместны.
            self.tabWidget.currentChanged.connect(self._update_report_buttons_visibility)
            self._update_report_buttons_visibility()

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
                if name == "report_date":
                    # Дата отчёта на титульном листе -- день в кавычках-ёлочках
                    # по канцелярской традиции: «15» ноября 2024. Текст в
                    # одинарных кавычках в формате QLocale выводится буквально.
                    self.data[name] = locale.toString(date, "'«'dd'»' MMMM yyyy")
                else:
                    # Формат: dd MMMM yyyy (пробелы, месяц в родительном падеже на русском)
                    self.data[name] = locale.toString(date, 'dd MMMM yyyy')
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
                # Колонки таблицы: 0 -- Должность, 1 -- ФИО, 2 -- Удостоверение.
                self.data["specialists"] = self._table_to_dicts(
                    self.table_specialists, ["position", "name", "cert_number"]
                )
                # name_initials -- "И. О. Фамилия" для таблицы подписи после
                # раздела 8 (Таблица 2 продолжает использовать полное "name").
                for specialist in self.data["specialists"]:
                    specialist["name_initials"] = format_fio_initials(specialist["name"])

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
                self.data["lead_specialist_cert_number"] = lead_specialist["cert_number"]

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
                self.data["programm_specialist_cert_number"] = programm_specialist["cert_number"]

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
                self.data["act2_specialist_cert_number"] = act2_specialist["cert_number"]

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
                self.data["vik_specialist_cert_number"] = vik_specialist["cert_number"]

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
                self.data["thick_specialist_cert_number"] = thick_specialist["cert_number"]

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
                self.data["uzk_specialist_cert_number"] = uzk_specialist["cert_number"]

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
            form_data = self.get_form_data()
            print("Данные для Word:", form_data)

            # 3. Проверяем наличие шаблона (используем config.py)
            from ..config import find_template, OUTPUT_DIR
            template_path = find_template(self.equipment_type.id)

            # 4. Загружаем и заполняем шаблон
            doc = DocxTemplate(template_path)
            doc.render(form_data)

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
        """Заполнение таблицы участков трассы. STEP_ORDER: 'segments'."""
        count = self.segments_count.value()
        size = self._first_pipe_material_value(3) or "-"
        table = self.table_segments
        table.setRowCount(count)
        for row in range(count):
            table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self._install_segment_type_combo(table, row)
            table.setItem(row, 2, QTableWidgetItem(size))
        self._completed_steps.add("segments")

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

            allowable_stress = get_allowable_stress(steel_grade, temp)
            result = calculate_pipeline_strength(
                p_working=p_working, d_outer=d_outer, allowable_stress=allowable_stress,
                s_actual=s_actual, c2=c2, phi=phi,
            )

            self.calc_sigma_allow.setPlainText(format_ru(allowable_stress))
            self.calc_sr.setPlainText(format_ru(result.s_calc))
            self.calc_s_reject.setPlainText(format_ru(result.s_reject))
            self.calc_p_allow.setPlainText(format_ru(result.p_allow))
            self.calc_strength_conclusion.setPlainText(
                "Условие прочности выполняется" if result.strength_ok
                else "Условие прочности не выполняется"
            )
            self._completed_steps.add("strength")

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

            result = calculate_pipeline_residual_life(
                s_nominal=s_nominal, s_actual=s_actual, s_reject=s_reject,
                years_of_operation=years, k=k,
            )

            self.calc_corrosion_rate.setPlainText(format_ru(result.corrosion_rate))
            self.calc_remaining_years.setPlainText(format_ru(result.remaining_years))
            self.calc_residual_comment.setPlainText(result.comment)
            self._completed_steps.add("residual_life")

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
        """Добавляет строку в table_specialists и сразу устанавливает в неё
        3 редактируемых комбобокса (Должность, ФИО, Удостоверение) -- см.
        _install_growable_combo()."""
        table = self.table_specialists
        row = table.rowCount()
        table.insertRow(row)
        for col in range(3):
            self._install_growable_combo(table, row, col)

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

    def _refresh_program_specialist_combo(self):
        """Обновляет списки в program_specialist (поле "Программу составил",
        Приложение 1), act2_specialist (поле "Анализ документации провёл",
        Приложение 2), vik_specialist (поле "Контроль провёл", Приложение 3),
        thick_specialist (поле "Измерение провёл", Приложение 4) и
        uzk_specialist (поле "Измерение провёл", Приложение 5) при
        переключении на вкладку "Приложения" -- источник вариантов для всех
        один и тот же: table_specialists (1.3 Сведения о специалистах,
        Таблица 2). Ни один из комбобоксов не входит ни в один список
        widget_names_pipeline.py (как pnevmo_pressure_hint) -- каждый даёт
        индекс строки специалиста, а не текст для .docx напрямую, итоговые
        плейсхолдеры собирает calculate()."""
        if self.tabWidget.widget(self.tabWidget.currentIndex()) is not self.tab_acts:
            return
        self._refresh_specialist_combo(self.program_specialist)
        self._refresh_specialist_combo(self.act2_specialist)
        self._refresh_specialist_combo(self.vik_specialist)
        self._refresh_specialist_combo(self.thick_specialist)
        self._refresh_specialist_combo(self.uzk_specialist)

    def _refresh_specialist_combo(self, combo):
        """Перезаполняет один комбобокс-выбор специалиста вариантами из
        table_specialists, сохраняя текущий выбор (по индексу строки), если
        он всё ещё существует -- общая логика для program_specialist и
        act2_specialist, см. _refresh_program_specialist_combo()."""
        previous = combo.currentData()
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

    def _update_report_buttons_visibility(self):
        """Скрывает кнопки "Выгрузить в Word"/"Сохранить проект"/"Открыть
        проект" на вкладке "Сотрудники" -- это общий справочник компании, не
        часть текущего отчёта (см. EmployeesTabController), эти действия к
        нему не относятся."""
        is_employees_tab = self.tabWidget.currentWidget() is self.tab_employees
        self.pushButt_generateWord.setVisible(not is_employees_tab)
        self.pushButton_saveProject.setVisible(not is_employees_tab)
        self.pushButton_openProject.setVisible(not is_employees_tab)

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

    def _update_pnevmo_pressure_hint(self):
        """Зеркалит "Испытательное давление" (pnevmo_pressure, Приложения
        8-9) в read-only pnevmo_pressure_hint рядом с result_76 (раздел
        7.6). Плейсхолдеры не вкладываются друг в друга, поэтому текст 7.6
        оставляет пробел "P=__________ кгс/см2" под ручное заполнение --
        это поле только подсказывает уже введённое оператором значение,
        само оно в шаблон .docx не попадает."""
        self.pnevmo_pressure_hint.setPlainText(self.pnevmo_pressure.toPlainText())

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


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
