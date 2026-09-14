from pathlib import Path

from src.models.employee import Employee
from src.services.employees_store import (
    load_employees, save_employees, store_kleishe_image, resolve_kleishe_path,
    find_employee_id_by_name,
)


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


def test_resolve_kleishe_path_no_employee_id_returns_none(tmp_path):
    employees = [Employee(id="abc123", kleishe_filename="signature.png")]

    assert resolve_kleishe_path(employees, None, tmp_path) is None


def test_resolve_kleishe_path_unknown_employee_id_returns_none(tmp_path):
    employees = [Employee(id="abc123", kleishe_filename="signature.png")]

    assert resolve_kleishe_path(employees, "unknown", tmp_path) is None


def test_resolve_kleishe_path_employee_without_kleishe_returns_none(tmp_path):
    employees = [Employee(id="abc123")]

    assert resolve_kleishe_path(employees, "abc123", tmp_path) is None


def test_resolve_kleishe_path_file_missing_on_disk_returns_none(tmp_path):
    employees = [Employee(id="abc123", kleishe_filename="signature.png")]

    assert resolve_kleishe_path(employees, "abc123", tmp_path) is None


def test_resolve_kleishe_path_returns_existing_file(tmp_path):
    (tmp_path / "signature.png").write_bytes(b"fake-image-bytes")
    employees = [Employee(id="abc123", kleishe_filename="signature.png")]

    result = resolve_kleishe_path(employees, "abc123", tmp_path)

    assert result == tmp_path / "signature.png"


def test_find_employee_id_by_name_exact_match():
    employees = [Employee(id="abc123", full_name="Иванов Иван Иванович")]

    assert find_employee_id_by_name(employees, "Иванов Иван Иванович") == "abc123"


def test_find_employee_id_by_name_no_match_returns_none():
    employees = [Employee(id="abc123", full_name="Иванов Иван Иванович")]

    assert find_employee_id_by_name(employees, "Петров Пётр Петрович") is None


def test_find_employee_id_by_name_empty_name_returns_none():
    employees = [Employee(id="abc123", full_name="Иванов Иван Иванович")]

    assert find_employee_id_by_name(employees, "") is None
    assert find_employee_id_by_name(employees, "   ") is None


def test_find_employee_id_by_name_tolerates_surrounding_whitespace():
    employees = [Employee(id="abc123", full_name="  Иванов Иван Иванович  ")]

    assert find_employee_id_by_name(employees, "Иванов Иван Иванович") == "abc123"
