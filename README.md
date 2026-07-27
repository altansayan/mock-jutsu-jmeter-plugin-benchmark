# Mock Jutsu JMeter Plugin Benchmark - JMeter Test Plans

[![JMeter](https://img.shields.io/badge/JMeter-5.6.x-D22128?logo=apachejmeter&logoColor=white)](https://jmeter.apache.org/)
[![Java](https://img.shields.io/badge/Java-17%20%7C%2021%20%7C%2025-007396?logo=openjdk&logoColor=white)](https://adoptium.net/)
[![Plugin](https://img.shields.io/badge/mock--jutsu--jmeter-1.1.0-blue)](https://github.com/altansayan/mock-jutsu-jmeter/releases)
[![Types](https://img.shields.io/badge/types%20tested-423-success)](test-plans/AllTypes-Wave.jmx)
[![License](https://img.shields.io/badge/License-MIT-green)](https://github.com/altansayan/mock-jutsu-jmeter/blob/main/LICENSE)

Independent load test plans for the [mock-jutsu-jmeter](https://github.com/altansayan/mock-jutsu-jmeter) plugin.

This repository exists for **transparency**: anyone can download these test plans, run them against their own JMeter installation, and independently verify the performance and correctness claims made in the plugin documentation.

[AllTypes-Wave.jmx](https://github.com/altansayan/mock-jutsu-jmeter-plugin-benchmark/blob/main/test-plans/AllTypes-Wave.jmx) — What Does It Answer? &nbsp; For Detailed AllTypes-Wave Test Results: [Wave Detailed Report](https://github.com/altansayan/mock-jutsu-jmeter-plugin-benchmark/blob/main/reports/wave-report.html)

1. How long does each function take in a single call? (p50, p95, p99)
2. What happens to performance under 1000 simultaneous calls? (true concurrent load)
3. Are there lazy-init spikes? (does the first call show inflated times?)
4. Does warmup help? (does the setUp warmup eliminate lazy-init spikes?)
5. What is the gap between Fast and Heavy types? (0.028 ms vs 0.898 ms)
6. Which types can be used per-request, and which should be pre-generated via CSV?

---
[AllTypes-Burnin.jmx](https://github.com/altansayan/mock-jutsu-jmeter-plugin-benchmark/blob/main/test-plans/AllTypes-Burnin.jmx) — What Does It Answer? &nbsp; For Detailed AllTypes-Burnin Test Results: [Burnin Detailed Report](https://github.com/altansayan/mock-jutsu-jmeter-plugin-benchmark/blob/main/reports/burnin-report.html)

1. Does performance degrade after 20 minutes of continuous load?
2. Are there memory leaks? (does RAM grow over time without releasing?)
3. Does GC pressure build up? (do sudden spikes appear over time?)
4. Is TPS stable? (is the throughput at minute 1 the same at minute 20?)
5. Do threads remain stable under sustained load?
6. Can it be safely used in production load tests? (the core question)

---
## Summary

Two test dimensions cover the plugin's production fitness:

| Test | Question | Verdict |
|------|----------|---------|
| Wave (449K samples, 1000 concurrent) | How fast is each type? | ✅ 98% of types <0.15 ms — negligible overhead |
| Burn-in (691K samples, 42 min) | Does it hold up over time? | ✅ No memory leak, stable threads, GC healthy |

**For teams running load tests:** 418 out of 423 types can be used per-request without affecting your response time measurements. The remaining 4 (OIDC, AI types) should be pre-generated via CSV — a one-time setUp step that reduces their overhead to ~0.01 ms.

**For QA engineers:** Full latency tables (avg, p50, p95, p99), CPU/RAM profiles, and tier classification (Fast / Medium / Slow) are available in the detailed reports below.

📄 [QA Performance Analysis — English](reports/qa-performance-analysis-en.html) &nbsp;|&nbsp; 📄 [QA Performans Analizi — Türkçe](reports/qa-performance-analysis-tr.html)

---

## Test Plans

### `AllTypes-Wave.jmx` — 423 Types, Peak Latency Measurement

Runs all 423 type/qualifier combinations under simultaneous peak load using a **per-sampler SyncTimer** pattern.

| Group | Threads | Pattern | Samplers |
|-------|---------|---------|----------|
| All Types | 1 000 | SyncTimer(1000) per sampler — all 1 000 threads fire simultaneously for each type | 423 |

Each sampler has its own SyncTimer barrier. All 1 000 threads must arrive before the sampler fires — this guarantees true concurrent peak load for every single type. The test completes one pass (loops = 1) through all 423 samplers and exits.

**setUp Thread Group** runs first (1 thread, 1 loop) to warm up JVM class loading and static init blocks before measurement begins.

**Tier classification (measured results):**

| Tier | Avg latency | Types | Examples |
|------|------------|-------|---------|
| Fast | < 0.05 ms | 347 | `tckn`, `iban`, `cardnum`, `email`, `age` |
| Medium | 0.05–0.15 ms | 71 | `btc_wallet`, `camt053`, `x509_cert`, `eth_wallet` |
| Slow | > 0.15 ms | 5 | `oidc_token_set` (0.898 ms), `ai_embedding` (0.872 ms), `jwks` (0.318 ms), `ai_vector` (0.214 ms), `prometheus_metrics` (0.121 ms) |

---

### `AllTypes-Burnin.jmx` — 417 Types, Stability & Durability

Runs sustained load for 1 200 seconds (20 minutes) with no SyncTimer — continuous throughput mode.

| Group | Threads | Duration | Focus |
|-------|---------|----------|-------|
| Fast Types | 1 000 | 1 200 s | Throughput stability, memory behavior |
| Heavy Types | 200 | 1 200 s | Long-running durability of slow types |

Both thread groups write to the same JTL file. The shift from Fast (1 000T) to Heavy (200T) in the second half produces a natural TPS drop and p95 rise — this is expected test design behavior, not performance degradation.

**Results: 691 239 samples, 42 minutes, RAM −2.2 pp, zero thread errors.**

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Apache JMeter | 5.6.x |
| Java | 17, 21, or 25 |
| mock-jutsu-jmeter JAR | 1.1.0+ |

---

## Setup

**1. Install the plugin JAR**

Download `mock-jutsu-jmeter-1.1.0.jar` from the [releases page](https://github.com/altansayan/mock-jutsu-jmeter/releases) and copy it to:

```
$JMETER_HOME/lib/ext/mock-jutsu-jmeter-1.1.0.jar
```

**2. Open a test plan**

```
File → Open → test-plans/AllTypes-Wave.jmx
File → Open → test-plans/AllTypes-Burnin.jmx
```

**3. Run**

```
Run → Start  (or Ctrl+R)
```

The test runs to completion automatically. Results are written to the directory where JMeter is run from.

---

## System Monitoring (Optional)

Use `monitor.ps1` to capture CPU, RAM, and disk write metrics during a test run. Start it before running JMeter, stop it with `Ctrl+C` when the test finishes.

```powershell
# Default: writes monitor_out.csv every 5 seconds
.\monitor.ps1

# Custom interval and output file
.\monitor.ps1 -OutFile my_monitor.csv -IntervalSec 10
```

The script uses `Get-CimInstance` (not `Get-Counter`) to avoid `c0000bb8` errors on Windows. It null-guards the disk counter for systems where physical disk performance counters are disabled.

The resulting `monitor_out.csv` is consumed by `analyze_wave.py` and `analyze_burnin.py` to overlay CPU/RAM on the latency trend charts.

---

## Reading the Results

### Why elapsed time is misleading (Wave only)

The **elapsed** time shown in JMeter's Response Time Graph includes the SyncTimer wait — the time each thread spent waiting at the barrier for all 1 000 threads to arrive. This is not the function execution time.

```
elapsed = SyncTimer wait (~3 300 ms) + actual generation (0.028–0.898 ms)
```

### Where to find real generation times

The JTL `Latency` column stores the actual `System.nanoTime()` delta divided by 1 000 (microseconds → converted to ms in reports).

**JMeter GUI:** View Results Tree → select any sample → Response Data tab shows `result [Xns]`

**HTML reports (recommended):**

Use `analyze_wave.py` for Wave results and `analyze_burnin.py` for Burn-in results:

```bash
# Wave report — default JTL path, 10-second buckets
python analyze_wave.py

# Wave report — custom JTL, custom output
python analyze_wave.py path/to/wave.jtl --out reports/my-wave.html --threads 1000 --meta "v1.1.0 · Java 25 · Win 10"

# Burn-in report — default JTL path, 60-second buckets
python analyze_burnin.py

# Burn-in report — custom JTL
python analyze_burnin.py path/to/burnin.jtl --out reports/my-burnin.html
```

| Flag | Description | Default |
|------|-------------|---------|
| `--out` | Output HTML path | `reports/wave-report.html` / `reports/burnin-report.html` |
| `--monitor` | Path to `monitor_out.csv` | repo root `monitor_out.csv` |
| `--threads` | Thread count badge | `1000` |
| `--meta` | Free-text environment badge | JTL filename |
| `--bucket` | Time bucket in seconds | `10` (wave) / `60` (burnin) |

Reports open in any browser — no server needed. They are fully self-contained and support search, sort, and tier filtering (Fast / Medium / Slow), plus TPS trend, p95 drift, and CPU/RAM overlay charts.

**Quick command-line analysis (Python):**

```python
import csv, collections, statistics

WARMUP = {"Warmup compile", "Lazy Init Warmup — Fast Types",
           "Heavy Types Warmup", "ScriptWarmup"}

data = collections.defaultdict(list)
with open("wave.jtl", newline="") as f:
    for row in csv.DictReader(f):
        lat = int(row.get("Latency", 0))
        if lat > 0 and row["label"] not in WARMUP:
            data[row["label"]].append(lat)

for label, vals in sorted(data.items(), key=lambda x: -statistics.mean(x[1])):
    avg = statistics.mean(vals)
    p50 = sorted(vals)[int(len(vals) * 0.50)]
    p95 = sorted(vals)[int(len(vals) * 0.95)]
    print(f"{label:<40} avg={avg/1000:.3f}ms  p50={p50/1000:.3f}ms  p95={p95/1000:.3f}ms")
```

---

## Pre-generating Slow Types via CSV

4 types have avg latency above 0.15 ms and will add measurable overhead if generated per-request in a production load test. Pre-generate them once in a `setUp Thread Group` and read them via `CSV Data Set Config`:

| Type | Avg latency | Overhead on 100 ms API |
|------|------------|----------------------|
| `oidc_token_set` | 0.898 ms | 0.9% |
| `ai_embedding` | 0.872 ms | 0.87% |
| `jwks` | 0.318 ms | 0.32% |
| `ai_vector` | 0.214 ms | 0.21% |

See the [QA Analysis Report](reports/qa-performance-analysis-en.html) for the full BeanShell setUp script and `CSV Data Set Config` settings.

---

## Why BeanShell instead of Groovy?

The samplers use BeanShell (`scriptLanguage=beanshell`) instead of the recommended JSR223/Groovy.

**Reason:** Groovy 3.0.20 (bundled with JMeter 5.6.3) uses ASM to inspect Java class files. Java 25 produces class files at version 69, which Groovy's ASM version cannot read. Attempting `System.nanoTime()` inside a Groovy script causes:

```
Unsupported class file major version 69
```

BeanShell uses JVM reflection directly and has no ASM dependency, so it works correctly on Java 25. This is a JMeter 5.6.x + Java 25 compatibility issue, not a plugin limitation. Groovy scripts work normally on Java 17 and 21.

---

## Related

- [mock-jutsu-jmeter](https://github.com/altansayan/mock-jutsu-jmeter) — the plugin itself
- [mockjutsu](https://pypi.org/project/mockjutsu/) — Python package (PyPI)
