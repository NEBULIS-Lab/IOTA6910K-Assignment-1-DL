from __future__ import annotations


def get_baseline_strategies(scenario: dict) -> list[dict]:
    clusters = scenario["clusters"]
    fastest = max(clusters, key=lambda c: c["gpu_tokens_per_sec"])

    single_region = {
        "name": "single_region_fastest",
        "placements": [
            {
                "cluster_id": fastest["id"],
                "num_gpus": fastest["num_gpus"],
            }
        ],
        "load_balance": "proportional",
        "sync_scheme": "intra_only",
        "sync_interval": 1,
        "notes": "Uses only the fastest single cluster and avoids inter-region synchronization.",
    }

    flat_all = {
        "name": "all_regions_flat_dp",
        "placements": [
            {
                "cluster_id": cluster["id"],
                "num_gpus": cluster["num_gpus"],
            }
            for cluster in clusters
        ],
        "load_balance": "uniform",
        "sync_scheme": "flat_all_reduce",
        "sync_interval": 1,
        "notes": "Uses all clusters with a naive flat synchronous data-parallel strategy.",
    }

    hierarchical_all = {
        "name": "all_regions_hierarchical_dp",
        "placements": [
            {
                "cluster_id": cluster["id"],
                "num_gpus": cluster["num_gpus"],
            }
            for cluster in clusters
        ],
        "load_balance": "proportional",
        "sync_scheme": "hierarchical_reduce",
        "sync_interval": 4,
        "notes": "Uses all clusters with regional aggregation and less frequent global synchronization.",
    }

    return [single_region, flat_all, hierarchical_all]

