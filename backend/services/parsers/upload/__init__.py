"""Multi-format BOM upload parsing (spreadsheet, JSON, text/HTML/markdown)."""

from backend.services.parsers.upload.dispatch import (
    ALLOWED_UPLOAD_EXTENSIONS,
    SUPPORTED_FORMAT_LABELS,
    detect_upload_format,
    parse_upload_bytes,
)

__all__ = [
    "ALLOWED_UPLOAD_EXTENSIONS",
    "SUPPORTED_FORMAT_LABELS",
    "detect_upload_format",
    "parse_upload_bytes",
]
