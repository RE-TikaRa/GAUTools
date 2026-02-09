from pathlib import Path

from gautools.client import GSAUClient


def test_resolve_credentials_prefers_env_then_config(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[auth]\nusername = from_config\npassword = cfg_pwd\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GSAU_USERNAME", "from_env")
    monkeypatch.setenv("GSAU_PASSWORD", "env_pwd")

    client = GSAUClient(prompt=True)
    monkeypatch.setattr(client, "_prompt_credentials", lambda: ("", ""))

    username, password = client._resolve_credentials()

    assert username == "from_env"
    assert password == "env_pwd"


def test_resolve_credentials_reads_cwd_config_without_prompt(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "[auth]\nusername = config_user\npassword = config_pass\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GSAU_USERNAME", raising=False)
    monkeypatch.delenv("GSAU_PASSWORD", raising=False)

    called = {"prompt": False}
    client = GSAUClient(prompt=True)

    def _fake_prompt():
        called["prompt"] = True
        return "", ""

    monkeypatch.setattr(client, "_prompt_credentials", _fake_prompt)
    username, password = client._resolve_credentials()

    assert username == "config_user"
    assert password == "config_pass"
    assert called["prompt"] is False
