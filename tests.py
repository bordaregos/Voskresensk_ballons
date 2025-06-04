import random


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
                d_min_rand = random.uniform(dmin, dmax)
                d_max_rand = random.uniform(dmin, dmax)
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


kolvo = int(input('Введите количество баллонов в секции: '))
d_min = int(input('Введите минимальный диаметр: '))
d_max = int(input('Введите максимальный диаметр: '))

ballony_zav_lst = [input(f'Введите зав.№ баллона {amount + 1}: ') for amount in range(kolvo)]

print(*ovalnost(ballony_zav_lst, d_min, d_max), sep='\n')
