import random


def ballon_generator(kolvo, ballony_zav_lst):
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
        tolshiny = {f's{i + 1}': str(round(random.uniform(s_min, s_max), 1)) for i in range(20)}
        s_min_total_lst.append(s_min)

        balloon_data = {
            "n": f'{i + 1}',
            "zav": ballony_zav_lst[i],
            "p_rab": "400",
            "v": "400",
            "massa": "1050",
            "s_min": f'{s_min}'
        }

        ballony_data_csv.append(balloon_data)

        # Объединяем словари данных и толщин по баллону.
        balloon_data = balloon_data | tolshiny
        # Закидываем безобразие сие в список данных баллонов.
        ballony.append(balloon_data)
    return ballony, ballony_data_csv, s_min_total_lst
