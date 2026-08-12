"""Декларативная схема .docx-шаблона отчёта: состав и порядок разделов.

Схема НЕ описывает визуальное оформление (шрифты/цвета/логотип/поля
страницы) — это сознательно остаётся зоной ручной правки в Word после
генерации (см. src/services/template_generator.py). Схема описывает только
СОСТАВ и ПОРЯДОК разделов и то, какие Jinja-плейсхолдеры/циклы генератор
должен туда вписать, чтобы результат совпадал с контрактом
src/ui/widget_names_pipeline.py (и widget_names.py для баллонов).

Три уровня, из которых собирается итоговый документ:
  - организация (src/organization_config.py) — реквизиты экспертной
    организации, одни и те же для всех отчётов;
  - тип объекта (этот модуль, ReportSchema per equipment_type) — состав
    разделов, нормативная база, заголовок титула;
  - отчёт (src/ui/widget_names_*.py + self.data в MainWindow) — то, что
    оператор заполняет каждый раз заново через форму.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union


@dataclass(frozen=True)
class TitleConfig:
    """Титульный лист. document_title — единственное поле, которое обычно
    меняют целиком между запусками генератора (см. --title в
    scripts/template_tool.py) — например, "Отчёт по результатам
    технического диагностирования" сегодня, "Заключение экспертизы
    промышленной безопасности" завтра, без правки схемы."""
    document_title: str
    subtitle_fields: Sequence[str] = ()  # имена плейсхолдеров под заголовком (напр. "report_number")


@dataclass(frozen=True)
class StaticTextSection:
    """Раздел из чистого текста без плейсхолдеров -- вводная часть,
    преамбулы. Значения -- отправная точка для ручной правки под
    конкретную нормативную базу, не претендуют на точность "как есть"."""
    heading: Optional[str]
    paragraphs: Sequence[str]


@dataclass(frozen=True)
class FieldLabel:
    """Одна строка 'метка -- плейсхолдер' в FieldsTableSection."""
    label: str
    placeholder: str  # -> {{ placeholder }}, должен существовать в widget_names_*.py


@dataclass(frozen=True)
class FieldsTableSection:
    """Плоская таблица меток+значений (Таблица 3, 5, 6 в примере) -- каждая
    строка это своё поле формы, не элемент списка."""
    heading: Optional[str]
    rows: Sequence[FieldLabel]
    caption: Optional[str] = None  # "Таблица 3" -- подпись над таблицей


@dataclass(frozen=True)
class StaticFieldsTableSection:
    """Таблица реквизитов организации (1.2, Таблица 1) -- значения
    подставляются ОДИН РАЗ при генерации из OrganizationConfig, это НЕ
    Jinja-плейсхолдеры (оператор их не заполняет, форма про них не знает).

    rows -- пары (метка, имя атрибута OrganizationConfig), например
    ("Экспертная организация", "full_name"); генератор резолвит
    getattr(org_config, attr) при сборке документа.
    """
    heading: Optional[str]
    rows: Sequence[Tuple[str, str]]
    caption: Optional[str] = None


@dataclass(frozen=True)
class RepeatingTableSection:
    """Таблица-цикл -- {% for %}...{% endfor %}, оборачивающий целиком
    <w:tbl> (весь блок повторяется по разу на элемент списка -- см.
    подтверждённый на реальном Шаблон_финал.docx паттерн).

    Два режима адресации ячеек образцовой строки:
      - именованный (по умолчанию): list_field это list[dict], ячейки --
        {{ loop_var.attr }} для attr из row_cells (Таблица 1.3 специалисты,
        segments -- список с уже собранными dict-ами в self.data);
      - позиционный (positional=True): list_field это list[list] "как есть"
        из get_form_data() (см. TABLE_WIDGET generic-сборка в
        main_window.py) -- ячейки {{ loop_var[0] }}, {{ loop_var[1] }}, ...
        без необходимости заводить отдельную dict-конверсию под каждую
        такую таблицу (Таблица 4 рассмотренных документов, ВИК, УЗК).
    """
    heading: Optional[str]
    list_field: str
    loop_var: str
    header_cells: Sequence[str]
    row_cells: Sequence[str] = ()  # имена атрибутов (без "loop_var."), для именованного режима
    positional: bool = False
    caption: Optional[str] = None


