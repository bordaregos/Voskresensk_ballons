"""Имена виджетов, резолвимые из pipeline_window.ui через findChild.

Тот же контракт, что и widget_names.py (баллоны): каждое имя здесь ==
objectName виджета в designer/pipeline_window.ui == ключ в MainWindow.data
== имя Jinja-плейсхолдера в шаблоне templates/Шаблон_трубопровод.docx.

Опорный документ по составу полей — TD_720291_otd_214_1.docx (отчёт по
техническому диагностированию трубопровода). Статичные/шаблонные разделы
отчёта (программа диагностирования, методики, лицензионные реквизиты
экспертной организации) в виджеты не выносятся — они остаются постоянным
текстом в самом .docx-шаблоне, а не Jinja-плейсхолдерами.
"""

PLAIN_TEXT_EDIT_NAMES = [
    # Отчёт и объект
    "report_number", "reg_number", "obj_naznach", "obj_location",
    "year_made", "year_start", "years_of_operation", "project_docs",
    "p_rab_mpa", "p_rab_kgs", "work_temp", "length_m", "construction_desc",
    "pipe_size", "pipe_gost",
    # Заказчик
    "customer_name", "customer_short_name", "customer_address",
    "customer_head", "customer_phone", "customer_inn",
    # Экспертная организация и специалист
    "expert_org_name", "specialist_name", "specialist_cert",
    # Акты и протоколы (Приложения 2-5, 8-9)
    "act2_conclusion", "vik_conclusion",
    "thick_device", "thick_seed_min", "thick_conclusion",
    "uzk_device", "uzk_conclusion",
    "pnevmo_pressure", "pnevmo_device", "pnevmo_conclusion",
    # Расчёт на прочность и остаточный ресурс (Приложение 6)
    "calc_temp", "calc_phi", "calc_da", "calc_sn", "calc_c2", "calc_sf",
    "calc_sigma_allow", "calc_sr", "calc_s_reject", "calc_p_allow",
    "calc_strength_conclusion",
    "calc_years_operation", "calc_k", "calc_corrosion_rate",
    "calc_remaining_years", "calc_residual_comment",
    # Выводы (раздел 9)
    "final_condition", "final_years_allowed",
]

COMBO_BOX_NAMES = [
    "work_medium", "steel_grade",
]

DATE_EDIT_NAMES = [
    "report_date", "act2_date", "vik_date", "thick_date", "uzk_date",
    "pnevmo_date", "final_deadline_date",
]

BUTTON_NAMES = [
    "pushButt_generateWord", "pushButton_saveProject", "pushButton_openProject",
    "pushButt_segments", "pushButton_genThickness",
    "pushButton_calcStrength", "pushButton_calcResidualLife",
]

SPIN_BOX_NAMES = [
    "segments_count", "pnevmo_sensors_count",
]

TABLE_WIDGET = [
    "table_reviewed_docs", "table_vik", "table_segments",
    "table_thick_pipeline", "table_uzk",
]

# Варианты "Тип элемента" для выпадающего списка в table_segments (колонка 1).
SEGMENT_TYPES = ["Прямой участок", "Отвод", "Тройник", "Переход"]
