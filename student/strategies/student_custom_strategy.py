from __future__ import annotations


def build_strategy(scenario: dict) -> dict:
    """
    Replace this starter with your own design.

    Minimum expectations:
    - choose which clusters to use
    - choose how many GPUs to use per cluster
    - choose load balancing policy
    - choose synchronization scheme
    - choose synchronization interval
    """
    clusters = sorted(
        scenario["clusters"],
        key=lambda cluster: cluster["gpu_tokens_per_sec"],
        reverse=True,
    )
    top_clusters = clusters[: min(2, len(clusters))]
    placements = [
        {"cluster_id": cluster["id"], "num_gpus": cluster["num_gpus"]}
        for cluster in top_clusters
    ]

    return {
        "name": "student_custom_strategy",
        "placements": placements,
        "load_balance": "proportional",
        "sync_scheme": "hierarchical_reduce",
        "sync_interval": 4,
        "notes": "Replace this with your own strategy and justify it in the report.",
    }
