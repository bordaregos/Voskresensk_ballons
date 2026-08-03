# CLAUDE.md

Указания для Claude Code при работе с этим репозиторием.

## О проекте

Десктопное приложение (PyQt6) для формирования **заключений по техническому
освидетельствованию баллонов-воздухохранителей высокого давления**: оператор вводит
паспортные данные партии баллонов и результаты замеров, приложение выполняет расчёты
по ГОСТ (прочность, остаточный ресурс, овальность, твёрдость) и рендерит готовый
Word-документ по .docx-шаблону.

Домен русскоязычный, вся терминология в коде — транслитерация: `prochnost` (прочность),
`tverdost` (твёрдость), `ovalnost` (овальность), `tolshiny` (толщины), `zav_nums`
(заводские номера), `s_min` (минимальная толщина стенки), `p_rab` (рабочее давление).

## Запуск

```bash
python main.py
```

**Запускать строго из корня проекта.** `ui_logic.py:65` загружает интерфейс по
относительному пути `loadUi("src/ui/designer/main_window.ui", self)`, а `calculate()`
пишет в относительную папку `output/`. Из другого CWD приложение падает на старте.

```bash
pip install -r requirements.txt
```

Зависимости: `PyQt6`, `docxtpl` (Jinja2 поверх python-docx). `openpyxl` и `python-dateutil`
перечислены в `requirements.txt`, но нигде не импортируются. Целевой интерпретатор — Python 3.12.

Тестов, линтеров, CI, `pyproject.toml` и Makefile в проекте **нет**. Проверка — только
ручной прогон GUI.

## Архитектура: что исполняется на самом деле

Проект находится в середине незавершённого рефакторинга. Формально слоёв два, фактически
работающий код — один файл.

```
main.py                 точка входа: QApplication + MainWindow из ui_logic
ui_logic.py  (602 стр.) ВЕСЬ рабочий код: GUI, все расчёты, генерация Word
src/                    библиотечный слой; исполняется лишь малая часть
templates/*.docx        шаблоны Word с Jinja-плейсхолдерами
output/                 результат: .docx, а также .csv/.json проектов
```

Из `src/` в рантайме реально задействовано **только четыре вещи** (ленивые импорты,
чтобы разорвать цикл UI ↔ сервисы):

| Что | Откуда вызывается |
|---|---|
| `src.config.find_template()` | `ui_logic.py:195` |
| `src.ui.file_handler.FileHandler` | `ui_logic.py:89` |
| `src.services.importer.import_balloon_list_from_csv` | через `FileHandler` |
| `src.services.exporter.export_balloon_list_to_csv`, `src.models.project.Project` | через `FileHandler` |

Всё остальное в `src/` — **параллельная неиспользуемая реализация** того, что `ui_logic.py`
делает инлайном: `services/calculations.py`, `services/generator.py`, `models/balloon.py`,
`utils/validators.py`, `utils/date_formatter.py`, `services/exporter.export_report_to_json`,
`services/importer.import_project_from_json`. Правка формулы в `CalculationsService`
**не влияет на приложение** — формулы живут в `ui_logic.py`.

### Карта `src/`

| Файл | Назначение | Задействован |
|---|---|---|
| `src/config.py` | пути (`PROJECT_ROOT`, `TEMPLATES_DIR`, `OUTPUT_DIR`), `TEMPLATE_WORD`, константы ГОСТ, `find_template()` | да (частично) |
| `src/ui/file_handler.py` | Qt-диалоги импорта/экспорта, чтение и заполнение `table_ballons` | да |
| `src/services/importer.py` | чтение CSV/JSON (`BALLOON_HEADERS` — карта алиасов заголовков) | да (CSV) |
| `src/services/exporter.py` | запись CSV/JSON | да (CSV) |
| `src/models/project.py` | `Project` — сериализация сессии в JSON | да (`Project`) |
| `src/services/calculations.py` | `CalculationsService` — дубль всех формул | нет |
| `src/services/generator.py` | `DocumentGenerator` — дубль генерации .docx | нет |
| `src/models/balloon.py` | `Balloon`, `Report` (dataclass-модели) | нет |
| `src/utils/validators.py`, `src/utils/date_formatter.py` | валидация, русские даты | нет |

У `src/` нет `__init__.py` (namespace package), у подпакетов — есть. Внутри `models/`,
`services/`, `utils/` используются относительные импорты (`from ..config import ...`),
а `src/ui/file_handler.py` — абсолютные (`from src.services.importer import ...`).
Поэтому корень проекта обязан быть в `sys.path` — это делает `main.py:12`.

## Главный контракт проекта

```
objectName виджета в .ui  ==  ключ в self.data  ==  имя плейсхолдера {{ ... }} в шаблоне .docx
```

`get_form_data()` (`ui_logic.py:136`) проходит по спискам имён и складывает значение каждого
виджета в `self.data` под его же именем; этот словарь целиком уходит в `doc.render()`.
Разрыв цепочки в любом звене — молча пустое место в готовом документе.