Section = Union[
    StaticTextSection, FieldsTableSection, StaticFieldsTableSection, RepeatingTableSection,
]


@dataclass(frozen=True)
class ReportSchema:
    """Полная схема одного типа объекта -- вход для генератора."""
    equipment_type_id: str
    title: TitleConfig
    sections: Sequence[Section]  # порядок = порядок вставки в документ


# ---------------------------------------------------------------------------
# Схема трубопровода -- по составу разделов реального примера
# TD_720291_otd_214_1.docx (читан в этой же сессии) и полям
# src/ui/widget_names_pipeline.py.
# ---------------------------------------------------------------------------

PIPELINE_SCHEMA = ReportSchema(
    equipment_type_id="pipeline",
    title=TitleConfig(
        document_title="Отчёт по результатам технического диагностирования",
        subtitle_fields=[
            "report_number", "reg_number", "report_date",
            "report_title", "report_year",
        ],
    ),
    sections=[
        # 1.1 -- раньше статичный текст ("ЗАПОЛНИТЬ под конкретный объект"),
        # теперь редактируемое поле формы intro_text (предзаполнено тем же
        # текстом, что раньше был статичным, оператор правит под объект).
        FieldsTableSection(
            heading="1. Вводная часть",
            rows=[FieldLabel("1.1", "intro_text")],
        ),
        # 1.2 -- раньше StaticFieldsTableSection, выпекаемая из
        # OrganizationConfig при генерации заготовки (форма о ней не знала).
        # Теперь обычные поля формы (org_*), предзаполненные тем же текстом
        # в качестве значения по умолчанию, но редактируемые per-отчёт.
        FieldsTableSection(
            heading="1.2 Сведения об экспертной организации",
            caption="Таблица 1",
            rows=[
                FieldLabel("Экспертная организация", "org_name"),
                FieldLabel("Адрес", "org_address"),
                FieldLabel("Руководитель", "org_head"),
                FieldLabel("Телефон", "org_phone"),
                FieldLabel("Факс", "org_fax"),
                FieldLabel("Е-mail", "org_email"),
                FieldLabel("Официальный сайт организации", "org_website"),
                FieldLabel("Лицензия", "org_license"),
                FieldLabel("Кем выдана", "org_license_issuer"),
                FieldLabel("Номер и дата выдачи", "org_license_number_date"),
                FieldLabel("Вид деятельности", "org_activity_type"),
                FieldLabel(
                    "Вид работ, выполняемых в составе лицензируемого вида "
                    "деятельности",
                    "org_activity_scope",
                ),
            ],
        ),
        RepeatingTableSection(
            heading="1.3 Сведения о специалистах",
            caption="Таблица 2",
            list_field="specialists",
            loop_var="s",
            header_cells=["Должность", "ФИО", "Удостоверение"],
            row_cells=["position", "name", "cert_number"],
        ),
        FieldsTableSection(
            heading="3. Данные о заказчике",
            caption="Таблица 3",
            rows=[
                FieldLabel("Наименование организации", "customer_name"),
                FieldLabel("Сокращённое наименование", "customer_short_name"),
                FieldLabel("Организационно-правовая форма", "customer_legal_form"),
                FieldLabel("Юридический адрес", "customer_address"),
                FieldLabel("Адрес местонахождения", "customer_actual_address"),
                FieldLabel("Руководитель", "customer_head"),
                FieldLabel("Контактный телефон", "customer_phone"),
                FieldLabel("ИНН/КПП", "customer_inn"),
            ],
        ),
        FieldsTableSection(
            heading="4. Цель технического диагностирования",
            rows=[FieldLabel("Цель", "goal_text")],
        ),
        # 5. Сведения о рассмотренных документах -- универсальный растущий
        # список (та же table_reviewed_docs, что и в Приложении 2 ниже:
        # один и тот же список данных печатается в шаблоне дважды, в двух
        # разных местах документа -- это не баг, docxtpl поддерживает
        # несколько {% for %} по одному и тому же списку).
        RepeatingTableSection(
            heading="5. Сведения о рассмотренных в процессе технического "
                    "диагностирования документах",
            caption="Таблица 4",
            list_field="table_reviewed_docs",
            loop_var="doc",
            header_cells=["Документ", "Примечание"],
            positional=True,
        ),
        FieldsTableSection(
            heading="6. Краткая характеристика и назначение объекта "
                    "технического диагностирования",
            caption="Таблица 5",
            rows=[
                FieldLabel("Наименование", "obj_name"),
                FieldLabel("Назначение", "obj_naznach"),
                FieldLabel("Местонахождение", "obj_location"),
                FieldLabel("Смонтирован в (раздел 2)", "obj_department"),
                FieldLabel("Год изготовления", "year_made"),
                FieldLabel("Год ввода в эксплуатацию", "year_start"),
                FieldLabel("Срок эксплуатации, лет", "years_of_operation"),
                FieldLabel("Рабочая среда", "work_medium"),
                FieldLabel("№ проекта (конструкторской документации)", "project_docs"),
                FieldLabel("Давление, МПа", "p_rab_mpa"),
                FieldLabel("Давление, кгс/см2", "p_rab_kgs"),
                FieldLabel("Рабочая температура", "work_temp"),
                FieldLabel("Протяжённость, м", "length_m"),
                FieldLabel("Краткая характеристика конструкции", "construction_desc"),
            ],
        ),
        # Типоразмер/марка стали больше не отдельные поля -- вводятся один
        # раз в Таблице 6 (первая строка = представительный образец для
        # расчёта на прочность и протокола пневмоиспытаний, см.
        # main_window._first_pipe_material_value()); шаблон ссылается на
        # table_pipe_materials[0][3]/[4] напрямую -- validate_against_widget_names
        # такие Jinja-выражения внутри {{ }} не разбирает, это ожидаемо.
        RepeatingTableSection(
            heading="Сведения о трубах, из которых изготовлены элементы "
                    "трубопровода",
            caption="Таблица 6",
            list_field="table_pipe_materials",
            loop_var="item",
            header_cells=[
                "№ п/п", "Наименование элемента", "Количество, п.м.",
                "Типоразмер, мм", "Марка стали, ГОСТ или ТУ", "Трубы, ГОСТ или ТУ",
            ],
            positional=True,
        ),
        FieldsTableSection(
            heading="7. Результаты технического диагностирования",
            rows=[
                FieldLabel("7.1. Анализ технической документации", "result_71"),
                FieldLabel(
                    "7.2 Оценка соответствия трубопровода требованиям "
                    "промышленной безопасности при эксплуатации",
                    "result_72",
                ),
                FieldLabel("7.3 Осмотр, визуальный и измерительный контроль", "result_73"),
                FieldLabel("7.4 Измерение толщины стенки элементов трубопровода", "result_74"),
                FieldLabel("7.5. Ультразвуковой контроль сварных соединений (УЗК)", "result_75"),
                # 7.6 -- весь абзац (включая упоминание испытательного
                # давления) теперь целиком внутри result_76: плейсхолдеры не
                # вкладываются друг в друга, поэтому живой {{ pnevmo_pressure
                # }} внутри текста result_76 не сработал бы -- в дефолтном
                # тексте (pipeline_window.ui) вместо него пробел "P=______".
                # Значение-подсказку оператор видит рядом, в read-only поле
                # pnevmo_pressure_hint (зеркалит pnevmo_pressure через
                # MainWindow._update_pnevmo_pressure_hint) -- само это поле
                # не резолвится через widget_names_pipeline.py и в шаблон
                # .docx не попадает, это чисто UI-подсказка.
                FieldLabel(
                    "7.6. Испытание технологического трубопровода на прочность и плотность",
                    "result_76",
                ),
                FieldLabel(
                    "7.7 Поверочный расчёт на прочность и определение остаточного ресурса",
                    "result_77",
                ),
            ],
        ),
        RepeatingTableSection(
            heading="Приложение 1 — Программа технического диагностирования",
            list_field="table_program",
            loop_var="row",
            header_cells=["№ п/п", "Состав работ"],
            positional=True,
        ),
        FieldsTableSection(
            heading="Приложение 1 — Программу составил",
            rows=[
                FieldLabel("Должность", "programm_specialist_position"),
                FieldLabel("ФИО", "programm_specialist_name_initials"),
                FieldLabel("Удостоверение", "programm_specialist_cert_number"),
            ],
        ),
        RepeatingTableSection(
            heading="Приложение 2 — Сведения о рассмотренных документах",
            caption="Таблица 1",
            list_field="table_reviewed_docs",
            loop_var="doc",
            header_cells=["Наименование документа", "Примечание"],
            positional=True,
        ),
        FieldsTableSection(
            heading="Приложение 2 — Акт анализа технической и "
                    "эксплуатационной документации",
            rows=[
                FieldLabel("Дата проведения", "act2_date"),
                FieldLabel("Вводная часть акта", "act2_intro_text"),
                FieldLabel("Вывод", "act2_conclusion"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 2 — Анализ документации провёл",
            rows=[
                FieldLabel("Должность", "act2_specialist_position"),
                FieldLabel("ФИО", "act2_specialist_name_initials"),
                FieldLabel("Удостоверение", "act2_specialist_cert_number"),
            ],
        ),
        RepeatingTableSection(
            heading="Приложение 3 — Наружный осмотр трубопровода",
            list_field="table_vik_visual",
            loop_var="row",
            header_cells=["№ п/п", "Элемент", "Состояние"],
            positional=True,
        ),
        RepeatingTableSection(
            heading="Приложение 3 — Визуальный и измерительный контроль трубопровода",
            list_field="table_vik_measure",
            loop_var="row",
            header_cells=["№ п/п", "Элемент", "Состояние"],
            positional=True,
        ),
        FieldsTableSection(
            heading="Приложение 3 — Вывод",
            rows=[
                FieldLabel("Дата проведения", "vik_date"),
                FieldLabel("Руководящие документы", "vik_guidance_docs"),
                FieldLabel("Оборудование и инструменты", "vik_equipment"),
                FieldLabel("Вывод по результатам ВИК", "vik_conclusion"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 3 — Контроль провёл",
            rows=[
                FieldLabel("Должность", "vik_specialist_position"),
                FieldLabel("ФИО", "vik_specialist_name_initials"),
                FieldLabel("Удостоверение", "vik_specialist_cert_number"),
            ],
        ),
        RepeatingTableSection(
            heading="Приложение 4 — Протокол по результатам измерения "
                    "толщины стенки элементов трубопровода",
            list_field="segments",
            loop_var="item",
            header_cells=["№", "Тип элемента", "Типоразмер", "Замер, мм"],
            row_cells=["number", "element_type", "size", "thickness"],
        ),
        FieldsTableSection(
            heading="Приложение 4 — Оборудование и вывод",
            rows=[
                FieldLabel("Толщиномер (тип, зав. №)", "thick_device"),
                FieldLabel("Дата проведения", "thick_date"),
                FieldLabel("Руководящие документы", "thick_guidance_docs"),
                FieldLabel("Вывод", "thick_conclusion"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 4 — Измерение провёл",
            rows=[
                FieldLabel("Должность", "thick_specialist_position"),
                FieldLabel("ФИО", "thick_specialist_name_initials"),
                FieldLabel("Удостоверение", "thick_specialist_cert_number"),
            ],
        ),
        RepeatingTableSection(
            heading="Приложение 5 — Протокол по результатам дефектоскопии "
                    "сварных соединений методом ультразвукового контроля",
            list_field="table_uzk",
            loop_var="row",
            header_cells=["№", "Участок", "Типоразмер", "Дефекты", "Оценка"],
            positional=True,
        ),
        FieldsTableSection(
            heading="Приложение 5 — Оборудование и вывод",
            rows=[
                FieldLabel("Дефектоскоп (тип, зав. №)", "uzk_device"),
                FieldLabel("Дата проведения", "uzk_date"),
                FieldLabel("Руководящие документы", "uzk_guidance_docs"),
                FieldLabel("Оценка результатов контроля", "uzk_evaluation_text"),
                FieldLabel("Вывод", "uzk_conclusion"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 5 — Измерение провёл",
            rows=[
                FieldLabel("Должность", "uzk_specialist_position"),
                FieldLabel("ФИО", "uzk_specialist_name_initials"),
                FieldLabel("Удостоверение", "uzk_specialist_cert_number"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 6 — Поверочный расчёт на прочность и "
                    "остаточный ресурс",
            rows=[
                FieldLabel("Температура стенки tст, °C", "calc_temp"),
                FieldLabel("Давление Pр, МПа", "p_rab_mpa"),
                FieldLabel("Допускаемое напряжение [σ], МПа", "calc_sigma_allow"),
                FieldLabel("Коэффициент прочности шва φw", "calc_phi"),
                FieldLabel("Номинальный диаметр Da, мм", "calc_da"),
                FieldLabel("Номинальная толщина Sн, мм", "calc_sn"),
                FieldLabel("Расчётная толщина стенки Sr, мм", "calc_sr"),
                FieldLabel("Эксплуатационная прибавка C2, мм", "calc_c2"),
                FieldLabel("Минимально допустимая толщина [S], мм", "calc_s_reject"),
                FieldLabel("Фактическая минимальная толщина Sф, мм", "calc_sf"),
                FieldLabel("Допускаемое давление [P], МПа", "calc_p_allow"),
                FieldLabel("Условия прочности", "calc_strength_conclusion"),
                FieldLabel("Срок эксплуатации t, лет", "calc_years_operation"),
                FieldLabel("Коэффициент K", "calc_k"),
                FieldLabel("Скорость коррозии Аф, мм/год", "calc_corrosion_rate"),
                FieldLabel("Остаточный ресурс Тост, лет", "calc_remaining_years"),
                FieldLabel("Комментарий", "calc_residual_comment"),
                FieldLabel("Основание для расчёта", "calc_gost_basis"),
                FieldLabel("Обоснование методики оценки остаточного ресурса", "calc_residual_methodology_note"),
                FieldLabel("Формула остаточного ресурса (пояснение)", "calc_residual_formula_text"),
                FieldLabel("Формула скорости коррозии (пояснение)", "calc_corrosion_formula_text"),
                FieldLabel("Пояснение к расчётному примеру", "calc_worked_example_note"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 6 — Расчёт выполнил",
            rows=[
                FieldLabel("Должность", "calc_specialist_position"),
                FieldLabel("ФИО", "calc_specialist_name_initials"),
                FieldLabel("Удостоверение", "calc_specialist_cert_number"),
            ],
        ),
        FieldsTableSection(
            heading="Приложение 7 — Схема НК",
            rows=[FieldLabel("Схема НК", "nk_scheme_image")],
        ),
        FieldsTableSection(
            heading="Приложение 8 — Протокол пневмоиспытания с "
                    "акустико-эмиссионным контролем",
            rows=[
                FieldLabel("Дата проведения (п.1)", "pnevmo_date"),
                # pnevmo_date_numeric -- производное поле (не виджет), считается
                # в calculate() из pnevmo_date.date() в формате "дд.мм.гггг" --
                # эталон в п.1 Приложения 8 использует числовую дату, а не
                # текстовую ("15 августа 2024"), как везде в остальном отчёте.
                FieldLabel("Дата проведения (п.1, числом)", "pnevmo_date_numeric"),
                FieldLabel("Испытательное давление (п.4)", "pnevmo_pressure"),
                FieldLabel("Аппаратура АЭ, тип/зав. № (п.6)", "pnevmo_device"),
                FieldLabel("Число датчиков (п.7)", "pnevmo_sensors_count"),
                FieldLabel("Заводской номер (п.3)", "pnevmo_pipe_serial"),
                FieldLabel("Метод изготовления (п.3)", "pnevmo_manufacture_method"),
                FieldLabel("Размеры контролируемой зоны (п.3)", "pnevmo_control_zone_size"),
                FieldLabel("Рабочая температура при НК (п.3)", "pnevmo_ndt_temp_range"),
                FieldLabel("Состояние поверхности (п.3)", "pnevmo_surface_condition"),
                FieldLabel("Магнитные свойства (п.3)", "pnevmo_magnetic_properties"),
                FieldLabel("Рабочее тело испытания (п.4)", "pnevmo_test_medium"),
                FieldLabel("Температура объекта (п.4)", "pnevmo_object_temp"),
                FieldLabel("Температура окружающей среды (п.4)", "pnevmo_ambient_temp"),
                FieldLabel("Марка нагружающего оборудования (п.4)", "pnevmo_loading_equipment"),
                FieldLabel("Скорость нагружения (п.5)", "pnevmo_loading_rate"),
                FieldLabel("Изготовитель аппаратуры АЭ (п.6)", "pnevmo_device_manufacturer"),
                FieldLabel("Модель преобразователей (п.7)", "pnevmo_sensor_model"),
                FieldLabel("Контактная среда (п.8)", "pnevmo_contact_medium"),
                FieldLabel("Коэффициент основного усиления (п.9)", "pnevmo_gain"),
                FieldLabel("Уровень дискриминации (п.9)", "pnevmo_discrimination"),
                FieldLabel("Рабочая полоса частот (п.9)", "pnevmo_frequency_band"),
                FieldLabel("Изменение параметров в ходе испытаний (п.10)", "pnevmo_param_changes"),
                FieldLabel("Размещение ПАЭ (п.13)", "pnevmo_sensor_placement_note"),
            ],
        ),
        # Read-only зеркала пункта 3 (обязательное автозаполнение из уже
        # введённых где-то в форме значений -- см. MainWindow._update_pnevmo_mirrors())
        # НЕ входят сюда: это чисто UI-подсказки, самих ключей нет в
        # self.data, шаблон использует исходные obj_naznach/reg_number/...
        RepeatingTableSection(
            heading="Приложение 8 — Таблица 1, результаты контроля (п.11)",
            list_field="pnevmo_ae_results",
            loop_var="row",
            header_cells=["ПАЭ №", "Нагрузка", "пассивный", "активный",
                          "критически активный", "катастрофически активный"],
            row_cells=["paje_num", "nagruzka", "klass"],
            caption="Таблица 1",
        ),
        FieldsTableSection(
            heading="Приложение 8 — Рисунок 1, график нагружения (п.12)",
            rows=[FieldLabel("График нагружения", "pnevmo_graph_image")],
        ),
        RepeatingTableSection(
            heading="Приложение 8 — Этапы пневматического испытания трубопровода",
            list_field="table_pnevmo_stages",
            loop_var="row",
            header_cells=["№ этапа", "Давление, кгс/см2", "Время выдержки, мин"],
            positional=True,
            caption="Таблица 2",
        ),
        FieldsTableSection(
            heading="Приложение 8 — Контроль выполнил",
            rows=[
                FieldLabel("Должность", "pnevmo_specialist_position"),
                FieldLabel("ФИО", "pnevmo_specialist_name_initials"),
                FieldLabel("Удостоверение", "pnevmo_specialist_cert_number"),
            ],
        ),
        # Приложение 9 -- своя QGroupBox (ae_zakl_group) в UI, идёт следом за
        # pnevmo_group. Дата/объект/рег.номер в самом разделе шаблона исполь-
        # зуют исходные pnevmo_date/obj_naznach/reg_number (те же значения,
        # что и в Приложении 8); дата в блоке "УТВЕРЖДАЮ" -- report_date
        # (1. Титульный лист); "Место проведения контроля" -- obj_location
        # (1.2 Местонахождение). Ни для одного из них отдельных полей нет,
        # см. ae_zakl_*_display (read-only зеркала, MainWindow._update_pnevmo_mirrors()).
        # pnevmo_conclusion -- поле "Вывод" физически осталось в pnevmo_group
        # (см. Приложение 8 -- Контроль выполнил выше), в шаблон попадает
        # под "Вывод:" этого же раздела.
        FieldsTableSection(
            heading="Приложение 9 — Заключение по результатам АЭ-контроля",
            rows=[
                FieldLabel("Абзац 1 — выявленные источники АЭ", "ae_zakl_sources_text"),
                FieldLabel("Абзац 2 — оценка результатов", "ae_zakl_evaluation_text"),
                FieldLabel("Вывод", "pnevmo_conclusion"),
            ],
        ),
        # Таблица под заголовком (тот же приём, что и "Приложение 8 --
        # Контроль выполнил" выше) -- изначально была пропущена: заголовок
        # "Заключение составил:" в шаблоне сопровождается таблицей из двух
        # строк (должность/ФИО, ниже -- "(удостоверение № ...)"), а не
        # отдельным абзацем с табуляцией -- второй, лишний абзац под таблицей
        # удалён из шаблона как дублирующий остаток.
        FieldsTableSection(
            heading="Приложение 9 — Заключение составил",
            rows=[
                FieldLabel("Должность", "ae_zakl_specialist_position"),
                FieldLabel("ФИО", "ae_zakl_specialist_name_initials"),
                FieldLabel("Удостоверение", "ae_zakl_specialist_cert_number"),
            ],
        ),
        FieldsTableSection(
            heading="8. Выводы по результатам технического диагностирования",
            rows=[
                FieldLabel("8.1 Оценка технического состояния", "final_condition"),
                FieldLabel("8.2 Разрешённый срок дальнейшей эксплуатации, лет", "final_years_allowed"),
                # "5 (пять)" -- число прописью в скобках рядом с цифрой;
                # MainWindow.calculate() считает через number_to_words_ru()
                # (src/services/formatting.py), в форму отдельным виджетом
                # не выносится -- производное от final_years_allowed.
                FieldLabel("8.2 Срок прописью (производное поле)", "final_years_allowed_words"),
                FieldLabel("Дата, до которой разрешена эксплуатация (к 8.2)", "final_deadline_date"),
            ],
        ),
        # Таблица подписи после раздела 8 -- подписывает только ПЕРВЫЙ по
        # списку специалист (не цикл по всем, в отличие от 1.3/Таблица 2).
        # lead_specialist_* -- плоские поля, которые MainWindow.calculate()
        # достраивает из specialists[0] (см. main_window.py) -- отдельных
        # виджетов формы под них нет, тот же plainText "ФИО"/"Должность"/
        # "Удостоверение" из Таблицы 2, просто взятый по первой строке.
        FieldsTableSection(
            heading="Таблица подписи (после раздела 8)",
            rows=[
                FieldLabel("Должность", "lead_specialist_position"),
                FieldLabel("Подпись", "lead_specialist_name_initials"),
                FieldLabel("Удостоверение", "lead_specialist_cert_number"),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Схема баллонов -- минимальная (баллонный Шаблон_финал.docx уже существует
# и работает, схема нужна только для validate_against_widget_names /
# будущей регенерации, не для первого запуска generate_template).
# ---------------------------------------------------------------------------

BALLOON_SCHEMA = ReportSchema(
    equipment_type_id="balloon",
    title=TitleConfig(document_title="Заключение по техническому освидетельствованию"),
    sections=[
        FieldsTableSection(
            heading="Общие данные",
            rows=[
                FieldLabel("Заключение №", "zakl_number"),
                FieldLabel("Рег/уч №", "reg_number"),
                FieldLabel("Рабочее давление", "p_rab"),
            ],
        ),
    ],
)

SCHEMAS: Dict[str, ReportSchema] = {
    "pipeline": PIPELINE_SCHEMA,
    "balloon": BALLOON_SCHEMA,
}
