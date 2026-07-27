"""
Shared analysis engine + HTML template for Wave and Burn-in reports.
Both reports contain identical sections:
  1. Header + badges
  2. Summary metrics
  3. TPS Trend chart
  4. p95 Drift chart
  5. CPU / RAM Overlay chart
  6. Type performance table (avg / p50 / p95 / p99, tier filter, search)
"""

import csv
import collections
import statistics
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

WARMUP_LABELS = {
    "Warmup compile",
    "Lazy Init Warmup — Fast Types",
    "Heavy Types Warmup",
    "ScriptWarmup",
}


def parse_jtl(path: Path) -> list[dict]:
    samples = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat = int(row.get("Latency", 0))
            label = row.get("label", "")
            ts = int(row.get("timeStamp", 0))
            if lat > 0 and label not in WARMUP_LABELS:
                samples.append({"ts": ts, "lat": lat, "label": label})
    return samples


def parse_monitor(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                rows.append({
                    "ts_str": row["timestamp"],
                    "cpu":    float(row["cpu_pct"]),
                    "ram":    float(row["ram_pct"]),
                    "diskw":  float(row["disk_write_kb_s"]),
                })
            except (ValueError, KeyError):
                pass
    return rows


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def calc_type_stats(samples: list[dict]) -> list[dict]:
    data: dict[str, list[int]] = collections.defaultdict(list)
    for s in samples:
        data[s["label"]].append(s["lat"])

    results = []
    for label, vals in sorted(data.items()):
        sv = sorted(vals)
        n = len(sv)
        results.append({
            "type":  label,
            "avg":   statistics.mean(vals) / 1000,
            "p50":   sv[int(n * 0.50)] / 1000,
            "p95":   sv[min(int(n * 0.95), n - 1)] / 1000,
            "p99":   sv[min(int(n * 0.99), n - 1)] / 1000,
            "count": n,
        })
    return results


def calc_time_buckets(samples: list[dict], bucket_sec: int) -> list[dict]:
    if not samples:
        return []
    ts_min = min(s["ts"] for s in samples)
    buckets: dict[int, list[int]] = collections.defaultdict(list)
    for s in samples:
        b = int((s["ts"] - ts_min) / (bucket_sec * 1000))
        buckets[b].append(s["lat"])

    result = []
    for b in sorted(buckets.keys()):
        vals = buckets[b]
        sv = sorted(vals)
        n = len(sv)
        result.append({
            "t":     round(b * bucket_sec),
            "tps":   round(len(vals) / bucket_sec, 1),
            "p50":   round(sv[int(n * 0.50)] / 1000, 3),
            "p95":   round(sv[min(int(n * 0.95), n - 1)] / 1000, 3),
            "p99":   round(sv[min(int(n * 0.99), n - 1)] / 1000, 3),
            "count": n,
        })
    return result


def align_monitor(monitor_rows: list[dict],
                  start_ts_ms: int, end_ts_ms: int) -> list[dict]:
    aligned = []
    for row in monitor_rows:
        try:
            dt = datetime.strptime(row["ts_str"], "%Y-%m-%d %H:%M:%S")
            ts_ms = dt.timestamp() * 1000
            offset = round((ts_ms - start_ts_ms) / 1000, 0)
            span = (end_ts_ms - start_ts_ms) / 1000
            if -120 <= offset <= span + 120:
                aligned.append({
                    "t":     offset,
                    "cpu":   row["cpu"],
                    "ram":   row["ram"],
                    "diskw": row["diskw"],
                })
        except Exception:
            pass
    return aligned


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --bg:#0E1219;--surface:#161B27;--surface2:#1E2535;--border:#252D3E;
  --text:#C9D1E0;--muted:#5A6A8A;--head:#E8EDF5;
  --accent:#4A9EFF;--ok:#2ECC8A;--warn:#F0A830;--bad:#E05555;--info:#7B8FD4;
  --mono:'Cascadia Code','Fira Mono','Consolas',monospace;
  --sans:system-ui,-apple-system,sans-serif;
  --r:7px;
}
@media(prefers-color-scheme:light){:root{
  --bg:#F0F4FA;--surface:#FFF;--surface2:#F5F8FF;--border:#DDE3EF;
  --text:#1A2235;--muted:#7A8AAA;--head:#0D1525;
  --accent:#2563EB;--ok:#16A067;--warn:#C47A10;--bad:#C03030;--info:#4A5FA3;
}}
:root[data-theme=dark]{--bg:#0E1219;--surface:#161B27;--surface2:#1E2535;--border:#252D3E;--text:#C9D1E0;--muted:#5A6A8A;--head:#E8EDF5;--accent:#4A9EFF;--ok:#2ECC8A;--warn:#F0A830;--bad:#E05555;--info:#7B8FD4}
:root[data-theme=light]{--bg:#F0F4FA;--surface:#FFF;--surface2:#F5F8FF;--border:#DDE3EF;--text:#1A2235;--muted:#7A8AAA;--head:#0D1525;--accent:#2563EB;--ok:#16A067;--warn:#C47A10;--bad:#C03030;--info:#4A5FA3}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:13px;line-height:1.6;min-height:100vh;padding-bottom:64px}
/* topbar */
.topbar{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;position:sticky;top:0;z-index:20}
.topbar-title{font-size:14px;font-weight:700;color:var(--head);letter-spacing:-.01em}
.topbar-title span{color:var(--accent);font-family:var(--mono);font-weight:400;font-size:12px;margin-left:6px}
.badges{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
.badge{display:inline-flex;align-items:center;gap:4px;background:var(--surface2);border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:11px;color:var(--muted);font-family:var(--mono)}
.badge b{color:var(--head);font-weight:600}
.badge.ok b{color:var(--ok)}.badge.warn b{color:var(--warn)}.badge.bad b{color:var(--bad)}
/* wrap */
.wrap{max-width:1100px;margin:0 auto;padding:28px 24px 0}
/* metrics row */
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:24px}
.metric{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:14px 18px}
.metric-val{font-family:var(--mono);font-size:24px;font-weight:700;color:var(--accent);line-height:1;margin-bottom:3px;font-variant-numeric:tabular-nums}
.metric-val.ok{color:var(--ok)}.metric-val.warn{color:var(--warn)}.metric-val.bad{color:var(--bad)}
.metric-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em}
.metric-note{font-size:10px;color:var(--muted);margin-top:2px;font-family:var(--mono)}
/* section */
section{margin-bottom:32px}
h2{font-size:13px;font-weight:700;color:var(--head);text-transform:uppercase;letter-spacing:.07em;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid var(--border)}
/* chart grid */
.chart-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:24px}
@media(max-width:900px){.chart-grid{grid-template-columns:1fr}}
.chart-box{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);padding:14px 16px}
.chart-title{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px}
canvas{width:100%;display:block}
.chart-no-data{font-size:12px;color:var(--muted);text-align:center;padding:24px 0}
/* table */
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.search-wrap{position:relative;flex:1;min-width:180px;max-width:300px}
.search-icon{position:absolute;left:8px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none}
input[type=search]{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:5px;color:var(--text);font-family:var(--mono);font-size:12px;padding:5px 8px 5px 26px;outline:none;transition:border-color .15s}
input[type=search]:focus{border-color:var(--accent)}
input[type=search]::placeholder{color:var(--muted)}
.filter-btns{display:flex;gap:4px}
.filter-btn{background:var(--surface2);border:1px solid var(--border);border-radius:4px;color:var(--muted);cursor:pointer;font-size:11px;padding:3px 10px;transition:all .12s;font-family:var(--sans)}
.filter-btn:hover{border-color:var(--accent);color:var(--accent)}
.filter-btn.active{background:var(--accent);border-color:var(--accent);color:#fff}
.count-label{font-size:11px;color:var(--muted);font-family:var(--mono);margin-left:auto}
.tbl-wrap{overflow-x:auto;border-radius:var(--r);border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:12px}
thead th{background:var(--surface2);color:var(--muted);font-size:10px;font-weight:700;letter-spacing:.07em;padding:7px 10px;text-align:left;text-transform:uppercase;white-space:nowrap;border-bottom:1px solid var(--border);cursor:pointer;user-select:none}
thead th:hover{color:var(--text)}
thead th.sorted{color:var(--accent)}
thead th .sa{margin-left:3px;opacity:.5}
thead th.sorted .sa{opacity:1}
tbody tr{border-bottom:1px solid var(--border)}
tbody tr:last-child{border-bottom:none}
tbody tr:hover{background:var(--surface2)}
td{padding:5px 10px;vertical-align:middle}
td.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
td.ok{color:var(--ok);font-weight:600}
td.warn{color:var(--warn);font-weight:600}
td.bad{color:var(--bad);font-weight:600}
td.muted{color:var(--muted)}
.tier-dot{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:6px;vertical-align:middle;position:relative;top:-1px}
.bar-cell{display:flex;align-items:center;gap:6px}
.bar-val{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums;min-width:50px;text-align:right}
.bar-track{flex:1;background:var(--surface2);border-radius:2px;height:4px;overflow:hidden;min-width:40px}
.bar-fill{height:100%;border-radius:2px}
</style>
</head>
<body>
<div class="topbar">
  <div class="topbar-title">mock-jutsu-jmeter <span>__SUBTITLE__</span></div>
  <div class="badges">
    __BADGES__
  </div>
</div>

<div class="wrap">

<!-- 1. Summary metrics -->
<section>
  <h2>Summary</h2>
  <div class="metrics" id="metrics-row"></div>
</section>

<!-- 2-4. Charts -->
<section>
  <h2>TPS Trend &nbsp;·&nbsp; p95 Drift &nbsp;·&nbsp; CPU / RAM Overlay</h2>
  <div class="chart-grid">
    <div class="chart-box">
      <div class="chart-title">TPS Trend</div>
      <canvas id="chart-tps" height="140"></canvas>
      <div class="chart-no-data" id="no-tps" style="display:none">No data</div>
    </div>
    <div class="chart-box">
      <div class="chart-title">p95 Drift (ms)</div>
      <canvas id="chart-p95" height="140"></canvas>
      <div class="chart-no-data" id="no-p95" style="display:none">No data</div>
    </div>
    <div class="chart-box">
      <div class="chart-title">CPU % &amp; RAM %</div>
      <canvas id="chart-cpu" height="140"></canvas>
      <div class="chart-no-data" id="no-cpu" style="display:none">No monitor data</div>
    </div>
  </div>
</section>

<!-- 5. Type table -->
<section>
  <h2>Type Performance Table</h2>
  <div class="controls">
    <div class="search-wrap">
      <svg class="search-icon" width="12" height="12" viewBox="0 0 16 16" fill="none">
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
      <button class="filter-btn" data-tier="heavy">Heavy</button>
    </div>
    <span class="count-label" id="count-label"></span>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th data-col="n" style="width:40px">#</th>
          <th data-col="type">Type<span class="sa">↕</span></th>
          <th data-col="avg" class="sorted" style="width:200px">Avg (ms)<span class="sa">↑</span></th>
          <th data-col="p50" style="width:80px">p50<span class="sa">↕</span></th>
          <th data-col="p95" style="width:80px">p95<span class="sa">↕</span></th>
          <th data-col="p99" style="width:80px">p99<span class="sa">↕</span></th>
          <th data-col="count" style="width:80px">Samples<span class="sa">↕</span></th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</section>

</div>

<script>
// ── data injected by Python ──────────────────────────────────────────────
const TYPE_DATA    = __TYPE_DATA__;
const BUCKET_DATA  = __BUCKET_DATA__;
const MONITOR_DATA = __MONITOR_DATA__;
const BAR_MAX      = __BAR_MAX__;

// ── theme ────────────────────────────────────────────────────────────────
const root = document.documentElement;
const mq   = window.matchMedia('(prefers-color-scheme: dark)');
function applyTheme(dark){ root.setAttribute('data-theme', dark ? 'dark' : 'light'); }
applyTheme(mq.matches);
mq.addEventListener('change', e => applyTheme(e.matches));

// ── helpers ──────────────────────────────────────────────────────────────
const css = v => getComputedStyle(root).getPropertyValue(v).trim();
function tier(a){ return a < 0.05 ? 'fast' : a < 0.15 ? 'medium' : a < 1 ? 'slow' : 'heavy'; }
function tc(t){
  return t==='fast'?css('--ok'):t==='medium'?css('--warn'):t==='slow'?css('--bad'):css('--info');
}

// ── summary metrics ──────────────────────────────────────────────────────
(function(){
  const avgs   = TYPE_DATA.map(d=>d[1]);
  const counts = TYPE_DATA.map(d=>d[4]);
  const total  = counts.reduce((a,b)=>a+b,0);
  const dur    = BUCKET_DATA.length > 0
    ? BUCKET_DATA[BUCKET_DATA.length-1].t + 0
    : 0;

  const items = [
    {val: TYPE_DATA.length,          label:'Types',         cls:''},
    {val: total.toLocaleString(),    label:'Total Samples', cls:''},
    {val: Math.min(...avgs).toFixed(3)+' ms', label:'Fastest Avg', cls:'ok'},
    {val: Math.max(...avgs).toFixed(3)+' ms', label:'Slowest Avg', cls:'bad'},
    {val: BUCKET_DATA.length>0 ? Math.max(...BUCKET_DATA.map(b=>b.tps)).toFixed(0)+' /s' : '—',
          label:'Peak TPS', cls:''},
    {val: dur > 0 ? Math.round(dur/60)+' min' : '—', label:'Test Duration', cls:''},
  ];
  const row = document.getElementById('metrics-row');
  items.forEach(it=>{
    row.innerHTML += `<div class="metric">
      <div class="metric-val ${it.cls}">${it.val}</div>
      <div class="metric-label">${it.label}</div>
    </div>`;
  });
})();

// ── chart helper ─────────────────────────────────────────────────────────
function drawChart(id, noId, series, opts){
  const canvas = document.getElementById(id);
  if(!series || !series.length){ document.getElementById(id).style.display='none'; document.getElementById(noId).style.display=''; return; }
  const W = canvas.offsetWidth || 320;
  const H = parseInt(canvas.getAttribute('height')) || 140;
  canvas.width  = W * devicePixelRatio;
  canvas.height = H * devicePixelRatio;
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(devicePixelRatio, devicePixelRatio);

  const PAD = {top:8, right:8, bottom:24, left:42};
  const cW = W - PAD.left - PAD.right;
  const cH = H - PAD.top  - PAD.bottom;

  const bg      = css('--surface');
  const border  = css('--border');
  const mutedC  = css('--muted');
  const textC   = css('--text');

  ctx.fillStyle = bg;
  ctx.fillRect(0,0,W,H);

  // compute ranges across all series
  let allX = [], allY = [];
  series.forEach(s=>{ s.points.forEach(p=>{ allX.push(p[0]); allY.push(p[1]); }); });
  const xMin = Math.min(...allX), xMax = Math.max(...allX);
  const yMin = opts.yMin !== undefined ? opts.yMin : 0;
  const yMax = opts.yMax !== undefined ? opts.yMax : Math.max(...allY) * 1.15 || 1;

  function px(x){ return PAD.left + (x - xMin) / (xMax - xMin || 1) * cW; }
  function py(y){ return PAD.top  + (1 - (y - yMin) / (yMax - yMin || 1)) * cH; }

  // grid
  ctx.strokeStyle = border;
  ctx.lineWidth   = 0.5;
  const yTicks = 4;
  for(let i=0; i<=yTicks; i++){
    const y = yMin + (yMax - yMin) * i / yTicks;
    const yy = py(y);
    ctx.beginPath(); ctx.moveTo(PAD.left, yy); ctx.lineTo(PAD.left+cW, yy); ctx.stroke();
    ctx.fillStyle   = mutedC;
    ctx.font        = `10px ${css('--mono')}`;
    ctx.textAlign   = 'right';
    ctx.fillText(y.toFixed(y < 10 ? 1 : 0), PAD.left - 4, yy + 3);
  }

  // x axis labels (first, mid, last)
  ctx.fillStyle = mutedC;
  ctx.textAlign = 'center';
  ctx.font      = `10px ${css('--mono')}`;
  const xLabel = x => opts.xUnit === 'min' ? (x/60).toFixed(0)+'m' : x+'s';
  [allX[0], allX[Math.floor(allX.length/2)], allX[allX.length-1]].forEach(x=>{
    ctx.fillText(xLabel(x), px(x), H - 4);
  });

  // lines
  series.forEach(s=>{
    ctx.strokeStyle = s.color;
    ctx.lineWidth   = 1.5;
    ctx.beginPath();
    s.points.forEach((p,i)=>{
      i===0 ? ctx.moveTo(px(p[0]),py(p[1])) : ctx.lineTo(px(p[0]),py(p[1]));
    });
    ctx.stroke();

    if(opts.fill){
      ctx.fillStyle = s.color + '22';
      ctx.lineTo(px(allX[allX.length-1]), py(yMin));
      ctx.lineTo(px(allX[0]), py(yMin));
      ctx.closePath();
      ctx.fill();
    }
  });

  // legend
  if(series.length > 1){
    let lx = PAD.left + 4;
    ctx.font = `10px ${css('--sans')}`;
    series.forEach(s=>{
      ctx.fillStyle = s.color;
      ctx.fillRect(lx, PAD.top+2, 10, 6);
      ctx.fillStyle = textC;
      ctx.textAlign = 'left';
      ctx.fillText(s.label, lx+13, PAD.top+9);
      lx += ctx.measureText(s.label).width + 26;
    });
  }
}

// ── TPS trend ────────────────────────────────────────────────────────────
drawChart('chart-tps','no-tps',
  BUCKET_DATA.length ? [{
    color:  css('--accent'),
    label:  'TPS',
    points: BUCKET_DATA.map(b=>[b.t, b.tps])
  }] : [],
  {fill:true, xUnit:'min'}
);

// ── p95 drift ────────────────────────────────────────────────────────────
drawChart('chart-p95','no-p95',
  BUCKET_DATA.length ? [{
    color:  css('--warn'),
    label:  'p95',
    points: BUCKET_DATA.map(b=>[b.t, b.p95])
  },{
    color:  css('--ok'),
    label:  'p50',
    points: BUCKET_DATA.map(b=>[b.t, b.p50])
  }] : [],
  {fill:false, xUnit:'min'}
);

// ── CPU / RAM overlay ────────────────────────────────────────────────────
drawChart('chart-cpu','no-cpu',
  MONITOR_DATA.length ? [
    {color: css('--bad'),  label:'CPU%',  points: MONITOR_DATA.map(m=>[m.t, m.cpu])},
    {color: css('--info'), label:'RAM%',  points: MONITOR_DATA.map(m=>[m.t, m.ram])},
  ] : [],
  {yMin:0, yMax:100, fill:false, xUnit:'min'}
);

// ── type table ───────────────────────────────────────────────────────────
let data = TYPE_DATA.map(([type,avg,p50,p95,p99,count])=>({
  type, avg, p50, p95, p99, count, t: tier(avg)
}));
let sortCol='avg', sortAsc=true, filterTier='all', filterText='';

function render(){
  let rows = data.filter(d=>{
    if(filterTier!=='all' && d.t!==filterTier) return false;
    if(filterText && !d.type.toLowerCase().includes(filterText)) return false;
    return true;
  });
  rows.sort((a,b)=>{
    let va=a[sortCol], vb=b[sortCol];
    if(typeof va==='string'){va=va.toLowerCase();vb=vb.toLowerCase();}
    return va<vb?(sortAsc?-1:1):va>vb?(sortAsc?1:-1):0;
  });
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  rows.forEach((d,i)=>{
    const color = tc(d.t);
    const pct   = Math.min(d.avg / BAR_MAX * 100, 100).toFixed(1);
    const tr    = document.createElement('tr');
    const clsP  = d.avg < 0.05 ? 'ok' : d.avg < 0.15 ? 'warn' : 'bad';
    tr.innerHTML = `
<td class="mono muted">${i+1}</td>
<td class="mono"><span class="tier-dot" style="background:${color}"></span>${d.type}</td>
<td><div class="bar-cell">
  <span class="bar-val" style="color:${color}">${d.avg.toFixed(3)}</span>
  <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
</div></td>
<td class="mono muted" style="text-align:right">${d.p50.toFixed(3)}</td>
<td class="mono ${clsP}" style="text-align:right">${d.p95.toFixed(3)}</td>
<td class="mono muted" style="text-align:right">${d.p99.toFixed(3)}</td>
<td class="mono muted" style="text-align:right">${d.count.toLocaleString()}</td>`;
    tbody.appendChild(tr);
  });
  document.getElementById('count-label').textContent = `${rows.length} / ${data.length}`;
}

document.querySelectorAll('thead th[data-col]').forEach(th=>{
  th.addEventListener('click',()=>{
    const col = th.dataset.col;
    if(sortCol===col) sortAsc=!sortAsc;
    else { sortCol=col; sortAsc = col!=='avg'; }
    document.querySelectorAll('thead th').forEach(t=>{
      t.classList.toggle('sorted', t.dataset.col===sortCol);
      const a = t.querySelector('.sa');
      if(a) a.textContent = t.dataset.col===sortCol ? (sortAsc?'↑':'↓') : '↕';
    });
    render();
  });
});
document.querySelectorAll('.filter-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    filterTier = btn.dataset.tier;
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    render();
  });
});
document.getElementById('search').addEventListener('input', e=>{
  filterText = e.target.value.trim().toLowerCase();
  render();
});
render();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _to_json_list(rows: list[dict], keys: list[str]) -> str:
    import json
    out = [tuple(r[k] for k in keys) for r in rows]
    return json.dumps(out, separators=(",", ":"))


