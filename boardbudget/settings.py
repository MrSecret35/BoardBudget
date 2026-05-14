from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ROOT_DIR


SETTINGS_PATH = ROOT_DIR / "boardbudget_settings.json"
DEFAULT_SETTINGS = {
    "font_size": "Normal",
    "theme": "System/default",
    "non_working_day_color": "#fdecec",
    "absence_day_color": "#fff4cc",
}


def load_app_settings(path: Path = SETTINGS_PATH) -> dict[str, str]:
    if not path.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()
    settings = DEFAULT_SETTINGS.copy()
    for key, value in data.items():
        if key in settings and isinstance(value, str):
            settings[key] = value
    return settings


def save_app_settings(settings: dict[str, str], path: Path = SETTINGS_PATH) -> None:
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
