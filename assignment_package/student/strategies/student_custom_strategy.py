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
    if scenario["scenario_name"] == "world_mix":
        placements = [
            {"cluster_id": "us-east-a100", "num_gpus": 8},
            {"cluster_id": "eu-west-h100", "num_gpus": 4},
        ]
    else:
        placements = [
            {"cluster_id": "us-central-h100", "num_gpus": 2},
            {"cluster_id": "us-west-a100", "num_gpus": 4},
        ]

    return {
        "name": "student_custom_strategy",
        "placements": placements,
        "load_balance": "proportional",
        "sync_scheme": "hierarchical_reduce",
        "sync_interval": 4,
        "notes": "Replace this with your own strategy and justify it in the report.",
    }
