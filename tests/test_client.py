from pathlib import Path

from src.client import GSAUClient


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


def test_session_file_path_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GSAU_SESSION_FILE", raising=False)

    client = GSAUClient(prompt=False)
    path = client._session_file_path()

    assert path == Path.home() / ".gsau_session"


def test_session_file_path_from_env(monkeypatch, tmp_path):
    custom_path = tmp_path / "custom_session"
    monkeypatch.setenv("GSAU_SESSION_FILE", str(custom_path))

    client = GSAUClient(prompt=False)
    path = client._session_file_path()

    assert path == custom_path


def test_session_file_path_from_config(monkeypatch, tmp_path):
    custom_path = tmp_path / "config_session"
    config_file = tmp_path / "config.ini"
    config_file.write_text(f"[session]\nfile = {custom_path}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GSAU_SESSION_FILE", raising=False)

    client = GSAUClient(prompt=False)
    path = client._session_file_path()

    assert path == custom_path


def test_save_and_load_session(monkeypatch, tmp_path):
    session_file = tmp_path / "test_session"
    monkeypatch.setenv("GSAU_SESSION_FILE", str(session_file))

    client = GSAUClient(prompt=False)
    client._username = "testuser"
    client.session.cookies.set("test_cookie", "test_value")
    client._save_session()

    assert session_file.exists()

    client2 = GSAUClient(prompt=False)
    client2.session.cookies.clear()
    loaded = client2._load_session()

    assert loaded is True
    assert client2.session.cookies.get("test_cookie") == "test_value"


def test_clear_session(monkeypatch, tmp_path):
    session_file = tmp_path / "test_session"
    monkeypatch.setenv("GSAU_SESSION_FILE", str(session_file))

    client = GSAUClient(prompt=False)
    client._username = "testuser"
    client.session.cookies.set("test_cookie", "test_value")
    client._save_session()

    assert session_file.exists()

    client.clear_session()

    assert not session_file.exists()
    assert client._logged_in is False


def test_load_session_returns_false_when_no_file(monkeypatch, tmp_path):
    session_file = tmp_path / "nonexistent_session"
    monkeypatch.setenv("GSAU_SESSION_FILE", str(session_file))

    client = GSAUClient(prompt=False)
    loaded = client._load_session()

    assert loaded is False


def test_load_session_returns_false_on_invalid_json(monkeypatch, tmp_path):
    session_file = tmp_path / "invalid_session"
    session_file.write_text("not valid json", encoding="utf-8")
    monkeypatch.setenv("GSAU_SESSION_FILE", str(session_file))

    client = GSAUClient(prompt=False)
    loaded = client._load_session()

    assert loaded is False
