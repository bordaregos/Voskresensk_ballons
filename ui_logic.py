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
        "pricaz_contora", "pricaz_vladelec", "s_min_total"
    ]

    COMBO_BOX_NAMES = [
        "construction", "material", "rab_sreda", "naznach"
    ]

    BUTTON_NAMES = [
        "pushButt_generateWord", "pushButt_generateCSV",
        "pushButt_amount", "pushButt_sMinMin", "pushButton_creatThickness"
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
        self.text = None
        self.s_min_lst = None
        loadUi("zakl_interface_v5-1_test.ui", self)

        # Автоматическая инициализация виджетов
        self.init_widgets()

        # Подключение сигналов
        self.pushButt_generateWord.clicked.connect(self.calculate)
        self.pushButt_generateCSV.clicked.connect(self.generate_csv)
        self.pushButt_amount.clicked.connect(self.fill_table)
        self.pushButt_sMinMin.clicked.connect(self.s_min_min_calc)
        self.pushButton_creatThickness.clicked.connect(self.calc_thick)

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

    def get_form_data(self) -> Dict[str, Union[str, float]]:
        """Возвращает все данные формы в виде словаря"""
        data = {}

        # Получаем текст из всех QPlainTextEdit
        for name in self.PLAIN_TEXT_EDIT_NAMES:
            widget = getattr(self, name)
            data[name] = widget.toPlainText()

        # Получаем текущий текст из QComboBox
        for name in self.COMBO_BOX_NAMES:
            widget = getattr(self, name)
            data[name] = widget.currentText()

        return data

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
            # Выводим результат в QPlainTextEdit
            self.s_min_total.setPlainText(s_min_tot)
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


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
