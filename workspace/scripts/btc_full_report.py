#!/usr/bin/env python3
"""BTCUSD 综合分析报告生成器 - 2026-05-10"""
import sqlite3, json, math, os
from datetime import datetime

DB = r'C:\Users\Administrator\.openclaw\workspace\data\taskflow.db'
SYMBOL = 'BTCUSDm'
OUTPUT_DIR = r'C:\Users\Administrator\.openclaw\workspace\reports'
DATE = datetime.now().strftime('%Y-%m-%d')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f'btc_analysis_{DATE}.html')

conn = sqlite3.connect(DB)
c = conn.cursor()

def fetch(tf):
    c.execute("SELECT time,open,high,low,close,tick_volume FROM kline_raw WHERE symbol=? AND timeframe=? ORDER BY time", (SYMBOL,tf))
    return c.fetchall()

d1_all = fetch('D1')
h4_all = fetch('H4')
h1_all = fetch('H1')
m5_all = fetch('M5')

d1 = [r for r in d1_all if r[0] >= '2025-06-01']
d1_2026 = [r for r in d1_all if r[0] >= '2026-01-01']
h1_recent = [r for r in h1_all if r[0] >= '2026-05-03']
latest = d1_all[-1]
cp = latest[4]  # current price

# --- 指标计算 ---
def sma(data, p):
    if len(data) < p: return sum(data)/len(data)
    return sum(data[-p:])/p

def calc_rsi(data, p=14):
    if len(data) < p+1: return 50.0
    g,l = 0,0
    for i in range(-p,0):
        chg = data[i] - data[i-1]
        if chg >= 0: g += chg
        else: l -= chg
    rs = (g/p)/(l/p) if l else 100
    return 100 - 100/(1+rs)

def find_pivots(data, w=3):
    hp, lp = [], []
    for i in range(w, len(data)-w):
        if all(data[i][2] >= data[j][2] for j in range(i-w,i+w+1)):
            hp.append((data[i][0], data[i][2]))
        if all(data[i][3] <= data[j][3] for j in range(i-w,i+w+1)):
            lp.append((data[i][0], data[i][3]))
    return hp, lp

d1c = [r[4] for r in d1]
ma5 = sma(d1c,5); ma20 = sma(d1c,20); ma60 = sma(d1c,60); ma200 = sma(d1c,200)
rsi_val = calc_rsi(d1c,14)
allig_lips = sma(d1c,5); allig_teeth = sma(d1c,8); allig_jaw = sma(d1c,13)

# 趋势评分
score = 0
if cp > ma20: score += 1
if cp > ma60: score += 1
if cp > ma200: score += 1
if ma5 > ma20: score += 1
if rsi_val > 50: score += 1
if rsi_val > 70: score -= 1
if allig_lips > allig_teeth > allig_jaw: score += 2

trend_map = {5:'强势多头 📈',4:'强势多头 📈',3:'偏多震荡 📈',2:'偏多震荡 📊',1:'震荡 📊',0:'震荡 📊','-1':'偏空震荡 📉','-2':'偏空震荡 📉'}
trend_str = trend_map.get(score if score >= -2 else -2, '震荡 📊')

# 波浪数据
highs_2026, lows_2026 = find_pivots(d1_2026, 3)
events = [(h[0],h[1],'H') for h in highs_2026] + [(l[0],l[1],'L') for l in lows_2026]
events.sort(key=lambda x: x[0])

# 图表数据（近60天D1）
chart_d1 = d1[-60:]
cd = {
    'dates': [r[0][:10] for r in chart_d1],
    'close': [round(r[4],2) for r in chart_d1],
    'high': [round(r[2],2) for r in chart_d1],
    'low': [round(r[3],2) for r in chart_d1]
}
# MA序列
ma5_seq = []
ma20_seq = []
cl_vals = [r[4] for r in chart_d1]
for i in range(len(chart_d1)):
    sub = cl_vals[:i+1]
    ma5_seq.append(round(sma(sub,5),2))
    ma20_seq.append(round(sma(sub,20),2))

# RSI序列
rsi_seq = []
for i in range(len(chart_d1)):
    sub = cl_vals[:i+1]
    rsi_seq.append(round(calc_rsi(sub,14),1))

