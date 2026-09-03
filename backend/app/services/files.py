import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from urllib.parse import quote

from app.core.config import Settings


def file_key(path: str) -> str:
    """Convert a stored path to the object key expected by the file-storage adapter."""
    normalized = path.replace("\\", "/").lstrip("/")
    return str(PurePosixPath(normalized))


def presign_download(settings: Settings, path: str) -> tuple[str, datetime]:
    """Create a short-lived URL for the configured object-storage download endpoint."""
    expires_at = datetime.now(UTC) + timedelta(seconds=settings.download_url_ttl_seconds)
    key = file_key(path)
    payload = f"GET\n{key}\n{int(expires_at.timestamp())}".encode()
    signature = hmac.new(settings.jwt_secret_key.encode(), payload, hashlib.sha256).hexdigest()
    base_url = settings.file_download_base_url.rstrip("/")
    url = f"{base_url}/{quote(key, safe='/')}?expires={int(expires_at.timestamp())}&signature={signature}"
    return url, expires_at
