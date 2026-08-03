import random

from src.services.calculations import generate_thickness_measurements


def test_returns_requested_count():
    rng = random.Random(42)
    result = generate_thickness_measurements(26.5, rng=rng)
    assert len(result) == 20


def test_minimum_is_forced_to_measured_s_min():
    # Инвариант из оригинала: минимум сгенерированного списка ВСЕГДА равен
    # фактически измеренному s_min, даже если случайно сгенерированный
    # минимум оказался другим.
    for seed in range(20):
        rng = random.Random(seed)
        result = generate_thickness_measurements(26.5, rng=rng)
        assert min(result) == 26.5


def test_all_values_within_spread_range():
    rng = random.Random(7)
    s_min = 26.5
    spread = 2.0
    result = generate_thickness_measurements(s_min, spread=spread, rng=rng)
    for value in result:
        assert s_min <= value <= s_min + spread


def test_deterministic_with_same_seed():
    result1 = generate_thickness_measurements(26.5, rng=random.Random(123))
    result2 = generate_thickness_measurements(26.5, rng=random.Random(123))
    assert result1 == result2


def test_zero_count_returns_empty_list():
    result = generate_thickness_measurements(26.5, count=0, rng=random.Random(1))
    assert result == []


def test_respects_custom_count():
    rng = random.Random(5)
    result = generate_thickness_measurements(26.5, count=5, rng=rng)
    assert len(result) == 5
