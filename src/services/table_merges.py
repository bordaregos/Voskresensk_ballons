"""Объединение ячеек таблицы редактора таблиц (src/ui/table_editor_dialog.py).

Модель: сетка `rows` остаётся полной прямоугольной (rows × cols), а
объединения хранятся отдельным необязательным списком `merges` --
[{"r": .., "c": .., "rowspan": .., "colspan": ..}, ...], где (r, c) --
левая верхняя («якорная») ячейка области. Токены объединённой ячейки
живут только в якоре; остальные ячейки области в `rows` остаются пустыми
списками и в интерфейсе/документе не показываются. Таблица без ключа
`merges` (сохранённая до появления этой возможности) -- просто без
объединений.

Все функции чистые, без Qt; функции, меняющие `rows`/`merges`, правят их
на месте.
"""

from typing import Dict, List, Optional, Tuple

Rect = Tuple[int, int, int, int]  # (r1, c1, r2, c2) включительно


def _rect_of(merge: Dict) -> Rect:
    return (
        merge["r"], merge["c"],
        merge["r"] + merge["rowspan"] - 1, merge["c"] + merge["colspan"] - 1,
    )


def _intersects(a: Rect, b: Rect) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def find_merge(merges: List[Dict], r: int, c: int) -> Optional[Dict]:
    """Объединение, накрывающее ячейку (r, c), включая её якорь, либо None."""
    for merge in merges:
        r1, c1, r2, c2 = _rect_of(merge)
        if r1 <= r <= r2 and c1 <= c <= c2:
            return merge
    return None


def is_covered(merges: List[Dict], r: int, c: int) -> bool:
    """Ячейка скрыта под чужим якорем (сама якорем не является)."""
    merge = find_merge(merges, r, c)
    return merge is not None and (merge["r"], merge["c"]) != (r, c)


def normalize_merges(merges: Optional[List[Dict]], n_rows: int, n_cols: int) -> List[Dict]:
    """Копия списка без некорректных записей: выходящих за сетку,
    вырожденных (1×1) и пересекающихся с уже принятыми."""
    result: List[Dict] = []
    for merge in merges or []:
        try:
            item = {k: int(merge[k]) for k in ("r", "c", "rowspan", "colspan")}
        except (KeyError, TypeError, ValueError):
            continue
        rect = _rect_of(item)
        if item["r"] < 0 or item["c"] < 0 or item["rowspan"] < 1 or item["colspan"] < 1:
            continue
        if rect[2] >= n_rows or rect[3] >= n_cols:
            continue
        if item["rowspan"] == 1 and item["colspan"] == 1:
            continue
        if any(_intersects(rect, _rect_of(other)) for other in result):
            continue
        result.append(item)
    return result


def expand_rect(merges: List[Dict], rect: Rect) -> Rect:
    """Расширяет прямоугольник выделения так, чтобы он не рассекал
    существующие объединения (повторяется до неподвижной точки)."""
    r1, c1, r2, c2 = min(rect[0], rect[2]), min(rect[1], rect[3]), max(rect[0], rect[2]), max(rect[1], rect[3])
    changed = True
    while changed:
        changed = False
        for merge in merges:
            m = _rect_of(merge)
            if _intersects((r1, c1, r2, c2), m):
                n = (min(r1, m[0]), min(c1, m[1]), max(r2, m[2]), max(c2, m[3]))
                if n != (r1, c1, r2, c2):
                    r1, c1, r2, c2 = n
                    changed = True
    return r1, c1, r2, c2


def merge_cells(rows: List[List[List[Dict]]], merges: List[Dict], rect: Rect) -> Optional[Tuple[int, int]]:
    """Объединяет ячейки прямоугольника (после expand_rect). Токены всех
    ячеек областей склеиваются в якорь в порядке строк; остальные
    очищаются. Внутри области старые объединения поглощаются. Возвращает
    координаты якоря или None, если объединять нечего (одна ячейка)."""
    r1, c1, r2, c2 = expand_rect(merges, rect)
    if r1 == r2 and c1 == c2:
        return None
    combined: List[Dict] = []
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            combined.extend(rows[r][c])
            if (r, c) != (r1, c1):
                rows[r][c] = []
    rows[r1][c1][:] = combined
    merges[:] = [m for m in merges if not _intersects(_rect_of(m), (r1, c1, r2, c2))]
    merges.append({"r": r1, "c": c1, "rowspan": r2 - r1 + 1, "colspan": c2 - c1 + 1})
    return r1, c1


def unmerge_cell(merges: List[Dict], r: int, c: int) -> Optional[Tuple[int, int]]:
    """Разъединяет объединение, накрывающее (r, c). Возвращает координаты
    якоря или None, если ячейка не была объединена."""
    merge = find_merge(merges, r, c)
    if merge is None:
        return None
    merges.remove(merge)
    return merge["r"], merge["c"]


def remove_row(rows: List[List[List[Dict]]], merges: List[Dict], index: int) -> None:
    """Удаляет строку, сжимая затронутые объединения. Если удаляется
    строка якоря высокого объединения, его токены переезжают в новый
    якорь (ячейку строки ниже)."""
    updated: List[Dict] = []
    for merge in merges:
        r1, _, r2, _ = _rect_of(merge)
        if index < r1:
            merge["r"] -= 1
        elif r1 <= index <= r2:
            if merge["rowspan"] == 1:
                continue
            if index == r1:
                rows[index + 1][merge["c"]][:] = rows[index][merge["c"]]
            merge["rowspan"] -= 1  # якорь после pop() остаётся на индексе r1
        updated.append(merge)
    rows.pop(index)
    merges[:] = [m for m in updated if m["rowspan"] > 1 or m["colspan"] > 1]


def remove_column(rows: List[List[List[Dict]]], merges: List[Dict], index: int) -> None:
    """Столбцовый аналог remove_row()."""
    updated: List[Dict] = []
    for merge in merges:
        _, c1, _, c2 = _rect_of(merge)
        if index < c1:
            merge["c"] -= 1
        elif c1 <= index <= c2:
            if merge["colspan"] == 1:
                continue
            if index == c1:
                rows[merge["r"]][index + 1][:] = rows[merge["r"]][index]
            merge["colspan"] -= 1  # якорь после pop() остаётся на индексе c1
        updated.append(merge)
    for row in rows:
        row.pop(index)
    merges[:] = [m for m in updated if m["rowspan"] > 1 or m["colspan"] > 1]
