import random
import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QMessageBox, QLabel, QVBoxLayout, QWidget


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Динамическая загрузка UI-файла
        uic.loadUi('tolshiny_interface.ui', self)  # Убедитесь, что файл в правильном пути

        # Подключаем обработчик кнопки
        self.pushButton.clicked.connect(self.calculate)

        # Установка значений по умолчанию
        self.spinBox_amount.setValue(10)
        self.sMin.setPlainText("1.0")
        self.sMax.setPlainText("10.0")  # Убедитесь, что в UI это поле называется sMax

        # Инициализация контейнера для результатов
        self.init_results_container()

    def init_results_container(self):
        """Инициализация области для вывода результатов"""
        # Очищаем предыдущий контейнер, если он есть
        if hasattr(self, 'scroll_content'):
            self.scroll_content.deleteLater()

        # Создаём новый контейнер
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Создаём ScrollArea и настраиваем её
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)

        # Добавляем ScrollArea в группу
        self.groupBox.layout().addWidget(self.scroll_area)

        # Список для хранения динамических полей
        self.result_fields = []

    def calculate(self):
        try:
            # Получаем параметры
            amount = self.spinBox_amount.value()
            s_min = float(self.sMin.toPlainText().replace(',', '.'))
            s_max = float(self.sMax.toPlainText().replace(',', '.'))  # Проверьте имя поля!

            # Валидация
            if amount <= 0:
                raise ValueError("Количество должно быть больше 0")
            if s_min >= s_max:
                raise ValueError("Smin должно быть меньше Smax")

            # Очищаем предыдущие результаты
            self.clear_results()

            # Генерируем и отображаем результаты
            self.show_results(amount, s_min, s_max)

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def clear_results(self):
        """Очистка предыдущих результатов"""
        for field in self.result_fields:
            field.deleteLater()
        self.result_fields.clear()

    def show_results(self, amount, s_min, s_max):
        """Генерация и отображение результатов"""
        for i in range(amount):
            # Создаём заголовок
            label = QLabel(f"Результат {i + 1}:")
            self.scroll_layout.addWidget(label)
            self.result_fields.append(label)

            # Создаём поле с результатами
            text_edit = QtWidgets.QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setMinimumHeight(80)

            # Генерация случайных чисел
            numbers = [round(random.uniform(s_min, s_max), 1) for _ in range(20)]
            formatted = [str(num).replace('.', ',') for num in numbers]
            text_edit.setPlainText("; ".join(formatted))

            self.scroll_layout.addWidget(text_edit)
            self.result_fields.append(text_edit)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())