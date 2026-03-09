from __future__ import annotations

import math


def _cluster_map(scenario: dict) -> dict[str, dict]:
    return {cluster["id"]: cluster for cluster in scenario["clusters"]}


def _region_matrix(scenario: dict, src: str, dst: str) -> dict:
    if src == dst:
        return {
            "bandwidth_gbps": scenario["intra_region_bandwidth_gbps"],
            "latency_ms": scenario["intra_region_latency_ms"],
        }
    return scenario["inter_region_network"][src][dst]


def _validate_strategy(strategy: dict, scenario: dict) -> None:
    cluster_by_id = _cluster_map(scenario)
    for placement in strategy["placements"]:
        cluster = cluster_by_id[placement["cluster_id"]]
        if placement["num_gpus"] <= 0:
            raise ValueError("num_gpus must be positive")
        if placement["num_gpus"] > cluster["num_gpus"]:
            raise ValueError(
                f"strategy requests {placement['num_gpus']} GPUs from {cluster['id']}, "
                f"but only {cluster['num_gpus']} are available"
            )
    if strategy["sync_interval"] < 1:
        raise ValueError("sync_interval must be >= 1")


def _compute_step_time_seconds(strategy: dict, scenario: dict) -> tuple[float, float]:
    task = scenario["task"]
    cluster_by_id = _cluster_map(scenario)
    total_tokens = task["global_batch_tokens"]

    placements = []
    for placement in strategy["placements"]:
        cluster = cluster_by_id[placement["cluster_id"]]
        placements.append({
            "cluster_id": cluster["id"],
            "region": cluster["region"],
            "num_gpus": placement["num_gpus"],
            "per_gpu_tokens_per_sec": cluster["gpu_tokens_per_sec"],
        })

    total_gpu_speed = sum(p["num_gpus"] * p["per_gpu_tokens_per_sec"] for p in placements)
    if total_gpu_speed <= 0:
        raise ValueError("total GPU speed must be positive")

    per_cluster_compute = []
    for placement in placements:
        cluster_speed = placement["num_gpus"] * placement["per_gpu_tokens_per_sec"]
        if strategy["load_balance"] == "proportional":
            cluster_tokens = total_tokens * (cluster_speed / total_gpu_speed)
        else:
            cluster_tokens = total_tokens / len(placements)
        cluster_compute = cluster_tokens / cluster_speed
        per_cluster_compute.append(cluster_compute)

    return max(per_cluster_compute), total_gpu_speed


def _communication_time_seconds(strategy: dict, scenario: dict) -> tuple[float, float]:
    task = scenario["task"]
    placements = strategy["placements"]
    if len(placements) == 1 and strategy["sync_scheme"] == "intra_only":
        return 0.0, 0.0

    cluster_by_id = _cluster_map(scenario)
    gradient_gb = task["gradient_size_gb"]
    gradient_gbit = gradient_gb * 8.0

    if strategy["sync_scheme"] == "flat_all_reduce":
        slowest = None
        for src in placements:
            src_region = cluster_by_id[src["cluster_id"]]["region"]
            for dst in placements:
                dst_region = cluster_by_id[dst["cluster_id"]]["region"]
                link = _region_matrix(scenario, src_region, dst_region)
                candidate = (link["bandwidth_gbps"], link["latency_ms"])
                if slowest is None or candidate[0] < slowest[0] or (
                    candidate[0] == slowest[0] and candidate[1] > slowest[1]
                ):
                    slowest = candidate
        bandwidth_gbps, latency_ms = slowest
        time_s = 2.0 * gradient_gbit / max(bandwidth_gbps, 1e-6) + (len(placements) - 1) * latency_ms / 1000.0
        volume_gb = gradient_gb * max(1, len(placements) - 1)
        return time_s, volume_gb

    if strategy["sync_scheme"] == "hierarchical_reduce":
        intra_time_s = 0.0
        intra_volume_gb = 0.0
        region_leaders = {}
        for placement in placements:
            cluster = cluster_by_id[placement["cluster_id"]]
            region = cluster["region"]
            if placement["num_gpus"] > 1:
                intra_time_s += 2.0 * gradient_gbit / scenario["intra_region_bandwidth_gbps"]
                intra_time_s += scenario["intra_region_latency_ms"] / 1000.0
                intra_volume_gb += gradient_gb
            if region not in region_leaders:
                region_leaders[region] = placement

        regions = list(region_leaders.keys())
        inter_time_s = 0.0
        inter_volume_gb = 0.0
        if len(regions) > 1:
            worst_bandwidth = min(
                _region_matrix(scenario, src, dst)["bandwidth_gbps"]
                for src in regions
                for dst in regions
                if src != dst
            )
            worst_latency_ms = max(
                _region_matrix(scenario, src, dst)["latency_ms"]
                for src in regions
                for dst in regions
                if src != dst
            )
            inter_time_s = 2.0 * gradient_gbit / max(worst_bandwidth, 1e-6) + (len(regions) - 1) * worst_latency_ms / 1000.0
            inter_volume_gb = gradient_gb * max(1, len(regions) - 1)
        return intra_time_s + inter_time_s, intra_volume_gb + inter_volume_gb

    raise ValueError(f"unknown sync_scheme: {strategy['sync_scheme']}")


