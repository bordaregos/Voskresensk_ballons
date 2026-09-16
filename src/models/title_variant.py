"""Пользовательский вариант титульного листа конструктора документов —
добавляется через UI (кнопка «Добавить» в списке «Титульные листы»), не
привязан к конкретному отчёту/проекту. Встроенные варианты (TITLE_VARIANTS,
src/services/template_schema.py) в этот справочник не входят и через UI не
удаляются.

content -- структурированное содержимое титульника: список параграфов,
каждый параграф -- список ранов вида {"text": "...", "bold": bool,
"italic": bool} (обычный текст) или {"placeholder": field_id} (плейсхолдер,
подставляется докстплом при рендере, в .docx-заготовке пишется буквально
как "{{ field_id }}", см. src/services/template_generator.py,
add_title_content()). Заполняется/редактируется через встроенный редактор
шаблона в конструкторе (src/ui/title_content_editor.py) -- в отличие от
subtitle_fields (плоский список id, только для built-in TITLE_VARIANTS),
здесь текст и плейсхолдеры могут свободно перемежаться в одной строке.

subtitle_fields для пользовательских вариантов -- ПРОИЗВОДНОЕ от content
(id плейсхолдеров в порядке первого появления, см.
derive_subtitle_fields_from_content()), не редактируется отдельно и
пересчитывается и сохраняется заново при каждой правке content. Оставлен
отдельным полем (не свойством) для обратной совместимости с вариантами,
у которых content ещё нет (созданы до этой возможности) -- у них
subtitle_fields как было, единственный источник истины."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class TitleVariant:
    id: str
    document_title: str = ""
    subtitle_fields: List[str] = field(default_factory=list)
    content: List[List[Dict[str, Any]]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TitleVariant':
        return cls(
            id=data['id'],
            document_title=data.get('document_title', ''),
            subtitle_fields=list(data.get('subtitle_fields', [])),
            content=[list(paragraph) for paragraph in data.get('content', [])],
        )


def derive_subtitle_fields_from_content(content: List[List[Dict[str, Any]]]) -> List[str]:
    """Список id плейсхолдеров, реально присутствующих в content -- порядок
    первого появления, без дублей. Источник истины для subtitle_fields
    пользовательского варианта после любой правки content (см. докстринг
    класса выше) -- реквизиты формы конструктора должны совпадать с тем,
    что реально есть в тексте титульника, а не с отдельно поддерживаемым
    списком."""
    seen: Dict[str, None] = {}
    for paragraph in content:
        for run in paragraph:
            placeholder = run.get('placeholder')
            if placeholder and placeholder not in seen:
                seen[placeholder] = None
    return list(seen)
