import random

s_min = float(input('Введите минимальную толщину: '))
s_max = float(input('Введите максимальную толщину: '))
tolshiny = {f's{i+1}': str(round(random.uniform(s_min, s_max), 2)) for i in range(24)}

print(tolshiny)
print(len(tolshiny))
print(type(tolshiny))
