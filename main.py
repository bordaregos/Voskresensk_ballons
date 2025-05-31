from docxtpl import DocxTemplate
from funcs import ballon_generator
import csv

# Ввод данных о секции
place = input('Введите название участка: ')
reg_sec = input('Введите регистрационный номер секции: ')
g_v = input('Введите дату ввода в эксплуатацию: ')
sreda = input('Введите среду в баллонах: ')
gost = input('Введите ГОСТ: ')
kolvo = int(input('Введите количество баллонов в секции: '))

# Ввод заводских номеров баллонов.
ballony_zav_lst = [input(f'Введите зав.№ баллона {amount + 1}: ') for amount in range(kolvo)]

ballony, ballony_data_csv = ballon_generator(kolvo, ballony_zav_lst)

# Формируем контекст для шаблона.
context = {
    "place": place,
    "reg_sec": reg_sec,
    "g_v": g_v,
    "sreda": sreda,
    "gost": gost,
    "kolvo": kolvo,
    "ballony": ballony
}

columns = ['n', 'zav', 'p_rab', 'v', 'massa', 'g_i', 's_min']

with open(f"Баллоны_Csv/Баллоны_секция_рег№-{reg_sec}.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=columns, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    for row in ballony_data_csv:
        writer.writerow(row)

# Загружаем шаблон
doc = DocxTemplate("Баллоны_Шаблон.docx")
# Заполняем шаблон и сохраняем результат
doc.render(context)
# Сохраняем по регу секции.
doc.save(f"Баллоны_Word/Баллоны_секция_рег№-{reg_sec}.docx")

print(f"\nДокумент успешно сформирован и сохранен как 'Баллоны_секция_рег№-{reg_sec}.docx'")
print(f"\nДокумент успешно сформирован и сохранен как 'Баллоны_секция_рег№-{reg_sec}.csv'")

