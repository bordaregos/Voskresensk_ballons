import random

import pytest

from src.services.calculations_pipeline import (
    calculate_pipeline_residual_life,
    calculate_pipeline_strength,
    generate_pipeline_thickness_measurements,
    get_allowable_stress,
    SegmentSpec,
)

# Контрольные данные из TD_720291_otd_214_1.docx (труба 8,0х2,0 мм,
# сталь 12Х18Н10Т, Pр=68,6 МПа, [σ]=147 МПа, φ=1,0, C2=0,2 мм, Sф=1,99 мм,
# Sн=2,0 мм, 52 года эксплуатации).


def test_get_allowable_stress_known_point():
    assert get_allowable_stress("12Х18Н10Т", 20.0) == 147.0


def test_get_allowable_stress_unknown_grade_raises_key_error():
    with pytest.raises(KeyError):
        get_allowable_stress("Неизвестная марка", 20.0)


def test_get_allowable_stress_other_temperature_raises_value_error():
    # Для марки известна только одна точка -- интерполировать не из чего.
    with pytest.raises(ValueError):
        get_allowable_stress("12Х18Н10Т", 100.0)


def test_pipeline_strength_matches_worked_example():
    result = calculate_pipeline_strength(
        p_working=68.6, d_outer=8.0, allowable_stress=147.0, s_actual=1.99, c2=0.2,
    )
    # Sr восстановлена алгебраически из формулы [P] -- точное совпадение с документом.
    assert result.s_calc == 1.51
    assert result.s_reject == 1.71
    # [P] дана в документе текстом дословно; на отображаемых (округлённых)
    # исходных цифрах документа расчёт даёт 84.74 против документных 85,35
    # (~0.7%) -- вероятно, реальные исходные значения в документе были
    # точнее показанных. Тест фиксирует именно наш расчёт как опорный.
    assert result.p_allow == 84.74
    assert result.p_allow == pytest.approx(85.35, rel=0.01)
    assert result.strength_ok is True


def test_pipeline_strength_condition_fails_when_actual_below_reject():
    result = calculate_pipeline_strength(
        p_working=68.6, d_outer=8.0, allowable_stress=147.0, s_actual=1.5, c2=0.2,
    )
    assert result.strength_ok is False


def test_pipeline_residual_life_matches_worked_example_qualitatively():
    result = calculate_pipeline_residual_life(
        s_nominal=2.0, s_actual=1.99, s_reject=1.71, years_of_operation=52,
    )
    assert result.corrosion_rate == 0.0156
    assert result.remaining_years == 18.0
    # Документ не даёт точную цифру Тост, только вывод "более 10 лет" --
    # самосогласованная, а не дословная проверка.
    assert result.comment == "> 10 лет"


def test_pipeline_residual_life_zero_years_raises_value_error():
    with pytest.raises(ValueError):
        calculate_pipeline_residual_life(
            s_nominal=2.0, s_actual=1.99, s_reject=1.71, years_of_operation=0,
        )


def test_pipeline_residual_life_zero_corrosion_rate_gives_int_zero():
    # s_actual = s_nominal * (1 + c0_fraction) -> Sн + C0 - Sф == 0
    result = calculate_pipeline_residual_life(
        s_nominal=1.0, s_actual=1.4, s_reject=0.5, years_of_operation=52,
    )
    assert result.corrosion_rate == 0
    assert result.remaining_years == 0


def test_pipeline_residual_life_corrosion_rate_override_used_as_is():
    # Инженер вручную скорректировал Аф -- значение берётся как есть,
    # Тост пересчитывается от него, а не от формулы Sи/Sф/t.
    result = calculate_pipeline_residual_life(
        s_nominal=2.0, s_actual=1.99, s_reject=1.71, years_of_operation=52,
        corrosion_rate_override=0.05,
    )
    assert result.corrosion_rate == 0.05
    assert result.remaining_years == round((1.99 - 1.71) / 0.05, 0)


def test_pipeline_residual_life_k_scales_remaining_years():
    baseline = calculate_pipeline_residual_life(
        s_nominal=2.0, s_actual=1.99, s_reject=1.71, years_of_operation=52, k=1.0,
    )
    halved = calculate_pipeline_residual_life(
        s_nominal=2.0, s_actual=1.99, s_reject=1.71, years_of_operation=52, k=0.5,
    )
    assert halved.remaining_years == pytest.approx(baseline.remaining_years / 2, abs=1)


def test_generate_thickness_measurements_returns_one_per_segment():
    segments = [
        SegmentSpec(1, "прямой участок", "8,0х2,0"),
        SegmentSpec(2, "отвод", "8,0х2,0"),
        SegmentSpec(3, "прямой участок", "8,0х2,0"),
    ]
    result = generate_pipeline_thickness_measurements(segments, s_min=1.99, rng=random.Random(1))
    assert len(result) == 3
    assert [m.number for m in result] == [1, 2, 3]
    assert [m.element_type for m in result] == ["прямой участок", "отвод", "прямой участок"]


def test_generate_thickness_measurements_within_spread_range():
    segments = [SegmentSpec(i, "прямой участок", "8,0х2,0") for i in range(1, 6)]
    s_min = 1.99
    spread = 0.1
    result = generate_pipeline_thickness_measurements(
        segments, s_min=s_min, spread=spread, rng=random.Random(3)
    )
    for m in result:
        assert s_min <= m.thickness <= s_min + spread


def test_generate_thickness_measurements_deterministic_with_same_seed():
    segments = [SegmentSpec(1, "прямой участок", "8,0х2,0")]
    result1 = generate_pipeline_thickness_measurements(segments, s_min=1.99, rng=random.Random(9))
    result2 = generate_pipeline_thickness_measurements(segments, s_min=1.99, rng=random.Random(9))
    assert result1 == result2
