from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator import get_baseline_strategies, load_scenario, simulate_strategy_with_trace


def _load_custom_builder(path: Path):
    spec = importlib.util.spec_from_file_location("student_custom_strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load custom strategy from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build_strategy"):
        raise RuntimeError("Custom strategy file must define build_strategy(scenario)")
    return module.build_strategy


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 scripts/run_custom.py <scenario.json>")

    scenario_path = Path(sys.argv[1])
    scenario = load_scenario(scenario_path)
    builder = _load_custom_builder(Path("strategies/student_custom_strategy.py"))
    custom_strategy = builder(scenario)

    rows = []
    traces = []
    for strategy in get_baseline_strategies(scenario):
        row, trace = simulate_strategy_with_trace(strategy, scenario)
        rows.append(row)
        traces.append({"strategy": strategy["name"], "events": trace})

    custom_row, custom_trace = simulate_strategy_with_trace(custom_strategy, scenario)
    rows.append(custom_row)
    traces.append({"strategy": custom_strategy["name"], "events": custom_trace})

    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{scenario['scenario_name']}_comparison.csv"
    trace_path = out_dir / f"{scenario['scenario_name']}_trace.json"

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    trace_path.write_text(json.dumps(traces, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote: {out_path}")
    print(f"Wrote: {trace_path}")


if __name__ == "__main__":
    main()
