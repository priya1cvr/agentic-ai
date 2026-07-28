"""
CLI / Orchestrator -- Enterprise Spark Observability Framework
-----------------------------------------------------------------
Invoke from the command line (cron, Airflow, or manually):

    spark-submit cli.py --config config/observability_config.yaml --mode all --run-date 2026-07-17

Modes:
    collect  -- pull data from YARN + History Server, write raw metrics to Hive
    analyze  -- run skew/small-file/underutilization detectors + trend/SLA analysis, write flags to Hive
    report   -- render + send the daily HTML report
    all      -- collect -> analyze -> report (default, what you'd actually schedule daily)
"""
import argparse
import logging
from datetime import datetime

import yaml
from pyspark.sql import SparkSession

import alerting
from history_collector import HistoryServerCollector
from metrics_store import MetricsStore
from report_generator import generate_html_report
from skew_and_small_file_detector import detect_skew, detect_small_files
from sla_predictor import predict_sla_breach
from trend_analyzer import build_trend_comparison
from underutilization_detector import detect_underutilization
from yarn_collector import YarnCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spark_obsv")


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def do_collect(cfg, run_date, store):
    yarn = YarnCollector(
        rm_urls=cfg["cluster"]["yarn_rm_urls"],
        timeout=cfg["collection"]["request_timeout_sec"],
        retries=cfg["collection"]["request_retries"],
        kerberos=cfg["cluster"].get("kerberos_enabled", False),
    )
    history = HistoryServerCollector(
        base_url=cfg["cluster"]["history_server_url"],
        timeout=cfg["collection"]["request_timeout_sec"],
        retries=cfg["collection"]["request_retries"],
        max_workers=cfg["collection"]["max_parallel_requests"],
    )

    logger.info("Fetching application list from YARN (lookback=%sh)...", cfg["collection"]["lookback_hours"])
    raw_apps = yarn.list_applications(cfg["collection"]["lookback_hours"])
    logger.info("Found %d applications", len(raw_apps))

    app_ids = [a["id"] for a in raw_apps]
    detail = history.collect_for_apps(app_ids)

    app_metrics, executor_metrics, stage_metrics = [], [], []
    for raw in raw_apps:
        app_id = raw["id"]
        base = YarnCollector.to_app_metric_dict(raw)
        d = detail.get(app_id, {"executors": [], "stages": []})

        env_props = history.get_environment(app_id)
        spark_cfg = HistoryServerCollector.parse_spark_config(
            env_props, num_executors_observed=len([e for e in d["executors"] if e.get("id") != "driver"])
        )

        app_metric = {**base, "run_date": run_date, **spark_cfg}
        app_metrics.append(app_metric)

        executor_metrics.extend(
            {**e, "run_date": run_date}
            for e in HistoryServerCollector.to_executor_metric_dicts(app_id, d["executors"])
        )
        stage_metrics.extend(
            {**s, "run_date": run_date}
            for s in HistoryServerCollector.to_stage_metric_dicts(app_id, d["stages"])
        )

    queue_json = yarn.get_queue_snapshot()
    queue_metrics = YarnCollector.parse_queue_metrics(queue_json, run_date, datetime.now().isoformat())

    store.save_app_metrics(app_metrics)
    store.save_executor_metrics(executor_metrics)
    store.save_stage_metrics(stage_metrics)
    store.save_queue_metrics(queue_metrics)

    logger.info(
        "Collected: %d apps, %d executor records, %d stage records, %d queues",
        len(app_metrics), len(executor_metrics), len(stage_metrics), len(queue_metrics),
    )
    return app_metrics, executor_metrics, stage_metrics, queue_metrics


