# mock-jutsu JMeter Test Plans

[![JMeter](https://img.shields.io/badge/JMeter-5.6.x-D22128?logo=apachejmeter&logoColor=white)](https://jmeter.apache.org/)
[![Java](https://img.shields.io/badge/Java-17%20%7C%2021%20%7C%2025-007396?logo=openjdk&logoColor=white)](https://adoptium.net/)
[![Plugin](https://img.shields.io/badge/mock--jutsu--jmeter-1.1.0-blue)](https://github.com/altansayan/mock-jutsu-jmeter/releases)
[![Types](https://img.shields.io/badge/types%20tested-423-success)](test-plans/AllTypes-Wave.jmx)
[![License](https://img.shields.io/badge/License-MIT-green)](https://github.com/altansayan/mock-jutsu-jmeter/blob/main/LICENSE)

Independent load test plans for the [mock-jutsu-jmeter](https://github.com/altansayan/mock-jutsu-jmeter) plugin.

This repository exists for **transparency**: anyone can download these test plans, run them against their own JMeter installation, and independently verify the performance and correctness claims made in the plugin documentation.

---

## Test Plans

### `AllTypes-Wave.jmx` — 423-Type Concurrent Wave

Runs every type and qualifier combination the plugin supports under concurrent wave load.

| Group | Threads | Pattern | Samplers |
|-------|---------|---------|----------|
| Fast Types | 1 000 | SyncTimer(1000) — all 1 000 threads fire simultaneously | 397 |
| Heavy Types | 100 | SyncTimer(100) — cryptographic / high-computation types | 26 |

Each thread group runs **one complete pass** (loops = 1) through all its samplers and exits. The test ends when the last thread finishes — no fixed time limit.

**Heavy types** (separate group, 100 threads): `oidc_token_set`, `jwks`, `oidc_token`, `eth_wallet`, `btc_wallet`, `sol_wallet`, `mnemonic`, `x509_cert`, `webauthn_credential`, `fido2_assertion`, `mt940`, `camt053`, `ubl_invoice`, `swift_mt103`, `pain001`, `fhir_patient`, `hl7_message`, `jwt_attack`, `asn1_fuzz`, `ai_embedding`, `ai_vector`

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

**2. Open the test plan**

```
File → Open → test-plans/AllTypes-Wave.jmx
```

**3. Run**

```
Run → Start  (or Ctrl+R)
```

The test runs to completion automatically. Results are written to:

| File | Listener |
|------|----------|
| `viewResultsTree.jtl` | View Results Tree |
| `viewResultsInTable.jtl` | View Results in Table |
| `responseTimeGraph.jtl` | Response Time Graph |

Files are created in the directory where JMeter is run from.

---

## Reading the Results

### The Response Time Graph is misleading

The **elapsed** time shown in the graph (~3 000–4 000 ms) includes the SyncTimer wait — the time each thread spent waiting at the wave barrier for all other threads to arrive. This is not the function execution time.

```
elapsed = SyncTimer wait (~3 300 ms) + actual generation (0.03–12 ms)
```

### Where to find real generation times

The JTL `Latency` column stores the actual `System.nanoTime()` measurement divided by 1 000 (microseconds). To read it:

**JMeter GUI:** View Results Tree → select any sample → Response Data tab shows `result [Xns]`

**HTML report (recommended):**

Use the included `analyze.py` script to generate an interactive report with avg, p50, and p95 for every type:

```bash
python analyze.py viewResultsTree.jtl
# → writes viewResultsTree-report-<timestamp>.html

python analyze.py viewResultsTree.jtl --threads 1000 --meta "v1.1.0 · Java 25 · Win 10"
# → adds thread count and environment badges to the report header

python analyze.py viewResultsTree.jtl --out my-report.html
# → custom output path

python analyze.py viewResultsTree.jtl --csv
# → prints CSV to stdout
```

| Flag | Description | Example |
|------|-------------|---------|
| `--threads` | Thread count shown as a badge | `--threads 1000` |
| `--meta` | Free-text environment badge | `--meta "v1.1.0 · Java 25 · Win 10"` |
| `--out` | Custom output path | `--out report.html` |
| `--csv` | Print CSV to stdout instead of HTML | |

Each run creates a new timestamped file — previous reports are never overwritten.

Open the generated `.html` file in any browser — no server needed. The report is fully self-contained and supports search, sort, and tier filtering (Fast / Medium / Slow).

**Quick command line analysis (Python):**

```python
import csv, collections, statistics

data = collections.defaultdict(list)
with open("viewResultsTree.jtl", newline="") as f:
    for row in csv.DictReader(f):
        lat = int(row.get("Latency", 0))
        if lat > 0 and row["label"] != "Warmup compile":
            data[row["label"]].append(lat)

for label, vals in sorted(data.items(), key=lambda x: -statistics.mean(x[1])):
    avg  = statistics.mean(vals)
    p50  = sorted(vals)[int(len(vals) * 0.50)]
    p95  = sorted(vals)[int(len(vals) * 0.95)]
    print(f"{label:<40} avg={avg/1000:.3f}ms  p50={p50/1000:.3f}ms  p95={p95/1000:.3f}ms")
```

### Baseline results (v1.1.0, Java 25, Windows 10, 1 000 concurrent threads)

| Type | Avg (ms) | p95 (ms) |
|------|----------|----------|
| cardnum:visa | 0.155 | 0.253 |
| sepa_qr | 0.108 | 0.138 |
| tckn | 0.041 | 0.071 |
| oidc_token_set | 12.063 | 35.115 |

All fast types complete well under **1.5 ms/call** — the CI regression threshold enforced by `PerfMeasurement.java`.

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
