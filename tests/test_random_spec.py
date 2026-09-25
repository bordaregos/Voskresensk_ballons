import random

import pytest

from src.services.random_spec import default_random_spec, generate_random_value, validate_random_spec


def spec(**kw):
    return {**default_random_spec(), **kw}


def test_default_valid():
    assert validate_random_spec(default_random_spec()) is None


@pytest.mark.parametrize("kw", [
    {"low": 5, "high": 5}, {"step": 0}, {"step": 200},
    {"step": 0.5}, {"kind": "float", "decimals": 9}, {"kind": "x"},
])
def test_invalid(kw):
    assert validate_random_spec(spec(**kw)) is not None


def test_int_on_grid():
    s = spec(low=10, high=20, step=5)
    values = {generate_random_value(s, random.Random(i)) for i in range(50)}
    assert values == {"10", "15", "20"}


def test_float_format_and_bounds():
    s = spec(kind="float", low=1, high=2, step=0.1, decimals=2)
    for i in range(100):
        v = generate_random_value(s, random.Random(i))
        assert "," in v and len(v.split(",")[1]) == 2
        assert 1 <= float(v.replace(",", ".")) <= 2.0


def test_generate_invalid_raises():
    with pytest.raises(ValueError):
        generate_random_value(spec(step=0))
