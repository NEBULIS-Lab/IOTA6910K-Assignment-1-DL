from __future__ import annotations

import math
from collections import defaultdict


def cluster_map(scenario: dict) -> dict[str, dict]:
    return {cluster["id"]: cluster for cluster in scenario["clusters"]}


def region_matrix(scenario: dict, src_region: str, dst_region: str) -> dict:
    if src_region == dst_region:
        return {
            "bandwidth_gbps": scenario["intra_region_bandwidth_gbps"],
            "latency_ms": scenario["intra_region_latency_ms"],
        }
    return scenario["inter_region_network"][src_region][dst_region]


def validate_strategy(strategy: dict, scenario: dict) -> None:
    cluster_by_id = cluster_map(scenario)
    placements = strategy.get("placements", [])
    if not placements:
        raise ValueError("strategy must provide at least one placement")

    seen_cluster_ids: set[str] = set()
    for placement in placements:
        cluster_id = placement["cluster_id"]
        if cluster_id not in cluster_by_id:
            raise ValueError(f"unknown cluster_id: {cluster_id}")
        if cluster_id in seen_cluster_ids:
            raise ValueError(f"duplicate placement for cluster_id: {cluster_id}")
        seen_cluster_ids.add(cluster_id)

        cluster = cluster_by_id[cluster_id]
        if placement["num_gpus"] <= 0:
            raise ValueError("num_gpus must be positive")
        if placement["num_gpus"] > cluster["num_gpus"]:
            raise ValueError(
                f"strategy requests {placement['num_gpus']} GPUs from {cluster_id}, "
                f"but only {cluster['num_gpus']} are available"
            )

    if strategy["sync_interval"] < 1:
        raise ValueError("sync_interval must be >= 1")
    if strategy["load_balance"] not in {"proportional", "uniform"}:
        raise ValueError(f"unknown load_balance: {strategy['load_balance']}")
    if strategy["sync_scheme"] not in {"intra_only", "flat_all_reduce", "hierarchical_reduce"}:
        raise ValueError(f"unknown sync_scheme: {strategy['sync_scheme']}")


def normalize_placements(strategy: dict, scenario: dict) -> list[dict]:
    cluster_by_id = cluster_map(scenario)
    task = scenario["task"]
    placements: list[dict] = []

    total_cluster_speed = 0.0
    for placement in strategy["placements"]:
        cluster = cluster_by_id[placement["cluster_id"]]
        cluster_speed = placement["num_gpus"] * cluster["gpu_tokens_per_sec"]
        total_cluster_speed += cluster_speed
        placements.append({
            "cluster_id": cluster["id"],
            "region": cluster["region"],
            "gpu_type": cluster["gpu_type"],
            "num_gpus": placement["num_gpus"],
            "per_gpu_tokens_per_sec": cluster["gpu_tokens_per_sec"],
            "cluster_speed": cluster_speed,
            "hourly_cost_usd": cluster["hourly_cost_usd"],
        })

    if total_cluster_speed <= 0:
        raise ValueError("total GPU speed must be positive")

    total_tokens = task["global_batch_tokens"]
    for placement in placements:
        if strategy["load_balance"] == "proportional":
            assigned_tokens = total_tokens * (placement["cluster_speed"] / total_cluster_speed)
        else:
            assigned_tokens = total_tokens / len(placements)
        placement["assigned_tokens"] = assigned_tokens

    return placements


