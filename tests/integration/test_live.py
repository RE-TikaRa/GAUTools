import os

import pytest

from src.client import GSAUClient
from src.schedule import get_terms


def _has_env_credentials() -> bool:
    return bool(os.getenv("GSAU_USERNAME") and os.getenv("GSAU_PASSWORD"))


def test_live_login_and_terms():
    if not _has_env_credentials():
        pytest.skip("GSAU_USERNAME/GSAU_PASSWORD not set")

    client = GSAUClient(prompt=False)
    assert client.login() is True

    terms = get_terms(client)
    assert terms
