import random

from src.services.calculations import (
    calculate_hardness_range,
    generate_hardness_measurements,
)


def test_happy_path_matches_worked_example():
    result = calculate_hardness_range(981.0)
    assert result.hb_min == 265
    assert result.hb_max == 285


def test_allowance_invariant_holds():
    for rm in (0.0, 100.0, 500.0, 950.0, 981.0, 1200.0):
        result = calculate_hardness_range(rm)
        assert result.hb_max - result.hb_min == 20


def test_rm_is_not_hardcoded_different_inputs_give_different_ranges():
    r1 = calculate_hardness_range(981.0)
    r2 = calculate_hardness_range(950.0)
    assert r1 != r2
    assert r2.hb_min == 256
    assert r2.hb_max == 276


def test_generate_measurements_within_range():
    rng = random.Random(11)
    hb_range = calculate_hardness_range(981.0)
    measurements = generate_hardness_measurements(hb_range.hb_min, hb_range.hb_max, rng=rng)
    assert len(measurements) == 20
    for value in measurements:
        assert hb_range.hb_min <= value <= hb_range.hb_max


def test_generate_measurements_respects_custom_count():
    rng = random.Random(2)
    measurements = generate_hardness_measurements(265, 285, count=5, rng=rng)
    assert len(measurements) == 5
