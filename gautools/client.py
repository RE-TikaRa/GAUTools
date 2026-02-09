import base64
import configparser
import getpass
import os
import random
import re
from pathlib import Path

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"


def random_user_agent():
    chrome = f"{random.randint(120, 144)}.0.{random.randint(0, 8000)}.{random.randint(0, 200)}"
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Safari/537.36"
    )


def _random_string(length):
    return "".join(random.choice(AES_CHARS) for _ in range(length))


def _encrypt_password(password, salt):
    if not salt:
        return password
    random_prefix = _random_string(64)
    random_iv = _random_string(16)
    data = random_prefix + password
    key = salt.strip().encode("utf-8")
    iv = random_iv.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def _extract_login_params(html):
    salt = ""
    execution = ""
    salt_match = re.search(r'id="pwdEncryptSalt"\s+value="([^"]*)"', html)
    if salt_match:
        salt = salt_match.group(1)
    pwd_start = html.find('id="pwdLoginDiv"')
    if pwd_start != -1:
        pwd_section = html[pwd_start:]
        execution_match = re.search(r'name="execution"\s+value="([^"]*)"', pwd_section)
        if execution_match:
            execution = execution_match.group(1)
    return salt, execution


class GSAUClient:
    """Core client for GSAU CAS login and requests."""

    LOGIN_ENTRY_URL = "https://jwgl.gsau.edu.cn/"
    LOGIN_POST_URL = (
        "https://authserver.gsau.edu.cn/authserver/login?"
        "service=https%3A%2F%2Fweb.gsau.edu.cn%2Fwengine-auth%2Flogin%3Fcas_login%3Dtrue"
    )
    AUTH_TEST_URL = "https://jwgl.gsau.edu.cn/jsxsd/framework/xsMain.jsp"

    def __init__(self, username=None, password=None, prompt=True, timeout=30):
        self._prompt = prompt
        self._timeout = timeout
        self._username = username
        self._password = password
        self._logged_in = False
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"User-Agent": random_user_agent()})

    def _prompt_credentials(self):
        username = ""
        password = ""
        if not self._prompt:
            return username, password
        try:
            username = input("GSAU username: ").strip()
        except EOFError:
            username = ""
        try:
            password = getpass.getpass("GSAU password: ").strip()
        except EOFError:
            password = ""
        return username, password

    def _env_credentials(self):
        return os.getenv("GSAU_USERNAME", ""), os.getenv("GSAU_PASSWORD", "")

    def _config_credentials(self):
        config = configparser.ConfigParser()
        repo_root = Path(__file__).resolve().parents[1]
        cwd = Path.cwd()
        candidates = [
            cwd / "config.ini",
            repo_root / "config.ini",
            cwd / "config.example.ini",
            repo_root / "config.example.ini",
        ]
        path = None
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
        if path is None:
            return "", ""
        config.read(path, encoding="utf-8")
        username = ""
        password = ""
        if config.has_section("auth"):
            username = config.get("auth", "username", fallback="").strip()
            password = config.get("auth", "password", fallback="").strip()
        return username, password

    def _resolve_credentials(self):
        env_user, env_pass = self._env_credentials()
        config_user, config_pass = self._config_credentials()

        username = self._username or env_user or config_user
        password = self._password or env_pass or config_pass
        if not username or not password:
            prompt_user, prompt_pass = self._prompt_credentials()
            username = username or prompt_user
            password = password or prompt_pass
        return username, password

    def _follow_js_redirects(self, response, max_steps=5):
        current = response
        steps = 0
        while True:
            match = re.search(r"window\.location\.href='([^']+)'", current.text)
            if not match:
                break
            steps += 1
            if steps > max_steps:
                break
            js_url = match.group(1)
            current = self.session.get(
                js_url, allow_redirects=True, timeout=self._timeout
            )
            current.encoding = "utf-8"
        return current

    def login(self):
        username, password = self._resolve_credentials()
        if not username or not password:
            self._logged_in = False
            return False

        entry_response = self.session.get(
            self.LOGIN_ENTRY_URL, allow_redirects=True, timeout=self._timeout
        )
        entry_response.encoding = "utf-8"
        salt, execution = _extract_login_params(entry_response.text)
        if not execution:
            self._logged_in = False
            return False

        encrypted_password = _encrypt_password(password, salt)
        form_data = {
            "username": username,
            "password": encrypted_password,
            "captcha": "",
            "_eventId": "submit",
            "cllt": "userNameLogin",
            "dllt": "generalLogin",
            "lt": "",
            "execution": execution,
        }
        login_response = self.session.post(
            self.LOGIN_POST_URL,
            data=form_data,
            allow_redirects=True,
            timeout=self._timeout,
        )
        login_response.encoding = "utf-8"
        final_response = self._follow_js_redirects(login_response)
        if "authserver" in final_response.url or "pwdLoginDiv" in final_response.text:
            self._logged_in = False
            return False

        test_response = self.session.get(
            self.AUTH_TEST_URL, allow_redirects=True, timeout=self._timeout
        )
        test_response.encoding = "utf-8"
        if "authserver" in test_response.url or "pwdLoginDiv" in test_response.text:
            self._logged_in = False
            return False

        self._logged_in = True
        self._username = username
        self._password = password
        return True

    def ensure_login(self):
        if self._logged_in:
            return True
        return self.login()

    def get(self, url, **kwargs):
        if not self.ensure_login():
            raise RuntimeError("Login failed")
        return self.session.get(url, **kwargs)

    def post(self, url, **kwargs):
        if not self.ensure_login():
            raise RuntimeError("Login failed")
        return self.session.post(url, **kwargs)
