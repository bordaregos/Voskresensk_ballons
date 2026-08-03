import random

from src.services.calculations import (
    generate_ovalness_measurement,
    generate_ovalness_measurements,
)


def test_d_max_always_gte_d_min():
    for seed in range(30):
        rng = random.Random(seed)
        m = generate_ovalness_measurement(rng=rng)
        assert m.d_max >= m.d_min


def test_values_within_declared_range():
    rng = random.Random(3)
    m = generate_ovalness_measurement(d_range=(465, 466), rng=rng)
    assert 465 <= m.d_min <= 466
    assert 465 <= m.d_max <= 466


def test_ovalness_formula():
    rng = random.Random(0)
    m = generate_ovalness_measurement(rng=rng)
    expected = round(((2 * (m.d_max - m.d_min)) / (m.d_max + m.d_min)) * 100, 3)
    assert m.ovalness == expected


def test_equal_diameters_give_zero_ovalness():
    m = generate_ovalness_measurement(d_range=(465, 465), rng=random.Random(1))
    assert m.d_min == m.d_max == 465
    assert m.ovalness == 0.0


def test_generate_measurements_returns_requested_count():
    rng = random.Random(9)
    result = generate_ovalness_measurements(count=3, rng=rng)
    assert len(result) == 3
