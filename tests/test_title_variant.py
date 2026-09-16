from src.models.title_variant import TitleVariant, derive_subtitle_fields_from_content


def test_content_round_trips_through_to_dict_from_dict():
    variant = TitleVariant(
        id="custom-1",
        document_title="Протокол по результатам контроля",
        subtitle_fields=["doc_number"],
        content=[
            [{"text": "Протокол №"}, {"placeholder": "doc_number"}],
            [{"text": "Дата: ", "bold": True}, {"placeholder": "doc_date"}],
        ],
    )

    restored = TitleVariant.from_dict(variant.to_dict())

    assert restored == variant


def test_from_dict_defaults_content_to_empty_list_for_legacy_data():
    # Варианты, добавленные до появления content -- в JSON этого ключа нет.
    variant = TitleVariant.from_dict({
        "id": "custom-1", "document_title": "Акт осмотра", "subtitle_fields": ["doc_number"],
    })

    assert variant.content == []


def test_derive_subtitle_fields_from_content_dedupes_in_order_of_first_appearance():
    content = [
        [{"text": "Протокол №"}, {"placeholder": "doc_number"}, {"text": " от "}, {"placeholder": "doc_date"}],
        [{"placeholder": "doc_number"}],  # повтор -- не должен задвоиться
        [{"placeholder": "reg_number"}],
    ]

    assert derive_subtitle_fields_from_content(content) == ["doc_number", "doc_date", "reg_number"]


def test_derive_subtitle_fields_from_content_ignores_text_only_paragraphs():
    content = [[{"text": "Просто текст без плейсхолдеров"}]]

    assert derive_subtitle_fields_from_content(content) == []


def test_derive_subtitle_fields_from_empty_content_is_empty():
    assert derive_subtitle_fields_from_content([]) == []
