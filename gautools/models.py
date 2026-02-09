from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Course:
    name: str
    teacher: Optional[str] = None
    location: Optional[str] = None
    day: Optional[str] = None
    sections: List[str] = field(default_factory=list)
    weeks: List[str] = field(default_factory=list)
    time: Optional[str] = None


@dataclass
class Grade:
    course_name: str
    score: Optional[str] = None
    credits: Optional[float] = None
    grade_point: Optional[float] = None
    year: Optional[str] = None
    term: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GradeDetail:
    course_name: str
    breakdown: Dict[str, Any] = field(default_factory=dict)
    raw_html: Optional[str] = None


@dataclass
class Term:
    year: str
    term: str
    label: Optional[str] = None


@dataclass
class ProofTemplate:
    name: str
    manage_id: Optional[str] = None
    action: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProofRecord:
    name: str
    generated_at: Optional[str] = None
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    generation_id: Optional[str] = None
    manage_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
