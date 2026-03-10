from __future__ import annotations

from simulator.core import (
    estimate_cluster_compute,
    estimate_global_sync,
    estimate_region_sync,
)


def build_actor_classes(ray):
    @ray.remote
    class ClusterWorker:
        def __init__(self, cluster: dict):
            self.cluster = cluster

        def run_local_step(self, placement: dict) -> dict:
            result = estimate_cluster_compute(placement)
            result["trace"] = [{
                "stage": "local_compute",
                "cluster_id": result["cluster_id"],
                "region": result["region"],
                "num_gpus": result["num_gpus"],
                "assigned_tokens": result["assigned_tokens"],
                "duration_s": result["compute_time_s"],
            }]
            return result

    @ray.remote
    class RegionalAggregator:
        def __init__(self, region: str, scenario: dict):
            self.region = region
            self.scenario = scenario

        def aggregate(self, cluster_results: list[dict], strategy: dict) -> dict:
            result = estimate_region_sync(self.region, cluster_results, strategy, self.scenario)
            result["trace"] = [{
                "stage": "regional_sync",
                "region": self.region,
                "leader_cluster_id": result["leader_cluster_id"],
                "participant_clusters": [cluster["cluster_id"] for cluster in cluster_results],
                "duration_s": result["intra_sync_time_s"],
                "volume_gb": result["intra_volume_gb"],
            }]
            return result

    @ray.remote
    class GlobalCoordinator:
        def __init__(self, scenario: dict):
            self.scenario = scenario

        def synchronize(
            self,
            cluster_results: list[dict],
            regional_results: list[dict],
            strategy: dict,
        ) -> dict:
            result = estimate_global_sync(cluster_results, regional_results, strategy, self.scenario)
            result["trace"] = [{
                "stage": "global_sync",
                "sync_scheme": strategy["sync_scheme"],
                "regions": [result_row["region"] for result_row in regional_results],
                "duration_s": result["global_sync_time_s"],
                "volume_gb": result["global_volume_gb"],
            }]
            return result

    return ClusterWorker, RegionalAggregator, GlobalCoordinator
