from __future__ import annotations

import logging
import mimetypes
import secrets
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MAX_BYTES_SIGNATURES: list[tuple[bytes, tuple[str, ...]]] = [
    (b"\xff\xd8\xff", ("image/jpeg",)),
    (b"\x89PNG\r\n\x1a\n", ("image/png",)),
    (b"RIFF", ("image/webp",)),  # verified further below
]


def detect_image_type(header: bytes) -> str | None:
    """Detect image content type from magic bytes; never trust the client header."""
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"
    return None


class FileValidationError(Exception):
    def __init__(self, message: str, code: str = "invalid_file") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def save_image_file(data: bytes, original_name: str) -> tuple[str, str]:
    """Validate and persist an uploaded plant image.

    Returns (stored_relative_url, safe_filename). Raises FileValidationError.
    Files are stored under UPLOAD_STORAGE_PATH/plant_images with random names.
    """
    settings = get_settings()
    if not data:
        raise FileValidationError("Empty file", "empty_file")
    if len(data) > settings.UPLOAD_MAX_BYTES:
        raise FileValidationError(
            f"File too large (max {settings.UPLOAD_MAX_BYTES // (1024 * 1024)} MB)", "file_too_large"
        )
    detected = detect_image_type(data[:64])
    allowed = set(settings.UPLOAD_ALLOWED_TYPES.split(","))
    if detected is None or detected not in allowed:
        raise FileValidationError(
            "Only JPG, JPEG, PNG and WEBP images are allowed", "unsupported_file_type"
        )

    ext = mimetypes.guess_extension(detected) or ".bin"
    if detected == "image/jpeg":
        ext = ".jpg"
    elif detected == "image/png":
        ext = ".png"
    elif detected == "image/webp":
        ext = ".webp"

    subdir = settings.upload_dir / "plant_images"
    subdir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{secrets.token_hex(16)}{ext}"
    (subdir / safe_name).write_bytes(data)
    return f"/static/plant_images/{safe_name}", safe_name


def save_avatar(data: bytes) -> str:
    settings = get_settings()
    if not data:
        raise FileValidationError("Empty file", "empty_file")
    if len(data) > 3 * 1024 * 1024:
        raise FileValidationError("Avatar too large (max 3 MB)", "file_too_large")
    detected = detect_image_type(data[:64])
    if detected not in ("image/jpeg", "image/png", "image/webp"):
        raise FileValidationError("Only JPG, PNG and WEBP images are allowed", "unsupported_file_type")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[detected]
    subdir = settings.upload_dir / "avatars"
    subdir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{secrets.token_hex(16)}{ext}"
    (subdir / safe_name).write_bytes(data)
    return f"/static/avatars/{safe_name}"