# H1图表数据
h1_recent_chart = h1_recent[-168:]
h1_d = {
    'dates': [r[0][11:16] for r in h1_recent_chart],
    'close': [round(r[4],2) for r in h1_recent_chart],
    'high': [round(r[2],2) for r in h1_recent_chart],
    'low': [round(r[3],2) for r in h1_recent_chart]
}

# --- 生成HTML ---
sco = score
tr = rsi_val
cl = cp
chart_json = json.dumps(cd)
ma5_json = json.dumps(ma5_seq)
ma20_json = json.dumps(ma20_seq)
rsi_json = json.dumps(rsi_seq)
h1_json = json.dumps(h1_d)
pct53 = round((cp/65868-1)*100, 1)
pct52 = round((cp/59781-1)*100, 1)

# H1最后5条表格行
h1_rows = ''
for r in h1_recent[-10:]:
    em = '📈' if r[4] >= r[1] else '📉'
    h1_rows += f'<tr><td>{r[0][11:16]}</td><td>${r[1]:,.2f}</td><td>${r[2]:,.2f}</td><td>${r[3]:,.2f}</td><td>{em} ${r[4]:,.2f}</td><td>{r[5]}</td></tr>\n'

# 鳄鱼线状态
alligator_status = ''
if allig_lips > allig_teeth > allig_jaw:
    alligator_status = '🐊 多头张嘴向上 — 趋势强烈'
elif allig_lips < allig_teeth < allig_jaw:
    alligator_status = '🐊 空头张嘴向下 — 趋势强烈'
else:
    alligator_status = '🐊 鳄鱼线纠缠 — 震荡整理'

# RSI状态
rsi_status = ''
rsi_color = ''
if rsi_val > 70:
    rsi_status = '⚠️ 超买区，回调风险'
    rsi_color = '#f85149'
elif rsi_val > 60:
    rsi_status = '偏强'
    rsi_color = '#d29922'
elif rsi_val > 40:
    rsi_status = '中性'
    rsi_color = '#8b949e'
elif rsi_val > 30:
    rsi_status = '偏弱'
    rsi_color = '#58a6ff'
else:
    rsi_status = '⚠️ 超卖区，反弹可能'
    rsi_color = '#3fb950'

# 均线排列状态
ma_status = '未知'
if ma5 > ma20 > ma60 > ma200:
    ma_status = '✅ 多头排列 · MA5 > MA20 > MA60 > MA200'
elif ma5 < ma20 < ma60 < ma200:
    ma_status = '❌ 空头排列 · MA5 < MA20 < MA60 < MA200'
else:
    ma_status = '⚠️ 均线纠缠'

