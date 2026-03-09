from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_SCENARIOS = ["world_mix", "budget_pressure"]


def _read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _as_float(row: dict, key: str) -> float:
    return float(row[key])


def _evaluate_scenario(rows: list[dict], scenario_name: str) -> dict:
    by_name = {row["strategy"]: row for row in rows}
    required = ["single_region_fastest", "all_regions_flat_dp", "all_regions_hierarchical_dp", "student_custom_strategy"]
    missing = [name for name in required if name not in by_name]
    if missing:
        return {
            "scenario": scenario_name,
            "score": 0,
            "max_score": 20,
            "status": "missing_rows",
            "details": missing,
        }

    custom = by_name["student_custom_strategy"]
    flat = by_name["all_regions_flat_dp"]
    hierarchical = by_name["all_regions_hierarchical_dp"]
    single = by_name["single_region_fastest"]

    score = 0
    details = []

    if _as_float(custom, "total_time_hours") < _as_float(flat, "total_time_hours"):
        score += 6
    else:
        details.append("custom does not beat flat_all_reduce on total_time_hours")

    if _as_float(custom, "communication_volume_gb") < _as_float(flat, "communication_volume_gb"):
        score += 4
    else:
        details.append("custom does not reduce communication_volume_gb vs flat_all_reduce")

    if _as_float(custom, "comm_share") < _as_float(flat, "comm_share"):
        score += 4
    else:
        details.append("custom does not reduce comm_share vs flat_all_reduce")

    if _as_float(custom, "dollar_cost") <= 1.2 * _as_float(single, "dollar_cost"):
        score += 3
    else:
        details.append("custom is much more expensive than single_region_fastest")

    if _as_float(custom, "convergence_penalty") <= 1.35:
        score += 3
    else:
        details.append("custom convergence_penalty is too large")

    if _as_float(custom, "total_time_hours") > min(
        _as_float(hierarchical, "total_time_hours"),
        _as_float(single, "total_time_hours"),
    ):
        details.append("custom is not the fastest among major baselines, but this is acceptable if tradeoffs are justified")

    return {
        "scenario": scenario_name,
        "score": score,
        "max_score": 20,
        "status": "ok",
        "details": details,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--student-output-dir", type=str, required=True, help="Student outputs directory containing *_comparison.csv")
    ap.add_argument("--out-json", type=str, default="reference_results/student_score_report.json")
    args = ap.parse_args()

    output_dir = Path(args.student_output_dir)
    report = {
        "artifact_score": 0,
        "artifact_score_max": 40,
        "manual_score_max": 60,
        "scenarios": [],
    }

    total = 0
    for scenario in REQUIRED_SCENARIOS:
        csv_path = output_dir / f"{scenario}_comparison.csv"
        if not csv_path.exists():
            report["scenarios"].append({
                "scenario": scenario,
                "score": 0,
                "max_score": 20,
                "status": "missing_file",
                "details": [str(csv_path)],
            })
            continue
        result = _evaluate_scenario(_read_rows(csv_path), scenario)
        total += result["score"]
        report["scenarios"].append(result)

    report["artifact_score"] = total
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

