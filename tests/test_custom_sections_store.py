from src.services.custom_sections_store import load_sections, save_sections, next_section_id


def test_load_sections_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "custom_sections.json"

    assert load_sections(path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "data" / "custom_sections.json"
    sections = [
        {"id": "section1", "label": "Программа испытаний"},
        {"id": "section2", "label": "Акт осмотра"},
    ]

    save_sections(sections, path)

    assert path.exists()
    assert load_sections(path) == sections


def test_save_sections_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "custom_sections.json"

    save_sections([], path)

    assert path.exists()


def test_next_section_id_increments_and_persists(tmp_path):
    path = tmp_path / "custom_sections.json"

    assert next_section_id(path) == "section1"
    assert next_section_id(path) == "section2"
    assert next_section_id(path) == "section3"


def test_next_section_id_never_reuses_id_of_deleted_section(tmp_path):
    # _delete_section() (src/ui/main_window.py) убирает раздел из
    # save_sections(), но next_section_id() не должен начать выдавать его id
    # заново -- счётчик отдельная секция файла, save_sections() её не трогает
    # (read-modify-write, см. модульный докстринг).
    path = tmp_path / "custom_sections.json"

    first_id = next_section_id(path)
    save_sections([{"id": first_id, "label": "Временный раздел"}], path)
    save_sections([], path)  # раздел удалили

    assert next_section_id(path) != first_id


def test_next_section_id_independent_of_sections_list(tmp_path):
    path = tmp_path / "custom_sections.json"
    save_sections([{"id": "section5", "label": "Заведено вручную"}], path)

    # next_section_id() не смотрит на текущий список секций -- он свой
    # отдельный счётчик, начинается с 1 независимо от того, что уже
    # записано в sections вручную (тем же способом, что и любой JSON-стор
    # в этом проекте -- никакой синхронизации между секциями файла не
    # подразумевается).
    assert next_section_id(path) == "section1"