def _convergence_penalty(strategy: dict, scenario: dict) -> float:
    placements = strategy["placements"]
    cluster_by_id = _cluster_map(scenario)
    throughputs = [cluster_by_id[p["cluster_id"]]["gpu_tokens_per_sec"] for p in placements]
    heterogeneity = (max(throughputs) / min(throughputs)) - 1.0 if len(throughputs) > 1 else 0.0
    region_count = len({cluster_by_id[p["cluster_id"]]["region"] for p in placements})
    sync_interval = strategy["sync_interval"]

    penalty = 1.0
    penalty += 0.04 * max(sync_interval - 1, 0)
    penalty += 0.03 * heterogeneity
    penalty += 0.02 * max(region_count - 1, 0)

    if strategy["sync_scheme"] == "hierarchical_reduce":
        penalty -= 0.02
    if strategy["sync_scheme"] == "intra_only":
        penalty -= 0.01

    return max(penalty, 1.0)


def simulate_strategy(strategy: dict, scenario: dict) -> dict:
    _validate_strategy(strategy, scenario)
    task = scenario["task"]
    cluster_by_id = _cluster_map(scenario)

    compute_step_s, total_gpu_speed = _compute_step_time_seconds(strategy, scenario)
    communication_step_s, communication_volume_gb = _communication_time_seconds(strategy, scenario)

    sync_interval = strategy["sync_interval"]
    effective_step_s = compute_step_s + communication_step_s / sync_interval
    penalty = _convergence_penalty(strategy, scenario)
    effective_steps = math.ceil(task["target_steps"] * penalty)
    total_time_s = effective_steps * effective_step_s

    total_gpus = sum(p["num_gpus"] for p in strategy["placements"])
    gpu_hours = total_gpus * total_time_s / 3600.0
    hourly_cost = 0.0
    for placement in strategy["placements"]:
        cluster = cluster_by_id[placement["cluster_id"]]
        hourly_cost += placement["num_gpus"] * cluster["hourly_cost_usd"]
    dollar_cost = hourly_cost * total_time_s / 3600.0

    comm_share = 0.0
    if effective_step_s > 0:
        comm_share = (communication_step_s / sync_interval) / effective_step_s

    return {
        "strategy": strategy["name"],
        "scenario": scenario["scenario_name"],
        "clusters_used": ",".join(p["cluster_id"] for p in strategy["placements"]),
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
        "communication_volume_gb": round(communication_volume_gb * effective_steps / sync_interval, 2),
        "total_time_hours": round(total_time_s / 3600.0, 3),
        "gpu_hours": round(gpu_hours, 3),
        "dollar_cost": round(dollar_cost, 2),
        "aggregate_tokens_per_sec": round(total_gpu_speed, 2),
        "notes": strategy.get("notes", ""),
    }

