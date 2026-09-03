import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "secret",
    [
        "too-short",
        "replace-with-a-32-byte-secret-value",
        "change-me-this-placeholder-is-long-enough",
    ],
)
def test_rejects_weak_or_placeholder_jwt_secrets(secret: str) -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret_key=secret)


def test_accepts_a_32_byte_jwt_secret() -> None:
    settings = Settings(jwt_secret_key="0123456789abcdef0123456789abcdef")

    assert settings.jwt_secret_key == "0123456789abcdef0123456789abcdef"


def test_requires_jwt_secret_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