`MainWindow` резолвит виджеты не по атрибутам сгенерированного класса, а через `findChild`
по спискам имён (`ui_logic.py:18-54`, метод `init_widgets()`):

| Список | Кол-во | Тип |
|---|---|---|
| `PLAIN_TEXT_EDIT_NAMES` | 49 | `QPlainTextEdit` |
| `COMBO_BOX_NAMES` | 4 | `QComboBox` |
| `DATE_EDIT_NAMES` | 5 | `QDateEdit` |
| `BUTTON_NAMES` | 12 | `QPushButton` |
| `SPIN_BOX_NAMES` | 1 | `QSpinBox` |
| `TABLE_WIDGET` | 2 | `QTableWidget` |

Количества точно совпадают с содержимым `main_window.ui`. Если имя есть в списке, но нет
в `.ui`, `init_widgets()` бросает `ValueError: Не найден QPlainTextEdit с именем ...` — окно
не откроется вовсе.

### Как добавить новое поле

1. В Qt Designer добавить виджет в `src/ui/designer/main_window.ui`, задать `objectName`.
2. Добавить это же имя в соответствующий список в `ui_logic.py:18-54`.
3. Добавить `{{ objectName }}` в `templates/Шаблон_финал.docx`.

Пересборка `pyuic` не нужна — `.ui` грузится в рантайме через `loadUi`.

## Обязательный порядок работы с интерфейсом

`self.data` накапливается инкрементально: каждая кнопка дописывает свои ключи. Это
неявная, но жёсткая последовательность — «Выгрузить в Word» раньше времени даёт документ
с пустыми циклами **без единой ошибки**.

| № | Кнопка | Метод | Что кладёт |
|---|---|---|---|
| 1 | Кол-во баллонов | `fill_table()` | `self.text` (зав. №№), `data["tables"]` |
| 2 | Smin-min | `s_min_min_calc()` | `s_min_lst`, поля `s_min_total`/`zav_s_min`, `data["min_year"]` |
| 3 | Расчитать толщины | `calc_thick()` | `data["ballony"]` (`s1`…`s20` на баллон) |
| 4 | Расчёт на прочность | `prochnost()` | `sigma`, `s_rasch`, `s_max_rasch`, `p_dop`, `data["p_rab_025/05/075"]` |
| 5 | Остаточный ресурс | `ost_res()` | `a_corr`, `tk_years`, `tk_just` |
| 6 | Расчёт овальности | `ovalnost_calc()` | `data["bal_oval"]` |
| 7 | Расчёт твёрдости | `tverdost()` | `data["hb_min"]`, `data["hb_max"]`, `data["tverdost_data"]` |
| 8 | Выгрузить в Word | `calculate()` | рендер и сохранение |

Шаги 2→3 и 4→5 связаны данными: `calc_thick()` читает `self.s_min_lst`, `ost_res()` читает
поле `s_max_rasch`, заполненное `prochnost()`.

Столбцы `table_ballons` захардкожены по индексам везде: `0` — зав. №, `1` — Smin,
`2` — год изготовления, `3` — масса. `table_thick`: `0` — зав. №, `1` — толщины.

## Расчёты (все — в `ui_logic.py`)

- `prochnost()` (`ui_logic.py:517`) — ГОСТ 34233:
  `sigma = min(Re/1.5, Rm/2.4)`, `sigma_gidro = Re/1.1`,
  `s_rasch = ((Dвн + 2·Sисп)·P) / (2·sigma + P)`, `s_max_rasch = max(s_rasch, s_rasch_gidro)`,
  `p_dop = (2·sigma·(Sисп−1)) / (Dвн + (Sисп−1))`, `p_pnevma_kgs = p_pnevma · 10.19`,
  плюс ступени пневмоиспытания 25/50/75 % от `p_rab`.
- `ost_res()` (`:561`) — скорость коррозии `a = (Sисп + C0 − Smin) / лет_эксплуатации`,
  ресурс `tk = (Smin − s_max_rasch) / a`, вердикт `"> 10 лет"` либо `"Пересчитать."`.
- `calc_thick()` (`:357`) — **генерирует** 20 замеров `random.uniform(s_min, s_min+2.0)`
  и принудительно подменяет минимум списка на фактический замеренный `s_min`.
- `ovalnost_calc()` (`:450`) — 3 замера, диаметры `randint(465, 466)` (захардкожено под
  корпус Ø466), `oval = 2·(dmax−dmin)/(dmax+dmin)·100`.
- `tverdost()` (`:477`) — `hb_min = round(2.7·Rm/10)`, `hb_max = hb_min + 20`, 20 значений HB.

Замеры толщин, диаметров и твёрдости **синтезируются `random`**, а не вводятся оператором.
Это осознанное поведение действующей программы — не «баг», который надо чинить попутно.

## Формат чисел

Русская десятичная запятая — сквозной контракт отображения. Любое значение при выводе
в виджет или шаблон проходит `str(x).replace('.', ',')`, при чтении обратно —
`float(text.replace(',', '.'))`. Новый код обязан соблюдать оба преобразования.

