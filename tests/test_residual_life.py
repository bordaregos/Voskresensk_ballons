import pytest

from src.services.calculations import calculate_residual_life


def test_happy_path_matches_worked_example():
    result = calculate_residual_life(
        s_isp=28.0,
        c0_plus_dop=2.0,
        s_min_total=26.5,
        years_of_operation=24.0,
        s_max_rasch=21.3,
    )
    assert result.corrosion_rate == 0.146
    assert result.remaining_years == 36.0
    assert result.comment == "> 10 лет"


def test_zero_years_of_operation_raises_value_error():
    with pytest.raises(ValueError):
        calculate_residual_life(
            s_isp=28.0,
            c0_plus_dop=2.0,
            s_min_total=26.5,
            years_of_operation=0.0,
            s_max_rasch=21.3,
        )


def test_zero_corrosion_rate_gives_int_zero_remaining_years():
    # a == 0 когда s_isp + c0_plus_dop == s_min_total
    result = calculate_residual_life(
        s_isp=26.5,
        c0_plus_dop=0.0,
        s_min_total=26.5,
        years_of_operation=24.0,
        s_max_rasch=21.3,
    )
    assert result.corrosion_rate == 0.0
    assert result.remaining_years == 0
    assert isinstance(result.remaining_years, int)


def test_comment_switches_at_ten_years_threshold():
    below = calculate_residual_life(
        s_isp=28.0, c0_plus_dop=2.0, s_min_total=26.5,
        years_of_operation=24.0, s_max_rasch=27.0,
    )
    assert below.comment == "Пересчитать."

    above = calculate_residual_life(
        s_isp=28.0, c0_plus_dop=2.0, s_min_total=26.5,
        years_of_operation=24.0, s_max_rasch=21.3,
    )
    assert above.comment == "> 10 лет"
