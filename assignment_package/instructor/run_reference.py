from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path


def _load_student_modules():
    student_root = Path(__file__).resolve().parents[1] / "student"
    if str(student_root) not in sys.path:
        sys.path.insert(0, str(student_root))
    from simulator import get_baseline_strategies, load_scenario, simulate_strategy

    return student_root, get_baseline_strategies, load_scenario, simulate_strategy


def _load_reference_builder(path: Path):
    spec = importlib.util.spec_from_file_location("reference_strategy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load reference strategy from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_strategy


def main() -> None:
    student_root, get_baseline_strategies, load_scenario, simulate_strategy = _load_student_modules()
    builder = _load_reference_builder(Path(__file__).resolve().parent / "reference_strategy" / "reference_strategy.py")

    output_dir = Path(__file__).resolve().parent / "reference_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    for scenario_name in ["world_mix", "budget_pressure"]:
        scenario = load_scenario(student_root / "scenarios" / f"{scenario_name}.json")
        rows = [simulate_strategy(strategy, scenario) for strategy in get_baseline_strategies(scenario)]
        rows.append(simulate_strategy(builder(scenario), scenario))

        out_path = output_dir / f"{scenario_name}_reference.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

