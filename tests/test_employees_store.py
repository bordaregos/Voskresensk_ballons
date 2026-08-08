from pathlib import Path

from src.models.employee import Employee
from src.services.employees_store import load_employees, save_employees, store_kleishe_image


def test_load_employees_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "employees.json"

    assert load_employees(path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "data" / "employees.json"
    employees = [
        Employee(
            id="abc123",
            position="Эксперт",
            full_name="Иванов Иван Иванович",
            certificates=["УДЛ-001", "УДЛ-002"],
            kleishe_filename="signature.png",
        ),
        Employee(id="def456", position="Инженер", full_name="Петров Пётр Петрович"),
    ]

    save_employees(employees, path)
    loaded = load_employees(path)

    assert path.exists()
    assert loaded == employees


def test_save_employees_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "employees.json"

    save_employees([], path)

    assert path.exists()


def test_store_kleishe_image_copies_file_with_unique_name(tmp_path):
    source = tmp_path / "signature.PNG"
    source.write_bytes(b"fake-image-bytes")
    dest_dir = tmp_path / "kleishe"

    filename = store_kleishe_image(source, dest_dir)

    stored_path = dest_dir / filename
    assert stored_path.exists()
    assert stored_path.read_bytes() == b"fake-image-bytes"
    assert filename.endswith(".png")
    assert filename != source.name


def test_store_kleishe_image_no_collision_for_same_source_name(tmp_path):
    source = tmp_path / "signature.png"
    source.write_bytes(b"data")
    dest_dir = tmp_path / "kleishe"

    filename1 = store_kleishe_image(source, dest_dir)
    filename2 = store_kleishe_image(source, dest_dir)

    assert filename1 != filename2
    assert (dest_dir / filename1).exists()
    assert (dest_dir / filename2).exists()
