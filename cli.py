import argparse
from typing import Any, Callable

from gautools.client import GSAUClient
from gautools.grades import get_grade_detail, get_grades
from gautools.proofs import get_proof_history, get_proof_templates
from gautools.schedule import get_schedule, get_terms
from gautools.utils import print_table, to_csv, to_json


def _format_output(data: Any, output_format: str) -> str:
    if output_format == "json":
        return to_json(data)
    if output_format == "csv":
        return to_csv(data)
    return print_table(data)


def _write_output(text: str, output_path: str | None) -> None:
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return
    print(text)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", help="Academic year, e.g. 2024")
    parser.add_argument("--term", help="Term, e.g. 1 or 2")
    parser.add_argument(
        "--format",
        default="table",
        choices=("table", "json", "csv"),
        help="Output format",
    )
    parser.add_argument("--output", help="Write output to file")


def _require_value(value: Any, label: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{label} is required")


def _handle_schedule(args: argparse.Namespace) -> str:
    _require_value(args.year, "--year")
    _require_value(args.term, "--term")
    client = GSAUClient()
    data = get_schedule(client, args.year, args.term)
    return _format_output(data, args.format)


def _handle_grades(args: argparse.Namespace) -> str:
    client = GSAUClient()
    data = get_grades(client, year=args.year, term=args.term)
    return _format_output(data, args.format)


def _handle_grade_detail(args: argparse.Namespace) -> str:
    client = GSAUClient()
    jxb_id = args.jxb_id
    course_name = args.course_name
    student_id = args.student_id
    student_name = args.student_name

    if not jxb_id:
        _require_value(args.course_name, "--course-name")
        _require_value(args.year, "--year")
        _require_value(args.term, "--term")
        grades = get_grades(client, year=args.year, term=args.term)
        normalized_target = str(args.course_name).strip().lower()
        matched = None
        for grade in grades:
            current = str(grade.course_name).strip().lower()
            if current == normalized_target or normalized_target in current:
                matched = grade
                break
        if not matched:
            raise ValueError("未在该学期成绩中找到匹配课程，请检查 --course-name")
        jxb_id = matched.raw.get("detail_url")
        if not jxb_id:
            raise ValueError("匹配到课程但缺少详情链接，无法获取成绩详情")
        course_name = matched.course_name

    if jxb_id and "pscj_list.do" not in str(jxb_id) and "=" not in str(jxb_id):
        _require_value(student_id, "--student-id")

    data = get_grade_detail(
        client,
        jxb_id=jxb_id,
        year=args.year,
        term=args.term,
        course_name=course_name or "成绩详情",
        student_id=student_id or "",
        student_name=student_name or "",
    )
    return _format_output(data, args.format)


def _handle_terms(args: argparse.Namespace) -> str:
    client = GSAUClient()
    data = get_terms(client)
    return _format_output(data, args.format)


def _handle_proofs(args: argparse.Namespace) -> str:
    client = GSAUClient()
    data = get_proof_templates(client)
    return _format_output(data, args.format)


def _handle_proof_history(args: argparse.Namespace) -> str:
    client = GSAUClient()
    data = get_proof_history(client)
    return _format_output(data, args.format)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gau", description="GSAU command line")
    subparsers = parser.add_subparsers(dest="command", required=True)

    schedule_parser = subparsers.add_parser("schedule", help="Fetch schedule")
    _add_common_options(schedule_parser)
    schedule_parser.set_defaults(handler=_handle_schedule)

    grades_parser = subparsers.add_parser("grades", help="Fetch grades")
    _add_common_options(grades_parser)
    grades_parser.set_defaults(handler=_handle_grades)

    detail_parser = subparsers.add_parser("grade-detail", help="Fetch grade detail")
    _add_common_options(detail_parser)
    detail_parser.add_argument(
        "--jxb-id",
        help="Teaching class id or detail_url; if omitted, auto-match by course name + year + term",
    )
    detail_parser.add_argument(
        "--course-name", help="Course name (required when --jxb-id is omitted)"
    )
    detail_parser.add_argument(
        "--student-id", help="Student id (required only when --jxb-id is plain id)"
    )
    detail_parser.add_argument("--student-name", help="Student name")
    detail_parser.set_defaults(handler=_handle_grade_detail)

    terms_parser = subparsers.add_parser("terms", help="List terms")
    terms_parser.add_argument(
        "--format",
        default="table",
        choices=("table", "json", "csv"),
        help="Output format",
    )
    terms_parser.add_argument("--output", help="Write output to file")
    terms_parser.set_defaults(handler=_handle_terms)

    proofs_parser = subparsers.add_parser(
        "proofs", help="List available proof templates"
    )
    proofs_parser.add_argument(
        "--format",
        default="table",
        choices=("table", "json", "csv"),
        help="Output format",
    )
    proofs_parser.add_argument("--output", help="Write output to file")
    proofs_parser.set_defaults(handler=_handle_proofs)

    history_parser = subparsers.add_parser(
        "proof-history", help="List generated proof records"
    )
    history_parser.add_argument(
        "--format",
        default="table",
        choices=("table", "json", "csv"),
        help="Output format",
    )
    history_parser.add_argument("--output", help="Write output to file")
    history_parser.set_defaults(handler=_handle_proof_history)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    handler: Callable[[argparse.Namespace], str] = args.handler
    try:
        output_text = handler(args)
    except ValueError as exc:
        parser.error(str(exc))
        return
    _write_output(output_text, args.output)


if __name__ == "__main__":
    main()
