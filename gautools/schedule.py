"""Schedule fetching helpers."""

from typing import Any, List, Optional, Tuple

import re

from bs4 import BeautifulSoup

from gautools.models import Course, Term  # type: ignore[reportMissingImports]

BASE_URL = "https://jwgl.gsau.edu.cn"


def _build_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"


def _build_term_id(year: Any, term: Any) -> str:
    year_text = "" if year is None else str(year).strip()
    term_text = "" if term is None else str(term).strip()
    if not year_text:
        return ""
    if re.match(r"^\d{4}-\d{4}-\d+$", year_text):
        return year_text
    if term_text:
        return f"{year_text}-{term_text}"
    return year_text


def _split_tokens(value: str) -> List[str]:
    text = value.replace("、", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        result.append(item)
        seen.add(item)
    return result


def _parse_cell_entries(cell_html: str) -> List[List[str]]:
    entries = []
    for part in re.split(r"-{5,}", cell_html):
        text = BeautifulSoup(part, "lxml").get_text("\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        lines = [line.replace("\xa0", " ").strip() for line in lines if line]
        if lines:
            entries.append(lines)
    return entries


def _apply_time_line(
    line: str, weeks: List[str], sections: List[str]
) -> Tuple[Optional[str], bool]:
    working = line
    parsed = False
    weeks_match = re.search(r"([0-9,、\-]+)\s*周", working)
    if weeks_match:
        weeks.extend(_split_tokens(weeks_match.group(1)))
        working = working.replace(weeks_match.group(0), "")
        parsed = True
    sections_match = re.search(r"([0-9,、\-]+)\s*节", working)
    if sections_match:
        sections.extend(_split_tokens(sections_match.group(1)))
        working = working.replace(sections_match.group(0), "")
        parsed = True
    if not parsed:
        return None, False
    cleaned = working.strip(" ()（）,，;；")
    return cleaned or None, True


def _parse_course_lines(lines: List[str], day: int) -> Optional[Course]:
    if not lines:
        return None
    name = lines[0].strip()
    if not name or name == "&nbsp;":
        return None
    teacher = None
    location = None
    weeks: List[str] = []
    sections: List[str] = []
    for raw_line in lines[1:]:
        line = raw_line.replace("\xa0", " ").strip()
        if not line:
            continue
        extracted_location, parsed = _apply_time_line(line, weeks, sections)
        if parsed:
            if extracted_location and location is None:
                location = extracted_location
            continue
        if teacher is None:
            teacher = line
            continue
        if location is None:
            location = line

    return Course(
        name=name,
        teacher=teacher,
        location=location,
        day=str(day),
        sections=_dedupe(sections),
        weeks=_dedupe(weeks),
    )


def _parse_schedule_html(html: str) -> List[Course]:
    soup = BeautifulSoup(html, "lxml")
    courses: List[Course] = []
    for row in soup.find_all("tr"):
        header = row.find("th")
        if not header:
            continue
        cells = row.find_all("td")
        if not cells:
            continue
        for day_index, cell in enumerate(cells, start=1):
            content = cell.find("div", class_="kbcontent")
            if not content:
                continue
            cell_html = content.decode_contents()
            for lines in _parse_cell_entries(cell_html):
                course = _parse_course_lines(lines, day_index)
                if course:
                    courses.append(course)
    return courses


def _split_term_value(value: str) -> Tuple[str, str]:
    parts = [part for part in value.split("-") if part]
    if len(parts) >= 3:
        return "-".join(parts[:-1]), parts[-1]
    if len(parts) == 2:
        return "-".join(parts), ""
    return value, ""


def _parse_term_options(html: str) -> List[Term]:
    soup = BeautifulSoup(html, "lxml")
    select = soup.find("select", attrs={"name": "xnxq01id"}) or soup.find(
        "select", id="xnxq01id"
    )
    if not select:
        return []
    results: List[Term] = []
    for option in select.find_all("option"):
        value = str(option.get("value", "")).strip()
        if not value:
            continue
        year_value, term_value = _split_term_value(value)
        label = option.get_text(strip=True) or None
        results.append(Term(year=year_value, term=term_value, label=label))
    return results


def get_schedule(client, year: Any, term: Any) -> List[Course]:
    term_id = _build_term_id(year, term)
    payload = {"xnxq01id": term_id} if term_id else {}
    response = client.post(_build_url("/jsxsd/xskb/xskb_list.do"), data=payload)
    if hasattr(response, "encoding"):
        response.encoding = "utf-8"
    return _parse_schedule_html(response.text)


def get_terms(client) -> List[Term]:
    response = client.get(_build_url("/jsxsd/xskb/xskb_list.do"))
    if hasattr(response, "encoding"):
        response.encoding = "utf-8"
    return _parse_term_options(response.text)
