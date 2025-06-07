import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel
import random


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("tolshiny_interface.ui", self)

        self.pushButton.clicked.connect(self.calculate)
        self.spinBox_amount.setValue(1)
        self.sMin.setPlainText("0")
        self.sMin_2.setPlainText("100")

        # Создаём контейнер для динамических полей
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)

        # Добавляем контейнер в QGroupBox
        self.groupBox.layout().addWidget(self.scroll_content)

        # Список для хранения динамически созданных полей
        self.result_fields = []

    def calculate(self):
        try:
            amount = self.spinBox_amount.value()
            s_min = float(self.sMin.toPlainText().replace(',', '.'))
            s_max = float(self.sMin_2.toPlainText().replace(',', '.'))

            if s_min >= s_max:
                raise ValueError("Smin должно быть меньше Smax")

            # Очищаем предыдущие поля
            for field in self.result_fields:
                field.deleteLater()
            self.result_fields.clear()

            # Создаём новые поля
            for i in range(amount):
                text_edit = QtWidgets.QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setMinimumHeight(80)

                # Генерация 20 случайных чисел
                numbers = [round(random.uniform(s_min, s_max), 1) for _ in range(20)]
                formatted = [str(num).replace('.', ',') for num in numbers]
                text_edit.setPlainText("; ".join(formatted))

                self.scroll_layout.addWidget(QLabel(f"Результат {i + 1}:"))
                self.scroll_layout.addWidget(text_edit)
                self.result_fields.append(text_edit)

            # Настраиваем прокрутку если полей больше 4
            if amount > 4:
                self.scroll_content.setMinimumHeight(200 * min(4, amount))
                self.verticalScrollBar.setVisible(True)
                self.scroll_area = QtWidgets.QScrollArea()
                self.scroll_area.setWidget(self.scroll_content)
                self.scroll_area.setWidgetResizable(True)
                self.groupBox.layout().addWidget(self.scroll_area)
            else:
                self.verticalScrollBar.setVisible(False)

        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Ошибка", str(e))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())