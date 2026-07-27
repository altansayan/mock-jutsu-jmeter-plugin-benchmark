"""
Wave Test Report Generator
Usage:
  python analyze_wave.py <jtl>
  python analyze_wave.py viewResultsTreeScrip.jtl --threads 1000 --meta "v1.1.4 · Java 25" --bucket 10
"""
import argparse
import sys
from pathlib import Path

from analyze_core import (
    parse_jtl, parse_monitor, calc_type_stats,
    calc_time_buckets, align_monitor, generate_html,
)

DEFAULT_JTL     = r"C:\tools\apache-jmeter-5.6.3\bin\viewResultsTreeScrip.jtl"
DEFAULT_MONITOR = r"C:\Users\altan\repos\mock-jutsu-jmeter-plugin-benchmark\monitor_out.csv"
DEFAULT_BUCKET  = 10   # seconds — wave is short, 10s buckets give fine granularity
DEFAULT_THREADS = 1000


def run(args):
    jtl_path = Path(args.jtl)
    if not jtl_path.exists():
        sys.exit(f"[ERROR] JTL not found: {jtl_path}")

    monitor_path = Path(args.monitor)

    print(f"[wave] Parsing JTL : {jtl_path}")
    samples = parse_jtl(jtl_path)
    if not samples:
        sys.exit("[ERROR] JTL is empty or all samples are warmup rows.")
    print(f"[wave] Samples     : {len(samples):,}")

    type_stats  = calc_type_stats(samples)
    bucket_data = calc_time_buckets(samples, bucket_sec=args.bucket)

    start_ts = min(s["ts"] for s in samples)
    end_ts   = max(s["ts"] for s in samples)
    dur_sec  = round((end_ts - start_ts) / 1000)

    print(f"[wave] Types       : {len(type_stats)}")
    print(f"[wave] Duration    : {dur_sec}s ({dur_sec//60}m {dur_sec%60}s)")

    print(f"[wave] Monitor     : {monitor_path}")
    raw_monitor  = parse_monitor(monitor_path)
    monitor_data = align_monitor(raw_monitor, start_ts, end_ts)
    print(f"[wave] Monitor pts : {len(monitor_data)}")

    # Bar scale: 95th percentile of all type averages (so fastest types scale well)
    avgs = sorted(r["avg"] for r in type_stats)
    bar_max = max(avgs[int(len(avgs) * 0.95)], 0.05) if avgs else 0.20

    threads = args.threads
    meta    = args.meta or f"JTL: {jtl_path.name}"

    total_samples = sum(r["count"] for r in type_stats)
    tps_peak = max((b["tps"] for b in bucket_data), default=0)

    badges = [
        ("types",   str(len(type_stats)),            ""),
        ("threads", str(threads),                    ""),
        ("samples", f"{total_samples:,}",            ""),
        ("duration", f"{dur_sec//60}m {dur_sec%60}s", ""),
        ("peak TPS", f"{tps_peak:.0f} /s",           ""),
        ("meta",    meta,                            ""),
    ]

    html = generate_html(
        type_stats   = type_stats,
        bucket_data  = bucket_data,
        monitor_data = monitor_data,
        title        = "Wave Test — Mock Jutsu JMeter Plugin",
        subtitle     = "AllTypes-Wave · 1000 simultaneous calls per type",
        badges       = badges,
        bar_max      = bar_max,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"[wave] Report saved: {out_path.resolve()}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Wave test HTML report generator")
    ap.add_argument("jtl",       nargs="?", default=DEFAULT_JTL,
                    help="Path to JTL result file")
    ap.add_argument("--out",     default="reports/wave-report.html",
                    help="Output HTML path (default: reports/wave-report.html)")
    ap.add_argument("--monitor", default=DEFAULT_MONITOR,
                    help="Path to monitor_out.csv")
    ap.add_argument("--threads", type=int, default=DEFAULT_THREADS,
                    help="Thread count label (default: 1000)")
    ap.add_argument("--meta",    default="",
                    help="Extra metadata label, e.g. 'v1.1.4 · Java 25'")
    ap.add_argument("--bucket",  type=int, default=DEFAULT_BUCKET,
                    help="Time bucket in seconds (default: 10)")
    run(ap.parse_args())
