"""
YARN Collector
--------------
Pulls per-application resource allocation (memory/vcore-seconds, containers,
queue) from the YARN ResourceManager REST API, plus point-in-time queue
capacity/usage snapshots.

RM REST reference:
  GET /ws/v1/cluster/apps?startedTimeBegin=...&states=...
  GET /ws/v1/cluster/scheduler
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


class YarnCollector:
    def __init__(self, rm_urls: List[str], timeout: int = 15, retries: int = 3, kerberos: bool = False):
        self.rm_urls = rm_urls
        self.timeout = timeout
        self.retries = retries
        self.auth = self._build_auth() if kerberos else None
        self._active_rm = None

    def _build_auth(self):
        from requests_kerberos import HTTPKerberosAuth  # optional dependency
        return HTTPKerberosAuth()

    def _get(self, path: str, params: dict = None) -> dict:
        last_err = None
        for rm in self._ordered_rms():
            url = f"{rm}{path}"
            for attempt in range(self.retries):
                try:
                    resp = requests.get(url, params=params, timeout=self.timeout, auth=self.auth)
                    if resp.status_code == 200:
                        self._active_rm = rm
                        return resp.json()
                    last_err = f"{url} -> HTTP {resp.status_code}"
                except requests.RequestException as e:
                    last_err = f"{url} -> {e}"
            logger.warning("RM %s unreachable/failing, trying next RM candidate", rm)
        raise ConnectionError(f"All YARN RM endpoints failed. Last error: {last_err}")

    def _ordered_rms(self):
        # try the last known-active RM first to avoid the redirect penalty every call
        if self._active_rm:
            return [self._active_rm] + [rm for rm in self.rm_urls if rm != self._active_rm]
        return self.rm_urls

    def list_applications(self, lookback_hours: int, states: Optional[List[str]] = None) -> List[dict]:
        started_after_ms = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp() * 1000)
        params = {"startedTimeBegin": started_after_ms}
        if states:
            params["states"] = ",".join(states)
        data = self._get("/ws/v1/cluster/apps", params=params)
        apps_wrapper = data.get("apps") or {}
        return apps_wrapper.get("app", [])

    def get_queue_snapshot(self) -> dict:
        return self._get("/ws/v1/cluster/scheduler")

    @staticmethod
    def parse_queue_metrics(scheduler_json: dict, run_date: str, snapshot_ts: str) -> List[dict]:
        """Flattens the (recursively nested) YARN capacity-scheduler queue tree."""
        results = []

        def walk(queue_node, path=""):
            name = queue_node.get("queueName", path)
            results.append({
                "run_date": run_date,
                "snapshot_ts": snapshot_ts,
                "queue_name": name,
                "capacity_pct": queue_node.get("capacity", 0.0),
                "used_capacity_pct": queue_node.get("usedCapacity", 0.0),
                "allocated_mb": queue_node.get("resourcesUsed", {}).get("memory", 0),
                "allocated_vcores": queue_node.get("resourcesUsed", {}).get("vCores", 0),
                "num_apps_running": queue_node.get("numActiveApplications", 0),
                "num_apps_pending": queue_node.get("numPendingApplications", 0),
            })
            children = (queue_node.get("queues") or {}).get("queue", [])
            for child in children:
                walk(child, path=f"{path}/{name}")

        root = scheduler_json.get("scheduler", {}).get("schedulerInfo", {})
        if root:
            walk(root)
        return results

    @staticmethod
    def to_app_metric_dict(app_json: dict) -> dict:
        """Normalizes one YARN app record. duration/timestamps -> ISO strings; memorySeconds
        and vcoreSeconds come straight from RM (it already tracks resource-seconds consumed)."""
        start_ms = app_json.get("startedTime", 0)
        finish_ms = app_json.get("finishedTime", 0)
        duration_ms = app_json.get("elapsedTime", 0)
        return {
            "app_id": app_json.get("id"),
            "app_name": app_json.get("name"),
            "user": app_json.get("user"),
            "queue": app_json.get("queue"),
            "state": app_json.get("state"),
            "final_status": app_json.get("finalStatus"),
            "start_time": datetime.fromtimestamp(start_ms / 1000).isoformat() if start_ms else None,
            "end_time": datetime.fromtimestamp(finish_ms / 1000).isoformat() if finish_ms else None,
            "duration_sec": round(duration_ms / 1000.0, 2),
            "memory_seconds": app_json.get("memorySeconds", 0),
            "vcore_seconds": app_json.get("vcoreSeconds", 0),
            "allocated_mb": app_json.get("allocatedMB", 0),
            "allocated_vcores": app_json.get("allocatedVCores", 0),
        }
