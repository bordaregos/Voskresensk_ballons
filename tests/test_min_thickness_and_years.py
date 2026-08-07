import pytest

from src.services.calculations import find_min_thickness, format_year_range


def test_find_min_thickness_empty_list_raises():
    with pytest.raises(ValueError):
        find_min_thickness([])


def test_find_min_thickness_returns_value_and_index():
    result = find_min_thickness([5.2, 3.1, 4.0])
    assert result.s_min == 3.1
    assert result.s_min_index == 1


def test_find_min_thickness_duplicate_minimum_returns_first_index():
    result = find_min_thickness([3.1, 5.2, 3.1])
    assert result.s_min == 3.1
    assert result.s_min_index == 0


def test_format_year_range_empty_list():
    assert format_year_range([]) == "Нет данных"


def test_format_year_range_single_year():
    assert format_year_range([2020]) == "2020 г."


def test_format_year_range_same_year_repeated():
    assert format_year_range([2020, 2020, 2020]) == "2020 г."


def test_format_year_range_multiple_years():
    assert format_year_range([2018, 2020]) == "2018 - 2020 гг."


def test_format_year_range_unordered_input():
    assert format_year_range([2020, 2016, 2018]) == "2016 - 2020 гг."
