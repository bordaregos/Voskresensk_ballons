from pathlib import Path

from src.models.project import Project
from src.services.workspace import (
    create_document,
    create_object,
    list_documents,
    list_objects,
    sanitize_object_name,
)


def test_list_objects_empty_when_dir_missing(tmp_path):
    assert list_objects(tmp_path / "does-not-exist") == []


def test_list_objects_ignores_top_level_files(tmp_path):
    (tmp_path / "плоский_проект.json").write_text("{}", encoding="utf-8")
    (tmp_path / "КБ ХИММАШ").mkdir()
    (tmp_path / "КАМПО").mkdir()

    assert list_objects(tmp_path) == ["КАМПО", "КБ ХИММАШ"]


def test_create_object_is_idempotent(tmp_path):
    path1 = create_object("КБ ХИММАШ", tmp_path)
    path2 = create_object("КБ ХИММАШ", tmp_path)

    assert path1 == path2
    assert path1.is_dir()


def test_sanitize_object_name_replaces_unsafe_characters():
    assert sanitize_object_name("КБ/ХИММАШ") == "КБ_ХИММАШ"
    assert sanitize_object_name("  КАМПО  ") == "КАМПО"
    assert sanitize_object_name("") == "Новый объект"


def test_create_document_writes_file_and_returns_path(tmp_path):
    object_dir = create_object("КБ ХИММАШ", tmp_path)

    doc_path = create_document(object_dir, "pipeline")

    assert doc_path.exists()
    assert doc_path.parent == object_dir
    project = Project.load_from_file(doc_path)
    assert project.equipment_type == "pipeline"


def test_create_document_names_dont_collide(tmp_path):
    object_dir = create_object("КБ ХИММАШ", tmp_path)

    path1 = create_document(object_dir, "pipeline")
    path2 = create_document(object_dir, "pipeline")

    assert path1 != path2
    assert path1.exists() and path2.exists()


def test_list_documents_filters_by_equipment_type(tmp_path):
    object_dir = create_object("КБ ХИММАШ", tmp_path)
    pipeline_path = create_document(object_dir, "pipeline")
    balloon_project = Project(equipment_type="balloon")
    balloon_project.save_to_file(object_dir / "документ_баллон.json")

    documents = list_documents(object_dir, "pipeline")

    assert [path for path, _ in documents] == [pipeline_path]


def test_list_documents_label_uses_reg_number_or_placeholder(tmp_path):
    object_dir = create_object("КБ ХИММАШ", tmp_path)
    new_doc = create_document(object_dir, "pipeline")

    filled_project = Project(equipment_type="pipeline", report_data={"reg_number": "720291"})
    filled_project.save_to_file(object_dir / "документ_с_рег_номером.json")

    documents = dict(
        (path.name, label) for path, label in list_documents(object_dir, "pipeline")
    )

    assert documents[new_doc.name] == "Новый документ"
    assert documents["документ_с_рег_номером.json"] == "рег.720291"


def test_list_documents_skips_unparseable_json(tmp_path):
    object_dir = create_object("КБ ХИММАШ", tmp_path)
    (object_dir / "мусор.json").write_text("не json{", encoding="utf-8")
    good_path = create_document(object_dir, "pipeline")

    documents = list_documents(object_dir, "pipeline")

    assert [path for path, _ in documents] == [good_path]


def test_list_documents_empty_when_object_dir_missing(tmp_path):
    assert list_documents(tmp_path / "does-not-exist", "pipeline") == []
