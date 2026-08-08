import pytest

from src.services.formatting import (
    format_ru,
    format_ru_fixed,
    parse_ru,
    format_thickness_block,
    format_fio_initials,
    number_to_words_ru,
)


def test_format_ru_float_uses_comma():
    assert format_ru(408.8) == "408,8"


def test_format_ru_int_has_no_decimal_part():
    # Регрессия: смешение format_ru/format_ru_fixed даёт "459,0" вместо "459"
    # в готовом документе (p_pnevma_kgs — целое число).
    assert format_ru(459) == "459"


def test_format_ru_fixed_keeps_trailing_zero():
    assert format_ru_fixed(21.0) == "21,0"
    assert format_ru_fixed(21.3) == "21,3"


def test_format_ru_fixed_custom_ndigits():
    assert format_ru_fixed(0.14567, ndigits=3) == "0,146"


def test_parse_ru_comma_to_float():
    assert parse_ru("12,5") == 12.5


def test_parse_ru_invalid_raises_value_error():
    with pytest.raises(ValueError):
        parse_ru("не число")


def test_format_thickness_block_five_lines_of_four():
    values = [26.5 + i * 0.1 for i in range(20)]
    block = format_thickness_block(values)
    lines = block.split("\n")
    assert len(lines) == 5
    for line in lines:
        assert len(line.split(" ")) == 4


def test_format_thickness_block_uses_comma():
    block = format_thickness_block([26.5, 27.0, 27.5, 28.0])
    assert block == "26,5 27,0 27,5 28,0"


def test_format_fio_initials_first_and_patronymic_shortened():
    # Реальный порядок ввода в Таблице 2 -- Фамилия Имя Отчество
    assert format_fio_initials("Грищенко Сергей Вадимович") == "С. В. Грищенко"


def test_format_fio_initials_wrong_word_count_raises_value_error():
    with pytest.raises(ValueError):
        format_fio_initials("Грищенко")
    with pytest.raises(ValueError):
        format_fio_initials("Грищенко Сергей Вадимович Александрович")


def test_number_to_words_ru_single_digits():
    assert number_to_words_ru(0) == "ноль"
    assert number_to_words_ru(5) == "пять"


def test_number_to_words_ru_teens():
    assert number_to_words_ru(15) == "пятнадцать"


def test_number_to_words_ru_tens_and_units():
    assert number_to_words_ru(20) == "двадцать"
    assert number_to_words_ru(25) == "двадцать пять"


def test_number_to_words_ru_hundreds():
    assert number_to_words_ru(100) == "сто"
    assert number_to_words_ru(152) == "сто пятьдесят два"


def test_number_to_words_ru_out_of_range_raises_value_error():
    with pytest.raises(ValueError):
        number_to_words_ru(-1)
    with pytest.raises(ValueError):
        number_to_words_ru(1000)
