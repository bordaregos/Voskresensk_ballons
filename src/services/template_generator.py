"""Генератор шаблонов-заготовок .docx из ReportSchema.

Пишет документ через python-docx (не через сам docxtpl -- тот только
рендерит готовый .docx, не создаёт его). Результат -- РАЗОВАЯ заготовка:
дальше пользователь дорабатывает её в Word вручную (логотип, вёрстка,
формулировки), генератор этот файл больше не трогает -- safe regeneration
сознательно не реализовано (см. src/services/template_schema.py).

Ключевой инвариант всех add_*-функций: каждый {{ }}/{% %}-тег -- РОВНО ОДИН
run. python-docx даёт это бесплатно (paragraph.add_run(text) и cell.text=
всегда создают один run), если не разбивать один тег на несколько вызовов.
Это устраняет самый источник бага, найденного в реальном Шаблон_финал.docx:
там часть тегов раздроблена автозаменой Word на несколько <w:r>, из-за чего
их пришлось искать по документу через склейку рантайм-текста (см.
template_validator.py). Генератор такой проблемы не создаёт в принципе.

Второй подтверждённый на реальном шаблоне факт: цикл по списку -- обычный
Jinja `{% for x in list %}...{% endfor %}`, оборачивающий ЦЕЛИКОМ таблицу
(включая шапку) -- НЕ специальные докстпл-теги {%tr%}/{%p%} (их в реальном
шаблоне нет вообще). add_repeating_table() воспроизводит именно этот
паттерн.
"""

from pathlib import Path
from typing import Union

from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from ..models.title_variant import TitleVariant
from ..organization_config import DEFAULT_ORGANIZATION, OrganizationConfig
from .template_schema import (
    FieldsTableSection,
    ReportSchema,
    RepeatingTableSection,
    SCHEMAS,
    Section,
    StaticFieldsTableSection,
    StaticTextSection,
    TitleConfig,
)


def add_page_border(doc: DocumentObject, size: int = 24, color: str = "1C1C1E") -> None:
    """Рамка по периметру страницы -- нативная функция Word (вкладка
    «Макет» -> «Границы страниц»), у python-docx для неё нет
    высокоуровневого API, пишем прямо в XML секции (<w:pgBorders> внутри
    <w:sectPr>) -- тот же приём, что и _set_paragraph_bottom_border() ниже.
    Открыв результат в Word, эту рамку можно будет поправить штатным
    диалогом «Границы страниц», в отличие от имитации через таблицу на всю
    страницу.

    size -- толщина линии в восьмых долях пункта (единица измерения Word),
    24 = 3pt -- под явную рамку с образца задачи, не тонкую линию."""
    sectPr = doc.sections[0]._sectPr
    pgBorders = OxmlElement('w:pgBorders')
    pgBorders.set(qn('w:offsetFrom'), 'page')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(size))
        el.set(qn('w:space'), '24')
        el.set(qn('w:color'), color)
        pgBorders.append(el)
    sectPr.append(pgBorders)


