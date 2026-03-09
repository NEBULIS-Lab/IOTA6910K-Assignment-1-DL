from __future__ import annotations


def build_strategy(scenario: dict) -> dict:
    if scenario["scenario_name"] == "world_mix":
        return {
            "name": "reference_world_mix_strategy",
            "placements": [
                {"cluster_id": "us-east-a100", "num_gpus": 8},
                {"cluster_id": "eu-west-h100", "num_gpus": 4}
            ],
            "load_balance": "proportional",
            "sync_scheme": "hierarchical_reduce",
            "sync_interval": 6,
            "notes": "Avoids the highest-latency AP-SG cluster while using hierarchical synchronization across the two strongest regions."
        }
    return {
        "name": "reference_budget_pressure_strategy",
        "placements": [
            {"cluster_id": "us-central-h100", "num_gpus": 2},
            {"cluster_id": "us-west-a100", "num_gpus": 4},
            {"cluster_id": "eu-north-l40s", "num_gpus": 4}
        ],
        "load_balance": "proportional",
        "sync_scheme": "hierarchical_reduce",
        "sync_interval": 5,
        "notes": "Uses all premium compute plus half of the cheaper region to keep cost moderate while reducing global sync frequency."
    }

