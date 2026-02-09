from src import grades


class FakeResponse:
    def __init__(self, *, json_data=None, text=""):
        self._json_data = json_data
        self.text = text
        self.encoding = None

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON payload")
        return self._json_data


class FakeClient:
    def __init__(self, response=None):
        self._response = response
        self.last_url = None
        self.last_data = None
        self.last_params = None
        self.get_responses = {}
        self.post_responses = {}

    def post(self, url, data=None):
        self.last_url = url
        self.last_data = data
        if url in self.post_responses:
            return self.post_responses[url]
        return self._response

    def get(self, url, params=None):
        self.last_url = url
        self.last_params = params
        if url in self.get_responses:
            return self.get_responses[url]
        return self._response


def test_get_grades_parses_items_and_payload():
    html = """
    <html>
        <body>
            <table>
                <tr>
                    <th>课程名称</th>
                    <th>成绩</th>
                    <th>学分</th>
                    <th>绩点</th>
                    <th>学年学期</th>
                    <th>详情</th>
                </tr>
                <tr>
                    <td>Linear Algebra</td>
                    <td>95</td>
                    <td>3</td>
                    <td>4.0</td>
                    <td>2024-2025-1</td>
                    <td>
                        <a href="javascript:openWindow('/jsxsd/kscj/pscj_list.do?jx0404id=JXB001&xs0101id=20240001')">Detail</a>
                    </td>
                </tr>
            </table>
        </body>
    </html>
    """
    response = FakeResponse(text=html)
    client = FakeClient(response)

    grades_list = grades.get_grades(
        client, year="2024-2025", term="1", page=2, show_count=50
    )

    expected_url = f"{grades.BASE_URL}/jsxsd/kscj/cjcx_list"
    assert client.last_url == expected_url
    assert client.last_data == {
        "kksj": "2024-2025-1",
        "kcxz": "",
        "kcmc": "",
        "xsfs": "",
    }
    assert len(grades_list) == 1
    grade = grades_list[0]
    assert grade.course_name == "Linear Algebra"
    assert grade.score == "95"
    assert grade.credits == 3.0
    assert grade.grade_point == 4.0
    assert grade.year == "2024-2025"
    assert grade.term == "1"
    assert (
        grade.raw["detail_url"]
        == "/jsxsd/kscj/pscj_list.do?jx0404id=JXB001&xs0101id=20240001"
    )


def test_get_grade_detail_parses_breakdown_and_payload():
    html = """
    <html>
        <body>
            <table>
                <tr>
                    <th>平时成绩</th>
                    <td>90</td>
                    <th>期末成绩</th>
                    <td>80</td>
                </tr>
            </table>
        </body>
    </html>
    """
    response = FakeResponse(text=html)
    client = FakeClient(response)

    detail = grades.get_grade_detail(
        client,
        jxb_id="JXB001",
        year="2024",
        term="2",
        course_name="Linear Algebra",
        student_id="20240001",
        student_name="Student",
    )

    assert client.last_url == f"{grades.BASE_URL}/jsxsd/kscj/pscj_list.do"
    assert client.last_params == {"xs0101id": "20240001", "jx0404id": "JXB001"}
    assert detail.course_name == "Linear Algebra"
    assert detail.raw_html == html
    assert detail.breakdown == {"平时成绩": "90", "期末成绩": "80"}


def test_get_grade_detail_auto_resolves_from_grade_list():
    list_html = """
    <html>
      <body>
        <table>
          <tr>
            <th>课程名称</th><th>成绩</th><th>详情</th>
          </tr>
          <tr>
            <td>Linear Algebra</td>
            <td>95</td>
            <td>
              <a href="javascript:openWindow('/jsxsd/kscj/pscj_list.do?jx0404id=JXB001&xs0101id=20240001',1000,750)">Detail</a>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    detail_html = """
    <html>
      <body>
        <table>
          <tr><th>平时成绩</th><th>期末成绩</th></tr>
          <tr><td>90</td><td>80</td></tr>
        </table>
      </body>
    </html>
    """
    client = FakeClient()
    client.post_responses[f"{grades.BASE_URL}/jsxsd/kscj/cjcx_list"] = FakeResponse(
        text=list_html
    )
    client.get_responses[
        f"{grades.BASE_URL}/jsxsd/kscj/pscj_list.do?jx0404id=JXB001&xs0101id=20240001"
    ] = FakeResponse(text=detail_html)

    detail = grades.get_grade_detail(
        client,
        jxb_id="",
        year="2024-2025",
        term="1",
        course_name="Linear Algebra",
        student_id="",
        student_name="",
    )

    assert detail.course_name == "Linear Algebra"
    assert detail.breakdown == {"平时成绩": "90", "期末成绩": "80"}
