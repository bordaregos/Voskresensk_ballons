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

from src.config import FRAGMENTS_DIR, TEMPLATES_DIR
from src.organization_config import DEFAULT_ORGANIZATION
from src.services.template_generator import generate_template
from src.services.template_schema import APPENDIX_VARIANTS, INTRO_VARIANTS, SCHEMAS, TITLE_VARIANTS, ReportSchema
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


def cmd_generate_title(args: argparse.Namespace) -> int:
    """Заготовка одного варианта титульного листа конструктора документов
    (Phase 1, см. src/services/template_schema.py, TITLE_VARIANTS) --
    маленький самостоятельный .docx-фрагмент, не целый отчёт. Переиспользует
    generate_template() как есть, передавая ему пустую sections."""
    if args.variant not in TITLE_VARIANTS:
        print(
            f"Неизвестный вариант: {args.variant!r}. Доступные: {', '.join(sorted(TITLE_VARIANTS))}",
            file=sys.stderr,
        )
        return 1

    schema = ReportSchema(equipment_type_id="constructor", title=TITLE_VARIANTS[args.variant], sections=())
    out_path = Path(args.out) if args.out else FRAGMENTS_DIR / f"title_{args.variant}.docx"
    path = generate_template("constructor", DEFAULT_ORGANIZATION, out_path, schema=schema)
    print(f"Шаблон сохранён: {path}")
    print("Это заготовка -- доработайте вёрстку/формулировки в Word, повторно не перегенерируется.\n")

    report = validate_template(path, schema)
    _print_report(report)
    return 0 if report.ok else 1


def cmd_generate_intro(args: argparse.Namespace) -> int:
    """Заготовка одного варианта вводной части конструктора документов --
    та же логика, что и cmd_generate_title(), только под второй,
    независимый реестр (INTRO_VARIANTS) и свой префикс файла фрагмента."""
    if args.variant not in INTRO_VARIANTS:
        print(
            f"Неизвестный вариант: {args.variant!r}. Доступные: {', '.join(sorted(INTRO_VARIANTS))}",
            file=sys.stderr,
        )
        return 1

    schema = ReportSchema(equipment_type_id="constructor", title=INTRO_VARIANTS[args.variant], sections=())
    out_path = Path(args.out) if args.out else FRAGMENTS_DIR / f"intro_{args.variant}.docx"
    path = generate_template("constructor", DEFAULT_ORGANIZATION, out_path, schema=schema)
    print(f"Шаблон сохранён: {path}")
    print("Это заготовка -- доработайте вёрстку/формулировки в Word, повторно не перегенерируется.\n")

    report = validate_template(path, schema)
    _print_report(report)
    return 0 if report.ok else 1


def cmd_generate_appendix(args: argparse.Namespace) -> int:
    """Заготовка одного варианта «Приложения 1» конструктора документов --
    та же логика, что и cmd_generate_intro(), только под третий,
    независимый реестр (APPENDIX_VARIANTS) и свой префикс файла фрагмента."""
    if args.variant not in APPENDIX_VARIANTS:
        print(
            f"Неизвестный вариант: {args.variant!r}. Доступные: {', '.join(sorted(APPENDIX_VARIANTS))}",
            file=sys.stderr,
        )
        return 1

    schema = ReportSchema(equipment_type_id="constructor", title=APPENDIX_VARIANTS[args.variant], sections=())
    out_path = Path(args.out) if args.out else FRAGMENTS_DIR / f"appendix1_{args.variant}.docx"
    path = generate_template("constructor", DEFAULT_ORGANIZATION, out_path, schema=schema)
    print(f"Шаблон сохранён: {path}")
    print("Это заготовка -- доработайте вёрстку/формулировки в Word, повторно не перегенерируется.\n")

    report = validate_template(path, schema)
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

    gen_title = subparsers.add_parser(
        "generate-title", help="Сгенерировать заготовку варианта титульного листа конструктора"
    )
    gen_title.add_argument("variant", help=f"Вариант титула ({', '.join(sorted(TITLE_VARIANTS))})")
    gen_title.add_argument("--out", default=None, help="Путь сохранения (по умолчанию — templates/fragments/)")
    gen_title.set_defaults(func=cmd_generate_title)

    gen_intro = subparsers.add_parser(
        "generate-intro", help="Сгенерировать заготовку варианта вводной части конструктора"
    )
    gen_intro.add_argument("variant", help=f"Вариант вводной части ({', '.join(sorted(INTRO_VARIANTS))})")
    gen_intro.add_argument("--out", default=None, help="Путь сохранения (по умолчанию — templates/fragments/)")
    gen_intro.set_defaults(func=cmd_generate_intro)

    gen_appendix = subparsers.add_parser(
        "generate-appendix", help="Сгенерировать заготовку варианта приложения 1 конструктора"
    )
    gen_appendix.add_argument("variant", help=f"Вариант приложения 1 ({', '.join(sorted(APPENDIX_VARIANTS))})")
    gen_appendix.add_argument("--out", default=None, help="Путь сохранения (по умолчанию — templates/fragments/)")
    gen_appendix.set_defaults(func=cmd_generate_appendix)

    val = subparsers.add_parser("validate", help="Проверить .docx на соответствие схеме")
    val.add_argument("docx_path", help="Путь к .docx-файлу")
    val.add_argument("equipment_type", help=f"Тип объекта ({', '.join(sorted(SCHEMAS))})")
    val.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