def generate_html(
    type_stats:   list[dict],
    bucket_data:  list[dict],
    monitor_data: list[dict],
    title:    str,
    subtitle: str,
    badges:   list[tuple[str, str, str]],   # (label, value, cls)
    bar_max:  float = 0.20,
) -> str:
    import json

    # TYPE_DATA: [[type, avg, p50, p95, p99, count], ...]
    type_js = json.dumps(
        [[r["type"], r["avg"], r["p50"], r["p95"], r["p99"], r["count"]]
         for r in type_stats],
        separators=(",", ":")
    )

    # BUCKET_DATA: [{t, tps, p50, p95, p99, count}, ...]
    bucket_js = json.dumps(
        [{"t": b["t"], "tps": b["tps"], "p50": b["p50"],
          "p95": b["p95"], "p99": b["p99"]}
         for b in bucket_data],
        separators=(",", ":")
    )

    # MONITOR_DATA: [{t, cpu, ram, diskw}, ...]
    monitor_js = json.dumps(
        [{"t": m["t"], "cpu": m["cpu"], "ram": m["ram"]}
         for m in monitor_data],
        separators=(",", ":")
    )

    badges_html = "".join(
        f'<div class="badge {cls}"><b>{val}</b> {label}</div>'
        for label, val, cls in badges
    )

    html = HTML
    html = html.replace("__TITLE__",      title)
    html = html.replace("__SUBTITLE__",   subtitle)
    html = html.replace("__BADGES__",     badges_html)
    html = html.replace("__TYPE_DATA__",  type_js)
    html = html.replace("__BUCKET_DATA__", bucket_js)
    html = html.replace("__MONITOR_DATA__", monitor_js)
    html = html.replace("__BAR_MAX__",    str(bar_max))
    return html
