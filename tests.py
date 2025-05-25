from tkinter import *
import random


def random_tolshiny(event):
    try:
        s_min = float(s_minimum.get())
        s_max = float(s_maximum.get())
        a = int(amount.get())

        # Проверка ввода
        if s_min >= s_max:
            label['text'] = "Ошибка: мин. значение должно быть меньше макс."
            return
        if a <= 0:
            label['text'] = "Ошибка: количество должно быть > 0"
            return

        rows = 6
        cols = 4
        total = rows * cols

        # Если введено меньше значений, чем нужно для матрицы
        if a < total:
            label['text'] = f"Нужно минимум {total} значений\nВы ввели: {a}"
            return

        data = [round(random.uniform(s_min, s_max), 2) for _ in range(a)]
        matrix = [[data[i * cols + j] for j in range(cols)] for i in range(rows)]

        # Форматируем вывод матрицы
        matrix_text = "\n".join(["\t".join(map(str, row)) for row in matrix])
        label['text'] = matrix_text

    except ValueError:
        label['text'] = "Ошибка: введите корректные числа"


root = Tk()
root.title("Генератор матрицы толщин")

# Улучшенный интерфейс
Label(root, text="Минимальная толщина:").pack()
s_minimum = Entry(root)
s_minimum.insert(0, "1.0")  # Значение по умолчанию

Label(root, text="Максимальная толщина:").pack()
s_maximum = Entry(root)
s_maximum.insert(0, "10.0")  # Значение по умолчанию

Label(root, text="Количество значений:").pack()
amount = Entry(root)
amount.insert(0, "24")  # Значение по умолчанию (6x4=24)

button = Button(root, text='Сгенерировать матрицу')
label = Label(root, width=50, height=20, bg='black', fg='white',
              font=('Courier', 10), justify=LEFT)

button.bind('<Button-1>', random_tolshiny)

s_minimum.pack(fill=X, padx=5, pady=2)
s_maximum.pack(fill=X, padx=5, pady=2)
amount.pack(fill=X, padx=5, pady=2)
button.pack(pady=10)
label.pack(fill=BOTH, expand=True, padx=5, pady=5)

root.mainloop()
