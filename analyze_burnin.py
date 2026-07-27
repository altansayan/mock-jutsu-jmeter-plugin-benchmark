"""
Burn-in Test Report Generator
Usage:
  python analyze_burnin.py <jtl>
  python analyze_burnin.py viewResultsTreeBurnIn.jtl --threads 1000 --meta "v1.1.4 · Java 25" --bucket 60
"""
import argparse
import sys
from pathlib import Path

from analyze_core import (
    parse_jtl, parse_monitor, calc_type_stats,
    calc_time_buckets, align_monitor, generate_html,
)

DEFAULT_JTL     = r"C:\tools\apache-jmeter-5.6.3\bin\viewResultsTreeBurnIn.jtl"
DEFAULT_MONITOR = r"C:\Users\altan\repos\mock-jutsu-jmeter-plugin-benchmark\monitor_out.csv"
DEFAULT_BUCKET  = 60   # seconds — burn-in is 20min, 1-min buckets = 20 data points
DEFAULT_THREADS = 1000


def run(args):
    jtl_path = Path(args.jtl)
    if not jtl_path.exists():
        sys.exit(f"[ERROR] JTL not found: {jtl_path}")

    monitor_path = Path(args.monitor)

    print(f"[burnin] Parsing JTL : {jtl_path}")
    samples = parse_jtl(jtl_path)
    if not samples:
        sys.exit("[ERROR] JTL is empty or all samples are warmup rows.")
    print(f"[burnin] Samples     : {len(samples):,}")

    type_stats  = calc_type_stats(samples)
    bucket_data = calc_time_buckets(samples, bucket_sec=args.bucket)

    start_ts = min(s["ts"] for s in samples)
    end_ts   = max(s["ts"] for s in samples)
    dur_sec  = round((end_ts - start_ts) / 1000)

    print(f"[burnin] Types       : {len(type_stats)}")
    print(f"[burnin] Duration    : {dur_sec}s ({dur_sec//60}m {dur_sec%60}s)")

    print(f"[burnin] Monitor     : {monitor_path}")
    raw_monitor  = parse_monitor(monitor_path)
    monitor_data = align_monitor(raw_monitor, start_ts, end_ts)
    print(f"[burnin] Monitor pts : {len(monitor_data)}")

    # Bar scale: 95th percentile of type averages (prevents heavy types from crushing scale)
    avgs = sorted(r["avg"] for r in type_stats)
    bar_max = max(avgs[int(len(avgs) * 0.95)], 0.05) if avgs else 0.20

    threads = args.threads
    meta    = args.meta or f"JTL: {jtl_path.name}"

    total_samples = sum(r["count"] for r in type_stats)
    tps_avg = (total_samples / dur_sec) if dur_sec else 0
    tps_peak = max((b["tps"] for b in bucket_data), default=0)

    # p95 stability: compare first 25% vs last 25% of buckets
    if len(bucket_data) >= 4:
        q = max(1, len(bucket_data) // 4)
        p95_early = sum(b["p95"] for b in bucket_data[:q]) / q
        p95_late  = sum(b["p95"] for b in bucket_data[-q:]) / q
        drift_pct = ((p95_late - p95_early) / p95_early * 100) if p95_early else 0
        drift_str = f"{drift_pct:+.1f}%"
        drift_cls = "ok" if abs(drift_pct) < 10 else ("warn" if abs(drift_pct) < 25 else "bad")
    else:
        drift_str = "—"
        drift_cls = ""

    badges = [
        ("types",     str(len(type_stats)),              ""),
        ("threads",   str(threads),                      ""),
        ("samples",   f"{total_samples:,}",              ""),
        ("duration",  f"{dur_sec//60}m {dur_sec%60}s",  ""),
        ("avg TPS",   f"{tps_avg:.0f} /s",               ""),
        ("p95 drift", drift_str,                         drift_cls),
        ("meta",      meta,                              ""),
    ]

    html = generate_html(
        type_stats   = type_stats,
        bucket_data  = bucket_data,
        monitor_data = monitor_data,
        title        = "Burn-in Test — Mock Jutsu JMeter Plugin",
        subtitle     = "AllTypes-Burnin · 1200s sustained load · stability analysis",
        badges       = badges,
        bar_max      = bar_max,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[burnin] Report saved: {out_path.resolve()}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Burn-in test HTML report generator")
    ap.add_argument("jtl",       nargs="?", default=DEFAULT_JTL,
                    help="Path to JTL result file")
    ap.add_argument("--out",     default="reports/burnin-report.html",
                    help="Output HTML path (default: reports/burnin-report.html)")
    ap.add_argument("--monitor", default=DEFAULT_MONITOR,
                    help="Path to monitor_out.csv")
    ap.add_argument("--threads", type=int, default=DEFAULT_THREADS,
                    help="Thread count label (default: 1000)")
    ap.add_argument("--meta",    default="",
                    help="Extra metadata label, e.g. 'v1.1.4 · Java 25'")
    ap.add_argument("--bucket",  type=int, default=DEFAULT_BUCKET,
                    help="Time bucket in seconds (default: 60)")
    run(ap.parse_args())
