from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator import get_baseline_strategies, load_scenario, simulate_strategy


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/run_baselines.py <scenario.json>")

    scenario_path = Path(sys.argv[1])
    scenario = load_scenario(scenario_path)
    rows = [simulate_strategy(strategy, scenario) for strategy in get_baseline_strategies(scenario)]

    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{scenario['scenario_name']}_baselines.csv"

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
