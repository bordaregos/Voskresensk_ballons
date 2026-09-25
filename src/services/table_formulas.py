"""Формулы ячеек таблицы конструктора документов -- «как в Excel»
(редактор таблиц, src/ui/table_editor_dialog.py).

Ячейка-формула -- токен {"type": "formula", "expr": "(B2-B3)/B2*100",
"decimals": 2} (единственный токен ячейки; ведущий «=» в expr не хранится).

Синтаксис выражения:
    числа           3,5  или  3.5
    ссылки          A1, $B$2 (столбец -- латиницей, строка -- с 1, считая
                    и шапку); диапазон -- A1:C3
    плейсхолдеры    {id_поля} -- числовое значение поля каталога
    операторы       + - * / ^ ( ), а также × ÷ −; постфикс % (5% = 0,05)
    функции         СУММ/SUM, СРЗНАЧ/AVERAGE, МИН/MIN, МАКС/MAX,
                    СЧЁТ/COUNT, ABS/МОДУЛЬ, ОКРУГЛ/ROUND, КОРЕНЬ/SQRT
    разделитель аргументов -- «;» (запятая занята десятичным знаком)

Пустая ячейка в арифметике -- 0, текст, не являющийся числом, -- ошибка;
в диапазонах пустые и нечисловые ячейки пропускаются, как в Excel.
Выражение разбирается собственным рекурсивным спуском, а не eval().

Протягивание (shift_expr) сдвигает относительные ссылки, $ фиксирует;
remap_refs() лежит в основе как протягивания, так и поправки ссылок при
удалении строки/столбца.
"""

import math
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .formatting import format_ru_fixed, parse_ru

ERROR_TEXT = "#ОШИБКА"
REF_ERROR = "#ССЫЛКА!"
DEFAULT_DECIMALS = 2


class FormulaError(ValueError):
    """Ошибка разбора/вычисления формулы; текст -- для пользователя."""


class NotANumberError(FormulaError):
    """В ячейке текст, не являющийся числом (в диапазонах такие ячейки
    пропускаются, в арифметике -- ошибка)."""


@dataclass(frozen=True)
class _Tok:
    kind: str  # num | ref | ph | name | op
    text: str
    start: int
    end: int


