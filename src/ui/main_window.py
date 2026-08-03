"""Главное окно приложения: связывает main_window.ui с расчётными сервисами."""

from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QComboBox,
                             QPushButton, QSpinBox, QDateEdit, QTableWidgetItem, QTableWidget,
                             QMessageBox)
from PyQt6.QtCore import QLocale
from PyQt6.uic import loadUi
from typing import Dict, Union
from docxtpl import DocxTemplate

import os

from . import widget_names
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
from ..services.formatting import format_ru, format_ru_fixed, parse_ru, format_thickness_block

DESIGNER_UI_PATH = Path(__file__).resolve().parent / "designer" / "main_window.ui"


class MainWindow(QMainWindow):
    # Списки для автоматической инициализации виджетов
    PLAIN_TEXT_EDIT_NAMES = widget_names.PLAIN_TEXT_EDIT_NAMES
    COMBO_BOX_NAMES = widget_names.COMBO_BOX_NAMES
    DATE_EDIT_NAMES = widget_names.DATE_EDIT_NAMES
    BUTTON_NAMES = widget_names.BUTTON_NAMES
    SPIN_BOX_NAMES = widget_names.SPIN_BOX_NAMES
    TABLE_WIDGET = widget_names.TABLE_WIDGET

    def __init__(self):
        """Инициализация конструктора класса. Пишем все атрибуты,
        что пригодятся нам по коду."""
        super().__init__()
        self.data = {}
        self.text = []
        self.s_min_lst = []
        self.file_handler = None

        loadUi(str(DESIGNER_UI_PATH), self)

        # Автоматическая инициализация виджетов
        self.init_widgets()

        # Инициализация FileHandler
        self.init_file_handler()

        # Подключение сигналов
        self.pushButt_generateWord.clicked.connect(self.calculate)
        self.pushButton_exportCSV.clicked.connect(self.export_csv)
        self.pushButt_amount.clicked.connect(self.fill_table)
        self.pushButt_sMinMin.clicked.connect(self.s_min_min_calc)
        self.pushButton_creatThickness.clicked.connect(self.calc_thick)
        self.pushButton_creatRasschProchn.clicked.connect(self.prochnost)
        self.pushButton_creatOstRes.clicked.connect(self.ost_res)
        self.pushButt_ovalnost.clicked.connect(self.ovalnost_calc)
        self.pushButt_tverdost.clicked.connect(self.tverdost)
        self.pushButton_importCSV.clicked.connect(self.import_csv)
        self.pushButton_saveProject.clicked.connect(self.save_project)
        self.pushButton_openProject.clicked.connect(self.open_project)

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
                # Формат: dd MMMM yyyy (пробелы, месяц в родительном падеже на русском)
                locale = QLocale('ru_RU')
                self.data[name] = locale.toString(date, 'dd MMMM yyyy')
            else:
                self.data[name] = ""

        # Получаем текст из QTableWidget.
        for name in self.TABLE_WIDGET:
            widget = getattr(self, name)
            table_data = []
            for row in range(widget.rowCount()):
                row_data = []
                for col in range(widget.columnCount()):
                    item = widget.item(row, col)
                    row_data.append(item.text() if item else "")
                table_data.append(row_data)
            self.data[name] = table_data

        return self.data

    def calculate(self):
        """Обработчик нажатия кнопки генерации Word с улучшенной обработкой ошибок"""
        try:
            # 1. Проверка заполненности полей
            if not all([
                self.zakl_number.toPlainText().strip(),
                self.reg_number.toPlainText().strip(),
                self.p_rab.toPlainText().strip()
            ]):
                raise ValueError("Не все обязательные поля заполнены")

            # 2. Получаем данные формы
            form_data = self.get_form_data()
            print("Данные для Word:", form_data)

            # 3. Проверяем наличие шаблона (используем config.py)
            from ..config import find_template
            template_path = find_template()

            # 4. Загружаем и заполняем шаблон
            doc = DocxTemplate(template_path)
            doc.render(form_data)

            # 5. Генерируем имя файла
            output_filename = (
                f"закл_{self.zakl_number.toPlainText().strip()}_"
                f"рег-{self.reg_number.toPlainText().strip()}_"
                f"р-{self.p_rab.toPlainText().strip()}_"
                f"{self.rab_sreda.currentText()}_"
                f"кбХиммаш_{self.amount.value()}шт.docx"
            )

            # 6. Сохраняем документ
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

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

        else:
            print(f"Кол-во баллонов {amount} не совпадает с введёными зав. №№ {len(self.text)}")

        self.data.update({"tables": [{"num": str(i + 1)} for i in range(len(self.text))]})

    def s_min_min_calc(self):
        """Вычисляет минимальное значение из второго столбца и выводит в QPlainTextEdit"""
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

    def tverdost(self) -> None:
        """Расчёт твёрдости и подготовка данных для Word."""
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

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.show_message("Ошибка ввода", str(e), QMessageBox.Icon.Warning)

    def prochnost(self):
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

        except ValueError as e:
            print(f"Ошибка ввода: {e}")
            self.sigma.setPlainText("Ошибка")
            self.sigma_gidro.setPlainText("Ошибка")
            self.s_max_rasch.setPlainText("Ошибка")

    def ost_res(self):
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

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.a_corr.setPlainText("Ошибка")
            self.tk_years.setPlainText("Ошибка")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