rsi_signal_bg = '#0f2d1a' if rsi_val < 60 else '#1c1a0a' if rsi_val < 70 else '#2d0f0f'

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>BTCUSD 分析报告 | {DATE}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;}}
.container{{max-width:1200px;margin:0 auto;}}
h1{{font-size:28px;margin-bottom:5px;color:#58a6ff;}}
h2{{font-size:20px;margin:25px 0 15px;color:#f0883e;border-bottom:1px solid #30363d;padding-bottom:8px;}}
h3{{font-size:16px;margin:15px 0 10px;color:#8b949e;}}
.subtitle{{color:#8b949e;font-size:14px;margin-bottom:20px;}}
.price-big{{font-size:42px;font-weight:700;color:#58a6ff;}}
.price-change{{font-size:16px;margin-left:10px;}}
.up{{color:#3fb950;}}
.down{{color:#f85149;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:15px 0;}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px;}}
.card .label{{color:#8b949e;font-size:12px;text-transform:uppercase;}}
.card .value{{font-size:22px;font-weight:600;margin-top:4px;}}
.signal{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:13px;font-weight:600;}}
.signal-bull{{background:#0f2d1a;color:#3fb950;border:1px solid #3fb950;}}
.signal-bear{{background:#2d0f0f;color:#f85149;border:1px solid #f85149;}}
.signal-neutral{{background:#1c1c1c;color:#d29922;border:1px solid #d29922;}}
.chart-box{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin:15px 0;}}
table{{width:100%;border-collapse:collapse;margin:10px 0;}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #21262d;font-size:14px;}}
th{{color:#8b949e;font-weight:600;background:#161b22;}}
tr:hover{{background:#1c2128;}}
.wave-section{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin:15px 0;}}
.footer{{text-align:center;color:#484f58;font-size:12px;margin-top:40px;padding:20px 0;border-top:1px solid #21262d;}}
</style>
</head>
<body>
<div class="container">

<h1>🪙 BTCUSD 综合分析报告</h1>
<div class="subtitle">{datetime.now().strftime("%Y-%m-%d %H:%M")} UTC+8 · 比尔威廉姆混沌理论 + 艾略特波浪 + 传统技术分析</div>

<div class="card" style="margin-bottom:15px;">
  <div class="label">BTCUSD 最新收盘</div>
  <div><span class="price-big">${cp:,.2f}</span><span style="color:#8b949e;font-size:14px;margin-left:8px;">（{latest[0][:10]} D1）</span></div>
  <div style="margin-top:8px;">
    <span>日高 ${latest[2]:,.2f}</span><span style="margin:0 10px;color:#30363d;">|</span>
    <span>日低 ${latest[3]:,.2f}</span><span style="margin:0 10px;color:#30363d;">|</span>
    <span>成交量 {latest[5]:,}</span>
  </div>
</div>

<div class="grid">
  <div class="card">
    <div class="label">趋势评级</div>
    <div class="value" style="font-size:20px;">{trend_str}</div>
    <div style="margin-top:5px;"><span class="value" style="font-size:18px;">{score}/7</span></div>
  </div>
  <div class="card">
    <div class="label">波浪阶段</div>
    <div class="value" style="color:#f0883e;font-size:20px;">浪⑤-③</div>
    <div style="margin-top:5px;color:#8b949e;font-size:13px;">第五浪推动中 · +{pct53}%</div>
  </div>
  <div class="card">
    <div class="label">RSI(14)</div>
    <div class="value" style="color:{rsi_color};">{rsi_val:.1f}</div>
    <div style="margin-top:5px;color:#8b949e;font-size:13px;">{rsi_status}</div>
  </div>
  <div class="card">
    <div class="label">鳄鱼线</div>
    <div class="value" style="font-size:18px;">{alligator_status}</div>
  </div>
</div>

<div class="chart-box">
  <h3>D1 K线 (近60天) + MA5 / MA20</h3>
  <canvas id="priceChart" height="280"></canvas>
  <canvas id="rsiChart" height="100" style="margin-top:8px;"></canvas>
</div>

<h2>📊 关键技术指标</h2>
<div class="grid">
  <div class="card"><div class="label">MA5</div><div class="value">${ma5:,.2f}</div></div>
  <div class="card"><div class="label">MA20（趋势线）</div><div class="value" style="color:{'#3fb950' if cp > ma20 else '#f85149'};">${ma20:,.2f}</div></div>
  <div class="card"><div class="label">MA60</div><div class="value">${ma60:,.2f}</div></div>
  <div class="card"><div class="label">MA200</div><div class="value">${ma200:,.2f}</div></div>
</div>

<div class="card" style="margin:15px 0;">
  <div class="label">均线排列</div>
  <div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;">
    <div style="background:#1c2128;padding:5px 12px;border-radius:6px;border:1px solid #30363d;"><span style="color:#8b949e;">MA5</span><span style="color:#fff;margin-left:6px;">${ma5:,.0f}</span></div>
    <div style="background:#1c2128;padding:5px 12px;border-radius:6px;border:1px solid #30363d;"><span style="color:#8b949e;">MA20</span><span style="color:#fff;margin-left:6px;">${ma20:,.0f}</span></div>
    <div style="background:#1c2128;padding:5px 12px;border-radius:6px;border:1px solid #30363d;"><span style="color:#8b949e;">MA60</span><span style="color:#fff;margin-left:6px;">${ma60:,.0f}</span></div>
    <div style="background:#1c2128;padding:5px 12px;border-radius:6px;border:1px solid #30363d;"><span style="color:#8b949e;">MA200</span><span style="color:#fff;margin-left:6px;">${ma200:,.0f}</span></div>
  </div>
  <div style="margin-top:8px;color:#8b949e;font-size:13px;">{ma_status}</div>
</div>

<h2>🌊 艾略特波浪分析</h2>
<div class="wave-section">
  <h3>大周期 5浪结构</h3>
  <table>
    <tr><th>波浪</th><th>时间</th><th>价格范围</th><th>涨跌幅</th><th>说明</th></tr>
    <tr><td><span class="signal signal-bull">浪①</span></td><td>2025初~2025-07-14</td><td>$XX,XXX→$123,260</td><td class="up">+108%</td><td>第一波主升（缺2025年初数据）</td></tr>
    <tr><td><span class="signal signal-neutral">浪②</span></td><td>2025-07-14~2025-08-14</td><td>$123,260→$124,560</td><td class="up">+1%</td><td>横盘整理</td></tr>
    <tr><td><span class="signal signal-bull">浪③🏆</span></td><td>2025-08~2025-10-06</td><td>$124,560→$126,304</td><td class="up">+1.4%</td><td>历史高点</td></tr>
    <tr><td><span class="signal signal-bear">浪④</span></td><td>2025-10-06~2026-02-06</td><td>$126,304→$59,781</td><td class="down">-52.7%</td><td>深度回调，未破浪①顶</td></tr>
    <tr><td><span class="signal signal-bull">浪⑤</span></td><td>2026-02-06~至今</td><td>$59,781→<b>${cp:,.0f}</b></td><td class="up">+{pct52}%</td><td>当前进行中 · 已运行3个月</td></tr>
  </table>
</div>

<div class="wave-section">
  <h3>浪⑤内部子浪分析</h3>
  <table>
    <tr><th>子浪</th><th>价格范围</th><th>涨幅</th><th>状态</th></tr>
    <tr><td><span class="signal signal-bull">⑤-①</span></td><td>$59,781→$71,313</td><td class="up">+19.3%</td><td>✅ 已完成</td></tr>
    <tr><td><span class="signal signal-neutral">⑤-②</span></td><td>$71,313→$65,868</td><td class="down">-7.6%</td><td>✅ 已完成</td></tr>
    <tr><td><span class="signal signal-bull">⑤-③</span></td><td>$65,868→<b>${cp:,.0f}</b></td><td class="up">+{pct53}%</td><td>🔴 进行中</td></tr>
    <tr><td><span class="signal signal-neutral">⑤-④</span></td><td>预估回踩</td><td class="down">待定</td><td>⏳ 待确认</td></tr>
    <tr><td><span class="signal signal-bull">⑤-⑤</span></td><td>回踩→新高</td><td class="up">预估+15~25%</td><td>⏳ 最终目标</td></tr>
  </table>
</div>

<div class="wave-section">
  <h3>鳄鱼线 & 混沌理论</h3>
  <table>
    <tr><th>指标</th><th>值</th><th>信号</th></tr>
    <tr><td>鳄鱼·唇线 (绿·SMA5)</td><td>${allig_lips:,.2f}</td><td rowspan="3"><b>{alligator_status}</b></td></tr>
    <tr><td>鳄鱼·牙齿 (红·SMA8)</td><td>${allig_teeth:,.2f}</td></tr>
    <tr><td>鳄鱼·颚骨 (蓝·SMA13)</td><td>${allig_jaw:,.2f}</td></tr>
  </table>
</div>

<h2>🎯 关键价位 & 斐波那契目标</h2>
<div class="grid">
  <div class="card" style="border-color:#3fb950;"><div class="label" style="color:#3fb950;">🎯 T3</div><div class="value" style="color:#3fb950;">$101,000</div><div style="color:#8b949e;font-size:13px;">Fib 0.382 · 乐观目标</div></div>
  <div class="card" style="border-color:#58a6ff;"><div class="label" style="color:#58a6ff;">🎯 T2</div><div class="value" style="color:#58a6ff;">$93,000</div><div style="color:#8b949e;font-size:13px;">Fib 0.500 · 2026-01阻力区</div></div>
  <div class="card" style="border-color:#d29922;"><div class="label" style="color:#d29922;">🎯 T1</div><div class="value" style="color:#d29922;">$85,200</div><div style="color:#8b949e;font-size:13px;">Fib 0.618 · 第一目标</div></div>
  <div class="card" style="border-color:#f0883e;"><div class="label" style="color:#f0883e;">📍 当前位置</div><div class="value" style="color:#f0883e;">${cp:,.0f}</div><div style="color:#8b949e;font-size:13px;">浪⑤-③推进中</div></div>
  <div class="card" style="border-color:#f85149;"><div class="label" style="color:#f85149;">🛡️ S1支撑</div><div class="value" style="color:#f85149;">$74,000</div><div style="color:#8b949e;font-size:13px;">MA20+Fib0.786</div></div>
  <div class="card" style="border-color:#f85149;"><div class="label" style="color:#f85149;">⛔ 止损线</div><div class="value" style="color:#f85149;">$59,781</div><div style="color:#8b949e;font-size:13px;">浪⑤结构失效位</div></div>
</div>

<h2>🔍 短线视角 (H1 · 近7天)</h2>
<div class="chart-box">
  <canvas id="h1Chart" height="200"></canvas>
</div>

<div class="wave-section">
  <h3>H1 最新数据</h3>
  <div style="overflow-x:auto;">
  <table>
    <tr><th>时间</th><th>开</th><th>高</th><th>低</th><th>收</th><th>量</th></tr>
    {h1_rows}
  </table>
  </div>
</div>

<div style="background:{'#1c1a0a' if rsi_val > 65 else '#161b22'};border:1px solid {'#d29922' if rsi_val > 65 else '#30363d'};border-radius:8px;padding:15px;margin:20px 0;">
  <b style="color:{'#d29922' if rsi_val > 65 else '#8b949e'};">⚠️ 风险提示</b>
  <p style="color:#8b949e;font-size:13px;margin-top:5px;">
    本报告基于技术分析自动生成，仅供参考，不构成投资建议。
    加密货币市场波动巨大。<br>
    RSI({rsi_val:.1f}){'偏高，短期有回调需求' if rsi_val > 65 else '正常'},
    浪⑤-③已运行+{pct53}%，当前追高风险较大。
    建议等待⑤-④回调后在MA20~MA60附近伺机做多。
  </p>
</div>

<div class="footer">BTCUSD 分析报告 · 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M")} · GPT/人工智能分析仅供参考</div>

</div>

<script>
const cd = {chart_json};
const ma5d = {ma5_json};
const ma20d = {ma20_json};
const rsid = {rsi_json};
const h1d = {h1_json};

// 主价格图
new Chart(document.getElementById('priceChart'), {{
  type: 'line',
  data: {{
    labels: cd.dates,
    datasets: [
      {{label:'收盘',data:cd.close,borderColor:'#3fb950',backgroundColor:'rgba(63,185,80,0.08)',fill:true,tension:0.15,pointRadius:0,borderWidth:2,yAxisID:'y'}},
      {{label:'MA5',data:ma5d,borderColor:'#f0883e',borderDash:[5,3],pointRadius:0,borderWidth:1,tension:0.15,yAxisID:'y'}},
      {{label:'MA20',data:ma20d,borderColor:'#58a6ff',borderDash:[5,3],pointRadius:0,borderWidth:1,tension:0.15,yAxisID:'y'}}
    ]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#8b949e'}}}}}},
    scales:{{
      x:{{ticks:{{color:'#484f58',maxTicksLimit:10}},grid:{{color:'#21262d'}}}},
      y:{{ticks:{{color:'#484f58'}},grid:{{color:'#21262d'}}}}
    }}
  }}
}});

// RSI
new Chart(document.getElementById('rsiChart'), {{
  type: 'line',
  data: {{
    labels: cd.dates,
    datasets: [{{label:'RSI(14)',data:rsid,borderColor:'#d29922',pointRadius:0,borderWidth:1.5,tension:0.15,yAxisID:'y'}}]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#8b949e'}}}}}},
    scales:{{
      x:{{display:false}},
      y:{{min:20,max:85,ticks:{{color:'#484f58',stepSize:10}},grid:{{color:'#21262d'}}}}
    }}
  }}
}});

// H1
new Chart(document.getElementById('h1Chart'), {{
  type: 'line',
  data: {{
    labels: h1d.dates,
    datasets: [{{label:'H1收盘',data:h1d.close,borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,0.08)',fill:true,tension:0.1,pointRadius:0,borderWidth:1.5,yAxisID:'y'}}]
  }},
  options: {{
    responsive:true, maintainAspectRatio:false,
    plugins:{{legend:{{labels:{{color:'#8b949e'}}}}}},
    scales:{{
      x:{{ticks:{{color:'#484f58',maxTicksLimit:12}},grid:{{color:'#21262d'}}}},
      y:{{ticks:{{color:'#484f58'}},grid:{{color:'#21262d'}}}}
    }}
  }}
}});
</script>

</body>
</html>"""

os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ 报告已生成: {OUTPUT_FILE}')
print(f'  D1: {len(d1)} 条 | H4: {len(h4_all)} 条 | H1: {len(h1_all)} 条 | M5: {len(m5_all)} 条')
print(f'  当前价格: ${cp:,.2f} | RSI: {rsi_val:.1f} | 趋势评分: {score}/7 | {trend_str}')

conn.close()
