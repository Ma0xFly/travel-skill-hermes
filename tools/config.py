from __future__ import annotations

import os
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = TOOL_ROOT.parent
HISTORY_ROOT = SKILL_ROOT / ".history"
SNAPSHOT_ROOT = HISTORY_ROOT / "snapshots"
VERSIONS_FILE = HISTORY_ROOT / "versions.json"

AMAP_KEY = os.getenv("AMAP_KEY", "")
AMAP_BASE_URL = os.getenv("AMAP_BASE_URL", "https://restapi.amap.com/v3")

WEATHER_KEY = os.getenv("WEATHER_KEY", "")
WEATHER_BASE_URL = os.getenv("WEATHER_BASE_URL", "https://devapi.qweather.com/v7")

WEB_SEARCH_BASE_URL = os.getenv("WEB_SEARCH_BASE_URL", "https://api.duckduckgo.com/")

REQUEST_TIMEOUT = int(os.getenv("TRAVEL_SKILL_REQUEST_TIMEOUT", "10"))
DEFAULT_FORECAST_DAYS = 3
DEFAULT_SEARCH_RADIUS = 2000
DEFAULT_WEB_SEARCH_LIMIT = 5

TRACKED_PATHS = [
    "SKILL.md",
    "reference.md",
    "examples.md",
    "requirements.md",
    "scripts",
    "tools",
]
