from src.models import Course, Grade, GradeDetail, Term


def test_course_defaults():
    course = Course(name="Linear Algebra")

    assert course.teacher is None
    assert course.location is None
    assert course.day is None
    assert course.sections == []
    assert course.weeks == []
    assert course.time is None


def test_grade_defaults():
    grade = Grade(course_name="Linear Algebra")

    assert grade.score is None
    assert grade.credits is None
    assert grade.grade_point is None
    assert grade.year is None
    assert grade.term is None
    assert grade.raw == {}


def test_grade_detail_defaults():
    detail = GradeDetail(course_name="Linear Algebra")

    assert detail.breakdown == {}
    assert detail.raw_html is None


def test_term_defaults():
    term = Term(year="2024-2025", term="1")

    assert term.label is None
