from __future__ import annotations

import json
from pathlib import Path


def load_scenario(path: str | Path) -> dict:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data

