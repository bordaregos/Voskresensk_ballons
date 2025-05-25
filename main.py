from docxtpl import DocxTemplate
import random

# Загружаем шаблон
doc = DocxTemplate("Баллоны_Шаблон.docx")

# Ввод данных о секции
place = input('Введите название участка: ')
reg_sec = input('Введите регистрационный номер секции: ')
g_v = input('Введите дату ввода в эксплуатацию: ')
sreda = input('Введите среду в баллонах: ')
gost = input('Введите ГОСТ: ')
kolvo = int(input('Введите количество баллонов в секции: '))

# Ввод заводских номеров баллонов.
ballony_zav_lst = [input(f'Введите зав.№ баллона {amount + 1}: ') for amount in range(kolvo)]

# Генерируем толщины.
s_min = float(input('Введите минимальную толщину: '))
s_max = float(input('Введите максимальную толщину: '))
tolshiny = {f's{i+1}': str(round(random.uniform(s_min, s_max), 2)) for i in range(24)}

# Список для сбора данных по баллонам.
ballony = []

for i in range(kolvo):
    print(f'\nВвод данных для баллона №{ballony_zav_lst[i]}:')
    balloon_data = {
        "n": f'{i + 1}',
        "zav": ballony_zav_lst[i],
        "p_rab": "400",
        "v": input('Объем (V), м3: '),
        "massa": input('Масса, кг: '),
        "g_i": input('Дата изготовления (Г.и.): ')
    }
    ballony.append(balloon_data)

# ballony.append(tolshiny)
# Формируем контекст для шаблона
context = {
    "place": place,
    "reg_sec": reg_sec,
    "g_v": g_v,
    "sreda": sreda,
    "gost": gost,
    "kolvo": kolvo,
    "ballony": ballony,
    "s_min": s_min
}

context = context | tolshiny

# Заполняем шаблон и сохраняем результат
doc.render(context)
doc.save("Баллоны_Готовые.docx")

print("\nДокумент успешно сформирован и сохранен как 'Баллоны_Готовые.docx'")
