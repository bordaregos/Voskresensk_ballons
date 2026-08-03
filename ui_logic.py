import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QComboBox,
                             QPushButton, QSpinBox, QDateEdit, QTableWidgetItem, QTableWidget,
                             QMessageBox)
from PyQt6.QtCore import QDate, QLocale
from PyQt6.uic import loadUi
from typing import Dict, Union
from docxtpl import DocxTemplate

import os


class MainWindow(QMainWindow):
    # Списки для автоматической инициализации виджетов
    PLAIN_TEXT_EDIT_NAMES = [
        "zakl_number", "reg_number", "gost", "g_vvod", "dataZakl",
        "yearsOfExpluatation", "chertezh", "p_rasch", "p_rab", "s_isp",
        "length", "d_nar", "d_min", "d_max", "volume", "zav_nums", "reg_nums",
        "place", "zavod_name", "vladelec", "dogContract",
        "pricaz_contora", "pricaz_vladelec", "s_min_total", "p_rab_MPa",
        "p_gidro", "p_pnevma", "d_vnutr", "pred_tek_min", "vrem_sopr_min",
        "sigma", "sigma_gidro", "s_rasch", "s_rasch_gidro", "s_max_rasch",
        "a_corr", "c0_plus_dop", "tk_years", "tk_just", "zav_s_min",
        "obj_name", "prev_zakl", "prev_pg_am", "volume_total", "p_pnevma_kgs",
        "p_dop", "place_obj", "pasp_pg_amount", "gost_material"
    ]

    COMBO_BOX_NAMES = [
        "construction", "material", "rab_sreda", "naznach"
    ]

    DATE_EDIT_NAMES = [
        "vik_date", "tolshTverdost_date", "ispRasch_date", "prodlEPB_date", "prodlTO_date"
    ]

    BUTTON_NAMES = [
        "pushButt_generateWord", "pushButton_exportCSV",
        "pushButt_amount", "pushButt_sMinMin", "pushButton_creatThickness",
        "pushButton_creatRasschProchn", "pushButton_creatOstRes",
        "pushButt_ovalnost", "pushButt_tverdost",
        "pushButton_importCSV", "pushButton_saveProject",
        "pushButton_openProject"
    ]

    SPIN_BOX_NAMES = [
        "amount"
    ]

    TABLE_WIDGET = [
        "table_ballons", "table_thick"
    ]

    def __init__(self):
        """Инициализация конструктора класса. Пишем все атрибуты,
        что пригодятся нам по коду."""
        super().__init__()
        self.data = {}
        self.text = []
        self.s_min_lst = []
        self.file_handler = None

        loadUi("src/ui/designer/main_window.ui", self)

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
        from src.ui.file_handler import FileHandler
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
            from src.config import find_template
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
                    self.s_min_lst.append(float(item.text().replace(',', '.')))
                except ValueError:
                    print(f"Пропуск нечислового значения в строке {row}")
                    continue

                # Вычисляем минимум (если есть данные)
        if self.s_min_lst:
            s_min_tot = str(min(self.s_min_lst)).replace('.', ',')
            # Находим индекс минимального значения
            min_val = min(self.s_min_lst)
            min_index = self.s_min_lst.index(min_val)
            
            # Проверяем что индекс валиден
            if min_index < len(self.text):
                zav_s_min = self.text[min_index]
                # Выводим результат в QPlainTextEdit
                self.s_min_total.setPlainText(s_min_tot)
                self.zav_s_min.setPlainText(zav_s_min)
            else:
                print(f"Ошибка: индекс {min_index} выходит за пределы списка {len(self.text)}")
                self.s_min_total.setPlainText(s_min_tot)
                self.zav_s_min.setPlainText("Нет данных")
        else:
            self.s_min_total.setPlainText("Нет данных")
            self.zav_s_min.setPlainText("Нет данных")
            print("Ошибка: нет числовых данных для вычисления минимума")

        # Собираем все года из третьего столбца.
        for row in range(table.rowCount()):
            item = table.item(row, 2)
            if item is not None and item.text():
                try:
                    years_min_max_lst.append(int(item.text()))
                except ValueError:
                    print(f"Пропуск нечислового значения в строке {row}")
                    continue

        # Вычисляем минимальный и максимальный года изготовления (если есть данные).
        # Если года совпадают - выводим один год (минимальный).
        # И добавляем их в словарь data на вывод в ворд.
        if years_min_max_lst:
            min_year = min(years_min_max_lst)
            max_year = max(years_min_max_lst)

            if min_year != max_year:
                self.data.update({"min_year": f'{min_year} - {max_year} гг.'})
            else:
                self.data.update({"min_year": f'{min_year} г.'})
        else:
            self.data.update({"min_year": "Нет данных"})

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
                    num_max = nums + 2.0

                    # Генерируем 20 случайных значений
                    res_thick = [round(random.uniform(nums, num_max), 1) for _ in range(20)]

                    # Находим минимальное значение в списке
                    min_value = min(res_thick)
                    min_index = res_thick.index(min_value)

                    # Проверяем и заменяем если нужно
                    if min_value != nums:
                        res_thick[min_index] = nums

                    # Добавляем значения в словарь
                    for i, value in enumerate(res_thick, 1):
                        tolshiny_dict[f"s{i}"] = f"{value:.1f}".replace(".", ",")

                    # Форматируем в 5 строк по 4 числа
                    formatted_values = []
                    for i in range(0, 20, 4):
                        group = res_thick[i:i + 4]
                        line = " ".join(f"{x:.1f}".replace('.', ',') for x in group)
                        formatted_values.append(line)
                    res_thick_str = "\n".join(formatted_values)

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
            for i in range(3):
                while True:
                    d_min_rand = random.randint(465, 466)
                    d_max_rand = random.randint(465, 466)
                    if d_max_rand >= d_min_rand:
                        break

                oval = round(((2 * (d_max_rand - d_min_rand)) / (d_max_rand + d_min_rand)) * 100, 3)

                bal_oval_dict.update({
                    f"d_max_rand{i}": f'{d_max_rand}',
                    f"d_min_rand{i}": f'{d_min_rand}',
                    f"oval{i}": f'{oval}'
                })

            bal_oval.append(bal_oval_dict)
        self.data.update({"bal_oval": bal_oval})

    def tverdost(self) -> None:
        """Расчёт твёрдости и подготовка данных для Word."""
        try:
            # 1. Получаем предел прочности (Rm) из интерфейса — то же поле,
            # что уже вводится оператором для расчёта прочности в prochnost().
            rm = float(self.vrem_sopr_min.toPlainText().replace(",", "."))

            # 2. Расчёт минимальной и максимальной твёрдости по ГОСТ
            hb_min = round(2.7 * (rm / 10))  # Нижний предел (HB)
            hb_max = round(2.7 * (rm / 10) + 20)  # Верхний предел (HB + допустимое отклонение)

            # 3. Генерация значений для каждого баллона (если нужно)
            tverdost_data = []

            for zav in self.text:
                tverdost_dict = {
                    "zav": zav
                }
                for i in range(20):
                    hb_random = round(random.uniform(hb_min, hb_max))
                    tverdost_dict.update({f"hb_{i + 1}": f"{hb_random}"})
                tverdost_data.append(tverdost_dict)

            # 4. Формируем словарь для плейсхолдеров Word
            self.data.update({
                "hb_min": str(hb_min).replace(".", ","),  # Для локализации (запятая)
                "hb_max": str(hb_max).replace(".", ","),
                "tverdost_data": tverdost_data  # Список для цикла в Word
            })

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.show_message("Ошибка ввода", str(e), QMessageBox.Icon.Warning)

    def prochnost(self):
        try:
            # Получаем данные из полей
            pred_tek_min = float(self.pred_tek_min.toPlainText().replace(",", "."))
            vrem_sopr_min = float(self.vrem_sopr_min.toPlainText().replace(",", "."))
            p_rab_MPa = float(self.p_rab_MPa.toPlainText().replace(",", "."))
            p_gidro = float(self.p_gidro.toPlainText().replace(",", "."))
            d_vnutr = float(self.d_vnutr.toPlainText().replace(",", "."))
            s_isp = float(self.s_isp.toPlainText().replace(",", "."))
            p_pnevma = float(self.p_pnevma.toPlainText().replace(",", "."))

            # Расчёты
            sigma = round(1.0 * min(pred_tek_min / 1.5, vrem_sopr_min / 2.4), 1)
            sigma_gidro = round(pred_tek_min / 1.1, 1)
            p_pnevma_kgs = round(p_pnevma * 10.19)

            s_rasch = round(((d_vnutr + (s_isp * 2)) * p_rab_MPa) / (2 * sigma + p_rab_MPa), 1)
            s_rasch_gidro = round(((d_vnutr + (s_isp * 2)) * p_gidro) / (2 * sigma_gidro + p_gidro), 1)
            s_max_rasch = max(s_rasch, s_rasch_gidro)

            # Вычисляем внутреннее избыточное давление.
            p_dop = str(round((2 * sigma * (s_isp - 1)) / (d_vnutr + (s_isp - 1)), 1)).replace(".", ",")

            # Вычисляем давление для этапов пневматического испытания.
            p_rab = float(self.p_rab.toPlainText().replace(",", "."))
            self.data.update({"p_rab_025": f"{round(p_rab * 0.25)}"})
            self.data.update({"p_rab_05": f"{round(p_rab * 0.5)}"})
            self.data.update({"p_rab_075": f"{round(p_rab * 0.75)}"})

            # Вывод в QPlainTextEdit
            self.sigma.setPlainText(str(sigma).replace(".", ","))
            self.sigma_gidro.setPlainText(str(sigma_gidro).replace(".", ","))
            self.s_rasch.setPlainText(str(s_rasch).replace(".", ","))
            self.s_rasch_gidro.setPlainText(str(s_rasch_gidro).replace(".", ","))
            self.s_max_rasch.setPlainText(str(s_max_rasch).replace(".", ","))
            self.p_pnevma_kgs.setPlainText(str(p_pnevma_kgs).replace(".", ","))
            self.p_dop.setPlainText(p_dop)

        except ValueError as e:
            print(f"Ошибка ввода: {e}")
            self.sigma.setPlainText("Ошибка")
            self.sigma_gidro.setPlainText("Ошибка")
            self.s_max_rasch.setPlainText("Ошибка")

    def ost_res(self):
        try:
            # Получаем данные из полей с проверкой на пустые значения
            s_isp = float(self.s_isp.toPlainText().replace(",", ".")) if self.s_isp.toPlainText() else 0.0
            c0_plus_dop = float(
                self.c0_plus_dop.toPlainText().replace(",", ".")) if self.c0_plus_dop.toPlainText() else 0.0
            s_min_total = float(
                self.s_min_total.toPlainText().replace(",", ".")) if self.s_min_total.toPlainText() else 0.0
            yearsOfExpluatation = float(self.yearsOfExpluatation.toPlainText().replace(",",
                                                                                       ".")) if self.yearsOfExpluatation.toPlainText() else 0.0

            # Проверка деления на ноль
            if yearsOfExpluatation == 0:
                raise ValueError("Срок эксплуатации не может быть нулевым")

            # Расчёты
            a = round((s_isp + c0_plus_dop - s_min_total) / yearsOfExpluatation, 3)

            # Получаем s_max_rasch (если это QPlainTextEdit)
            s_max_rasch = float(self.s_max_rasch.toPlainText().replace(",", ".")) if hasattr(self,
                                                                                             's_max_rasch') and self.s_max_rasch.toPlainText() else 0.0

            tk = round((s_min_total - s_max_rasch) / a, 0) if a != 0 else 0

            tk_j = "> 10 лет" if tk > 10 else "Пересчитать."

            # Вывод результатов
            self.a_corr.setPlainText(str(a).replace(".", ","))
            self.tk_years.setPlainText(str(tk).replace(".", ","))
            self.tk_just.setPlainText(tk_j)

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            self.a_corr.setPlainText("Ошибка")
            self.tk_years.setPlainText("Ошибка")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
