"""Тесты формул ячеек таблицы (src/services/table_formulas.py)."""

import pytest

from src.services import table_formulas as tf


def _text(value):
    return [{"type": "text", "value": value}]


def _formula(expr, decimals=2):
    return [{"type": "formula", "expr": expr, "decimals": decimals}]


def _ev(rows, ph=None):
    def resolve(token):
        return token.get("value", "") if token["type"] == "text" else ph[token["id"]]

    def get_ph(field_id):
        return float(ph[field_id].replace(",", "."))

    return tf.evaluate_table(rows, resolve, get_ph)


def test_arithmetic_and_precedence():
    rows = [[_text("10"), _text("4"), _formula("A1-B1*2^2/8")]]
    texts, errors = _ev(rows)
    assert texts[0][2] == "8,00" and not errors


def test_ru_decimal_comma_and_functions():
    rows = [[_text("1,5"), _text("2,5"), _formula("СУММ(A1:B1)"), _formula("ОКРУГЛ(A1/3;1)", 1)]]
    texts, _ = _ev(rows)
    assert texts[0][2:] == ["4,00", "0,5"]


def test_range_skips_empty_and_text():
    rows = [[_text("1")], [_text("")], [_text("abc")], [_text("3")], [_formula("СРЗНАЧ(A1:A4)")]]
    texts, _ = _ev(rows)
    assert texts[4][0] == "2,00"


def test_min_max_count():
    rows = [[_text("5"), _text("2"), _text("9"), _formula("МАКС(A1:C1)-МИН(A1:C1)"), _formula("СЧЁТ(A1:C1)", 0)]]
    texts, _ = _ev(rows)
    assert texts[0][3:] == ["7,00", "3"]


def test_placeholder_reference():
    rows = [[_formula("{d}*2")]]
    texts, _ = _ev(rows, ph={"d": "465,5"})
    assert texts[0][0] == "931,00"


def test_random_chip_resolved_once_per_cell():
    calls = []

    def resolve(token):
        calls.append(1)
        return str(len(calls))

    rows = [[[{"type": "placeholder", "id": "x"}], _formula("A1+A1")]]
    texts, _ = tf.evaluate_table(rows, resolve, lambda f: 0.0)
    assert texts[0] == ["1", "2,00"] and len(calls) == 1


def test_formula_refers_to_formula():
    rows = [[_text("2"), _formula("A1*3"), _formula("B1+1")]]
    texts, _ = _ev(rows)
    assert texts[0][2] == "7,00"


def test_errors():
    rows = [[_text("x"), _formula("A1+1"), _formula("1/0"), _formula("B2+"), _formula("D1"), _formula("Z9")]]
    texts, errors = _ev(rows)
    assert texts[0][1:] == [tf.ERROR_TEXT] * 5
    assert "не число" in errors[(0, 1)]
    assert "ноль" in errors[(0, 2)]
    assert "вне таблицы" in errors[(0, 5)]


def test_cycle_detected_even_inside_range():
    rows = [[_formula("СУММ(A1:B1)"), _formula("A1")]]
    texts, errors = _ev(rows)
    assert texts[0] == [tf.ERROR_TEXT, tf.ERROR_TEXT]
    assert "Циклическая" in errors[(0, 0)]


def test_validate_expr():
    assert tf.validate_expr("=(A1+B2)/2") is None
    assert tf.validate_expr("A1+") is not None
    assert tf.validate_expr("ФУНК(A1)") is not None
    assert tf.validate_expr("СУММ(A1;") is not None
    assert tf.validate_expr("") is not None


def test_diapason_outside_function_rejected():
    _, errors = _ev([[_text("1"), _formula("A1:A1")]])
    assert (0, 1) in errors


def test_shift_relative_and_absolute():
    assert tf.shift_expr("A1+$B$2+$C3+D$4", 1, 1) == "B2+$B$2+$C4+E$4"
    assert tf.shift_expr("СУММ(A1:A3)", 0, 2) == "СУММ(C1:C3)"
    assert tf.shift_expr("{поле}+A2", 1, 0) == "{поле}+A3"
    assert tf.shift_expr("A1", -1, 0) == tf.REF_ERROR


def test_cell_name():
    assert tf.cell_name(0, 0) == "A1" and tf.cell_name(2, 27) == "AB3"


def test_row_removal_adjusts_refs():
    assert tf.adjust_for_row_removal("A1+A3", 1) == "A1+A2"
    assert tf.adjust_for_row_removal("A1+A2", 1) == tf.REF_ERROR
    assert tf.adjust_for_row_removal("СУММ(A1:A4)", 1) == "СУММ(A1:A3)"
    assert tf.adjust_for_row_removal("СУММ(A2:A2)", 1) == tf.REF_ERROR
    assert tf.adjust_for_row_removal("СУММ(A2:A4)", 1) == "СУММ(A2:A3)"


def test_column_removal_adjusts_refs():
    assert tf.adjust_for_column_removal("C1*A1", 1) == "B1*A1"
    assert tf.adjust_for_column_removal("B1", 1) == tf.REF_ERROR


def test_round_half_up_like_excel():
    texts, _ = _ev([[_formula("ОКРУГЛ(2,5;0)", 0), _formula("ОКРУГЛ(-2,5;0)", 0)]])
    assert texts[0] == ["3", "-3"]


def test_covered_cells_are_empty():
    rows = [[_text("1"), _text("junk"), _formula("СУММ(A1:B1)")]]
    texts, _ = tf.evaluate_table(
        rows, lambda t: t.get("value", ""), lambda f: 0.0, is_covered=lambda r, c: (r, c) == (0, 1)
    )
    assert texts[0] == ["1", "", "1,00"]


def test_postfix_percent_like_excel():
    rows = [[_text("50"), _formula("A1*10%"), _formula("(A1+50)%"), _formula("200*A1%^2", 2)]]
    texts, errors = _ev(rows)
    assert texts[0][1:] == ["5,00", "1,00", "50,00"] and not errors
    assert tf.validate_expr("=(2*(МАКС(B3:B4)-МИН(B3:B4))/(МАКС(B3:B4)+МИН(B3:B4)))*100%") is None