def _set_paragraph_bottom_border(paragraph, size: int = 8, color: str = "000000") -> None:
    """Нижняя граница параграфа -- в Word нет отдельного элемента-разделителя
    (аналога HTML <hr>), эмулируется через <w:pBdr><w:bottom/></w:pBdr> в
    pPr -- используется как черта под шапкой организации
    (add_organization_letterhead()). Как и add_page_border(), в обход
    высокоуровневого API python-docx, которого для этого нет."""
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(size))
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def add_organization_letterhead(doc: DocumentObject, org: OrganizationConfig = DEFAULT_ORGANIZATION) -> None:
    """Шапка организации на титульном листе конструктора документов --
    полное название (жирным) + адрес/телефон/e-mail + ОКПО/ОГРН/ИНН/КПП
    одной строкой, черта снизу (см. обсуждение задачи и реальный образец
    бланка). Значения org впечатываются буквально, НЕ Jinja-плейсхолдеры --
    тот же принцип, что и add_static_fields_table() (одни и те же для всех
    отчётов, форма оператора про них не знает и не должна).

    Без логотипа: реального файла картинки пока нет (см. обсуждение),
    место под него сознательно не зарезервировано -- проще один раз
    доверстать руками, когда появится, чем поддерживать пустую колонку
    сейчас. Вызывается из generate_title_fragment() для ВСЕХ
    пользовательских вариантов конструктора без исключений -- это
    корпоративный формат бланка, не настройка per-вариант."""
    name_p = doc.add_paragraph()
    name_run = name_p.add_run(org.full_name)
    name_run.bold = True
    if org.short_name:
        short_run = name_p.add_run(f" ({org.short_name})")
        short_run.bold = True

    contact_lines = []
    if org.address:
        contact_lines.append(f"Юридический адрес: {org.address}")
    phone_email = ", ".join(filter(None, [
        f"тел. {org.phone}" if org.phone else "",
        f"e-mail: {org.email}" if org.email else "",
    ]))
    if phone_email:
        contact_lines.append(phone_email)
    ids_line = ", ".join(filter(None, [
        f"ОКПО {org.okpo}" if org.okpo else "",
        f"ОГРН {org.ogrn}" if org.ogrn else "",
        f"ИНН {org.inn}" if org.inn else "",
        f"КПП {org.kpp}" if org.kpp else "",
    ]))
    if ids_line:
        contact_lines.append(ids_line)

    contacts_p = doc.add_paragraph()
    contacts_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, line in enumerate(contact_lines):
        if i > 0:
            contacts_p.add_run().add_break()
        run = contacts_p.add_run(line)
        run.font.size = Pt(9)
    _set_paragraph_bottom_border(contacts_p, size=8, color="1C1C1E")


def _add_heading(doc: DocumentObject, text: str, level: int = 2) -> None:
    doc.add_heading(text, level=level)


def _add_caption(doc: DocumentObject, caption: Union[str, None]) -> None:
    if caption:
        p = doc.add_paragraph()
        run = p.add_run(caption)
        run.italic = True


def add_title(doc: DocumentObject, title: TitleConfig) -> None:
    """Титульный лист: настраиваемый заголовок + плейсхолдеры отчёта."""
    heading = doc.add_heading(title.document_title, level=0)
    heading.alignment = 1  # WD_ALIGN_PARAGRAPH.CENTER
    for name in title.subtitle_fields:
        p = doc.add_paragraph()
        p.add_run("{{ " + name + " }}")


def add_static_text_section(doc: DocumentObject, section: StaticTextSection) -> None:
    """Раздел из чистого текста без плейсхолдеров (вводная часть и т.п.)."""
    if section.heading:
        _add_heading(doc, section.heading)
    for paragraph_text in section.paragraphs:
        doc.add_paragraph(paragraph_text)


def add_fields_table(doc: DocumentObject, section: FieldsTableSection) -> None:
    """Плоская таблица метка -> {{ placeholder }} (одна Jinja-переменная на
    строку, заполняется оператором через форму)."""
    if section.heading:
        _add_heading(doc, section.heading)
    _add_caption(doc, section.caption)
    table = doc.add_table(rows=len(section.rows), cols=2)
    table.style = "Table Grid"
    for row_idx, field_label in enumerate(section.rows):
        table.cell(row_idx, 0).text = field_label.label
        table.cell(row_idx, 1).text = "{{ " + field_label.placeholder + " }}"


def add_static_fields_table(
    doc: DocumentObject, section: StaticFieldsTableSection, org: OrganizationConfig,
) -> None:
    """Таблица реквизитов организации -- значения впечатываются буквально из
    org СЕЙЧАС, при генерации, а не оставляются Jinja-плейсхолдерами.
    Форма отчёта про эти поля ничего не знает, оператор их не заполняет --
    смешать эту таблицу с FieldsTableSection значило бы воссоздать тот же
    класс бага, ради устранения которого всё затевается (плейсхолдер,
    который никто и никогда не заполняет)."""
    if section.heading:
        _add_heading(doc, section.heading)
    _add_caption(doc, section.caption)
    table = doc.add_table(rows=len(section.rows), cols=2)
    table.style = "Table Grid"
    for row_idx, (label, attr_name) in enumerate(section.rows):
        table.cell(row_idx, 0).text = label
        table.cell(row_idx, 1).text = str(getattr(org, attr_name, ""))


