class Scales:
    def __init__(self):
        self.left = 0
        self.right = 0

    def add_right(self, mass):
        self.right += mass

    def add_left(self, mass):
        self.left += mass

    def get_result(self):
        if self.left == self.right:
            return "Весы в равновесии"
        elif self.left > self.right:
            return "Левая чаша тяжелее"
        else:
            return "Правая чаша тяжелее"


scales = Scales()

scales.add_right(1)
scales.add_right(1)
scales.add_left(2)

print(scales.get_result())
