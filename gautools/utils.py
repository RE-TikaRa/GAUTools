import csv
import json
from dataclasses import asdict, is_dataclass
from io import StringIO


def _normalize_data(data):
    if is_dataclass(data) and not isinstance(data, type):
        return asdict(data)
    if isinstance(data, dict):
        return data
    if isinstance(data, (list, tuple)):
        normalized = []
        for item in data:
            if is_dataclass(item) and not isinstance(item, type):
                normalized.append(asdict(item))
            elif isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append(str(item))
        return normalized
    return str(data)


def _infer_headers(rows):
    headers = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                headers.append(key)
                seen.add(key)
    return headers


def to_json(data):
    normalized = _normalize_data(data)
    return json.dumps(normalized, indent=2)


def to_csv(data):
    normalized = _normalize_data(data)
    if not isinstance(normalized, list):
        return str(normalized)
    if not normalized:
        return ""
    if not all(isinstance(item, dict) for item in normalized):
        return str(normalized)

    headers = _infer_headers(normalized)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in normalized:
        writer.writerow(row)
    return buffer.getvalue()


def print_table(data):
    normalized = _normalize_data(data)
    if not isinstance(normalized, list):
        return str(normalized)
    if not normalized:
        return ""
    if not all(isinstance(item, dict) for item in normalized):
        return str(normalized)

    headers = _infer_headers(normalized)
    rows = []
    for row in normalized:
        rows.append(
            [
                "" if row.get(header) is None else str(row.get(header))
                for header in headers
            ]
        )

    widths = [len(str(header)) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            if len(value) > widths[index]:
                widths[index] = len(value)

    header_line = " | ".join(
        str(header).ljust(widths[index]) for index, header in enumerate(headers)
    )
    separator_line = "-+-".join("-" * widths[index] for index in range(len(headers)))
    row_lines = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, separator_line] + row_lines)
