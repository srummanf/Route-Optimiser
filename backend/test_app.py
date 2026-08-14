import pytest
from fastapi.testclient import TestClient

from app import create_app, get_allowed_origins


def test_configured_origin_is_allowed_with_credentials():
    client = TestClient(create_app("https://app.example.com"))

    response = client.options(
        "/optimize",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unconfigured_origin_is_rejected():
    client = TestClient(create_app("https://app.example.com"))

    response = client.options(
        "/optimize",
        headers={
            "Origin": "https://attacker.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_wildcard_origin_fails_configuration():
    with pytest.raises(ValueError, match="cannot contain '\\*'"):
        get_allowed_origins("*")
