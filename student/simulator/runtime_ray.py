from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from simulator.actors import build_actor_classes
from simulator.core import (
    cluster_map,
    group_placements_by_region,
    normalize_placements,
    summarize_simulation,
    validate_strategy,
)


def _import_ray():
    try:
        import ray
    except ImportError as exc:
        raise RuntimeError(
            "Ray is required for this assignment. Install it with "
            "`python3 -m pip install -r requirements.txt` from the `student/` folder."
        ) from exc
    return ray


def _ensure_local_ray_runtime(ray) -> None:
    if ray.is_initialized():
        return
    os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")
    student_root = Path(__file__).resolve().parents[1]
    ray.init(
        ignore_reinit_error=True,
        include_dashboard=False,
        log_to_driver=False,
        logging_level="ERROR",
        num_cpus=max(1, min(4, os.cpu_count() or 1)),
        runtime_env={"working_dir": str(student_root)},
    )


def simulate_strategy_with_trace(strategy: dict, scenario: dict) -> tuple[dict, list[dict]]:
    validate_strategy(strategy, scenario)
    placements = normalize_placements(strategy, scenario)

    ray = _import_ray()
    _ensure_local_ray_runtime(ray)
    ClusterWorker, RegionalAggregator, GlobalCoordinator = build_actor_classes(ray)

    cluster_by_id = cluster_map(scenario)
    worker_handles = {
        placement["cluster_id"]: ClusterWorker.remote(cluster_by_id[placement["cluster_id"]])
        for placement in placements
    }
    cluster_result_refs = [
        worker_handles[placement["cluster_id"]].run_local_step.remote(placement)
        for placement in placements
    ]
    cluster_results = ray.get(cluster_result_refs)

    results_by_region: dict[str, list[dict]] = defaultdict(list)
    for cluster_result in cluster_results:
        results_by_region[cluster_result["region"]].append(cluster_result)

    region_placements = group_placements_by_region(placements)
    region_handles = {
        region: RegionalAggregator.remote(region, scenario)
        for region in region_placements
    }
    regional_result_refs = [
        region_handles[region].aggregate.remote(results_by_region[region], strategy)
        for region in region_placements
    ]
    regional_results = ray.get(regional_result_refs)

    coordinator = GlobalCoordinator.remote(scenario)
    global_sync = ray.get(coordinator.synchronize.remote(cluster_results, regional_results, strategy))

    trace_events: list[dict] = []
    for cluster_result in cluster_results:
        trace_events.extend(cluster_result.pop("trace", []))
    for regional_result in regional_results:
        trace_events.extend(regional_result.pop("trace", []))
    trace_events.extend(global_sync.pop("trace", []))

    summary = summarize_simulation(
        strategy=strategy,
        scenario=scenario,
        cluster_results=cluster_results,
        regional_results=regional_results,
        global_sync=global_sync,
        trace_events=trace_events,
    )
    return summary, trace_events


def simulate_strategy(strategy: dict, scenario: dict) -> dict:
    summary, _ = simulate_strategy_with_trace(strategy, scenario)
    return summary
