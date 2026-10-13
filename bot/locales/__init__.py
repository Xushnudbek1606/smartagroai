from __future__ import annotations

import json
from pathlib import Path

DEFAULT_LANG = "uz-Latn"
SUPPORTED = ("uz-Latn", "uz-Cyrl", "en", "ru")

_dir = Path(__file__).parent
_locales: dict[str, dict[str, str]] = {}
for code in SUPPORTED:
    path = _dir / f"{code}.json"
    if path.exists():
        _locales[code] = json.loads(path.read_text(encoding="utf-8"))


def tr(lang: str, key: str, **kwargs) -> str:
    """Translate a bot message key; falls back to uz-Latn then the key itself."""
    table = _locales.get(lang) or _locales.get(DEFAULT_LANG, {})
    text = table.get(key) or _locales.get(DEFAULT_LANG, {}).get(key) or key
    try:
        return text.format(**kwargs) if kwargs else text
    except (KeyError, IndexError):
        return text
