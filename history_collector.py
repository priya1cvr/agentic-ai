"""
History Server Collector
-------------------------
Pulls per-application executor and stage detail from the Spark History
Server REST API. Since you have 400-500 apps/day, this fans out per-app
calls across a thread pool -- sequential collection at that volume would
take too long to be useful for a daily job.

History Server REST reference (per application, appId = YARN app id or the
Spark-internal id -- History Server accepts the YARN application_ ID directly
for apps launched on YARN):
  GET /api/v1/applications/{app_id}/executors
  GET /api/v1/applications/{app_id}/stages
"""
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import requests

logger = logging.getLogger(__name__)


class HistoryServerCollector:
    def __init__(self, base_url: str, timeout: int = 15, retries: int = 3, max_workers: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.max_workers = max_workers

    def _get(self, path: str):
        url = f"{self.base_url}{path}"
        last_err = None
        for attempt in range(self.retries):
            try:
                resp = requests.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    return None  # app not yet indexed by History Server, or eventLog missing
                last_err = f"HTTP {resp.status_code}"
            except requests.RequestException as e:
                last_err = str(e)
        logger.warning("Giving up on %s after %d attempts (%s)", url, self.retries, last_err)
        return None

    def get_executors(self, app_id: str) -> List[dict]:
        data = self._get(f"/api/v1/applications/{app_id}/executors")
        return data or []

    def get_stages(self, app_id: str) -> List[dict]:
        data = self._get(f"/api/v1/applications/{app_id}/stages?details=true")
        return data or []

    def get_environment(self, app_id: str) -> dict:
        """Returns the flattened spark.* config for the app -- used to pull
        executor-memory/cores/instances and driver-memory since YARN's app
        record doesn't carry Spark-level config."""
        data = self._get(f"/api/v1/applications/{app_id}/environment")
        if not data:
            return {}
        props = {}
        for section in ("sparkProperties", "systemProperties"):
            for k, v in data.get(section, []):
                props[k] = v
        return props

    @staticmethod
    def parse_spark_config(env_props: dict, num_executors_observed: int) -> dict:
        def _parse_mb(val, default=0):
            if not val:
                return default
            val = str(val).lower().strip()
            try:
                if val.endswith("g"):
                    return int(float(val[:-1]) * 1024)
                if val.endswith("m"):
                    return int(float(val[:-1]))
                if val.endswith("k"):
                    return int(float(val[:-1]) / 1024)
                return int(float(val))
            except ValueError:
                return default

        configured_instances = env_props.get("spark.executor.instances")
        return {
            "executor_memory_mb": _parse_mb(env_props.get("spark.executor.memory"), default=1024),
            "driver_memory_mb": _parse_mb(env_props.get("spark.driver.memory"), default=1024),
            "executor_cores": int(env_props.get("spark.executor.cores", 1) or 1),
            "num_executors": int(configured_instances) if configured_instances else num_executors_observed,
        }

    def collect_for_apps(self, app_ids: List[str]) -> dict:
        """Returns {app_id: {"executors": [...], "stages": [...]}} using a thread pool."""
        results = {}

        def fetch(app_id):
            return app_id, self.get_executors(app_id), self.get_stages(app_id)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(fetch, app_id) for app_id in app_ids]
            for fut in as_completed(futures):
                try:
                    app_id, executors, stages = fut.result()
                    results[app_id] = {"executors": executors, "stages": stages}
                except Exception as e:  # noqa: BLE001
                    logger.warning("Failed collecting history-server detail: %s", e)
        return results

    @staticmethod
    def to_executor_metric_dicts(app_id: str, executors_json: List[dict]) -> List[dict]:
        out = []
        for e in executors_json:
            if e.get("id") == "driver":
                continue  # tracked separately via the app-level driver_memory_mb field
            mem_metrics = e.get("peakMemoryMetrics") or {}
            peak_jvm = mem_metrics.get("JVMHeapMemory", 0)
            out.append({
                "app_id": app_id,
                "executor_id": e.get("id"),
                "host": (e.get("hostPort") or "").split(":")[0],
                "total_cores": e.get("totalCores", 0),
                "max_memory_mb": round(e.get("maxMemory", 0) / (1024 * 1024), 2),
                "total_tasks": e.get("totalTasks", 0),
                "total_duration_ms": e.get("totalDuration", 0),
                "total_gc_time_ms": e.get("totalGCTime", 0),
                "total_input_bytes": e.get("totalInputBytes", 0),
                "total_shuffle_read_bytes": e.get("totalShuffleRead", 0),
                "total_shuffle_write_bytes": e.get("totalShuffleWrite", 0),
                "peak_jvm_used_memory_mb": round(peak_jvm / (1024 * 1024), 2),
                "is_active": e.get("isActive", False),
            })
        return out

    @staticmethod
    def to_stage_metric_dicts(app_id: str, stages_json: List[dict]) -> List[dict]:
        out = []
        for s in stages_json:
            task_summary = s.get("taskMetricsDistributions") or {}
            durations = task_summary.get("executorRunTime") or []
            # History Server returns quantile arrays [0, 0.25, 0.5, 0.75, 1.0] when details=true
            if len(durations) >= 5:
                d_min, d_median, d_max = durations[0], durations[2], durations[4]
            else:
                d_min = d_median = d_max = 0.0
            num_tasks = s.get("numTasks", 0) or s.get("numCompleteTasks", 0)
            input_bytes = s.get("inputBytes", 0)
            skew_ratio = (d_max / d_median) if d_median else 0.0
            out.append({
                "app_id": app_id,
                "stage_id": s.get("stageId"),
                "stage_name": s.get("name"),
                "num_tasks": num_tasks,
                "task_duration_min_ms": d_min,
                "task_duration_max_ms": d_max,
                "task_duration_median_ms": d_median,
                "task_duration_p90_ms": durations[3] if len(durations) >= 4 else d_median,
                "skew_ratio": round(skew_ratio, 2),
                "input_bytes": input_bytes,
                "shuffle_read_bytes": s.get("shuffleReadBytes", 0),
                "shuffle_write_bytes": s.get("shuffleWriteBytes", 0),
                "avg_bytes_per_task": round(input_bytes / num_tasks, 2) if num_tasks else 0.0,
            })
        return out
