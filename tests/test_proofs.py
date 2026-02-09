from cli import _build_parser, _handle_proof_download
from gautools.proofs import download_proof, get_proof_history, get_proof_templates


class FakeResponse:
    def __init__(self, text=""):
        self.text = text
        self.encoding = None


class FakeBinaryResponse:
    def __init__(self, headers=None, content=b""):
        self.headers = headers or {}
        self.content = content


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


def test_download_proof_uses_content_disposition_filename_with_output_dir(tmp_path):
    output_dir = tmp_path / "downloads"
    output_dir.mkdir()
    headers = {"Content-Disposition": "attachment; filename*=UTF-8''proof%20file.pdf"}
    response = FakeBinaryResponse(headers=headers, content=b"proof-data")
    download_url = "/kxzm/kxzmDownload?generationid=AAA"
    client = FakeClient({"https://jwgl.gsau.edu.cn" + download_url: response})

    saved_path = download_proof(client, download_url, str(output_dir))

    expected_path = output_dir / "proof file.pdf"
    assert saved_path == str(expected_path)
    assert expected_path.read_bytes() == b"proof-data"


def test_download_proof_falls_back_to_output_path_when_no_header(tmp_path):
    output_file = tmp_path / "explicit.pdf"
    response = FakeBinaryResponse(headers={}, content=b"proof-data")
    download_url = "/kxzm/proofs/downloads/proof-file.pdf"
    client = FakeClient({"https://jwgl.gsau.edu.cn" + download_url: response})

    saved_path = download_proof(client, download_url, str(output_file))

    assert saved_path == str(output_file)
    assert output_file.read_bytes() == b"proof-data"


def test_proof_download_parser_sets_handler_and_args():
    parser = _build_parser()
    args = parser.parse_args(["proof-download", "--id", "123", "--output", "out.pdf"])

    assert args.handler is _handle_proof_download
    assert args.id == "123"
    assert args.output == "out.pdf"
