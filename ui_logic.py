import random
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPlainTextEdit, QComboBox,
                             QPushButton, QSpinBox, QTableWidgetItem, QLabel, QGroupBox, QVBoxLayout, QTableWidget,
                             QHeaderView)
from PyQt6.uic import loadUi
from typing import List, Dict, Union

from PyQt6.uic.properties import QtWidgets


class MainWindow(QMainWindow):
    # Списки для автоматической инициализации виджетов
    PLAIN_TEXT_EDIT_NAMES = [
        "zakl_number", "reg_number", "gost", "g_vvod", "dataZakl",
        "yearsOfExpluatation", "chertezh", "p_rasch", "p_rab", "s_isp",
        "length", "d_nar", "d_min", "d_max", "volume", "zav_nums", "reg_nums",
        "place", "zavod_name", "vladelec", "vik_date", "tolshTverdost_date",
        "ispRasch_date", "prodlEPB_date", "prodlTO_date", "dogContract",
        "pricaz_contora", "pricaz_vladelec", "s_min_total", "p_rab_MPa",
        "p_gidro", "p_pnevma", "d_vnutr", "pred_tek_min", "vrem_sopr_min",
        "sigma", "sigma_gidro", "s_rasch", "s_rasch_gidro", "s_max_rasch",
        "a_corr", "c0_plus_dop", "tk_years", "tk_just", "zav_s_min"
    ]

    COMBO_BOX_NAMES = [
        "construction", "material", "rab_sreda", "naznach"
    ]

    BUTTON_NAMES = [
        "pushButt_generateWord", "pushButt_generateCSV",
        "pushButt_amount", "pushButt_sMinMin", "pushButton_creatThickness",
        "pushButton_creatRasschProchn", "pushButton_creatOstRes",
        "pushButt_ovalnost", "pushButt_tverdost"
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
        self.text = None
        self.s_min_lst = None
        # self.sigma = QPlainTextEdit(self)
        # self.sigma_gidro = QPlainTextEdit(self)
        # self.s_max_rasch = self.s_max_rasch.toPlainText(self)

        loadUi("zakl_interface_v5-1_test.ui", self)

        # Автоматическая инициализация виджетов
        self.init_widgets()

        # Подключение сигналов
        self.pushButt_generateWord.clicked.connect(self.calculate)
        self.pushButt_generateCSV.clicked.connect(self.generate_csv)
        self.pushButt_amount.clicked.connect(self.fill_table)
        self.pushButt_sMinMin.clicked.connect(self.s_min_min_calc)
        self.pushButton_creatThickness.clicked.connect(self.calc_thick)
        self.pushButton_creatRasschProchn.clicked.connect(self.prochnost)
        self.pushButton_creatOstRes.clicked.connect(self.ost_res)
        self.pushButt_ovalnost.clicked.connect(self.ovalnost_calc)
        self.pushButt_tverdost.clicked.connect(self.tverdost)

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

        # Инициализация QTableWidget.
        for name in self.TABLE_WIDGET:
            widget = self.findChild(QTableWidget, name)
            if widget is None:
                raise ValueError(f"Не найден QTableWidget с именем {name}")
            setattr(self, name, widget)

    def get_form_data(self) -> Dict[str, Union[str, float]]:
        """Возвращает все данные формы в виде словаря"""
        # data = {}

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
        """Обработчик нажатия кнопки генерации Word"""
        form_data = self.get_form_data()
        print("Данные для Word:", form_data)
        # Здесь будет ваша логика генерации Word

    def generate_csv(self):
        """Обработчик нажатия кнопки генерации CSV"""
        form_data = self.get_form_data()
        print("Данные для CSV:", form_data)
        # Здесь будет ваша логика генерации CSV

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

    def s_min_min_calc(self):
        """Вычисляет минимальное значение из второго столбца и выводит в QPlainTextEdit"""
        self.s_min_lst = []
        table = self.table_ballons

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
            zav_s_min = self.text[self.s_min_lst.index(min(self.s_min_lst))]
            # Выводим результат в QPlainTextEdit
            self.s_min_total.setPlainText(s_min_tot)
            self.zav_s_min.setPlainText(zav_s_min)
        else:
            self.s_min_total.setPlainText("Нет данных")
            print("Ошибка: нет числовых данных для вычисления минимума")

    def calc_thick(self):
        """Функция - генератор толщин."""
        thick_table = self.table_thick
        amount = self.amount.value()

        # Устанавливаем высоту строки (вызовите это один раз при инициализации)
        thick_table.verticalHeader().setDefaultSectionSize(100)  # Подберите подходящее значение

        if len(self.text) == amount:
            thick_table.setRowCount(amount)

            for row, zav_num in enumerate(self.text):
                # Устанавливаем заводской номер в первый столбец
                item = QTableWidgetItem(zav_num)
                thick_table.setItem(row, 0, item)

                # Проверяем, что есть данные в self.s_min_lst
                if row < len(self.s_min_lst):
                    nums = self.s_min_lst[row]
                    num_max = nums + 2.0

                    # Генерируем 20 случайных значений
                    res_thick = [round(random.uniform(nums, num_max), 1) for _ in range(20)]

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
        for i in range(3):
            while True:
                d_min_rand = random.randint(465, 466)
                d_max_rand = random.randint(465, 466)
                if d_max_rand >= d_min_rand:
                    break

            oval = round(((2 * (d_max_rand - d_min_rand)) / (d_max_rand + d_min_rand)) * 100, 3)

            self.data.update({
                f"d1_{i}": f'{d_max_rand}',
                f"d2_{i}": f'{d_min_rand}',
                f"oval{i}": f'{oval}'
            })


    def tverdost(self) -> dict:
        """
        Расчёт твёрдости и подготовка данных для Word.
        Возвращает словарь с результатами в формате {плейсхолдер: значение}.
        """
        try:
            # 1. Получаем предел прочности (Rm) из интерфейса
            rm = 981

            # 2. Расчёт минимальной и максимальной твёрдости по ГОСТ
            hb_min = round(2.7 * (rm / 10), 0)  # Нижний предел (HB)
            hb_max = round(2.7 * (rm / 10) + 20, 0)  # Верхний предел (HB + допустимое отклонение)

            # 3. Генерация значений для каждого баллона (если нужно)
            tverdost_data = []
            for zav_num in range(1, self.amount.value() + 1):  # self.amount — QSpinBox
                hb_random = round(random.uniform(hb_min, hb_max), 0)
                tverdost_data.append({
                    "zav_num": zav_num,
                    "tverdost": hb_random
                })

            # 4. Формируем словарь для плейсхолдеров Word
            self.data.update({
                "hb_min": str(hb_min).replace(".", ","),  # Для локализации (запятая)
                "hb_max": str(hb_max).replace(".", ","),
                "tverdost_list": tverdost_data  # Список для цикла в Word
            })

        except ValueError as e:
            print(f"Ошибка ввода данных: {e}")
            return {
                "hb_min": "Ошибка",
                "hb_max": "Ошибка",
                "tverdost_list": []
            }

    def prochnost(self):
        try:
            # Получаем данные из полей
            pred_tek_min = float(self.pred_tek_min.toPlainText().replace(",", "."))
            vrem_sopr_min = float(self.vrem_sopr_min.toPlainText().replace(",", "."))
            p_rab_MPa = float(self.p_rab_MPa.toPlainText().replace(",", "."))
            p_gidro = float(self.p_gidro.toPlainText().replace(",", "."))
            d_vnutr = float(self.d_vnutr.toPlainText().replace(",", "."))
            s_isp = float(self.s_isp.toPlainText().replace(",", "."))

            # Расчёты
            sigma = round(1.0 * min(pred_tek_min / 1.5, vrem_sopr_min / 2.4), 1)
            sigma_gidro = round(pred_tek_min / 1.1, 1)

            s_rasch = round(((d_vnutr + (s_isp * 2)) * p_rab_MPa) / (2 * sigma + p_rab_MPa), 1)
            s_rasch_gidro = round(((d_vnutr + (s_isp * 2)) * p_gidro) / (2 * sigma_gidro + p_gidro), 1)
            s_max_rasch = max(s_rasch, s_rasch_gidro)

            # Вывод в QPlainTextEdit
            self.sigma.setPlainText(str(sigma).replace(".", ","))
            self.sigma_gidro.setPlainText(str(sigma_gidro).replace(".", ","))
            self.s_rasch.setPlainText(str(s_rasch).replace(".", ","))
            self.s_rasch_gidro.setPlainText(str(s_rasch_gidro).replace(".", ","))
            self.s_max_rasch.setPlainText(str(s_max_rasch).replace(".", ","))

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
