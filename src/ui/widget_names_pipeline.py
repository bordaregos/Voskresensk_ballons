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
    # Вводная часть (1.1, 1.2 -- сейчас редактируемые поля формы, а не
    # статичный текст/таблица, выпеченная из organization_config.py при
    # генерации заготовки; см. template_schema.py)
    "intro_text",
    "org_name", "org_address", "org_head", "org_phone", "org_fax",
    "org_email", "org_website", "org_license", "org_license_issuer",
    "org_license_number_date", "org_activity_type", "org_activity_scope",
    # Отчёт и объект
    "report_number", "report_year", "reg_number", "obj_naznach", "obj_location",
    "obj_name",
    "year_made", "year_start", "years_of_operation", "project_docs",
    "p_rab_mpa", "p_rab_kgs", "work_temp", "length_m", "construction_desc",
    # Заказчик
    "customer_name", "customer_short_name", "customer_legal_form",
    "customer_address", "customer_actual_address",
    "customer_head", "customer_phone", "customer_inn",
    # Цель технического диагностирования
    "goal_text",
    # 7. Результаты технического диагностирования (7.1-7.7)
    "result_71", "result_72", "result_73", "result_74", "result_75",
    "result_76", "result_77",
    # Акты и протоколы (Приложения 2-5, 8-9)
    "act2_conclusion", "vik_conclusion",
    "thick_seed_min", "thick_conclusion",
    "uzk_conclusion",
    "pnevmo_pressure", "pnevmo_conclusion",
    # Расчёт на прочность и остаточный ресурс (Приложение 6)
    "calc_temp", "calc_phi", "calc_da", "calc_sn", "calc_c2", "calc_sf",
    "calc_sigma_allow", "calc_sr", "calc_s_reject", "calc_p_allow",
    "calc_strength_conclusion",
    "calc_years_operation", "calc_k", "calc_corrosion_rate",
    "calc_remaining_years", "calc_residual_comment",
    # Выводы (раздел 8)
    "final_condition", "final_years_allowed",
]

COMBO_BOX_NAMES = [
    "work_medium",
    # Редактируемые -- список пополняется вводом оператора (см.
    # SEGMENT_TYPES ниже для контраста: там фиксированный набор вариантов).
    "thick_device", "uzk_device", "pnevmo_device", "report_title",
]

DATE_EDIT_NAMES = [
    "report_date", "act2_date", "vik_date", "thick_date", "uzk_date",
    "pnevmo_date", "final_deadline_date",
]

BUTTON_NAMES = [
    "pushButt_generateWord", "pushButton_saveProject", "pushButton_openProject",
    "pushButt_segments", "pushButton_genThickness",
    "pushButton_calcStrength", "pushButton_calcResidualLife",
    "pushButt_addSpecialist", "pushButt_removeSpecialist",
    "pushButt_addReviewedDoc", "pushButt_removeReviewedDoc",
    "pushButt_addVikRow", "pushButt_removeVikRow",
    "pushButt_removeThickDevice", "pushButt_removeUzkDevice",
    "pushButt_removePnevmoDevice", "pushButt_removeReportTitle",
    "pushButt_addPipeMaterial", "pushButt_removePipeMaterial",
]

SPIN_BOX_NAMES = [
    "segments_count", "pnevmo_sensors_count",
]

TABLE_WIDGET = [
    "table_reviewed_docs", "table_vik", "table_segments",
    "table_thick_pipeline", "table_uzk", "table_specialists",
    "table_pipe_materials",
]

# Варианты "Тип элемента" для выпадающего списка в table_segments (колонка 1).
SEGMENT_TYPES = ["Прямой участок", "Отвод", "Тройник", "Переход"]
