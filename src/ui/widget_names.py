"""Имена виджетов, резолвимые из main_window.ui через findChild.

Каждое имя здесь == objectName виджета в designer/main_window.ui ==
ключ в MainWindow.data == имя Jinja-плейсхолдера в шаблоне .docx.
Добавление нового поля в форму требует правки во всех трёх местах.
"""

PLAIN_TEXT_EDIT_NAMES = [
    "zakl_number", "reg_number", "gost", "g_vvod", "dataZakl",
    "yearsOfExpluatation", "chertezh", "p_rasch", "p_rab", "s_isp",
    "length", "d_nar", "d_min", "d_max", "volume", "zav_nums", "reg_nums",
    "place", "zavod_name", "vladelec", "dogContract",
    "pricaz_contora", "pricaz_vladelec", "s_min_total", "p_rab_MPa",
    "p_gidro", "p_pnevma", "d_vnutr", "pred_tek_min", "vrem_sopr_min",
    "sigma", "sigma_gidro", "s_rasch", "s_rasch_gidro", "s_max_rasch",
    "a_corr", "c0_plus_dop", "tk_years", "tk_just", "zav_s_min",
    "obj_name", "prev_zakl", "prev_pg_am", "volume_total", "p_pnevma_kgs",
    "p_dop", "place_obj", "pasp_pg_amount", "gost_material"
]

COMBO_BOX_NAMES = [
    "construction", "material", "rab_sreda", "naznach"
]

DATE_EDIT_NAMES = [
    "vik_date", "tolshTverdost_date", "ispRasch_date", "prodlEPB_date", "prodlTO_date"
]

BUTTON_NAMES = [
    "pushButt_generateWord", "pushButton_exportCSV",
    "pushButt_amount", "pushButt_sMinMin", "pushButton_creatThickness",
    "pushButton_creatRasschProchn", "pushButton_creatOstRes",
    "pushButt_ovalnost", "pushButt_tverdost",
    "pushButton_importCSV", "pushButton_saveProject",
    "pushButton_openProject"
]

SPIN_BOX_NAMES = [
    "amount"
]

TABLE_WIDGET = [
    "table_ballons", "table_thick"
]
