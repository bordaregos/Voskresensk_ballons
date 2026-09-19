from src.services.formula_engine import (
    parse_formula_number, evaluate_formula, format_formula_result,
)


def _resolve(values):
    return lambda field_id: values.get(field_id)


def test_parse_formula_number_accepts_dot_and_comma():
    assert parse_formula_number("3,5") == 3.5
    assert parse_formula_number("3.5") == 3.5


def test_parse_formula_number_invalid_returns_none():
    assert parse_formula_number("abc") is None


def test_evaluate_formula_empty_returns_none():
    assert evaluate_formula([], _resolve({})) is None


def test_evaluate_formula_number_token():
    tokens = [{"type": "number", "value": "2,5"}]
    assert evaluate_formula(tokens, _resolve({})) == 2.5


def test_evaluate_formula_addition_of_placeholders():
    tokens = [
        {"type": "placeholder", "id": "a"},
        {"type": "op", "value": "+"},
        {"type": "placeholder", "id": "b"},
    ]
    assert evaluate_formula(tokens, _resolve({"a": 2.0, "b": 3.0})) == 5.0


def test_evaluate_formula_respects_operator_precedence():
    # 2 + 3 × 4 = 14, не 20 -- обычный приоритет операций, без явных скобок
    tokens = [
        {"type": "number", "value": "2"},
        {"type": "op", "value": "+"},
        {"type": "number", "value": "3"},
        {"type": "op", "value": "×"},
        {"type": "number", "value": "4"},
    ]
    assert evaluate_formula(tokens, _resolve({})) == 14.0


def test_evaluate_formula_parentheses_override_precedence():
    tokens = [
        {"type": "op", "value": "("},
        {"type": "number", "value": "2"},
        {"type": "op", "value": "+"},
        {"type": "number", "value": "3"},
        {"type": "op", "value": ")"},
        {"type": "op", "value": "×"},
        {"type": "number", "value": "4"},
    ]
    assert evaluate_formula(tokens, _resolve({})) == 20.0


def test_evaluate_formula_unicode_minus_sign():
    # «−» (U+2212) -- то, что реально хранит кнопка минуса в редакторе
    # формул (src/ui/formula_editor_dialog.py), не ASCII "-" -- ast.parse()
    # такой символ как оператор не распознаёт без перевода в _OP_SYMBOLS.
    tokens = [
        {"type": "number", "value": "10"},
        {"type": "op", "value": "−"},
        {"type": "number", "value": "4"},
    ]
    assert evaluate_formula(tokens, _resolve({})) == 6.0


def test_evaluate_formula_division_symbol():
    tokens = [
        {"type": "number", "value": "10"},
        {"type": "op", "value": "÷"},
        {"type": "number", "value": "4"},
    ]
    assert evaluate_formula(tokens, _resolve({})) == 2.5


def test_evaluate_formula_fraction():
    # (2 + 3) / 5 = 1
    tokens = [{
        "type": "fraction",
        "num": [{"type": "number", "value": "2"}, {"type": "op", "value": "+"}, {"type": "number", "value": "3"}],
        "den": [{"type": "number", "value": "5"}],
    }]
    assert evaluate_formula(tokens, _resolve({})) == 1.0


def test_evaluate_formula_missing_placeholder_returns_none():
    tokens = [{"type": "placeholder", "id": "a"}]
    assert evaluate_formula(tokens, _resolve({})) is None


def test_evaluate_formula_non_numeric_placeholder_returns_none():
    tokens = [{"type": "placeholder", "id": "a"}]
    assert evaluate_formula(tokens, _resolve({"a": None})) is None


def test_evaluate_formula_division_by_zero_returns_none():
    tokens = [
        {"type": "number", "value": "1"},
        {"type": "op", "value": "÷"},
        {"type": "number", "value": "0"},
    ]
    assert evaluate_formula(tokens, _resolve({})) is None


def test_evaluate_formula_resolves_reference_to_another_formula():
    # b = a * 2, формула ссылается на b -- должна пройти через formulas и посчитать a*2
    formulas = {"b": {"tokens": [
        {"type": "placeholder", "id": "a"}, {"type": "op", "value": "×"}, {"type": "number", "value": "2"},
    ]}}
    tokens = [{"type": "placeholder", "id": "b"}]
    assert evaluate_formula(tokens, _resolve({"a": 3.0}), formulas) == 6.0


def test_evaluate_formula_detects_direct_cycle():
    # a ссылается на a -- зациклилось бы, если бы не visiting
    formulas = {"a": {"tokens": [{"type": "placeholder", "id": "a"}]}}
    tokens = [{"type": "placeholder", "id": "a"}]
    assert evaluate_formula(tokens, _resolve({}), formulas) is None


def test_evaluate_formula_detects_indirect_cycle():
    formulas = {
        "a": {"tokens": [{"type": "placeholder", "id": "b"}]},
        "b": {"tokens": [{"type": "placeholder", "id": "a"}]},
    }
    tokens = [{"type": "placeholder", "id": "a"}]
    assert evaluate_formula(tokens, _resolve({}), formulas) is None


def test_format_formula_result_none_is_dash():
    assert format_formula_result(None, 2) == "—"


def test_format_formula_result_fixed_decimals_with_comma():
    assert format_formula_result(12.5, 2) == "12,50"
    assert format_formula_result(12.0, 0) == "12"
