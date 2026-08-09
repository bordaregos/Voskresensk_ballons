from src.models.instrument import Instrument
from src.services.instruments_store import load_instruments, save_instruments


def test_load_instruments_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "instruments.json"

    assert load_instruments(path) == []


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "data" / "instruments.json"
    instruments = [
        Instrument(
            id="abc123",
            name="Штангенциркуль ШЦ-II",
            serial_number="12345",
            cert_number="СВД-001 от 01.01.2026",
            documents=["Свидетельство о поверке.pdf", "Паспорт прибора.pdf"],
        ),
        Instrument(id="def456", name="Толщиномер УТ-93П"),
    ]

    save_instruments(instruments, path)
    loaded = load_instruments(path)

    assert path.exists()
    assert loaded == instruments


def test_save_instruments_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "instruments.json"

    save_instruments([], path)

    assert path.exists()
