from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator import get_baseline_strategies, load_scenario, simulate_strategy_with_trace


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/run_baselines.py <scenario.json>")

    scenario_path = Path(sys.argv[1])
    scenario = load_scenario(scenario_path)
    rows = []
    traces = []
    for strategy in get_baseline_strategies(scenario):
        row, trace = simulate_strategy_with_trace(strategy, scenario)
        rows.append(row)
        traces.append({"strategy": strategy["name"], "events": trace})

    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{scenario['scenario_name']}_baselines.csv"
    trace_path = out_dir / f"{scenario['scenario_name']}_baseline_trace.json"

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    trace_path.write_text(json.dumps(traces, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Wrote: {trace_path}")


if __name__ == "__main__":
    main()
