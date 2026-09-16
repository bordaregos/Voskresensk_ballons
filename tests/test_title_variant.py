from src.models.title_variant import TitleVariant


def test_round_trips_through_to_dict_from_dict():
    variant = TitleVariant(
        id="custom-1",
        document_title="Протокол по результатам контроля",
        subtitle_fields=["doc_number", "doc_date"],
    )

    restored = TitleVariant.from_dict(variant.to_dict())

    assert restored == variant


def test_from_dict_defaults_subtitle_fields_to_empty_list():
    variant = TitleVariant.from_dict({"id": "custom-1", "document_title": "Акт осмотра"})

    assert variant.subtitle_fields == []


def test_from_dict_ignores_legacy_content_key():
    # Реальные данные на диске (data/title_variants.json) созданы до отказа
    # от rich-content модели и ещё содержат ключ "content" -- from_dict()
    # должен просто его не читать, а не падать на нём.
    variant = TitleVariant.from_dict({
        "id": "custom-1",
        "document_title": "Акт осмотра",
        "subtitle_fields": ["doc_number"],
        "content": [{"kind": "paragraph", "runs": [{"placeholder": "doc_number"}]}],
    })

    assert variant.subtitle_fields == ["doc_number"]
    assert not hasattr(variant, "content")