def do_analyze(cfg, run_date, spark, store, app_metrics, executor_metrics, stage_metrics):
    thresholds = cfg["thresholds"]
    flags = []

    stages_by_app = {}
    for s in stage_metrics:
        stages_by_app.setdefault(s["app_id"], []).append(s)

    executors_by_app = {}
    for e in executor_metrics:
        executors_by_app.setdefault(e["app_id"], []).append(e)

    for app in app_metrics:
        app_id, app_name = app["app_id"], app["app_name"]
        app_stages = stages_by_app.get(app_id, [])
        app_executors = executors_by_app.get(app_id, [])

        flags += detect_skew(app_stages, app_id, app_name, run_date, thresholds["skew"])
        flags += detect_small_files(app_stages, app_id, app_name, run_date, thresholds["small_file"])
        flags += detect_underutilization(app, app_executors, run_date, thresholds["underutilization"])

    # Trend comparison (7d / 30d) -- requires prior days' data already in Hive
    trend_df = build_trend_comparison(
        spark, cfg["hive"]["app_metrics_table"], run_date,
        windows_days=tuple(cfg["trend"]["compare_windows_days"]),
        min_history_runs=cfg["trend"]["min_history_runs"],
    )
    trend_rows = trend_df.collect()

    # SLA prediction per app, using 30-day mean/stddev as the "normal" model
    sla_cfg = thresholds["sla"]
    sla_predictions = []
    hist_by_name = {
        r["app_name"]: r for r in trend_rows
    }
    for app in app_metrics:
        name = app["app_name"]
        sla_minutes = sla_cfg["sla_overrides"].get(name, sla_cfg["default_sla_minutes"])
        hist = hist_by_name.get(name, {})
        pred = predict_sla_breach(
            app_name=name,
            duration_sec=app["duration_sec"],
            state=app["state"],
            hist_mean_sec=hist.get("avg_duration_sec_30d"),
            hist_stddev_sec=None,  # extend build_trend_comparison with STDDEV(duration_sec) if needed
            n_hist_runs=hist.get("n_runs_30d", 0) or 0,
            sla_minutes=sla_minutes,
        )
        sla_predictions.append(pred)
        if pred["severity"] in ("WARNING", "CRITICAL"):
            flags.append({
                "run_date": run_date,
                "app_id": app["app_id"],
                "app_name": name,
                "flag_type": "SLA_RISK",
                "severity": pred["severity"],
                "detail": pred["note"],
                "metric_value": pred["breach_probability"] or 0.0,
            })

    store.save_flags(flags)
    logger.info("Analysis complete: %d flags raised", len(flags))
    return flags, sla_predictions, [row.asDict() for row in trend_rows]


def do_report(cfg, run_date, app_metrics, queue_metrics, flags, sla_predictions):
    total_apps = len(app_metrics)
    total_mem_sec = sum(a["memory_seconds"] for a in app_metrics)
    total_vcore_sec = sum(a["vcore_seconds"] for a in app_metrics)

    top_offenders = sorted(app_metrics, key=lambda a: a["memory_seconds"], reverse=True)[: cfg["report"]["top_n_offenders"]]

    path = generate_html_report(
        run_date=run_date,
        total_apps=total_apps,
        total_memory_seconds=total_mem_sec,
        total_vcore_seconds=total_vcore_sec,
        queue_summary=queue_metrics,
        flags=flags,
        top_offenders=top_offenders,
        sla_predictions=sla_predictions,
        output_dir=cfg["report"]["output_dir"],
    )
    logger.info("Report written to %s", path)

    alert_cfg = cfg["alerting"]
    sla_risk = [p for p in sla_predictions if p["severity"] in ("WARNING", "CRITICAL")]
    alerting.post_summary(alert_cfg.get("slack_webhook"), alert_cfg.get("teams_webhook"), run_date, total_apps, flags, sla_risk)
    alerting.email_report(alert_cfg.get("smtp"), run_date, path)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--mode", choices=["collect", "analyze", "report", "all"], default="all")
    parser.add_argument("--run-date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    run_date = args.run_date

    spark = SparkSession.builder.appName("spark-observability").enableHiveSupport().getOrCreate()
    store = MetricsStore(spark, cfg["hive"], cfg.get("jdbc"))

    app_metrics = executor_metrics = stage_metrics = queue_metrics = []
    flags, sla_predictions = [], []

    if args.mode in ("collect", "all"):
        app_metrics, executor_metrics, stage_metrics, queue_metrics = do_collect(cfg, run_date, store)

    if args.mode in ("analyze", "all"):
        if not app_metrics:
            app_metrics = [r.asDict() for r in spark.sql(
                f"SELECT * FROM {cfg['hive']['app_metrics_table']} WHERE run_date = '{run_date}'"
            ).collect()]
            executor_metrics = [r.asDict() for r in spark.sql(
                f"SELECT * FROM {cfg['hive']['executor_metrics_table']} WHERE run_date = '{run_date}'"
            ).collect()]
            stage_metrics = [r.asDict() for r in spark.sql(
                f"SELECT * FROM {cfg['hive']['stage_metrics_table']} WHERE run_date = '{run_date}'"
            ).collect()]
        flags, sla_predictions, _ = do_analyze(cfg, run_date, spark, store, app_metrics, executor_metrics, stage_metrics)

    if args.mode in ("report", "all"):
        if not queue_metrics:
            queue_metrics = [r.asDict() for r in spark.sql(
                f"SELECT * FROM {cfg['hive']['queue_metrics_table']} WHERE run_date = '{run_date}'"
            ).collect()]
        do_report(cfg, run_date, app_metrics, queue_metrics, flags, sla_predictions)

    logger.info("Done. mode=%s run_date=%s", args.mode, run_date)


if __name__ == "__main__":
    main()
