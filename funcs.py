import random

# Словарь с правильными склонениями месяцев
MONTH_NAMES = {
    1: "января", 2: "февраля", 3: "марта",
    4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября",
    10: "октября", 11: "ноября", 12: "декабря"
}


def format_russian_date(date_str):
    try:
        day, month, year = map(int, date_str.split('.'))
        return f'"{day}" {MONTH_NAMES[month]} {year}г.'
    except (ValueError, KeyError):
        return None


def ballon_generator(kolvo, ballony_zav_lst, g_i):
    """Функция - генератор данных по баллонам"""

    # Список для сбора данных по баллонам.
    ballony = []
    ballony_data_csv = []
    s_min_total_lst = []

    for i in range(kolvo):
        print(f'\nВвод данных для баллона №{ballony_zav_lst[i]}:')
        # Собираем мин толщину и макс толщину и генерим необходимое кол - во замеров.
        s_min = float(input('Введите минимальную толщину: '))
        s_max = float(input('Введите максимальную толщину: '))
        g_i_bal = g_i[i]

        tolshiny = {f's{i + 1}': round(random.uniform(s_min, s_max), 1) for i in range(20)}

        # Находим мимальное значение в словаре.
        min_key = min(tolshiny, key=tolshiny.get)

        # Проверяем и заменяем если нужно
        if tolshiny[min_key] != s_min:
            tolshiny[min_key] = s_min

        # Меняем в словаре точки на запятые.
        tolshiny_str = {k: str(v).replace('.', ',') for k, v in tolshiny.items()}

        s_min_total_lst.append(s_min)

        balloon_data = {
            # "n": f'{i + 1}',
            "zav": ballony_zav_lst[i],
            "p_rab": "400",
            "v": "400",
            "massa": "1050",
            "s_min": str(s_min).replace('.', ','),
            "g_i_bal": f"{g_i_bal}"
        }

        ballony_data_csv.append(balloon_data)

        # Объединяем словари данных и толщин по баллону.
        balloon_data = balloon_data | tolshiny_str
        # Закидываем безобразие сие в список данных баллонов.
        ballony.append(balloon_data)
    return ballony, ballony_data_csv, s_min_total_lst


def ovalnost(ballony_lst, dmin, dmax):
    """не доделал..."""

    # Проверка на одинаковые значения.
    if dmin == dmax:
        return 0.0

    bal_oval = []

    for zav in ballony_lst:
        bal_oval_dict = {
            "z_n": zav
        }
        for i in range(3):
            while True:
                d_min_rand = random.randint(dmin, dmax)
                d_max_rand = random.randint(dmin, dmax)
                if d_max_rand >= d_min_rand:
                    break

            oval = round(((2 * (d_max_rand - d_min_rand)) / (d_max_rand + d_min_rand)) * 100, 3)

            bal_oval_dict.update({
                f"d_max_rand{i}": f'{d_max_rand}',
                f"d_min_rand{i}": f'{d_min_rand}',
                f"oval{i}": f'{oval}'
            })

        bal_oval.append(bal_oval_dict)

    return bal_oval


def tverdost():
    pass
