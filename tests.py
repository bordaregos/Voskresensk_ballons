from itertools import cycle


class Gun:
    def __init__(self):
        self.count = 0
        self.sounds = cycle(("pif", "paf"))

    def shoot(self):
        print(next(self.sounds))

    def shoots_count(self):
        print(self.count)

    def shoots_reset(self):
        delattr(self.shoot(), "0")
