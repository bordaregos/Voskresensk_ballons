#!/usr/bin/env python3
"""CLI: генерация и проверка .docx-шаблонов отчётов.

    python scripts/template_tool.py generate pipeline
    python scripts/template_tool.py generate pipeline --title "Заключение экспертизы промышленной безопасности"
    python scripts/template_tool.py validate templates/Шаблон_трубопровод.docx pipeline

generate создаёт .docx-заготовку ОДИН РАЗ (см. src/services/template_generator.py)
-- дальше файл дорабатывается в Word вручную и инструмент его больше не
трогает. Запускать из корня репозитория.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import TEMPLATES_DIR
from src.organization_config import DEFAULT_ORGANIZATION
from src.services.template_generator import generate_template
from src.services.template_schema import SCHEMAS
from src.services.template_validator import ValidationReport, validate_template

_DEFAULT_TEMPLATE_NAMES = {
    "pipeline": "Шаблон_трубопровод.docx",
}


def _default_output_path(equipment_type_id: str) -> Path:
    name = _DEFAULT_TEMPLATE_NAMES.get(equipment_type_id, f"Шаблон_{equipment_type_id}.docx")
    return TEMPLATES_DIR / name


def _print_report(report: ValidationReport) -> None:
    if not report.issues:
        print("Проблем не найдено.")
        return
    for issue in report.issues:
        print(issue)
    print(f"\nИтого: {len(report.errors)} ошибок, {len(report.warnings)} предупреждений.")


def _require_known_type(equipment_type_id: str) -> bool:
    if equipment_type_id not in SCHEMAS:
        print(
            f"Неизвестный тип объекта: {equipment_type_id!r}. "
            f"Доступные: {', '.join(sorted(SCHEMAS))}",
            file=sys.stderr,
        )
        return False
    return True


def cmd_generate(args: argparse.Namespace) -> int:
    if not _require_known_type(args.equipment_type):
        return 1

    out_path = Path(args.out) if args.out else _default_output_path(args.equipment_type)
    path = generate_template(
        args.equipment_type, DEFAULT_ORGANIZATION, out_path, title_override=args.title,
    )
    print(f"Шаблон сохранён: {path}")
    print("Это заготовка -- доработайте вёрстку/формулировки в Word, повторно не перегенерируется.\n")

    report = validate_template(path, SCHEMAS[args.equipment_type])
    _print_report(report)
    return 0 if report.ok else 1


def cmd_validate(args: argparse.Namespace) -> int:
    if not _require_known_type(args.equipment_type):
        return 1

    report = validate_template(args.docx_path, SCHEMAS[args.equipment_type])
    _print_report(report)
    return 0 if report.ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Сгенерировать шаблон-заготовку .docx")
    gen.add_argument("equipment_type", help=f"Тип объекта ({', '.join(sorted(SCHEMAS))})")
    gen.add_argument("--title", default=None, help="Переопределить заголовок титульного листа")
    gen.add_argument("--out", default=None, help="Путь сохранения (по умолчанию — templates/)")
    gen.set_defaults(func=cmd_generate)

    val = subparsers.add_parser("validate", help="Проверить .docx на соответствие схеме")
    val.add_argument("docx_path", help="Путь к .docx-файлу")
    val.add_argument("equipment_type", help=f"Тип объекта ({', '.join(sorted(SCHEMAS))})")
    val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
