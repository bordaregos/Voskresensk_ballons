from src.models.title_variant import TitleVariant
from src.services.template_schema import TITLE_FIELD_LABELS, TITLE_VARIANTS
from src.services.title_variants_store import (
    load_title_variants, save_title_variants, get_all_title_variants,
    load_field_catalog, save_field_catalog, get_all_field_labels,
    load_hidden_builtin_fields, save_hidden_builtin_fields,
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


def test_load_field_catalog_missing_file_returns_empty_dict(tmp_path):
    path = tmp_path / "title_variants.json"

    assert load_field_catalog(path) == {}


def test_save_and_load_field_catalog_round_trip(tmp_path):
    path = tmp_path / "title_variants.json"
    catalog = {"field_1": "Дата составления", "field_2": "Ответственный"}

    save_field_catalog(catalog, path)

    assert load_field_catalog(path) == catalog


def test_save_title_variants_does_not_clobber_field_catalog(tmp_path):
    path = tmp_path / "title_variants.json"
    save_field_catalog({"field_1": "Дата составления"}, path)

    save_title_variants([TitleVariant(id="custom-1", document_title="Акт осмотра")], path)

    assert load_field_catalog(path) == {"field_1": "Дата составления"}
    assert [v.id for v in load_title_variants(path)] == ["custom-1"]


def test_save_field_catalog_does_not_clobber_title_variants(tmp_path):
    path = tmp_path / "title_variants.json"
    save_title_variants([TitleVariant(id="custom-1", document_title="Акт осмотра")], path)

    save_field_catalog({"field_1": "Дата составления"}, path)

    assert [v.id for v in load_title_variants(path)] == ["custom-1"]
    assert load_field_catalog(path) == {"field_1": "Дата составления"}


def test_get_all_field_labels_includes_built_in(tmp_path):
    path = tmp_path / "title_variants.json"

    result = get_all_field_labels(path)

    assert TITLE_FIELD_LABELS.items() <= result.items()


def test_get_all_field_labels_merges_custom_on_top(tmp_path):
    path = tmp_path / "title_variants.json"
    save_field_catalog({"field_1": "Дата составления"}, path)

    result = get_all_field_labels(path)

    assert result["field_1"] == "Дата составления"
    assert TITLE_FIELD_LABELS.items() <= result.items()


def test_load_hidden_builtin_fields_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "title_variants.json"

    assert load_hidden_builtin_fields(path) == []


def test_save_and_load_hidden_builtin_fields_round_trip(tmp_path):
    path = tmp_path / "title_variants.json"
    builtin_id = next(iter(TITLE_FIELD_LABELS))

    save_hidden_builtin_fields([builtin_id], path)

    assert load_hidden_builtin_fields(path) == [builtin_id]


def test_get_all_field_labels_excludes_hidden_builtin_fields(tmp_path):
    path = tmp_path / "title_variants.json"
    builtin_id = next(iter(TITLE_FIELD_LABELS))
    save_hidden_builtin_fields([builtin_id], path)

    result = get_all_field_labels(path)

    assert builtin_id not in result
    other_builtins = {k: v for k, v in TITLE_FIELD_LABELS.items() if k != builtin_id}
    assert other_builtins.items() <= result.items()


def test_hidden_builtin_fields_does_not_clobber_other_sections(tmp_path):
    path = tmp_path / "title_variants.json"
    save_title_variants([TitleVariant(id="custom-1", document_title="Акт осмотра")], path)
    save_field_catalog({"field_1": "Дата составления"}, path)

    save_hidden_builtin_fields([next(iter(TITLE_FIELD_LABELS))], path)

    assert [v.id for v in load_title_variants(path)] == ["custom-1"]
    assert load_field_catalog(path) == {"field_1": "Дата составления"}
