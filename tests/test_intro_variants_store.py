from src.models.title_variant import TitleVariant
from src.services.template_schema import INTRO_VARIANTS
from src.services.intro_variants_store import (
    load_intro_variants, save_intro_variants, get_all_intro_variants,
)


def test_load_intro_variants_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "intro_variants.json"

    assert load_intro_variants(path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "data" / "intro_variants.json"
    variants = [
        TitleVariant(id="abc123", document_title="Вводная часть — заключение",
                     subtitle_fields=["field_1", "field_2"]),
        TitleVariant(id="def456", document_title="Вводная часть — отчёт"),
    ]

    save_intro_variants(variants, path)
    loaded = load_intro_variants(path)

    assert path.exists()
    assert loaded == variants


def test_save_intro_variants_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "intro_variants.json"

    save_intro_variants([], path)

    assert path.exists()


def test_get_all_intro_variants_includes_built_in(tmp_path):
    path = tmp_path / "intro_variants.json"

    result = get_all_intro_variants(path)

    assert set(INTRO_VARIANTS) <= set(result)
    for variant_id, config in INTRO_VARIANTS.items():
        assert result[variant_id] is config


def test_get_all_intro_variants_merges_custom_on_top(tmp_path):
    path = tmp_path / "intro_variants.json"
    save_intro_variants(
        [TitleVariant(id="custom-1", document_title="Вводная часть — заключение",
                      subtitle_fields=["field_1"])],
        path,
    )

    result = get_all_intro_variants(path)

    assert "custom-1" in result
    assert result["custom-1"].document_title == "Вводная часть — заключение"
    assert result["custom-1"].subtitle_fields == ["field_1"]
    assert set(INTRO_VARIANTS) <= set(result)


def test_intro_and_title_variants_stored_independently(tmp_path):
    # Разные файлы -- сохранение вариантов вводной части не должно задевать
    # соседний title_variants.json и наоборот (они лежат в разных путях по
    # умолчанию, см. src/config.py: TITLE_VARIANTS_FILE/INTRO_VARIANTS_FILE).
    from src.services.title_variants_store import load_title_variants, save_title_variants

    title_path = tmp_path / "title_variants.json"
    intro_path = tmp_path / "intro_variants.json"

    save_title_variants([TitleVariant(id="t-1", document_title="Титульный лист")], title_path)
    save_intro_variants([TitleVariant(id="i-1", document_title="Вводная часть")], intro_path)

    assert [v.id for v in load_title_variants(title_path)] == ["t-1"]
    assert [v.id for v in load_intro_variants(intro_path)] == ["i-1"]


def test_load_variants_save_variants_get_all_variants_aliases_match():
    # _slot_store(slot).load_variants()/save_variants()/get_all_variants()
    # (src/ui/main_window.py) полагаются на то, что эти алиасы -- буквально
    # те же функции, что и load_intro_variants()/save_intro_variants()/
    # get_all_intro_variants(), а не копии с похожим поведением.
    from src.services import intro_variants_store as store

    assert store.load_variants is load_intro_variants
    assert store.save_variants is save_intro_variants
    assert store.get_all_variants is get_all_intro_variants
