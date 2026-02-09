from gautools.proofs import get_proof_history, get_proof_templates


class FakeResponse:
    def __init__(self, text=""):
        self.text = text
        self.encoding = None


class FakeClient:
    def __init__(self, responses):
        self.responses = responses

    def get(self, url, **kwargs):
        return self.responses[url]


def test_get_proof_templates_parses_manage_ids():
    html = """
    <html><body><table>
      <tr><th>序号</th><th>证明名称</th><th>操作</th></tr>
      <tr>
        <td>1</td>
        <td>在读证明</td>
        <td><a href="javascript:void(0);" onclick="operate('/kxzm/kxzm_generation?manageid=05')">生成并签章</a></td>
      </tr>
      <tr>
        <td>2</td>
        <td>成绩卡</td>
        <td><a href="javascript:void(0);" onclick="operate('/kxzm/kxzm_generation?manageid=01')">生成并签章</a></td>
      </tr>
    </table></body></html>
    """
    client = FakeClient(
        {"https://jwgl.gsau.edu.cn/jsxsd/kxzm/kxzm_manage": FakeResponse(text=html)}
    )

    templates = get_proof_templates(client)

    assert len(templates) == 2
    assert templates[0].name == "在读证明"
    assert templates[0].manage_id == "05"
    assert templates[1].name == "成绩卡"
    assert templates[1].manage_id == "01"


def test_get_proof_history_parses_preview_and_download_urls():
    html = """
    <html><body><table>
      <tr><th>序号</th><th>证明名称</th><th>生成时间</th><th>生成人</th><th>状态</th><th>操作</th></tr>
      <tr>
        <td>1</td>
        <td>在读证明</td>
        <td>2026-02-08 17:25:27</td>
        <td></td>
        <td></td>
        <td>
          <a href="javascript:openWindow('/jsxsd/kxzm/kxzmView?generationid=AAA',1000,750)">预览</a>
          <a href="javascript:void(0);" onclick="operate('/kxzm/kxzmDownload?generationid=AAA&manageid=05&sqlx_mc=在读证明')">下载</a>
        </td>
      </tr>
    </table></body></html>
    """
    client = FakeClient(
        {
            "https://jwgl.gsau.edu.cn/jsxsd/kxzm/kxzm_generationsView": FakeResponse(
                text=html
            )
        }
    )

    records = get_proof_history(client)

    assert len(records) == 1
    assert records[0].name == "在读证明"
    assert records[0].generation_id == "AAA"
    assert records[0].manage_id == "05"
    assert records[0].preview_url == "/jsxsd/kxzm/kxzmView?generationid=AAA"
    assert (
        records[0].download_url
        == "/kxzm/kxzmDownload?generationid=AAA&manageid=05&sqlx_mc=在读证明"
    )
