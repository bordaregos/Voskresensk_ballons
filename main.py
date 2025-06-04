from docxtpl import DocxTemplate
from funcs import ballon_generator, format_russian_date, ovalnost
import csv
import locale

# Русская локализация даты.
locale.setlocale(locale.LC_TIME, 'russian')

# Ввод данных о секции
place = input('Введите название участка: ')
reg_sec = input('Введите регистрационный номер секции: ')
g_v = input('Введите дату ввода в эксплуатацию: ')
sreda = input('Введите среду в баллонах: ')
gost = input('Введите ГОСТ: ')
kolvo = int(input('Введите количество баллонов в секции: '))
chert = input('Введите № чертежа: ')
length = input('Введите длину баллона: ')
d_nar = input('Введите наружный диаметр: ')
d_min = int(input('Введите минимальный диаметр: '))
d_max = int(input('Введите максимальный диаметр: '))
control_date = input('Введите дату контроля (в формате ДД.ММ.ГГГГ): ')

# Забираем из функции отформатированную дату.
formatted_date = format_russian_date(control_date)

# Ввод заводских номеров баллонов.
ballony_zav_lst = [input(f'Введите зав.№ баллона {amount + 1}: ') for amount in range(kolvo)]

# Ввод годов изготовления баллонов. Мин и макс года.
g_i = [int(input(f'Введите г.и. баллона {amount + 1}: ')) for amount in range(kolvo)]
g_i_min, g_i_max = min(g_i), max(g_i)

# Готовим данные по овальности для шаблона.
bal_oval = ovalnost(ballony_zav_lst, d_min, d_max)

# Вытаскиваем данные для csv.
ballony, ballony_data_csv, s_min_total_lst = ballon_generator(kolvo, ballony_zav_lst, g_i)

# Нижний регистр среды для назначения баллона.
sreda_lower = sreda.lower()

# Формируем контекст для шаблона.
context = {
    "place": place,
    "reg_sec": reg_sec,
    "g_v": g_v,
    "sreda": sreda,
    "sreda_lower": sreda_lower,
    "gost": gost,
    "kolvo": kolvo,
    "ballony": ballony,
    "bal_oval": bal_oval,
    "chert": chert,
    "length": length,
    "d_nar": d_nar,
    "zav_nums": ', '.join(ballony_zav_lst),
    "g_i_min": g_i_min,
    "g_i_max": g_i_max,
    "control_date": formatted_date,
    "s_min_total": str(min(s_min_total_lst)).replace('.', ','),
    "v": "400",
    "p_rab": "400"
}

# Словарь для замены наименований ячеек.
renamed_columns = {
    # 'n': '№',
    'zav': 'зав№',
    'p_rab': 'Рраб',
    'v': 'объём',
    'massa': 'масса',
    'g_i_bal': 'г.и.',
    's_min': 'Sмин'
}

# Сохраняем документ в csv.
with open(f"Баллоны_Csv/Баллоны_секция_рег№-{reg_sec}.csv", "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=renamed_columns.values(), delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    for row in ballony_data_csv:
        renamed_row = {renamed_columns[key]: value for key, value in row.items()}
        writer.writerow(renamed_row)

# Загружаем шаблон
doc = DocxTemplate("Шаблон_баллоны_2.docx")
# Заполняем шаблон и сохраняем результат
doc.render(context)
# Сохраняем по регу секции.
doc.save(f"Баллоны_Word/Баллоны_секция_рег№-{reg_sec}.docx")

print(f"\nДокумент успешно сформирован и сохранен как 'Баллоны_секция_рег№-{reg_sec}.docx'")
print(f"Документ успешно сформирован и сохранен как 'Баллоны_секция_рег№-{reg_sec}.csv'")
