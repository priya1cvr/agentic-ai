"""
Trend Analyzer
--------------
Compares today's run of each app (keyed by app_name, since app_id changes
every run) against its own trailing 7-day and 30-day baseline, using the
Hive app_metrics table as history. Surfaces duration and resource drift --
this is what feeds both the daily report and the SLA predictor's "is this
job trending toward breaching SLA" signal.
"""
from pyspark.sql import functions as F


def build_trend_comparison(spark, app_metrics_table: str, run_date: str, windows_days=(7, 30), min_history_runs=3):
    """
    Returns a Spark DataFrame with one row per app_name for `run_date`, plus
    trailing-average duration/memory_seconds for each configured window and
    the % delta of today's run vs each baseline.
    """
    today_df = spark.sql(f"""
        SELECT app_id, app_name, queue, duration_sec, memory_seconds, vcore_seconds
        FROM {app_metrics_table}
        WHERE run_date = '{run_date}'
    """)

    result = today_df
    for window in windows_days:
        hist = spark.sql(f"""
            SELECT app_name,
                   COUNT(*) AS n_runs,
                   AVG(duration_sec) AS avg_duration_sec,
                   AVG(memory_seconds) AS avg_memory_seconds,
                   AVG(vcore_seconds) AS avg_vcore_seconds
            FROM {app_metrics_table}
            WHERE run_date >= date_sub('{run_date}', {window})
              AND run_date < '{run_date}'
            GROUP BY app_name
            HAVING COUNT(*) >= {min_history_runs}
        """).select(
            "app_name",
            F.col("avg_duration_sec").alias(f"avg_duration_sec_{window}d"),
            F.col("avg_memory_seconds").alias(f"avg_memory_seconds_{window}d"),
            F.col("n_runs").alias(f"n_runs_{window}d"),
        )
        result = result.join(hist, on="app_name", how="left")
        result = result.withColumn(
            f"duration_delta_pct_{window}d",
            F.when(
                F.col(f"avg_duration_sec_{window}d").isNotNull() & (F.col(f"avg_duration_sec_{window}d") > 0),
                (F.col("duration_sec") - F.col(f"avg_duration_sec_{window}d")) / F.col(f"avg_duration_sec_{window}d") * 100,
            ),
        )
    return result


def flag_significant_drift(trend_df, run_date: str, drift_pct_threshold: float = 50.0):
    """Rows where duration is >= threshold% slower than its 7-day baseline -- these
    feed straight into the daily report's 'regressions' section."""
    if "duration_delta_pct_7d" not in trend_df.columns:
        return trend_df.limit(0)
    return trend_df.filter(F.col("duration_delta_pct_7d") >= drift_pct_threshold).select(
        "app_id", "app_name", "queue", "duration_sec", "avg_duration_sec_7d", "duration_delta_pct_7d"
    ).withColumn("run_date", F.lit(run_date))