def add_repeating_table(doc: DocumentObject, section: RepeatingTableSection) -> None:
    """{% for %}-параграф -> таблица (шапка + одна образцовая строка) ->
    {% endfor %}-параграф, строго последовательно. Вся таблица целиком
    повторяется по разу на элемент списка -- см. модульный докстринг."""
    if section.heading:
        _add_heading(doc, section.heading)
    _add_caption(doc, section.caption)

    for_paragraph = doc.add_paragraph()
    for_paragraph.add_run(
        "{% for " + section.loop_var + " in " + section.list_field + " %}"
    )

    table = doc.add_table(rows=2, cols=len(section.header_cells))
    table.style = "Table Grid"
    for col_idx, header_text in enumerate(section.header_cells):
        table.cell(0, col_idx).text = header_text

    if section.positional:
        for col_idx in range(len(section.header_cells)):
            table.cell(1, col_idx).text = f"{{{{ {section.loop_var}[{col_idx}] }}}}"
    else:
        for col_idx, attr_name in enumerate(section.row_cells):
            table.cell(1, col_idx).text = f"{{{{ {section.loop_var}.{attr_name} }}}}"

    endfor_paragraph = doc.add_paragraph()
    endfor_paragraph.add_run("{% endfor %}")


def add_section(doc: DocumentObject, section: Section, org: OrganizationConfig) -> None:
    if isinstance(section, StaticTextSection):
        add_static_text_section(doc, section)
    elif isinstance(section, StaticFieldsTableSection):
        add_static_fields_table(doc, section, org)
    elif isinstance(section, RepeatingTableSection):
        add_repeating_table(doc, section)
    elif isinstance(section, FieldsTableSection):
        add_fields_table(doc, section)
    else:
        raise TypeError(f"Неизвестный тип раздела схемы: {type(section)!r}")


