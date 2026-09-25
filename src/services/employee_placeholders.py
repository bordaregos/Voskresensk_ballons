"""Готовые представления данных сотрудника для «Редактора сотрудника»
конструктора документов (ПКМ на чипе плейсхолдера -> «Создать сотрудника»,
см. src/ui/employee_placeholder_dialog.py и src/ui/main_window.py,
_show_chip_context_menu()/_render_slot_fields()).

Чистые функции, без Qt -- тот же принцип, что и у
src/services/calculations.py/formula_engine.py. EMPLOYEE_DATA_FIELDS --
статические представления, общие для всех сотрудников; employee_chip_fields()
поверх неё добавляет динамическую часть (своя пара чипов на каждое
удостоверение, см. её докстринг) -- вместе они общий источник и для диалога
(какие чипы предложить выбрать), и для рендера реквизитов (каждое
отмеченное представление -- отдельное поле, см. MainWindow._create_employee_
from_chip_menu()/employee_data_value())."""

from typing import Callable, List, NamedTuple

from ..models.employee import Employee


def fio_short(full_name: str) -> str:
    """"Клименко Алексей Александрович" -> "Клименко А. А." -- фамилия
    полностью, имя и отчество сокращаются до инициала с точкой. Без
    отчества (два слова) даёт "Клименко А.". Пустая строка на пустом/
    состоящем из пробелов имени."""
    parts = full_name.split()
    if not parts:
        return ""
    surname, rest = parts[0], parts[1:]
    initials = [f"{part[0].upper()}." for part in rest]
    return surname if not initials else surname + " " + " ".join(initials)


def format_certificate(certificate) -> str:
    """Текст одного удостоверения для отображения/плейсхолдера -- сам текст
    записи плюс срок действия, если он указан ("Удостоверение № ... от ... —
    до 25.02.2029"). Без даты -- просто текст, как и раньше (до появления
    Certificate.expires)."""
    if not certificate.expires:
        return certificate.text
    return f"{certificate.text} — до {certificate.expires}"


class EmployeeDataField(NamedTuple):
    key: str
    label: str
    value: Callable[[Employee], str]


# Ключ поля-клише -- вынесен в константу (а не голая строка "kleishe"
# россыпью по коду): в отличие от остальных представлений, клише -- не
# текст, а картинка (Employee.kleishe_filename), и MainWindow сверяется
# именно с этим ключом (не с employee_data_value()) в НЕСКОЛЬКИХ местах,
# где готовое текстовое значение этого поля не годится -- см.
# src/ui/main_window.py: _render_slot_fields()/_build_employee_group_row()
# (виджет реквизита -- readOnly-подсказка, а не текст, иначе в документ
# буквально уехала бы строка "Есть клише"/"Без клише"), get_form_data()
# (вместо значения -- маркер, тот же приём, что у field_tables) и
# _splice_kleishe_placeholders() (маркер после tpl.render() меняется на
# настоящую .docx-картинку через python-docx Run.add_picture(), тем же
# принципом, что и _splice_table_placeholders()/_build_table_element()
# для таблиц). employee_data_value() ниже по-прежнему возвращает ДЛЯ ЭТОГО
# КЛЮЧА обычную строку -- статус "есть/нет клише" -- но она используется
# только для превью чипа в EmployeePlaceholderDialog (и как запасной текст
# плашки в _build_employee_group_row(), которая для этого ключа его не
# использует, см. её докстринг) -- НИКОГДА не как то, что реально уходит в
# документ.
KLEISHE_FIELD_KEY = "kleishe"

# Порядок -- тот же, что в докстрине модуля и в docs/design/
# редактор_сотрудника.html (CHIP_DEFS): полное ФИО, фамилия с инициалами,
# должность, квалификация, уровень квалификации, удостоверения, срок
# действия. certificates_expires -- срок действия удостоверений отдельным
# готовым полем (введён в employee_certificate_expires, см.
# EmployeesTabController), а не только вклеенным в текст "certificates" --
# по аналогии с остальными полями формы, каждое из которых доступно и как
# самостоятельный чип. kleishe -- новее остальных (в мокапе редактор_
# сотрудника.html его нет), добавлен в конец списка, а не по смыслу между
# другими полями, чтобы не переставлять уже сохранённые пользователем
# наборы отмеченных ключей (EmployeePlaceholderDialog читает существующую
# привязку по key, не по позиции, так что порядок тут визуальный, не
# структурный -- но менять его без необходимости всё равно незачем).
#
# "certificates" здесь -- ГОЛЫЙ c.text, БЕЗ format_certificate() (который
# приписывает "— до {expires}"): раз срок действия теперь свой отдельный
# чип (certificates_expires), совмещать оба представления в одном поле
# нельзя -- оператор, вставивший в документ оба чипа рядом, иначе увидел
# бы дату дважды ("№ ... от ... — до 20.12.2029" и following "20.12.2029").
# format_certificate() (с датой внутри одной строки) остаётся как есть для
# мест, где отдельного поля "Срок действия" нет и не будет -- table_employees
# (справочник, см. EmployeesTabController._refresh_table()) и базовый
# (нередактированный) рендер элемента списка удостоверений
# (_append_certificate_item()/_wrap_certificate_item() в employees_tab.py).
EMPLOYEE_DATA_FIELDS: List[EmployeeDataField] = [
    EmployeeDataField("fio_full", "Полное ФИО", lambda e: e.full_name),
    EmployeeDataField("fio_short", "Фамилия И.О.", lambda e: fio_short(e.full_name)),
    EmployeeDataField("position", "Должность", lambda e: e.position),
    EmployeeDataField("qualification", "Квалификация", lambda e: e.qualification),
    EmployeeDataField("qualification_level", "Уровень квалификации", lambda e: e.qualification_level),
    EmployeeDataField(
        "certificates", "Удостоверения",
        lambda e: "; ".join(c.text for c in e.certificates),
    ),
    EmployeeDataField(
        "certificates_expires", "Срок действия",
        lambda e: "; ".join(c.expires for c in e.certificates if c.expires),
    ),
    EmployeeDataField(
        KLEISHE_FIELD_KEY, "Клише",
        lambda e: "Есть клише" if e.kleishe_filename else "Без клише",
    ),
]

