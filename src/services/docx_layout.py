"""Перевод вставленных docxtpl.InlineImage картинок из обычного инлайн-
положения в плавающее "за текстом" -- Word называет это "Обтекание
текстом -> За текстом" (behindDoc="1"). docxtpl/python-docx умеют только
вставлять инлайн-картинки (см. docx.oxml.shape.CT_Inline.new_pic_inline),
отдельного класса для плавающих картинок в них нет -- поэтому уже
отрендеренный XML патчится напрямую, см. MainWindow._float_kleishe_drawings
_behind_text() (src/ui/main_window.py), которая вызывает этот модуль после
doc.render(), но до doc.save().

Не зависит от Qt/docxtpl -- только python-docx (см. CLAUDE.md, тестовый
слой намеренно без Qt/docxtpl).
"""

from typing import Iterable, Set

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def float_drawings_behind_text(
    document, target_rids: Iterable[str], anchor_to_placeholder: bool = False,
) -> int:
    """Находит все <w:drawing> в теле документа, чья картинка (<a:blip
    r:embed="...">) ссылается на один из target_rids, и переводит их из
    <wp:inline> в <wp:anchor behindDoc="1" ...> -- размер (<wp:extent>) при
    этом не меняется, узел переносится как есть, а не создаётся заново.

    anchor_to_placeholder -- см. _inline_to_anchor(): False (по умолчанию,
    исторический вариант для клише специалистов трубопровода/баллонов, см.
    MainWindow._float_kleishe_drawings_behind_text()) держит прежнее
    поведение неизменным, True (клише конструктора документов, см.
    MainWindow._splice_kleishe_placeholders()) привязывает картинку к
    месту САМОГО плейсхолдера, а не к началу абзаца/колонки.

    Возвращает количество изменённых <w:drawing>. Драйвинги, чей rId не
    входит в target_rids (например, схема НК/график нагружения, см.
    MainWindow.calculate()), не трогаются.
    """
    target_rids: Set[str] = set(target_rids)
    if not target_rids:
        return 0

    changed = 0
    relative_height = 1
    for drawing in document.element.body.iter(qn("w:drawing")):
        inline = drawing.find(qn("wp:inline"))
        if inline is None:
            continue
        blip = inline.find(f".//{qn('a:blip')}")
        if blip is None or blip.get(qn("r:embed")) not in target_rids:
            continue

        anchor = _inline_to_anchor(inline, relative_height, anchor_to_placeholder)
        drawing.replace(inline, anchor)
        changed += 1
        relative_height += 1

    return changed


def _inline_to_anchor(inline, relative_height: int, anchor_to_placeholder: bool = False):
    """<wp:inline>...</wp:inline> -> <wp:anchor behindDoc="1" ...>...
    </wp:anchor>. <wp:extent>/<wp:docPr>/<wp:cNvGraphicFramePr>/<a:graphic>
    переносятся из inline как есть (те же узлы, не копии) -- размер и
    содержимое картинки не меняются.

    Позиция управляется anchor_to_placeholder:
    - False (по умолчанию) -- левый верхний угол текущего абзаца/колонки
      (relativeFrom="paragraph"/"column", ближайший эквивалент прежнего
      инлайн-положения, когда картинка -- единственное или главное
      содержимое своего абзаца/ячейки, как у клише специалистов
      трубопровода/баллонов).
    - True -- relativeFrom="character"/"line": точка отсчёта -- сам якорь
      <w:drawing> В ТЕКСТЕ (то самое место, где физически стоял run с
      плейсхолдером до замены на картинку), а не начало абзаца/колонки.
      Нужно для клише конструктора документов, где плейсхолдер клише часто
      НЕ единственное содержимое абзаца (например, стоит перед текстом ФИО
      в одной строке подписи, см. _splice_kleishe_placeholders()) -- с
      relativeFrom="paragraph"/"column" картинка уезжала бы к началу всей
      строки/ячейки, а не оставалась там, где стоял её собственный
      плейсхолдер.

    В обоих случаях offset -- 0 (точная точка отсчёта, без сдвига);
    точную позицию оператор при необходимости поправит перетаскиванием
    картинки в Word -- в отличие от инлайн-картинки, плавающую можно
    двигать мышью."""
    anchor = OxmlElement("wp:anchor")
    anchor.set("distT", inline.get("distT", "0"))
    anchor.set("distB", inline.get("distB", "0"))
    anchor.set("distL", inline.get("distL", "0"))
    anchor.set("distR", inline.get("distR", "0"))
    anchor.set("simplePos", "0")
    anchor.set("relativeHeight", str(relative_height))
    anchor.set("behindDoc", "1")
    anchor.set("locked", "0")
    anchor.set("layoutInCell", "1")
    anchor.set("allowOverlap", "1")

    simple_pos = OxmlElement("wp:simplePos")
    simple_pos.set("x", "0")
    simple_pos.set("y", "0")
    anchor.append(simple_pos)

    h_relative_from = "character" if anchor_to_placeholder else "column"
    v_relative_from = "line" if anchor_to_placeholder else "paragraph"

    position_h = OxmlElement("wp:positionH")
    position_h.set("relativeFrom", h_relative_from)
    offset_h = OxmlElement("wp:posOffset")
    offset_h.text = "0"
    position_h.append(offset_h)
    anchor.append(position_h)

    position_v = OxmlElement("wp:positionV")
    position_v.set("relativeFrom", v_relative_from)
    offset_v = OxmlElement("wp:posOffset")
    offset_v.text = "0"
    position_v.append(offset_v)
    anchor.append(position_v)

    for tag in ("wp:extent", "wp:effectExtent"):
        element = inline.find(qn(tag))
        if element is not None:
            anchor.append(element)

    anchor.append(OxmlElement("wp:wrapNone"))

    for tag in ("wp:docPr", "wp:cNvGraphicFramePr", "a:graphic"):
        element = inline.find(qn(tag))
        if element is not None:
            anchor.append(element)

    return anchor
