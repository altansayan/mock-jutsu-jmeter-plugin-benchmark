#!/usr/bin/env python3
"""
Analyze mock-jutsu-jmeter JTL output and generate an HTML performance report.

Usage:
    python analyze.py viewResultsTree.jtl
    python analyze.py viewResultsTree.jtl --out report.html
    python analyze.py viewResultsTree.jtl --csv
"""

import argparse
import collections
import csv
import statistics
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(jtl_path: Path) -> list[dict]:
    data: dict[str, list[int]] = collections.defaultdict(list)
    with open(jtl_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat = int(row.get("Latency", 0))
            label = row.get("label", "")
            if lat > 0 and label != "Warmup compile":
                data[label].append(lat)

    results = []
    for label, vals in sorted(data.items()):
        sv = sorted(vals)
        results.append({
            "type":  label,
            "avg":   statistics.mean(vals) / 1000,
            "p50":   sv[int(len(sv) * 0.50)] / 1000,
            "p95":   sv[int(len(sv) * 0.95)] / 1000,
            "count": len(vals),
        })
    return results


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def print_csv(results: list[dict]) -> None:
    print("type,avg_ms,p50_ms,p95_ms,count")
    for r in results:
        print(f"{r['type']},{r['avg']:.3f},{r['p50']:.3f},{r['p95']:.3f},{r['count']}")


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>mock-jutsu — Performance Report</title>
<style>
:root{
  --bg:#0E1219;--surface:#161B27;--surface2:#1E2535;--border:#252D3E;
  --text:#C9D1E0;--muted:#5A6A8A;--accent:#4A9EFF;
  --fast:#2ECC8A;--medium:#F0A830;--slow:#E05555;
  --bar-bg:#1E2535;--badge-bg:#1E2535;--header-bg:#111620;
  --search-bg:#1A2030;--search-border:#2E3850;--th-bg:#131824;
  --mono:'Cascadia Code','Fira Mono','Consolas',monospace;
  --sans:system-ui,-apple-system,sans-serif;
}
@media(prefers-color-scheme:light){:root{
  --bg:#F0F4FA;--surface:#FFF;--surface2:#F5F8FF;--border:#DDE3EF;
  --text:#1A2235;--muted:#7A8AAA;--accent:#2563EB;
  --fast:#16A067;--medium:#C47A10;--slow:#C03030;
  --bar-bg:#EEF2FA;--badge-bg:#EEF2FA;--header-bg:#FFF;
  --search-bg:#FFF;--search-border:#C8D3E8;--th-bg:#F5F8FF;
}}
:root[data-theme=dark]{--bg:#0E1219;--surface:#161B27;--surface2:#1E2535;--border:#252D3E;--text:#C9D1E0;--muted:#5A6A8A;--accent:#4A9EFF;--fast:#2ECC8A;--medium:#F0A830;--slow:#E05555;--bar-bg:#1E2535;--badge-bg:#1E2535;--header-bg:#111620;--search-bg:#1A2030;--search-border:#2E3850;--th-bg:#131824}
:root[data-theme=light]{--bg:#F0F4FA;--surface:#FFF;--surface2:#F5F8FF;--border:#DDE3EF;--text:#1A2235;--muted:#7A8AAA;--accent:#2563EB;--fast:#16A067;--medium:#C47A10;--slow:#C03030;--bar-bg:#EEF2FA;--badge-bg:#EEF2FA;--header-bg:#FFF;--search-bg:#FFF;--search-border:#C8D3E8;--th-bg:#F5F8FF}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:13px;line-height:1.5;min-height:100vh}
.header{background:var(--header-bg);border-bottom:1px solid var(--border);padding:18px 24px 14px;position:sticky;top:0;z-index:10}
.header-top{display:flex;align-items:baseline;gap:14px;margin-bottom:12px;flex-wrap:wrap}
.title{font-size:15px;font-weight:600;color:var(--text);letter-spacing:-.01em}
.title span{color:var(--accent);font-family:var(--mono);font-size:13px;font-weight:400}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;gap:5px;background:var(--badge-bg);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:11px;color:var(--muted);font-family:var(--mono)}
.badge b{color:var(--text);font-weight:600}
.badge.fast b{color:var(--fast)}.badge.slow b{color:var(--slow)}
.controls{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.search-wrap{position:relative;flex:1;min-width:200px;max-width:340px}
.search-icon{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
input[type=search]{width:100%;background:var(--search-bg);border:1px solid var(--search-border);border-radius:5px;color:var(--text);font-family:var(--mono);font-size:12px;padding:6px 10px 6px 28px;outline:none;transition:border-color .15s}
input[type=search]:focus{border-color:var(--accent)}
input[type=search]::placeholder{color:var(--muted)}
.filter-btns{display:flex;gap:4px}
.filter-btn{background:var(--badge-bg);border:1px solid var(--border);border-radius:4px;color:var(--muted);cursor:pointer;font-size:11px;padding:4px 10px;transition:all .15s;font-family:var(--sans)}
.filter-btn:hover{border-color:var(--accent);color:var(--accent)}
.filter-btn.active{background:var(--accent);border-color:var(--accent);color:#fff}
.count-label{font-size:11px;color:var(--muted);font-family:var(--mono);margin-left:auto}
.table-wrap{overflow-x:auto;padding:0 24px 24px}
table{width:100%;border-collapse:collapse;table-layout:fixed}
col.col-n{width:44px}col.col-type{width:auto}col.col-avg{width:180px}col.col-p50{width:90px}col.col-p95{width:90px}col.col-count{width:80px}
thead th{background:var(--th-bg);border-bottom:1px solid var(--border);color:var(--muted);cursor:pointer;font-size:10px;font-weight:600;letter-spacing:.06em;padding:8px 10px;text-align:left;text-transform:uppercase;user-select:none;white-space:nowrap;position:sticky;top:var(--header-h,0px)}
thead th:hover{color:var(--text)}thead th.sorted{color:var(--accent)}
thead th .sa{margin-left:3px;opacity:.5}thead th.sorted .sa{opacity:1}
tbody tr{border-bottom:1px solid var(--border);transition:background .08s}
tbody tr:hover{background:var(--surface2)}
td{padding:5px 10px;vertical-align:middle}
td.col-n{color:var(--muted);font-family:var(--mono);font-size:10px;font-variant-numeric:tabular-nums;text-align:right;padding-right:8px}
td.col-type{font-family:var(--mono);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tier-dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:7px;vertical-align:middle;position:relative;top:-1px}
td.col-avg{padding-right:12px}
.avg-cell{display:flex;align-items:center;gap:8px}
.avg-val{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums;min-width:52px;text-align:right}
.bar-track{flex:1;background:var(--bar-bg);border-radius:2px;height:5px;overflow:hidden}
.bar-fill{height:100%;border-radius:2px}
td.col-p50,td.col-p95{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums;text-align:right;color:var(--muted)}
td.col-count{font-family:var(--mono);font-size:11px;font-variant-numeric:tabular-nums;text-align:right;color:var(--muted)}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <div class="title">mock-jutsu <span>Performance Report</span></div>
    <div class="badges">
      <div class="badge"><b id="stat-total">—</b> types</div>
      <div class="badge fast">fastest avg <b id="stat-fastest">—</b></div>
      <div class="badge slow">slowest avg <b id="stat-slowest">—</b></div>
    </div>
  </div>
  <div class="controls">
    <div class="search-wrap">
      <svg class="search-icon" width="13" height="13" viewBox="0 0 16 16" fill="none">
        <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10 10l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <input type="search" id="search" placeholder="filter types…" autocomplete="off">
    </div>
    <div class="filter-btns">
      <button class="filter-btn active" data-tier="all">All</button>
      <button class="filter-btn" data-tier="fast">Fast</button>
      <button class="filter-btn" data-tier="medium">Medium</button>
      <button class="filter-btn" data-tier="slow">Slow</button>
    </div>
    <span class="count-label" id="count-label"></span>
  </div>
</div>
<div class="table-wrap">
  <table>
    <colgroup>
      <col class="col-n"><col class="col-type"><col class="col-avg">
      <col class="col-p50"><col class="col-p95"><col class="col-count">
    </colgroup>
    <thead>
      <tr>
        <th data-col="n">#</th>
        <th data-col="type">Type<span class="sa">↕</span></th>
        <th data-col="avg" class="sorted">Avg (ms)<span class="sa">↑</span></th>
        <th data-col="p50">p50 (ms)<span class="sa">↕</span></th>
        <th data-col="p95">p95 (ms)<span class="sa">↕</span></th>
        <th data-col="count">Samples<span class="sa">↕</span></th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>
<script>
function setHeaderOffset(){
  const h=document.querySelector('.header');
  if(h) document.documentElement.style.setProperty('--header-h', h.getBoundingClientRect().height+'px');
}
setHeaderOffset();
window.addEventListener('resize', setHeaderOffset);
const RAW=__DATA__;
const BAR_MAX=0.20;
function tier(a){return a<0.05?'fast':a<0.15?'medium':'slow'}
function tc(t){return t==='fast'?'var(--fast)':t==='medium'?'var(--medium)':'var(--slow)'}
let data=RAW.map(([type,avg,p50,p95,count])=>({type,avg,p50,p95,count,t:tier(avg)}));
let sortCol='avg',sortAsc=true,filterTier='all',filterText='';
const avgs=data.map(d=>d.avg);
document.getElementById('stat-total').textContent=data.length;
document.getElementById('stat-fastest').textContent=Math.min(...avgs).toFixed(3)+' ms';
document.getElementById('stat-slowest').textContent=Math.max(...avgs).toFixed(3)+' ms';
function render(){
  let rows=data.filter(d=>{
    if(filterTier!=='all'&&d.t!==filterTier)return false;
    if(filterText&&!d.type.toLowerCase().includes(filterText))return false;
    return true;
  });
  rows.sort((a,b)=>{
    let va=a[sortCol],vb=b[sortCol];
    if(typeof va==='string'){va=va.toLowerCase();vb=vb.toLowerCase()}
    return va<vb?(sortAsc?-1:1):va>vb?(sortAsc?1:-1):0;
  });
  const tbody=document.getElementById('tbody');
  tbody.innerHTML='';
  rows.forEach((d,i)=>{
    const pct=Math.min(d.avg/BAR_MAX*100,100).toFixed(1);
    const color=tc(d.t);
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="col-n">${i+1}</td>
<td class="col-type"><span class="tier-dot" style="background:${color}"></span>${d.type}</td>
<td class="col-avg"><div class="avg-cell"><span class="avg-val" style="color:${color}">${d.avg.toFixed(3)}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div></div></td>
<td class="col-p50">${d.p50.toFixed(3)}</td>
<td class="col-p95">${d.p95.toFixed(3)}</td>
<td class="col-count">${d.count.toLocaleString()}</td>`;
    tbody.appendChild(tr);
  });
  document.getElementById('count-label').textContent=`${rows.length} / ${data.length}`;
}
document.querySelectorAll('thead th[data-col]').forEach(th=>{
  th.addEventListener('click',()=>{
    const col=th.dataset.col;
    if(sortCol===col)sortAsc=!sortAsc;
    else{sortCol=col;sortAsc=col!=='avg'}
    document.querySelectorAll('thead th').forEach(t=>{
      t.classList.toggle('sorted',t.dataset.col===sortCol);
      const a=t.querySelector('.sa');
      if(a)a.textContent=t.dataset.col===sortCol?(sortAsc?'↑':'↓'):'↕';
    });
    render();
  });
});
document.querySelectorAll('.filter-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    filterTier=btn.dataset.tier;
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    render();
  });
});
document.getElementById('search').addEventListener('input',e=>{
  filterText=e.target.value.trim().toLowerCase();
  render();
});
render();
</script>
</body>
</html>
"""


def generate_html(results: list[dict], jtl_name: str) -> str:
    rows = []
    for r in results:
        t = r["type"].replace("\\", "\\\\").replace('"', '\\"')
        rows.append(f'["{t}",{r["avg"]:.3f},{r["p50"]:.3f},{r["p95"]:.3f},{r["count"]}]')
    js_data = "[\n" + ",\n".join(rows) + "\n]"
    return HTML.replace("__DATA__", js_data).replace(
        "Performance Report", f"Performance Report — {jtl_name}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze mock-jutsu-jmeter JTL and generate HTML report."
    )
    parser.add_argument("jtl", help="Path to JTL file (e.g. viewResultsTree.jtl)")
    parser.add_argument("--out", help="Output HTML file (default: <jtl-stem>-report.html)")
    parser.add_argument("--csv", action="store_true", help="Print CSV to stdout instead of HTML")
    args = parser.parse_args()

    jtl_path = Path(args.jtl)
    if not jtl_path.exists():
        print(f"Error: file not found: {jtl_path}", file=sys.stderr)
        sys.exit(1)

    results = analyze(jtl_path)

    if args.csv:
        print_csv(results)
        return

    html = generate_html(results, jtl_path.name)
    out_path = Path(args.out) if args.out else jtl_path.with_name(jtl_path.stem + "-report.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written to: {out_path}  ({len(results)} types)")


if __name__ == "__main__":
    main()