def generate_template(
    equipment_type_id: str,
    org_config: OrganizationConfig,
    output_path: Union[str, Path],
    schema: Union[ReportSchema, None] = None,
    title_override: Union[str, None] = None,
) -> Path:
    """Собирает .docx-заготовку с нуля из ReportSchema + OrganizationConfig.

    Разовая операция: результат далее правится в Word вручную (логотип,
    точная вёрстка, формулировки), генератор его больше не трогает.
    title_override перекрывает schema.title.document_title без правки кода
    -- например, "сегодня отчёт, завтра заключение экспертизы".

    Raises:
        KeyError: неизвестный equipment_type_id и schema не передана явно.
    """
    if schema is None:
        schema = SCHEMAS[equipment_type_id]

    title = schema.title
    if title_override is not None:
        title = TitleConfig(document_title=title_override, subtitle_fields=title.subtitle_fields)

    doc = Document()
    add_title(doc, title)
    for section in schema.sections:
        add_section(doc, section, org_config)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def generate_title_fragment(
    variant: TitleVariant,
    output_path: Union[str, Path],
    org_config: OrganizationConfig = DEFAULT_ORGANIZATION,
) -> Path:
    """.docx-заготовка ОДНОГО пользовательского варианта титульного листа
    конструктора документов (variant: TitleVariant) -- маленький
    самостоятельный фрагмент, как add_title()/cmd_generate_title в
    scripts/template_tool.py, но без обвязки в ReportSchema (у
    фрагмента-титульника нет разделов схемы) -- в отличие от неё,
    OrganizationConfig тут как раз нужен: рамка страницы + шапка
    организации (add_page_border()/add_organization_letterhead()) теперь
    печатаются на КАЖДОМ сгенерированном фрагменте безусловно (см.
    обсуждение задачи и её мокап-эскиз -- скриншоты реального бланка) --
    это фирменный формат бланка организации, не настройка per-вариант.

    В отличие от generate_template()/cmd_generate_title -- вызывается один
    раз при создании нового варианта («Добавить»), чтобы у варианта сразу
    была рабочая заготовка вместо "осиротевшего" JSON-описания без .docx
    (см. src/config.py, find_title_template()), и как сеть безопасности,
    если файл варианта пропал с диска. НЕ вызывается при каждой правке
    каталога плейсхолдеров (src/ui/main_window.py, _add_title_variant_placeholder()/
    _remove_title_variant_placeholder()) -- в отличие от более ранней версии
    этой функции: дальнейший текст,
    вёрстка, таблицы и подпись титульника ведутся пользователем напрямую в
    Word, повторная генерация затёрла бы эту ручную правку. Тот же принцип,
    что уже действует для встроенных вариантов (TITLE_VARIANTS,
    template_schema.py) и для generate_template() -- safe-regeneration
    сознательно не реализована, см. модульный докстринг.
    """
    doc = Document()
    add_page_border(doc)
    add_organization_letterhead(doc, org_config)
    add_title(doc, TitleConfig(
        document_title=variant.document_title, subtitle_fields=variant.subtitle_fields,
    ))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def generate_intro_fragment(variant: TitleVariant, output_path: Union[str, Path]) -> Path:
    """.docx-заготовка ОДНОГО пользовательского варианта вводной части
    конструктора документов -- второй, независимый от титульного листа слот
    (см. src/ui/main_window.py). Структурно калька generate_title_fragment()
    (заголовок + плейсхолдеры-параграфы под variant.subtitle_fields), но
    БЕЗ add_page_border()/add_organization_letterhead(): рамка страницы и
    шапка организации -- атрибут ПЕРВОЙ страницы документа, печатаются один
    раз на титульном фрагменте; если бы их печатал ещё и фрагмент вводной
    части, при склейке обоих в один файл (см. _calculate_constructor())
    получилась бы вторая, лишняя рамка/шапка посреди документа. Поэтому и
    без org_config -- он здесь просто не нужен.

    Плейсхолдеры пишутся с префиксом "intro_" ("{{ intro_doc_number }}", а
    не "{{ doc_number }}"), хотя каталог полей (TITLE_FIELD_LABELS) общий с
    титульным листом -- у обоих слотов оператор вставляет плейсхолдеры из
    ОДНОГО и того же меню «Вставить плейсхолдер». Без префикса совпадающий
    field_id, добавленный сразу в оба слота, делил бы один и тот же
    self.<field_id>/form_data[field_id] на два РАЗНЫХ виджета реквизитов --
    значение того, что создан вторым, молча перезаписывало бы значение
    первого (см. src/ui/main_window.py, _render_slot_fields()).
    generate_title_fragment() эту схему НЕ использует -- у него плейсхолдеры
    остаются голыми: там уже есть реальные, вручную доработанные в Word
    файлы title_*.docx с голыми "{{ field }}" -- смена схемы молча сломала
    бы уже существующие фрагменты."""
    doc = Document()
    add_title(doc, TitleConfig(
        document_title=variant.document_title,
        subtitle_fields=[f"intro_{field_id}" for field_id in variant.subtitle_fields],
    ))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


def generate_appendix_fragment(variant: TitleVariant, output_path: Union[str, Path]) -> Path:
    """.docx-заготовка ОДНОГО пользовательского варианта «Приложения 1»
    конструктора документов -- третий, независимый от титульного листа и
    вводной части слот (см. src/ui/main_window.py). Структурно калька
    generate_intro_fragment() (тот же принцип: без add_page_border()/
    add_organization_letterhead(), плейсхолдеры с префиксом слота), только
    под свой префикс "appendix1_" -- по той же причине, что и у "intro_" в
    generate_intro_fragment(): общий каталог полей (TITLE_FIELD_LABELS) на
    все слоты, префикс нужен, чтобы одинаковый field_id, вставленный сразу
    в несколько слотов, не делил один и тот же self.<field_id> на несколько
    разных виджетов реквизитов (см. docstring generate_intro_fragment())."""
    doc = Document()
    add_title(doc, TitleConfig(
        document_title=variant.document_title,
        subtitle_fields=[f"appendix1_{field_id}" for field_id in variant.subtitle_fields],
    ))

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
