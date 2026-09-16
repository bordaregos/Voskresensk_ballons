"""Пользовательский вариант титульного листа конструктора документов —
добавляется через UI (кнопка «Добавить» в списке «Титульные листы»), не
привязан к конкретному отчёту/проекту. Встроенные варианты (TITLE_VARIANTS,
src/services/template_schema.py) в этот справочник не входят и через UI не
удаляются.

subtitle_fields -- каталог плейсхолдеров варианта: упорядоченный список id
полей (без дублей). Напрямую редактируется встроенным в главный экран
каталогом плейсхолдеров (src/ui/main_window.py,
_build_title_placeholder_catalog()) -- добавить/удалить плейсхолдер значит
добавить/удалить id из этого списка, тем же способом, что уже был у
встроенных TITLE_VARIANTS. Определяет: (1) форму реквизитов на главном
экране (_render_title_fields()), (2) какие "{{ id }}" можно скопировать по
ПКМ по чипу для вставки в Word.

template_filename -- имя файла, загруженного через «Загрузить шаблон
Word» (src/ui/main_window.py, _upload_title_variant_template()) -- чисто
для отображения над каталогом плейсхолдеров ("с каким документом идёт
работа"), на резолюцию файла не влияет: она всегда идёт через фиксированный
путь FRAGMENTS_DIR/title_{id}.docx (см. find_title_template()), независимо
от исходного имени. Пустая строка -- шаблон ещё не загружался, работает
только автосгенерированная заготовка (generate_title_fragment()).

Сам текст/вёрстка/таблицы/подпись титульника этим приложением больше не
редактируются -- пользователь ведёт их напрямую в .docx-файле варианта
через Word (см. find_title_template()/generate_title_fragment()). Раньше
(до этой версии) здесь ещё было поле content -- структурированный список
абзацев/таблиц, который редактировался через rich-text редактор и
перегенерировал .docx при каждом сохранении; отказались от этого в пользу
модели "плейсхолдеры + правка в Word" (см. обсуждение задачи и мокап
docs/design/constructor_mockup.html) -- итоговое форматирование там, где
для него есть реальный набор инструментов, а не через ограниченный набор
примитивов python-docx. Старые записи в data/title_variants.json могут
ещё содержать ключ "content" -- from_dict() его просто не читает, он
останется мёртвым и исчезнет из файла при следующем save_title_variants()."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class TitleVariant:
    id: str
    document_title: str = ""
    subtitle_fields: List[str] = field(default_factory=list)
    template_filename: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TitleVariant':
        return cls(
            id=data['id'],
            document_title=data.get('document_title', ''),
            subtitle_fields=list(data.get('subtitle_fields', [])),
            template_filename=data.get('template_filename', ''),
        )