_REF_RE = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)(?![A-Za-z0-9_(])")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
_NAME_RE = re.compile(r"[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_.0-9]*")
_OPS = "+-−*/×÷^();:%"


def _tokenize(expr: str) -> List[_Tok]:
    toks: List[_Tok] = []
    i, n = 0, len(expr)
    while i < n:
        ch = expr[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "{":
            end = expr.find("}", i)
            if end == -1 or end == i + 1:
                raise FormulaError("Незакрытый плейсхолдер {…}.")
            toks.append(_Tok("ph", expr[i + 1:end], i, end + 1))
            i = end + 1
            continue
        m = _NUM_RE.match(expr, i)
        if m:
            toks.append(_Tok("num", m.group(), i, m.end()))
            i = m.end()
            continue
        m = _REF_RE.match(expr, i)
        if m:
            toks.append(_Tok("ref", m.group(), i, m.end()))
            i = m.end()
            continue
        m = _NAME_RE.match(expr, i)
        if m:
            toks.append(_Tok("name", m.group(), i, m.end()))
            i = m.end()
            continue
        if ch in _OPS:
            toks.append(_Tok("op", ch, i, i + 1))
            i += 1
            continue
        raise FormulaError(f"Недопустимый символ «{ch}».")
    return toks


def _col_to_index(letters: str) -> int:
    index = 0
    for ch in letters.upper():
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index - 1


def _index_to_col(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def cell_name(r: int, c: int) -> str:
    """(0, 1) -> 'B1'."""
    return f"{_index_to_col(c)}{r + 1}"


def _parse_ref(text: str) -> Tuple[int, int, bool, bool]:
    m = _REF_RE.fullmatch(text)
    return int(m.group(4)) - 1, _col_to_index(m.group(2)), bool(m.group(1)), bool(m.group(3))
    # (row, col, col_absolute, row_absolute)


# -- Разбор -------------------------------------------------------------------

_FUNCS: Dict[str, str] = {
    "СУММ": "sum", "SUM": "sum",
    "СРЗНАЧ": "avg", "AVERAGE": "avg",
    "МИН": "min", "MIN": "min",
    "МАКС": "max", "MAX": "max",
    "СЧЁТ": "count", "СЧЕТ": "count", "COUNT": "count",
    "ABS": "abs", "МОДУЛЬ": "abs",
    "ОКРУГЛ": "round", "ROUND": "round",
    "КОРЕНЬ": "sqrt", "SQRT": "sqrt",
}
_ARITY = {"abs": 1, "sqrt": 1, "round": 2}

Node = tuple


class _Parser:
    def __init__(self, expr: str):
        self.toks = _tokenize(expr)
        self.pos = 0

    def _peek(self) -> Optional[_Tok]:
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def _next(self) -> _Tok:
        tok = self._peek()
        if tok is None:
            raise FormulaError("Выражение обрывается — не хватает операнда или «)».")
        self.pos += 1
        return tok

    def _accept(self, *ops: str) -> Optional[_Tok]:
        tok = self._peek()
        if tok and tok.kind == "op" and tok.text in ops:
            self.pos += 1
            return tok
        return None

    def parse(self) -> Node:
        if not self.toks:
            raise FormulaError("Формула пуста.")
        node = self._expr()
        if self._peek() is not None:
            raise FormulaError(f"Лишний фрагмент «{self._peek().text}».")
        return node

    def _expr(self) -> Node:
        node = self._term()
        while (op := self._accept("+", "-", "−")):
            node = ("bin", "+" if op.text == "+" else "-", node, self._term())
        return node

    def _term(self) -> Node:
        node = self._unary()
        while (op := self._accept("*", "×", "/", "÷")):
            node = ("bin", "*" if op.text in "*×" else "/", node, self._unary())
        return node

    def _unary(self) -> Node:
        if (op := self._accept("+", "-", "−")):
            operand = self._unary()
            return operand if op.text == "+" else ("neg", operand)
        return self._power()

    def _power(self) -> Node:
        base = self._atom()
        while self._accept("%"):
            base = ("bin", "/", base, ("num", 100.0))  # постфиксный процент: 5% = 0,05
        if self._accept("^"):
            return ("bin", "^", base, self._unary())
        return base

    def _atom(self) -> Node:
        tok = self._next()
        if tok.kind == "num":
            return ("num", parse_ru(tok.text))
        if tok.kind == "ph":
            return ("ph", tok.text)
        if tok.kind == "ref":
            first = _parse_ref(tok.text)[:2]
            if self._accept(":"):
                second_tok = self._next()
                if second_tok.kind != "ref":
                    raise FormulaError("После «:» ожидается ссылка на ячейку.")
                second = _parse_ref(second_tok.text)[:2]
                return ("range", first, second)
            return ("ref", first)
        if tok.kind == "name":
            func = _FUNCS.get(tok.text.upper())
            if func is None:
                raise FormulaError(f"Неизвестная функция или имя «{tok.text}».")
            if not self._accept("("):
                raise FormulaError(f"После «{tok.text}» ожидается «(».")
            args = [self._arg()]
            while self._accept(";"):
                args.append(self._arg())
            if not self._accept(")"):
                raise FormulaError("Не закрыта скобка функции.")
            if func in _ARITY and len(args) != _ARITY[func]:
                raise FormulaError(f"«{tok.text}» принимает аргументов: {_ARITY[func]}.")
            return ("func", func, args)
        if tok.text == "(":
            node = self._expr()
            if not self._accept(")"):
                raise FormulaError("Не закрыта скобка.")
            return node
        raise FormulaError(f"Неожиданный фрагмент «{tok.text}».")

    def _arg(self) -> Node:
        return self._expr()


def parse_expr(expr: str) -> Node:
    """Разбирает выражение; FormulaError при синтаксической ошибке."""
    return _Parser(expr.lstrip().lstrip("=")).parse()


# -- Вычисление ---------------------------------------------------------------

# cell(r, c) -> число, None (пустая ячейка) или FormulaError (уже ошибочная /
# нечисловая ячейка -- бросает сам колбэк).
CellGetter = Callable[[int, int], Optional[float]]
# ph(field_id) -> число; ошибку («поле не найдено/не число») бросает сам колбэк.
PlaceholderGetter = Callable[[str], float]


def _range_values(get_cell: CellGetter, first, second) -> List[float]:
    r1, r2 = sorted((first[0], second[0]))
    c1, c2 = sorted((first[1], second[1]))
    values: List[float] = []
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            try:
                value = get_cell(r, c)
            except NotANumberError:
                continue
            if value is not None:
                values.append(value)
    return values


def _eval(node: Node, get_cell: CellGetter, get_ph: PlaceholderGetter) -> float:
    kind = node[0]
    if kind == "num":
        return node[1]
    if kind == "ph":
        return get_ph(node[1])
    if kind == "ref":
        value = get_cell(*node[1])
        return 0.0 if value is None else value
    if kind == "range":
        raise FormulaError("Диапазон допустим только внутри функции, например СУММ(A1:A3).")
    if kind == "neg":
        return -_eval(node[1], get_cell, get_ph)
    if kind == "bin":
        _, op, left, right = node
        a, b = _eval(left, get_cell, get_ph), _eval(right, get_cell, get_ph)
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise FormulaError("Деление на ноль.")
            return a / b
        try:
            result = a ** b
        except (OverflowError, ZeroDivisionError):
            raise FormulaError("Некорректная степень.")
        if isinstance(result, complex):
            raise FormulaError("Некорректная степень.")
        return result
    # func
    _, func, args = node
    if func in ("sum", "avg", "min", "max", "count"):
        values: List[float] = []
        for arg in args:
            if arg[0] == "range":
                values.extend(_range_values(get_cell, arg[1], arg[2]))
            elif arg[0] == "ref":
                try:
                    value = get_cell(*arg[1])
                except NotANumberError:
                    continue
                if value is not None:
                    values.append(value)
            else:
                values.append(_eval(arg, get_cell, get_ph))
        if func == "sum":
            return math.fsum(values)
        if func == "count":
            return float(len(values))
        if not values:
            raise FormulaError("В аргументах функции нет чисел.")
        if func == "avg":
            return math.fsum(values) / len(values)
        return min(values) if func == "min" else max(values)
    x = _eval(args[0], get_cell, get_ph)
    if func == "abs":
        return abs(x)
    if func == "sqrt":
        if x < 0:
            raise FormulaError("Корень из отрицательного числа.")
        return math.sqrt(x)
    digits = _eval(args[1], get_cell, get_ph)
    return _round_half_up(x, int(digits))


def _round_half_up(x: float, digits: int) -> float:
    """Округление «как в Excel» (половина -- от нуля), а не банковское."""
    factor = 10 ** digits
    return math.copysign(math.floor(abs(x) * factor + 0.5) / factor, x)


def evaluate_expr(expr: str, get_cell: CellGetter, get_ph: PlaceholderGetter) -> float:
    """Значение выражения; FormulaError при любой ошибке."""
    result = _eval(parse_expr(expr), get_cell, get_ph)
    if math.isnan(result) or math.isinf(result):
        raise FormulaError("Результат не число.")
    return result


def validate_expr(expr: str) -> Optional[str]:
    """None -- выражение разбирается, иначе текст ошибки для пользователя."""
    try:
        parse_expr(expr)
    except FormulaError as exc:
        return str(exc)
    return None


def referenced_cells(expr: str) -> set:
    """Множество (r, c) ячеек, на которые ссылается выражение (диапазоны
    раскрываются) -- для подсветки в редакторе. Непарсибельное -- пусто."""
    try:
        node = parse_expr(expr)
    except FormulaError:
        return set()
    cells: set = set()

    def walk(n):
        if n[0] == "ref":
            cells.add(n[1])
        elif n[0] == "range":
            (r1, c1), (r2, c2) = n[1], n[2]
            cells.update((r, c) for r in range(min(r1, r2), max(r1, r2) + 1)
                         for c in range(min(c1, c2), max(c1, c2) + 1))
        elif n[0] == "neg":
            walk(n[1])
        elif n[0] == "bin":
            walk(n[2]); walk(n[3])
        elif n[0] == "func":
            for arg in n[2]:
                walk(arg)

    walk(node)
    return cells


# -- Сдвиг/поправка ссылок ----------------------------------------------------

# fn(row, col, is_range_start, is_range_end) -> (row, col) | None (ссылка
# больше не существует).
RefMapper = Callable[[int, int, bool, bool], Optional[Tuple[int, int]]]


def _format_ref(r: int, c: int, col_abs: bool, row_abs: bool) -> str:
    return f"{'$' if col_abs else ''}{_index_to_col(c)}{'$' if row_abs else ''}{r + 1}"


def remap_refs(expr: str, mapper: RefMapper) -> str:
    """Переписывает каждую ссылку выражения через mapper, сохраняя $ и всё
    остальное как есть. Ссылка, которую mapper вернул как None (или
    отрицательную), превращает всю формулу в REF_ERROR. Непарсибельное
    выражение возвращается как есть."""
    try:
        toks = _tokenize(expr)
    except FormulaError:
        return expr
    out, last = [], 0
    for i, tok in enumerate(toks):
        if tok.kind != "ref":
            continue
        prev_colon = i > 0 and toks[i - 1].kind == "op" and toks[i - 1].text == ":"
        next_colon = i + 1 < len(toks) and toks[i + 1].kind == "op" and toks[i + 1].text == ":"
        r, c, col_abs, row_abs = _parse_ref(tok.text)
        mapped = mapper(r, c, next_colon, prev_colon)
        if mapped is None or mapped[0] < 0 or mapped[1] < 0:
            return REF_ERROR
        out.append(expr[last:tok.start])
        out.append(_format_ref(mapped[0], mapped[1], col_abs, row_abs))
        last = tok.end
    out.append(expr[last:])
    return "".join(out)


def shift_expr(expr: str, d_row: int, d_col: int) -> str:
    """Протягивание: относительные части ссылок сдвигаются на (d_row, d_col),
    абсолютные ($) остаются. Выход за край таблицы -- REF_ERROR."""
    try:
        toks = _tokenize(expr)
    except FormulaError:
        return expr
    out, last = [], 0
    for tok in toks:
        if tok.kind != "ref":
            continue
        r, c, col_abs, row_abs = _parse_ref(tok.text)
        nr, nc = (r if row_abs else r + d_row), (c if col_abs else c + d_col)
        if nr < 0 or nc < 0:
            return REF_ERROR
        out.append(expr[last:tok.start])
        out.append(_format_ref(nr, nc, col_abs, row_abs))
        last = tok.end
    out.append(expr[last:])
    return "".join(out)


def _map_after_delete(index: int, deleted: int, is_start: bool, is_end: bool) -> Optional[int]:
    if index < deleted:
        return index
    if index > deleted:
        return index - 1
    # ссылка попала ровно на удалённую линию
    if is_start:
        return index  # начало диапазона -- на её место «съезжает» следующая
    if is_end:
        return index - 1  # конец диапазона -- предыдущая
    return None


def adjust_for_row_removal(expr: str, removed: int) -> str:
    """Поправка ссылок после удаления строки removed (0-based)."""
    def mapper(r, c, is_start, is_end):
        nr = _map_after_delete(r, removed, is_start, is_end)
        return None if nr is None else (nr, c)
    return _fix_ranges(remap_refs(expr, mapper))


def adjust_for_column_removal(expr: str, removed: int) -> str:
    """Поправка ссылок после удаления столбца removed (0-based)."""
    def mapper(r, c, is_start, is_end):
        nc = _map_after_delete(c, removed, is_start, is_end)
        return None if nc is None else (r, nc)
    return _fix_ranges(remap_refs(expr, mapper))


def _fix_ranges(expr: str) -> str:
    """Диапазон, целиком лежавший в удалённой линии, вывернулся наизнанку
    (начало > конца) -- это уже не существующая ссылка."""
    if expr == REF_ERROR:
        return expr
    try:
        toks = _tokenize(expr)
    except FormulaError:
        return expr
    for i, tok in enumerate(toks[:-2]):
        if tok.kind == "ref" and toks[i + 1].text == ":" and toks[i + 2].kind == "ref":
            (r1, c1, _, _), (r2, c2, _, _) = _parse_ref(tok.text), _parse_ref(toks[i + 2].text)
            if r1 > r2 or c1 > c2:
                # Диапазон, целиком лежавший в удалённой линии.
                return REF_ERROR
    return expr


# -- Вычисление всей таблицы --------------------------------------------------

def is_formula_cell(tokens: List[Dict]) -> bool:
    return len(tokens) == 1 and tokens[0].get("type") == "formula"


def evaluate_table(
    rows: List[List[List[Dict]]],
    resolve_token: Callable[[Dict], str],
    get_ph: PlaceholderGetter,
    is_covered: Callable[[int, int], bool] = lambda r, c: False,
) -> Tuple[List[List[str]], Dict[Tuple[int, int], str]]:
    """Тексты всех ячеек таблицы: обычные -- склейка токенов через
    resolve_token (каждая ячейка резолвится ОДИН раз, поэтому рандом-чип
    даёт одно значение и для самой ячейки, и для формул, что на неё
    ссылаются), формулы -- посчитанный результат с русской запятой.

    Возвращает (texts, errors): errors -- (r, c) -> сообщение для ячеек,
    формула которых не посчиталась (в texts там ERROR_TEXT).
    Циклические ссылки -- тоже ошибка ячейки."""
    n_rows = len(rows)
    n_cols = len(rows[0]) if rows else 0
    plain: Dict[Tuple[int, int], str] = {}
    values: Dict[Tuple[int, int], float] = {}
    errors: Dict[Tuple[int, int], str] = {}
    visiting: set = set()

    def plain_text(r: int, c: int) -> str:
        if (r, c) not in plain:
            plain[(r, c)] = "".join(resolve_token(t) for t in rows[r][c])
        return plain[(r, c)]

    def cell_value(r: int, c: int) -> Optional[float]:
        if not (0 <= r < n_rows and 0 <= c < n_cols):
            raise FormulaError(f"Ячейка {cell_name(r, c)} вне таблицы.")
        if is_covered(r, c):
            return None
        tokens = rows[r][c]
        if is_formula_cell(tokens):
            return formula_value(r, c)
        text = plain_text(r, c).strip()
        if not text:
            return None
        try:
            return parse_ru(text)
        except ValueError:
            raise NotANumberError(f"В ячейке {cell_name(r, c)} не число: «{text}».")

    def formula_value(r: int, c: int) -> float:
        key = (r, c)
        if key in values:
            return values[key]
        if key in errors:
            raise FormulaError(errors[key])
        if key in visiting:
            raise FormulaError(f"Циклическая ссылка на {cell_name(r, c)}.")
        visiting.add(key)
        try:
            value = evaluate_expr(rows[r][c][0].get("expr", ""), cell_value, get_ph)
        except FormulaError as exc:
            errors[key] = str(exc)
            raise
        finally:
            visiting.discard(key)
        values[key] = value
        return value

    texts: List[List[str]] = []
    for r in range(n_rows):
        line: List[str] = []
        for c in range(n_cols):
            if is_covered(r, c):
                line.append("")
            elif is_formula_cell(rows[r][c]):
                try:
                    decimals = int(rows[r][c][0].get("decimals", DEFAULT_DECIMALS))
                    line.append(format_ru_fixed(formula_value(r, c), decimals))
                except FormulaError:
                    line.append(ERROR_TEXT)
            else:
                line.append(plain_text(r, c))
        texts.append(line)
    return texts, errors


def evaluate_table_outputs(
    rows: List[List[List[Dict]]],
    outputs: List[Dict],
    resolve_token: Callable[[Dict], str],
    get_ph: PlaceholderGetter,
    is_covered: Callable[[int, int], bool] = lambda r, c: False,
) -> Tuple[List[List[str]], Dict[str, str]]:
    """Как evaluate_table(), плюс значения чипов-результатов таблицы.

    outputs -- [{"field_id", "expr", "decimals"}]: формула чипа пишется по
    тем же правилам, что и формула ячейки (ссылки на ячейки, диапазоны,
    {поле}, функции). Считаются в ОДНОМ проходе с ячейками таблицы -- каждая
    ячейка резолвится один раз, поэтому рандом-чип даёт одно значение и
    ячейке, и чипу-результату, что на неё ссылается.

    Возвращает (texts, values): texts -- как у evaluate_table(), values --
    field_id -> текст с русской запятой (ERROR_TEXT при ошибке формулы,
    "" при пустой формуле)."""
    n_cols = len(rows[0]) if rows else 0
    if not n_cols or not outputs:
        texts, _errors = evaluate_table(rows, resolve_token, get_ph, is_covered)
        return texts, {o.get("field_id", ""): "" for o in outputs}
    # Каждый чип -- дополнительная виртуальная строка с одной ячейкой-формулой:
    # так он делит с таблицей и кэш ячеек, и обнаружение циклов.
    extended = [list(row) for row in rows]
    for output in outputs:
        expr = output.get("expr", "").strip()
        cell = [{"type": "formula", "expr": expr, "decimals": output.get("decimals", DEFAULT_DECIMALS)}] if expr else []
        extended.append([cell] + [[] for _ in range(n_cols - 1)])
    texts_ext, _errors = evaluate_table(extended, resolve_token, get_ph, is_covered)
    n_rows = len(rows)
    values = {o.get("field_id", ""): texts_ext[n_rows + i][0] for i, o in enumerate(outputs)}
    return texts_ext[:n_rows], values
