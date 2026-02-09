from gautools.models import Course, Term
from gautools.schedule import get_schedule, get_terms


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeClient:
    def __init__(self, response):
        self._response = response
        self.last_url = None
        self.last_data = None

    def post(self, url, data=None):
        self.last_url = url
        self.last_data = data
        return self._response

    def get(self, url, data=None):
        self.last_url = url
        self.last_data = data
        return self._response


def test_get_schedule_parses_html():
    html = """
    <html>
      <body>
        <table>
          <tr>
            <th>第一大节</th>
            <td><div class="kbcontent">&nbsp;</div></td>
            <td>
              <div class="kbcontent">
                Linear Algebra<br/>
                Dr. Smith<br/>
                1-16周(1-2节) 教1-101
              </div>
            </td>
            <td><div class="kbcontent">&nbsp;</div></td>
            <td><div class="kbcontent">&nbsp;</div></td>
            <td><div class="kbcontent">&nbsp;</div></td>
            <td><div class="kbcontent">&nbsp;</div></td>
            <td><div class="kbcontent">&nbsp;</div></td>
          </tr>
        </table>
      </body>
    </html>
    """
    client = FakeClient(FakeResponse(html))

    courses = get_schedule(client, "2024-2025", "1")

    assert client.last_url == "https://jwgl.gsau.edu.cn/jsxsd/xskb/xskb_list.do"
    assert client.last_data == {"xnxq01id": "2024-2025-1"}
    assert courses == [
        Course(
            name="Linear Algebra",
            teacher="Dr. Smith",
            location="教1-101",
            day="2",
            sections=["1-2"],
            weeks=["1-16"],
        )
    ]


def test_get_schedule_uses_term_suffix():
    html = "<html><body><table></table></body></html>"
    client = FakeClient(FakeResponse(html))

    courses = get_schedule(client, "2024-2025-2", "1")

    assert client.last_data == {"xnxq01id": "2024-2025-2"}
    assert courses == []


def test_get_terms_parses_options():
    html = """
    <html>
      <body>
        <select name="xnxq01id">
          <option value="2024-2025-1">2024-2025学年第一学期</option>
          <option value="2024-2025-2">2024-2025学年第二学期</option>
        </select>
      </body>
    </html>
    """
    client = FakeClient(FakeResponse(html))

    terms = get_terms(client)

    assert client.last_url == "https://jwgl.gsau.edu.cn/jsxsd/xskb/xskb_list.do"
    assert terms == [
        Term(year="2024-2025", term="1", label="2024-2025学年第一学期"),
        Term(year="2024-2025", term="2", label="2024-2025学年第二学期"),
    ]
