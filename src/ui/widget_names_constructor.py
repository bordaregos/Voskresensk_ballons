"""Имена виджетов, резолвимые из constructor_window.ui через findChild.

Тот же контракт, что и widget_names.py/widget_names_pipeline.py: каждое имя
здесь == objectName виджета в designer/constructor_window.ui == ключ в
MainWindow.data == имя Jinja-плейсхолдера в шаблоне-фрагменте (см.
src/services/template_schema.py, TITLE_VARIANTS).

Поля реквизитов титульного листа (doc_number, title_heading и т.п.) сюда
НЕ входят -- у разных вариантов свой набор (см. TITLE_VARIANTS[...].subtitle_fields),
поэтому виджеты под них создаются в рантайме
(MainWindow._render_title_fields()) и регистрируются в
self.PLAIN_TEXT_EDIT_NAMES динамически, а не здесь статично.
"""

PLAIN_TEXT_EDIT_NAMES = []
COMBO_BOX_NAMES = []
DATE_EDIT_NAMES = []
BUTTON_NAMES = ["pushButt_generateWord", "pushButton_saveProject", "pushButton_openProject"]
SPIN_BOX_NAMES = []
TABLE_WIDGET = []
