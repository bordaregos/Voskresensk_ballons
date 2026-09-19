"""Вычисление пользовательских формул конструктора документов.

Портировано 1:1 из JS-мокапа (docs/design/вводная_часть.html,
evaluateFormula()/tokensToExpr()) -- те же типы токенов, тот же обход
дерева. Используется редактором формул (src/ui/formula_editor_dialog.py,
открывается из ПКМ на чипе плейсхолдера в src/ui/main_window.py) и живым
пересчётом вычисляемых полей в реквизитах.

Токен -- plain dict, JSON-совместимый (хранится в секции field_formulas
data/title_variants.json, см. title_variants_store.load_field_formulas()):
    {"type": "number", "value": "3,5"}
    {"type": "placeholder", "id": "diametr"}
    {"type": "op", "value": "+" | "-" | "×" | "÷" | "(" | ")"}
    {"type": "fraction", "num": [...токены...], "den": [...токены...]}

Формула привязана к field_id в общем каталоге плейсхолдеров, а не к
конкретному варианту -- одна формула действует везде, где встречается этот
плейсхолдер (см. _open_formula_editor() в main_window.py), поэтому
placeholder-токен может ссылаться на ДРУГОЕ вычисляемое поле -- отсюда
рекурсия и защита от циклов (visiting) в evaluate_formula().

В отличие от JS-мокапа (там -- Function('return (...)')() на собранной
строке), готовое выражение здесь считается через ast, а не через eval() --
уже, а не просто безопасно-по-построению набор узлов (числа, +-*/, унарный
минус, скобки), даже притом что сама строка всегда собрана только из
токенов, которые UI и так не даёт заполнить произвольным текстом.
"""

import ast
import operator
from typing import Callable, Dict, FrozenSet, List, Optional

from .formatting import format_ru_fixed, parse_ru

Token = Dict
ResolvePlaceholder = Callable[[str], Optional[float]]

_BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
# "−" (U+2212, знак минуса) -- то, что реально показывает кнопка минуса в
# редакторе формул (см. src/ui/formula_editor_dialog.py) и хранит как
# значение своего op-токена; Python это не тот же символ, что ASCII "-",
# ast.parse() его как оператор не распознаёт -- переводим наравне с ×/÷.
_OP_SYMBOLS = {"×": "*", "÷": "/", "−": "-"}


def parse_formula_number(raw: str) -> Optional[float]:
    """'3,5' и '3.5' -> 3.5 -- ввод не чувствителен к разделителю (см.
    formulaInsertNumber() в мокапе). None при некорректном вводе, а не
    исключение -- вызывающая сторона (evaluate_formula()) просто
    прерывает вычисление и показывает "—", как при незаполненном поле."""
    try:
        return parse_ru(raw)
    except ValueError:
        return None


def _tokens_to_expr(
    tokens: List[Token],
    resolve_placeholder: ResolvePlaceholder,
    formulas: Dict[str, Dict],
    visiting: FrozenSet[str],
) -> Optional[str]:
    parts = []
    for token in tokens:
        ttype = token.get("type")
        if ttype == "number":
            value = parse_formula_number(token.get("value", ""))
            if value is None:
                return None
            parts.append(repr(value))
        elif ttype == "placeholder":
            field_id = token.get("id")
            if field_id in visiting:
                return None  # цикл формул -- поле ссылается само на себя через цепочку других
            if field_id in formulas:
                value = evaluate_formula(
                    formulas[field_id].get("tokens", []), resolve_placeholder, formulas,
                    visiting | {field_id},
                )
            else:
                value = resolve_placeholder(field_id)
            if value is None:
                return None
            parts.append(repr(value))
        elif ttype == "op":
            parts.append(_OP_SYMBOLS.get(token.get("value"), token.get("value", "")))
        elif ttype == "fraction":
            num_expr = _tokens_to_expr(token.get("num", []), resolve_placeholder, formulas, visiting)
            den_expr = _tokens_to_expr(token.get("den", []), resolve_placeholder, formulas, visiting)
            if num_expr is None or den_expr is None:
                return None
            parts.append(f"(({num_expr})/({den_expr}))")
        else:
            return None
    return " ".join(parts) if parts else None


def _eval_ast(node) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_ast(node.operand))
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    raise ValueError(f"Недопустимый узел выражения формулы: {node!r}")


def evaluate_formula(
    tokens: List[Token],
    resolve_placeholder: ResolvePlaceholder,
    formulas: Optional[Dict[str, Dict]] = None,
    visiting: FrozenSet[str] = frozenset(),
) -> Optional[float]:
    """None -- формула пустая, ссылается на незаполненный/нечисловой
    плейсхолдер, зациклилась (visiting) или синтаксически некорректна
    (напр. пустая дробь/незакрытая скобка) -- вызывающая сторона в этом
    случае показывает "—" (format_formula_result()), а не падает.

    formulas -- весь каталог формул (field_id -> {"tokens":.., "decimals":..}),
    нужен для рекурсивного вычисления, если сама формула ссылается на ДРУГОЕ
    вычисляемое поле -- resolve_placeholder() тогда для этого id не
    вызывается вовсе (у него нет ручного значения, оно всегда вычисляемое)."""
    formulas = formulas or {}
    expr = _tokens_to_expr(tokens, resolve_placeholder, formulas, visiting)
    if expr is None:
        return None
    try:
        return _eval_ast(ast.parse(expr, mode="eval"))
    except (ValueError, ZeroDivisionError, SyntaxError, TypeError):
        return None


def format_formula_result(value: Optional[float], decimals: int) -> str:
    """"—" при None (см. evaluate_formula()), иначе -- ФИКСИРОВАННОЕ число
    знаков после запятой (format_ru_fixed()), а не "не больше N, лишние
    нули обрезать": если явно попросили округлить до 2 знаков, результат
    "12,50", а не "12,5" -- иначе выбранное число знаков не всегда было бы
    видно на глаз."""
    if value is None:
        return "—"
    return format_ru_fixed(value, decimals)
