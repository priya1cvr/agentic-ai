"""
Metrics Store
-------------
Persists collected metrics into Hive tables (partitioned by run_date), and
optionally mirrors them to Postgres via JDBC for Grafana. Works unmodified
against Delta tables too -- just point hive.*_table at a Delta-backed table
and swap saveAsTable's format to "delta" if your metastore supports it.
"""
from typing import List

from pyspark.sql import Row


class MetricsStore:
    def __init__(self, spark, hive_cfg: dict, jdbc_cfg: dict = None):
        self.spark = spark
        self.hive_cfg = hive_cfg
        self.jdbc_cfg = jdbc_cfg or {"enabled": False}

    def _write(self, records: List[dict], hive_table: str, jdbc_table: str = None):
        if not records:
            return
        df = self.spark.createDataFrame([Row(**r) for r in records])
        db, tbl = hive_table.split(".", 1)
        if self.spark.catalog.tableExists(tbl, db):
            df.write.mode("append").insertInto(hive_table)
        else:
            df.write.mode("append").partitionBy("run_date").format("parquet").saveAsTable(hive_table)

        if self.jdbc_cfg.get("enabled") and jdbc_table:
            df.drop("run_date").write.mode("append").jdbc(
                url=self.jdbc_cfg["url"], table=jdbc_table, properties=self.jdbc_cfg["properties"]
            )

    def save_app_metrics(self, records: List[dict]):
        self._write(records, self.hive_cfg["app_metrics_table"], "app_metrics")

    def save_executor_metrics(self, records: List[dict]):
        self._write(records, self.hive_cfg["executor_metrics_table"], "executor_metrics")

    def save_stage_metrics(self, records: List[dict]):
        self._write(records, self.hive_cfg["stage_metrics_table"], "stage_metrics")

    def save_queue_metrics(self, records: List[dict]):
        self._write(records, self.hive_cfg["queue_metrics_table"], "queue_metrics")

    def save_flags(self, records: List[dict]):
        self._write(records, self.hive_cfg["flags_table"], "flags")

    def read_app_history(self, app_name: str, since_days: int):
        """Trailing history for one logical job, keyed by app_name (not app_id, which
        changes every run) -- used by the trend analyzer and SLA predictor."""
        table = self.hive_cfg["app_metrics_table"]
        return self.spark.sql(f"""
            SELECT * FROM {table}
            WHERE app_name = '{app_name}'
              AND run_date >= date_sub(current_date(), {since_days})
            ORDER BY start_time
        """)
