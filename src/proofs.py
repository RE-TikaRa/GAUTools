"""Proof generation helpers."""

from typing import Dict, List, Optional
import os
import re
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from src.models import ProofRecord, ProofTemplate  # type: ignore[reportMissingImports]

BASE_URL = "https://jwgl.gsau.edu.cn"


def _build_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _extract_operate_path(value: str) -> Optional[str]:
    match = re.search(r"operate\(['\"]([^'\"]+)['\"]\)", value)
    if match:
        return match.group(1)
    return None


def _extract_open_window_path(value: str) -> Optional[str]:
    match = re.search(r"openWindow\(['\"]([^'\"]+)['\"]", value)
    if match:
        return match.group(1)
    return None


def _extract_query_value(path: Optional[str], key: str) -> Optional[str]:
    if not path:
        return None
    match = re.search(rf"(?:\?|&){re.escape(key)}=([^&]+)", path)
    if match:
        return match.group(1)
    return None


def _extract_filename(content_disposition: str) -> Optional[str]:
    if not content_disposition:
        return None

    filename_star = re.search(
        r"filename\*\s*=\s*([^;]+)", content_disposition, re.IGNORECASE
    )
    if filename_star:
        value = filename_star.group(1).strip().strip('"').strip("'")
        if "''" in value:
            value = value.split("''", 1)[1]
        value = unquote(value)
        return value or None

    filename_match = re.search(
        r"filename\s*=\s*([^;]+)", content_disposition, re.IGNORECASE
    )
    if filename_match:
        value = filename_match.group(1).strip().strip('"').strip("'")
        return value or None

    return None


def get_proof_templates(client) -> List[ProofTemplate]:
    response = client.get(_build_url("/jsxsd/kxzm/kxzm_manage"))
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text or "", "lxml")
    table = soup.find("table")
    if not table:
        return []

    templates: List[ProofTemplate] = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        name = _clean_text(cells[1].get_text(" ", strip=True))
        if not name:
            continue

        action_path = None
        action_link = cells[2].find("a", onclick=True)
        if action_link:
            action_path = _extract_operate_path(action_link.get("onclick", ""))

        raw: Dict[str, str] = {
            "index": _clean_text(cells[0].get_text(" ", strip=True)),
            "name": name,
            "action_text": _clean_text(cells[2].get_text(" ", strip=True)),
        }

        templates.append(
            ProofTemplate(
                name=name,
                manage_id=_extract_query_value(action_path, "manageid"),
                action=action_path,
                raw=raw,
            )
        )

    return templates


def get_proof_history(client) -> List[ProofRecord]:
    response = client.get(_build_url("/jsxsd/kxzm/kxzm_generationsView"))
    response.encoding = "utf-8"
    soup = BeautifulSoup(response.text or "", "lxml")
    table = soup.find("table")
    if not table:
        return []

    records: List[ProofRecord] = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        name = _clean_text(cells[1].get_text(" ", strip=True))
        if not name:
            continue

        preview_path = None
        download_path = None
        for link in cells[5].find_all("a"):
            href = link.get("href", "")
            onclick = link.get("onclick", "")
            preview_path = preview_path or _extract_open_window_path(href)
            download_path = download_path or _extract_operate_path(onclick)

        raw: Dict[str, str] = {
            "index": _clean_text(cells[0].get_text(" ", strip=True)),
            "name": name,
            "generated_at": _clean_text(cells[2].get_text(" ", strip=True)),
            "generator": _clean_text(cells[3].get_text(" ", strip=True)),
            "status": _clean_text(cells[4].get_text(" ", strip=True)),
            "actions": _clean_text(cells[5].get_text(" ", strip=True)),
        }

        records.append(
            ProofRecord(
                name=name,
                generated_at=raw["generated_at"] or None,
                preview_url=preview_path,
                download_url=download_path,
                generation_id=_extract_query_value(preview_path, "generationid"),
                manage_id=_extract_query_value(download_path, "manageid"),
                raw=raw,
            )
        )

    return records


def download_proof(client, download_url, output_path=None):
    response = client.get(_build_url(download_url))
    filename = _extract_filename(response.headers.get("Content-Disposition", ""))
    if not filename:
        parsed = urlparse(download_url or "")
        filename = os.path.basename(parsed.path) or "proof"

    if output_path:
        if os.path.isdir(output_path):
            final_path = os.path.join(output_path, filename)
        else:
            final_path = output_path
    else:
        final_path = filename

    with open(final_path, "wb") as file_handle:
        file_handle.write(response.content)

    return final_path