Даты читаются через русскую локаль: `QLocale('ru_RU').toString(date, 'dd MMMM yyyy')`
(`ui_logic.py:160`).

## Генерация документа

`calculate()` (`ui_logic.py:179`): проверка обязательных полей (`zakl_number`, `reg_number`,
`p_rab`) → `get_form_data()` → `find_template()` → `DocxTemplate(...).render(data)` → сохранение.

Имя файла собирается по шаблону:
`закл_{zakl_number}_рег-{reg_number}_р-{p_rab}_{rab_sreda}_кбХиммаш_{amount}шт.docx`

Шаблоны в `templates/`: `Шаблон_финал.docx` — рабочий (~24 МБ, 111 Jinja-тегов, циклы
`{% for i in ballony %}`, `{% for i in tables %}`, `{% for i in tverdost_data %}`,
`{% for j in bal_oval %}`); `Шаблон_баллоны_2.docx` — legacy; `Плейсхолдеры_шаблона.docx` —
справочник имён плейсхолдеров.

## Импорт/экспорт

`FileHandler` (`src/ui/file_handler.py`): CSV баллонов (разделитель `;`, кодировка
`utf-8-sig`, запятая как десятичный разделитель) и JSON проекта (`Project`).
`_fill_balloon_table_from_data()` содержит эвристики миграции старого формата JSON
(различает год/массу/толщину по величине значения — `>1900` год, `<100` толщина).

Загрузка проекта восстанавливает только значения виджетов и таблицу; `self.text` и
вычисленные ключи `self.data` не восстанавливаются — после «Открыть проект» цепочку
кнопок нужно прогнать заново.

## Конвенции кода

- Комментарии, докстринги, сообщения об ошибках и текст для пользователя — **по-русски**.
- Идентификаторы — английские либо транслитерация домена; сохраняйте существующий стиль.
- В `src/` — Google-style докстринги с русским текстом (`Args:`/`Returns:`/`Raises:`),
  аннотации типов, `@dataclass` для моделей, сервисы из `@staticmethod`, `pathlib.Path`.
- В `ui_logic.py` — короткие однострочные докстринги, аннотаций почти нет, `os.path`.
- Логирования нет: диагностика — `print()`, сообщения пользователю — `MainWindow.show_message()`
  (`QMessageBox`).
- PyQt6-синтаксис перечислений: `QMessageBox.Icon.Information`, `QMessageBox.StandardButton.Ok`.
- Именование кнопок непоследовательно (`pushButt_*` и `pushButton_*`), в UI-именах есть
  camelCase-наследие (`dataZakl`, `yearsOfExpluatation` — с опечаткой в оригинале). Не
  переименовывайте: имена завязаны на `.ui` и на плейсхолдеры шаблона.

## Ловушки и фактическое состояние

- **`src/` — в основном мёртвый код.** Меняя формулу, правьте `ui_logic.py`; дубль в
  `src/services/calculations.py` на поведение не влияет. Не считайте `README.md`
  описанием рабочего пути.
- **`README.md` устарел.** Описанных в нём `Dockerfile`, `docker-compose.yml`,
  `docker-start.sh`, юнит-тестов и `src/__init__.py` в проекте не существует.
- **Запуск только из корня** — относительный путь к `.ui` (`ui_logic.py:65`).
- **Порядок кнопок обязателен**, нарушение не диагностируется — документ просто выходит
  неполным.
- **`rm = 981` захардкожено** в `tverdost()` (`ui_logic.py:484`) с комментарием автора
  `# ЭТО ДОЛЖНО ПОЛУЧАТЬСЯ ИЗ ИНТЕРФЕЙСА!!!` — предел прочности не берётся из формы.
  Метод аннотирован `-> dict`, но на успешном пути возвращает `None`.
- **`BalloonProject.from_dict()` (`src/models/project.py:137`) сломан**: передаёт в
  `Balloon(...)` аргументы `min_thickness`/`max_thickness`, которые у `Balloon` объявлены
  read-only `@property`, а не полями → `TypeError`. Сейчас не вызывается (используется
  `Project`), но при попытке задействовать упадёт.
- **`.gitignore` игнорирует `templates/*.docx`** — шаблоны не в репозитории, свежий клон
  генерировать документы не сможет, пока файлы не положат вручную.
- **Состояние git не соответствует диску**: в индексе всё ещё старая раскладка (`common/`,
  `.ui` в корне), а `src/`, `main.py`, `README.md`, `requirements.txt`, `templates/`
  не отслеживаются. Перед коммитом уточняйте у пользователя, что именно версионировать.
- В `src/ui/designer/` четыре `.ui`, грузится только `main_window.ui`;
  `main_window_v1-1.ui` и `test1.ui` — устаревшие копии, `vodoprovod.ui` — заготовка
  от другого проекта.
- `src/services/importer.py` определяет собственный класс `ImportError`, перекрывающий
  встроенный. В `ui_logic.py` есть неиспользуемые импорты, включая бессмысленный
  `from PyQt6.uic.properties import QtWidgets` (строка 13).
