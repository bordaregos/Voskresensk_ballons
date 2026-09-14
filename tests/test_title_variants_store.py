from src.models.title_variant import TitleVariant
from src.services.template_schema import TITLE_VARIANTS
from src.services.title_variants_store import (
    load_title_variants, save_title_variants, get_all_title_variants,
)


def test_load_title_variants_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "title_variants.json"

    assert load_title_variants(path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "data" / "title_variants.json"
    variants = [
        TitleVariant(id="abc123", document_title="Протокол по результатам контроля",
                     subtitle_fields=["doc_number", "reg_number"]),
        TitleVariant(id="def456", document_title="Акт осмотра"),
    ]

    save_title_variants(variants, path)
    loaded = load_title_variants(path)

    assert path.exists()
    assert loaded == variants


def test_save_title_variants_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "title_variants.json"

    save_title_variants([], path)

    assert path.exists()


def test_get_all_title_variants_includes_built_in(tmp_path):
    path = tmp_path / "title_variants.json"

    result = get_all_title_variants(path)

    assert set(TITLE_VARIANTS) <= set(result)
    for variant_id, config in TITLE_VARIANTS.items():
        assert result[variant_id] is config


def test_get_all_title_variants_merges_custom_on_top(tmp_path):
    path = tmp_path / "title_variants.json"
    save_title_variants(
        [TitleVariant(id="custom-1", document_title="Протокол по результатам контроля",
                      subtitle_fields=["doc_number"])],
        path,
    )

    result = get_all_title_variants(path)

    assert "custom-1" in result
    assert result["custom-1"].document_title == "Протокол по результатам контроля"
    assert result["custom-1"].subtitle_fields == ["doc_number"]
    # встроенные варианты остаются на месте
    assert set(TITLE_VARIANTS) <= set(result)
