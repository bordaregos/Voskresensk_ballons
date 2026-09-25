"""Тесты объединения ячеек таблицы (src/services/table_merges.py)."""

from src.services import table_merges as tm


def _grid(n_rows, n_cols):
    return [[[{"type": "text", "value": f"{r}{c}"}] for c in range(n_cols)] for r in range(n_rows)]


def _texts(cell):
    return "".join(t["value"] for t in cell)


def test_merge_concatenates_tokens_into_anchor():
    rows, merges = _grid(2, 3), []
    anchor = tm.merge_cells(rows, merges, (0, 0, 0, 1))
    assert anchor == (0, 0)
    assert _texts(rows[0][0]) == "0001"
    assert rows[0][1] == []
    assert merges == [{"r": 0, "c": 0, "rowspan": 1, "colspan": 2}]


def test_merge_single_cell_is_noop():
    rows, merges = _grid(2, 2), []
    assert tm.merge_cells(rows, merges, (1, 1, 1, 1)) is None
    assert merges == []


def test_selection_expands_over_existing_merge():
    merges = [{"r": 0, "c": 1, "rowspan": 2, "colspan": 2}]
    assert tm.expand_rect(merges, (0, 0, 0, 1)) == (0, 0, 1, 2)


def test_merge_absorbs_inner_merge():
    rows = _grid(3, 3)
    merges = [{"r": 0, "c": 0, "rowspan": 1, "colspan": 2}]
    tm.merge_cells(rows, merges, (0, 0, 2, 2))
    assert merges == [{"r": 0, "c": 0, "rowspan": 3, "colspan": 3}]


def test_find_and_covered():
    merges = [{"r": 0, "c": 0, "rowspan": 2, "colspan": 2}]
    assert tm.find_merge(merges, 1, 1) is merges[0]
    assert tm.is_covered(merges, 1, 1)
    assert not tm.is_covered(merges, 0, 0)
    assert tm.find_merge(merges, 2, 2) is None


def test_unmerge():
    merges = [{"r": 0, "c": 0, "rowspan": 2, "colspan": 1}]
    assert tm.unmerge_cell(merges, 1, 0) == (0, 0)
    assert merges == []
    assert tm.unmerge_cell(merges, 0, 0) is None


def test_remove_row_above_shifts_merge():
    rows = _grid(3, 2)
    merges = [{"r": 1, "c": 0, "rowspan": 2, "colspan": 1}]
    tm.remove_row(rows, merges, 0)
    assert merges == [{"r": 0, "c": 0, "rowspan": 2, "colspan": 1}]


def test_remove_row_inside_merge_shrinks_and_drops_degenerate():
    rows = _grid(3, 2)
    merges = [{"r": 0, "c": 0, "rowspan": 2, "colspan": 1}]
    tm.remove_row(rows, merges, 1)
    assert merges == []
    assert len(rows) == 2


def test_remove_anchor_row_moves_tokens_to_new_anchor():
    rows = _grid(3, 2)
    merges = [{"r": 0, "c": 0, "rowspan": 3, "colspan": 1}]
    rows[1][0] = []
    rows[2][0] = []
    tm.remove_row(rows, merges, 0)
    assert merges == [{"r": 0, "c": 0, "rowspan": 2, "colspan": 1}]
    assert _texts(rows[0][0]) == "00"


def test_remove_column_symmetry():
    rows = _grid(2, 3)
    merges = [{"r": 0, "c": 0, "rowspan": 1, "colspan": 3}]
    rows[0][1] = []
    rows[0][2] = []
    tm.remove_column(rows, merges, 0)
    assert merges == [{"r": 0, "c": 0, "rowspan": 1, "colspan": 2}]
    assert _texts(rows[0][0]) == "00"
    assert all(len(row) == 2 for row in rows)


def test_normalize_drops_invalid():
    raw = [
        {"r": 0, "c": 0, "rowspan": 1, "colspan": 2},
        {"r": 0, "c": 1, "rowspan": 2, "colspan": 1},  # пересекается
        {"r": 5, "c": 0, "rowspan": 2, "colspan": 1},  # вне сетки
        {"r": 1, "c": 1, "rowspan": 1, "colspan": 1},  # вырожденное
        {"bad": 1},
    ]
    assert tm.normalize_merges(raw, 2, 2) == [raw[0]]
    assert tm.normalize_merges(None, 2, 2) == []