_FIELDS_BY_KEY = {field.key: field for field in EMPLOYEE_DATA_FIELDS}

# Префиксы составных ключей -- одна запись справочника (Certificate) на
# каждый индекс, см. employee_certificate_fields()/employee_data_value()
# ниже. Формат ключа -- "certificates:<индекс>"/"certificates_expires:<индекс>",
# индекс -- позиция в employee.certificates (0-based).
_CERTIFICATE_KEY_PREFIXES = ("certificates", "certificates_expires")


def employee_certificate_fields(employee: Employee) -> List[EmployeeDataField]:
    """По ДВА готовых представления (номер удостоверения + срок действия)
    на КАЖДУЮ запись employee.certificates -- в разделе «Сотрудники»
    удостоверения и так вводятся отдельными записями (список, каждая
    запись -- своя строка/пара полей, см. EmployeesTabController), а
    статические "certificates"/"certificates_expires" в EMPLOYEE_DATA_FIELDS
    выше схлопывают их ВСЕ через "; " в одно значение -- оператор,
    ожидавший отдельный чип на каждое удостоверение (как они и заведены в
    справочнике), вместо этого получал один общий текст (баг, найденный
    пользователем). "certificates"/"certificates_expires" остаются в
    EMPLOYEE_DATA_FIELDS ТОЛЬКО ради employee_data_value() -- уже заведённые
    в документах поля с этими ключами продолжают отображать значение без
    изменений -- но employee_chip_fields() (единственный источник чипов для
    диалога и для создания новых полей, см. её докстринг) их больше НЕ
    предлагает: показ обоих вариантов рядом (первая версия) путал
    оператора похожими подписями ("Удостоверения" vs "Удостоверение 1") --
    он снова случайно получал слияние, выбрав не тот чип.

    Без номера в подписи, если запись ровно одна ("Удостоверение", не
    "Удостоверение 1") -- нумерация имеет смысл только когда есть из чего
    выбирать; при 0 записей -- пустой список (нечего показывать)."""
    n = len(employee.certificates)
    fields = []
    for i in range(n):
        suffix = "" if n == 1 else f" {i + 1}"
        fields.append(EmployeeDataField(
            f"certificates:{i}", f"Удостоверение{suffix}",
            lambda e, i=i: e.certificates[i].text if i < len(e.certificates) else "",
        ))
        fields.append(EmployeeDataField(
            f"certificates_expires:{i}", f"Срок действия{suffix}",
            lambda e, i=i: (e.certificates[i].expires or "") if i < len(e.certificates) else "",
        ))
    return fields


def employee_chip_fields(employee: Employee) -> List[EmployeeDataField]:
    """Полный упорядоченный список готовых представлений ДЛЯ КОНКРЕТНОГО
    сотрудника, ПРЕДЛАГАЕМЫХ К ВЫБОРУ -- EMPLOYEE_DATA_FIELDS (статические,
    общие для всех), КРОМЕ "certificates"/"certificates_expires" (см. их
    докстринг в EMPLOYEE_DATA_FIELDS -- объединяют все удостоверения в одно
    значение через "; "), на их месте -- представления отдельных
    удостоверений (employee_certificate_fields(), своё количество у
    каждого сотрудника).

    Объединённые "certificates"/"certificates_expires" НЕ удалены из
    EMPLOYEE_DATA_FIELDS целиком (см. _FIELDS_BY_KEY/employee_data_value()
    -- уже созданные в документах поля с этими ключами продолжают
    отображать значение как раньше), просто больше не предлагаются как
    выбираемый чип: первая версия этой функции показывала их РЯДОМ с
    гранулярными чипами -- пользователь путал их (оба называются похоже,
    "Удостоверения" против "Удостоверение 1"/"Удостоверение 2") и снова
    получал слияние через "; ", случайно выбрав не тот чип. Единый
    источник порядка/подписей и для EmployeePlaceholderDialog.
    _render_placeholders(), и для MainWindow._create_employee_from_chip_menu()
    -- иначе они могли бы разойтись в том, что показывает чип и что реально
    заводится полем."""
    fields = []
    for field in EMPLOYEE_DATA_FIELDS:
        if field.key == "certificates":
            continue
        if field.key == "certificates_expires":
            fields.extend(employee_certificate_fields(employee))
            continue
        fields.append(field)
    return fields


def employee_data_value(employee: Employee, key: str) -> str:
    """Значение одного готового представления (key из EMPLOYEE_DATA_FIELDS
    либо составной ключ "certificates:<i>"/"certificates_expires:<i>", см.
    employee_certificate_fields()) для конкретного сотрудника. Неизвестный
    key, а также индекс за пределами employee.certificates (запись могла
    исчезнуть уже после того, как привязка была сохранена, см.
    load_field_employee_bindings()) -- пустая строка, а не исключение."""
    base_key, sep, index_str = key.partition(":")
    if sep and base_key in _CERTIFICATE_KEY_PREFIXES and index_str.isdigit():
        index = int(index_str)
        if 0 <= index < len(employee.certificates):
            certificate = employee.certificates[index]
            return certificate.text if base_key == "certificates" else (certificate.expires or "")
        return ""
    field = _FIELDS_BY_KEY.get(key)
    return field.value(employee) if field is not None else ""
