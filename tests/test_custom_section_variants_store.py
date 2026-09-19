from src.models.title_variant import TitleVariant
from src.services.custom_section_variants_store import (
    load_variants, save_variants, get_all_variants,
)


def test_load_variants_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "custom_section_variants.json"

    assert load_variants("section1", path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "data" / "custom_section_variants.json"
    variants = [
        TitleVariant(id="abc123", document_title="Вариант раздела",
                     subtitle_fields=["field_1", "field_2"]),
        TitleVariant(id="def456", document_title="Второй вариант"),
    ]

    save_variants("section1", variants, path)
    loaded = load_variants("section1", path)

    assert path.exists()
    assert loaded == variants


def test_save_variants_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "custom_section_variants.json"

    save_variants("section1", [], path)

    assert path.exists()


def test_get_all_variants_has_no_builtins(tmp_path):
    # В отличие от get_all_title_variants()/get_all_intro_variants() --
    # пользовательский раздел всегда стартует пустым, встроенных вариантов
    # у него не бывает (см. src/config.py, find_section_template()).
    path = tmp_path / "custom_section_variants.json"

    assert get_all_variants("section1", path) == {}


def test_get_all_variants_reflects_saved(tmp_path):
    path = tmp_path / "custom_section_variants.json"
    save_variants(
        "section1",
        [TitleVariant(id="v-1", document_title="Программа испытаний", subtitle_fields=["field_1"])],
        path,
    )

    result = get_all_variants("section1", path)

    assert "v-1" in result
    assert result["v-1"].document_title == "Программа испытаний"
    assert result["v-1"].subtitle_fields == ["field_1"]


def test_different_sections_stored_independently_in_one_file(tmp_path):
    # В отличие от title/intro/appendix1 (отдельный файл на слот) --
    # разделы, заведённые оператором, делят один файл, по одному ключу на
    # раздел (см. модульный докстринг) -- запись одного не должна задевать
    # соседние.
    path = tmp_path / "custom_section_variants.json"

    save_variants("section1", [TitleVariant(id="a-1", document_title="Раздел A")], path)
    save_variants("section2", [TitleVariant(id="b-1", document_title="Раздел B")], path)

    assert [v.id for v in load_variants("section1", path)] == ["a-1"]
    assert [v.id for v in load_variants("section2", path)] == ["b-1"]


def test_save_variants_for_one_section_does_not_touch_another(tmp_path):
    path = tmp_path / "custom_section_variants.json"
    save_variants("section1", [TitleVariant(id="a-1", document_title="Раздел A")], path)

    save_variants("section2", [TitleVariant(id="b-1", document_title="Раздел B")], path)
    save_variants("section2", [], path)

    assert [v.id for v in load_variants("section1", path)] == ["a-1"]
    assert load_variants("section2", path) == []