def group_placements_by_region(placements: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for placement in placements:
        grouped[placement["region"]].append(placement)
    return dict(grouped)


def estimate_cluster_compute(placement: dict) -> dict:
    compute_time_s = placement["assigned_tokens"] / placement["cluster_speed"]
    return {
        "cluster_id": placement["cluster_id"],
        "region": placement["region"],
        "gpu_type": placement["gpu_type"],
        "num_gpus": placement["num_gpus"],
        "cluster_speed": placement["cluster_speed"],
        "assigned_tokens": round(placement["assigned_tokens"], 2),
        "compute_time_s": round(compute_time_s, 6),
    }


def estimate_region_sync(region: str, cluster_results: list[dict], strategy: dict, scenario: dict) -> dict:
    if strategy["sync_scheme"] != "hierarchical_reduce":
        return {
            "region": region,
            "leader_cluster_id": cluster_results[0]["cluster_id"],
            "intra_sync_time_s": 0.0,
            "intra_volume_gb": 0.0,
        }

    gradient_gbit = scenario["task"]["gradient_size_gb"] * 8.0
    intra_bandwidth = scenario["intra_region_bandwidth_gbps"]
    intra_latency_s = scenario["intra_region_latency_ms"] / 1000.0

    intra_sync_time_s = 0.0
    intra_volume_gb = 0.0

    for cluster_result in cluster_results:
        if cluster_result["num_gpus"] > 1:
            intra_sync_time_s += 2.0 * gradient_gbit / max(intra_bandwidth, 1e-6)
            intra_sync_time_s += intra_latency_s
            intra_volume_gb += scenario["task"]["gradient_size_gb"]

    if len(cluster_results) > 1:
        intra_sync_time_s += 2.0 * gradient_gbit / max(intra_bandwidth, 1e-6)
        intra_sync_time_s += (len(cluster_results) - 1) * intra_latency_s
        intra_volume_gb += scenario["task"]["gradient_size_gb"] * (len(cluster_results) - 1)

    leader = max(cluster_results, key=lambda result: result["cluster_speed"])
    return {
        "region": region,
        "leader_cluster_id": leader["cluster_id"],
        "intra_sync_time_s": round(intra_sync_time_s, 6),
        "intra_volume_gb": round(intra_volume_gb, 6),
    }


def estimate_global_sync(cluster_results: list[dict], regional_results: list[dict], strategy: dict, scenario: dict) -> dict:
    if strategy["sync_scheme"] == "intra_only":
        return {"global_sync_time_s": 0.0, "global_volume_gb": 0.0}

    gradient_gb = scenario["task"]["gradient_size_gb"]
    gradient_gbit = gradient_gb * 8.0
    cluster_by_id = cluster_map(scenario)

    if strategy["sync_scheme"] == "flat_all_reduce":
        slowest_bandwidth = None
        highest_latency_ms = 0.0
        for src_result in cluster_results:
            src_region = src_result["region"]
            for dst_result in cluster_results:
                dst_region = dst_result["region"]
                link = region_matrix(scenario, src_region, dst_region)
                if slowest_bandwidth is None or link["bandwidth_gbps"] < slowest_bandwidth:
                    slowest_bandwidth = link["bandwidth_gbps"]
                highest_latency_ms = max(highest_latency_ms, link["latency_ms"])

        sync_time_s = 2.0 * gradient_gbit / max(slowest_bandwidth or 1e-6, 1e-6)
        sync_time_s += (len(cluster_results) - 1) * highest_latency_ms / 1000.0
        return {
            "global_sync_time_s": round(sync_time_s, 6),
            "global_volume_gb": round(gradient_gb * max(1, len(cluster_results) - 1), 6),
        }

    regions = [result["region"] for result in regional_results]
    if len(regions) <= 1:
        return {"global_sync_time_s": 0.0, "global_volume_gb": 0.0}

    slowest_bandwidth = min(
        region_matrix(scenario, src_region, dst_region)["bandwidth_gbps"]
        for src_region in regions
        for dst_region in regions
        if src_region != dst_region
    )
    highest_latency_ms = max(
        region_matrix(scenario, src_region, dst_region)["latency_ms"]
        for src_region in regions
        for dst_region in regions
        if src_region != dst_region
    )
    sync_time_s = 2.0 * gradient_gbit / max(slowest_bandwidth, 1e-6)
    sync_time_s += (len(regions) - 1) * highest_latency_ms / 1000.0

    return {
        "global_sync_time_s": round(sync_time_s, 6),
        "global_volume_gb": round(gradient_gb * max(1, len(regions) - 1), 6),
    }


def convergence_penalty(strategy: dict, scenario: dict) -> float:
    cluster_by_id = cluster_map(scenario)
    throughputs = [cluster_by_id[p["cluster_id"]]["gpu_tokens_per_sec"] for p in strategy["placements"]]
    heterogeneity = (max(throughputs) / min(throughputs)) - 1.0 if len(throughputs) > 1 else 0.0
    region_count = len({cluster_by_id[p["cluster_id"]]["region"] for p in strategy["placements"]})

    penalty = 1.0
    penalty += 0.04 * max(strategy["sync_interval"] - 1, 0)
    penalty += 0.03 * heterogeneity
    penalty += 0.02 * max(region_count - 1, 0)

    if strategy["sync_scheme"] == "hierarchical_reduce":
        penalty -= 0.02
    if strategy["sync_scheme"] == "intra_only":
        penalty -= 0.01

    return max(penalty, 1.0)


def summarize_simulation(
    strategy: dict,
    scenario: dict,
    cluster_results: list[dict],
    regional_results: list[dict],
    global_sync: dict,
    trace_events: list[dict],
) -> dict:
    compute_step_s = max(result["compute_time_s"] for result in cluster_results)
    communication_step_s = sum(result["intra_sync_time_s"] for result in regional_results) + global_sync["global_sync_time_s"]
    communication_step_s = round(communication_step_s, 6)

    sync_interval = strategy["sync_interval"]
    effective_step_s = compute_step_s + communication_step_s / sync_interval
    penalty = convergence_penalty(strategy, scenario)
    effective_steps = math.ceil(scenario["task"]["target_steps"] * penalty)
    total_time_s = effective_steps * effective_step_s

    total_gpus = sum(placement["num_gpus"] for placement in strategy["placements"])
    hourly_cost = sum(
        placement["num_gpus"] * cluster_map(scenario)[placement["cluster_id"]]["hourly_cost_usd"]
        for placement in strategy["placements"]
    )
    gpu_hours = total_gpus * total_time_s / 3600.0
    dollar_cost = hourly_cost * total_time_s / 3600.0
    comm_share = (communication_step_s / sync_interval) / effective_step_s if effective_step_s > 0 else 0.0

    total_volume_gb = sum(result["intra_volume_gb"] for result in regional_results) + global_sync["global_volume_gb"]
    aggregate_tokens_per_sec = sum(result["cluster_speed"] for result in cluster_results)

    return {
        "strategy": strategy["name"],
        "scenario": scenario["scenario_name"],
        "clusters_used": ",".join(placement["cluster_id"] for placement in strategy["placements"]),
        "num_clusters": len(strategy["placements"]),
        "num_gpus": total_gpus,
        "sync_scheme": strategy["sync_scheme"],
        "sync_interval": sync_interval,
        "load_balance": strategy["load_balance"],
        "effective_steps": effective_steps,
        "convergence_penalty": round(penalty, 4),
        "compute_step_s": round(compute_step_s, 4),
        "communication_step_s": round(communication_step_s, 4),
        "comm_share": round(comm_share, 4),
        "communication_volume_gb": round(total_volume_gb * effective_steps / sync_interval, 2),
        "total_time_hours": round(total_time_s / 3600.0, 3),
        "gpu_hours": round(gpu_hours, 3),
        "dollar_cost": round(dollar_cost, 2),
        "aggregate_tokens_per_sec": round(aggregate_tokens_per_sec, 2),
        "runtime_backend": "ray_actor_simulator",
        "trace_events": len(trace_events),
        "notes": strategy.get("notes", ""),
    }
