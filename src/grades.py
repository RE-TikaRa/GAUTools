"""Grade fetching helpers."""

from typing import Any, Dict, List, Optional, Tuple

import re
from urllib.parse import parse_qsl

from bs4 import BeautifulSoup

from src.models import Grade, GradeDetail  # type: ignore[reportMissingImports]

BASE_URL = "https://jwgl.gsau.edu.cn"


def _build_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"


def _safe_json(response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _normalize_term(term: Any) -> str:
    if term is None:
        return ""
    term_text = str(term).strip()
    if term_text in {"1", "01"}:
        return "1"
    if term_text in {"2", "02"}:
        return "2"
    if term_text == "3":
        return "1"
    if term_text == "12":
        return "2"
    return term_text


def _term_to_xqm(term: Any) -> str:
    normalized = _normalize_term(term)
    if normalized == "1":
        return "3"
    if normalized == "2":
        return "12"
    if normalized in {"3", "12"}:
        return normalized
    return normalized


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def _build_term_id(year: Any, term: Any) -> str:
    if year is None:
        return ""
    year_text = str(year).strip()
    if not year_text:
        return ""
    if term is None:
        return year_text
    term_text = _normalize_term(term)
    if not term_text:
        return year_text
    if year_text.endswith(f"-{term_text}"):
        return year_text
    return f"{year_text}-{term_text}"


def _split_year_term(value: str) -> Tuple[Optional[str], Optional[str]]:
    if not value:
        return None, None
    text = _clean_text(value)
    year = None
    term = None
    year_match = re.search(r"(\d{4}\s*-\s*\d{4})", text)
    if year_match:
        year = year_match.group(1).replace(" ", "")
    term_match = re.search(r"(?:\d{4}\s*-\s*\d{4})\D*([12])", text)
    if not term_match:
        term_match = re.search(r"(?:\b|年)([12])\b", text)
    if term_match:
        term = _normalize_term(term_match.group(1))
    return year, term


def _pick_value(row: Dict[str, str], keys: List[str]) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return None


def _match_grade_by_course_name(
    grades: List[Grade], course_name: str, jxb_hint: Optional[str] = None
) -> Optional[Grade]:
    target = _clean_text(course_name)
    if not target:
        return None
    exact: List[Grade] = []
    fuzzy: List[Grade] = []
    for grade in grades:
        current = _clean_text(grade.course_name)
        if not current:
            continue
        if current == target:
            exact.append(grade)
        elif target in current or current in target:
            fuzzy.append(grade)

    candidates = exact or fuzzy
    if not candidates:
        return None
    if jxb_hint:
        for grade in candidates:
            detail_url = str(grade.raw.get("detail_url", "")).strip()
            if jxb_hint in detail_url:
                return grade
    return candidates[0]


def _resolve_detail_url_from_grades(
    client, year: Any, term: Any, course_name: str, jxb_hint: Optional[str] = None
) -> Optional[str]:
    if year is None or term is None:
        return None
    grades = get_grades(client, year=year, term=term)
    matched = _match_grade_by_course_name(grades, course_name, jxb_hint=jxb_hint)
    if not matched:
        return None
    detail_url = str(matched.raw.get("detail_url", "")).strip()
    return detail_url or None


def _extract_detail_url(raw_href: str) -> Optional[str]:
    if not raw_href:
        return None
    href = raw_href.strip()
    if href.startswith("javascript:") and "openWindow" in href:
        match = re.search(r"openWindow\(\s*['\"]([^'\"]+)['\"]\s*(?:,|\))", href)
        if match:
            return match.group(1)
    if "/jsxsd/kscj/pscj_list.do" in href:
        return href
    return None


def _parse_grade_table(
    html: str, fallback_year: Any, fallback_term: Any
) -> List[Grade]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    table = None
    for candidate in soup.find_all("table"):
        if candidate.find("tr"):
            table = candidate
            break
    if not table:
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    header_cells = rows[0].find_all(["th", "td"])
    headers = [_clean_text(cell.get_text(" ", strip=True)) for cell in header_cells]
    if not any(headers):
        return []

    grades: List[Grade] = []
    for row in rows[1:]:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        values = [_clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        row_dict: Dict[str, str] = {}
        for index, value in enumerate(values):
            key = (
                headers[index]
                if index < len(headers) and headers[index]
                else f"col_{index + 1}"
            )
            row_dict[key] = value

        detail_url = None
        for link in row.find_all("a", href=True):
            detail_url = _extract_detail_url(link["href"])
            if detail_url:
                break
        if detail_url:
            row_dict["detail_url"] = detail_url

        course_name = _pick_value(
            row_dict,
            [
                "课程名称",
                "课程",
                "课程名",
                "课程名称/环节",
                "课程名称(环节)",
                "课程名称（环节）",
                "课程名/环节",
            ],
        )
        if not course_name:
            continue

        score = _pick_value(row_dict, ["成绩", "总评成绩", "最终成绩", "总成绩"])
        credits = _to_float(_pick_value(row_dict, ["学分", "课程学分", "学分数"]))
        grade_point = _to_float(_pick_value(row_dict, ["绩点", "成绩绩点", "绩点值"]))
        year = _pick_value(row_dict, ["学年"])
        term_value = _pick_value(row_dict, ["学期"])

        year_term = _pick_value(row_dict, ["学年学期", "学年/学期"])
        if year_term:
            parsed_year, parsed_term = _split_year_term(year_term)
            year = year or parsed_year
            term_value = term_value or parsed_term

        if not year and fallback_year is not None:
            year = str(fallback_year).strip()
        if not term_value and fallback_term is not None:
            term_value = _normalize_term(fallback_term)

        grades.append(
            Grade(
                course_name=course_name,
                score=score,
                credits=credits,
                grade_point=grade_point,
                year=year,
                term=term_value,
                raw=row_dict,
            )
        )

    return grades


def _parse_breakdown_table(html: str) -> Dict[str, Any]:
    breakdown: Dict[str, Any] = {}
    if not html:
        return breakdown

    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        headers = [_clean_text(cell.get_text(" ", strip=True)) for cell in header_cells]
        if sum(1 for header in headers if header) < 2:
            continue
        value_cells = rows[1].find_all(["th", "td"])
        values = [_clean_text(cell.get_text(" ", strip=True)) for cell in value_cells]
        for index, header in enumerate(headers):
            if not header:
                continue
            value = values[index] if index < len(values) else ""
            breakdown[header] = value
        if breakdown:
            return breakdown

    if not tables:
        return breakdown

    for row in tables[0].find_all("tr"):
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        texts = [_clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        index = 0
        while index + 1 < len(texts):
            key = texts[index]
            value = texts[index + 1]
            if key:
                breakdown[key] = value
            index += 2
    return breakdown


def get_grades(
    client, year: Any = None, term: Any = None, page: int = 1, show_count: int = 100
) -> List[Grade]:
    payload = {
        "kksj": _build_term_id(year, term),
        "kcxz": "",
        "kcmc": "",
        "xsfs": "",
    }
    response = client.post(_build_url("/jsxsd/kscj/cjcx_list"), data=payload)
    response.encoding = "utf-8"
    html = response.text or ""
    return _parse_grade_table(html, year, term)


def get_grade_detail(
    client,
    *,
    jxb_id: Any,
    year: Any,
    term: Any,
    course_name: str,
    student_id: Any,
    student_name: str,
) -> GradeDetail:
    detail_url: Optional[str] = None
    params: Optional[Dict[str, str]] = None
    jxb_hint: Optional[str] = None
    if isinstance(jxb_id, dict):
        params = {
            str(key): str(value).strip()
            for key, value in jxb_id.items()
            if value is not None
        }
    elif isinstance(jxb_id, str):
        jxb_text = jxb_id.strip()
        jxb_hint = jxb_text
        if "pscj_list.do" in jxb_text:
            detail_url = _extract_detail_url(jxb_text)
        elif "=" in jxb_text:
            params = {key: value for key, value in parse_qsl(jxb_text) if key}

    if not detail_url and params is None:
        detail_url = _resolve_detail_url_from_grades(
            client,
            year=year,
            term=term,
            course_name=course_name,
            jxb_hint=jxb_hint,
        )

    if detail_url:
        response = client.get(_build_url(detail_url))
    else:
        if params is None:
            jxb_value = "" if jxb_id is None else str(jxb_id).strip()
            student_value = "" if student_id is None else str(student_id).strip()
            if not jxb_value or not student_value:
                raise ValueError(
                    "无法自动定位成绩详情，请提供可用的 --jxb-id，或提供 --course-name/--year/--term 用于自动匹配"
                )
            params = {
                "xs0101id": student_value,
                "jx0404id": jxb_value,
            }
        response = client.get(_build_url("/jsxsd/kscj/pscj_list.do"), params=params)

    response.encoding = "utf-8"
    html = response.text or ""
    breakdown = _parse_breakdown_table(html)
    return GradeDetail(
        course_name=str(course_name).strip(), breakdown=breakdown, raw_html=html
    )
