"""
生成黄金混沌理论分析HTML报告并推送到GitHub Pages
"""

import os, sqlite3, json
from datetime import datetime

DB = r'C:\Users\Administrator\.openclaw\workspace\data\taskflow.db'
REPO = r'C:\Users\Administrator\.openclaw\workspace'
GH_BRANCH = 'gh-pages'
OUTPUT_FILE = 'gold_analysis.html'

def generate_html():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    c.execute('SELECT content, created_at FROM analysis_log WHERE symbol=? AND analysis_type=? ORDER BY id DESC LIMIT 1', 
              ('XAUUSD', 'chaos_wave'))
    row = c.fetchone()
    if not row:
        print('No analysis record found')
        conn.close()
        return False
    
    analysis = json.loads(row[0])
    created_at = row[1]
    
    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe='D1' ORDER BY time DESC LIMIT 10")
    recent_bars = c.fetchall()
    
    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe='H4' ORDER BY time DESC LIMIT 8")
    h4_bars = c.fetchall()
    
    conn.close()
    
    price = analysis.get('latest_price', 0)
    d1_state = analysis.get('d1_state', 'unknown')
    h4_state = analysis.get('h4_state', 'unknown')
    h1_state = analysis.get('h1_state', 'unknown')
    
    d1_ao = analysis.get('d1_ao', 'N/A')
    h4_ao = analysis.get('h4_ao', 'N/A')
    h1_ao = analysis.get('h1_ao', 'N/A')
    
    targets = analysis.get('targets', {})
    supports = analysis.get('supports', {})
    bull_sh = analysis.get('bullish_signals', [])
    bear_sh = analysis.get('bearish_signals', [])
    wave_stage = analysis.get('wave_stage', '数据不足')
    is_bearish_trend = analysis.get('is_bearish_trend', False)
    is_bullish_trend = analysis.get('is_bullish_trend', False)
    key_resistances = analysis.get('key_resistances', [])
    key_supports = analysis.get('key_supports', [])
    latest_time = analysis.get('latest_time', '')

    def calc_pct(val, base):
        if not val or not base or not isinstance(val, (int, float)): return ''
        return f"{'+' if val >= base else ''}{(val/base-1)*100:.2f}%"

    def fmt_target(val, pct_str):
        if pct_str:
            return f"${val} ({pct_str})"
        return f"${val}" if isinstance(val, (int, float)) else str(val)

    t1_val = targets.get('T1', 'N/A')
    t2_val = targets.get('T2', 'N/A')
    t3_val = targets.get('T3', 'N/A')
    s1_val = supports.get('S1', 'N/A')
    s2_val = supports.get('S2', 'N/A')
    s3_val = supports.get('S3', 'N/A')

    t1_line = fmt_target(t1_val, calc_pct(t1_val, price))
    t2_line = fmt_target(t2_val, calc_pct(t2_val, price))
    t3_line = fmt_target(t3_val, calc_pct(t3_val, price))
    s1_line = fmt_target(s1_val, calc_pct(s1_val, price))
    s2_line = fmt_target(s2_val, calc_pct(s2_val, price))
    s3_line = fmt_target(s3_val, calc_pct(s3_val, price))
    
    state_names = {
        'eating_up': '多头进食', 'eating_down': '空头进食',
        'awakening_up': '苏醒偏多', 'awakening_down': '苏醒偏空',
        'sleeping': '盘整睡觉', 'mixed': '方向不明确', 'unknown': '数据不足'
    }
    d1_name = state_names.get(d1_state, d1_state)
    h4_name = state_names.get(h4_state, h4_state)
    h1_name = state_names.get(h1_state, h1_state)
    
    # AO显示精度统一
    def fmt_ao(v):
        if v is None: return 'N/A'
        return f"{v:.2f}"
    
    d1_ao_str = fmt_ao(d1_ao)
    h4_ao_str = fmt_ao(h4_ao)
    h1_ao_str = fmt_ao(h1_ao)
    
    # AO描述
    d1_ao_desc = '空头动能衰减' if d1_ao is not None and d1_ao < 0 else '多头区域'
    h4_ao_desc = '上穿零轴看涨' if h4_ao is not None and h4_ao > 0 else '空头区域'
    h1_ao_desc = '多头强势' if h1_ao is not None and h1_ao > 0 else '空头区域'
    
    date_str = created_at[:10] if len(created_at) >= 10 else created_at
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 信号HTML
    bull_html = ''
    for s in bull_sh:
        bull_html += f'<li class="bull">{s}</li>\n'
    bear_html = ''
    for s in bear_sh:
        bear_html += f'<li class="bear">{s}</li>\n'
    
    # 趋势方向说明
    trend_desc = '📉 空头主导' if is_bearish_trend else ('📈 多头主导' if is_bullish_trend else '🔄 方向不明确')
    
    # 关键阻力支撑行
    resist_rows = ''
    for i, p in enumerate(key_resistances[:3], 1):
        dist = ((p - price) / price * 100) if price else 0
        resist_rows += f'<tr><td>R{i}</td><td class="red">${p:.2f}</td><td class="red">{dist:+.2f}%</td></tr>'
    support_rows = ''
    for i, p in enumerate(key_supports[:3], 1):
        dist = ((p - price) / price * 100) if price else 0
        support_rows += f'<tr><td>S{i}</td><td class="green">${p:.2f}</td><td class="green">{dist:+.2f}%</td></tr>'
    
    bars_rows = ''
    for r in recent_bars:
        chg = ((r[4] - r[1]) / r[1] * 100) if r[1] else 0
        color = 'up' if chg >= 0 else 'down'
        bars_rows += f'\n        <tr class="{color}"><td>{r[0][:10]}</td><td>{r[1]:.2f}</td><td>{r[2]:.2f}</td><td>{r[3]:.2f}</td><td><strong>{r[4]:.2f}</strong></td><td>{r[5]:,}</td><td class="{"green" if chg>=0 else "red"}">{"+" if chg>=0 else ""}{chg:.2f}%</td></tr>'
    
    h4_rows = ''
    for r in h4_bars:
        chg = ((r[4] - r[1]) / r[1] * 100) if r[1] else 0
        color = 'up' if chg >= 0 else 'down'
        h4_rows += f'\n        <tr class="{color}"><td>{r[0][:16]}</td><td>{r[1]:.2f}</td><td>{r[4]:.2f}</td><td class="{"green" if chg>=0 else "red"}">{"+" if chg>=0 else ""}{chg:.2f}%</td></tr>'
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>XAUUSD 黄金混沌理论分析 | {date_str}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0f;color:#e0e0e0;line-height:1.6}}
.container{{max-width:900px;margin:0 auto;padding:20px}}
.header{{text-align:center;padding:40px 0;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);border-radius:16px;margin-bottom:24px;border:1px solid #2a2a4a}}
.header h1{{font-size:2em;color:#f0c040;margin-bottom:8px}}
.header .price{{font-size:3em;font-weight:bold;color:#fff}}
.header .sub{{color:#888;font-size:0.9em}}
.green{{color:#4caf50}}
.red{{color:#f44336}}
.card{{background:#111118;border:1px solid #222;border-radius:12px;padding:20px;margin-bottom:20px}}
.card h2{{font-size:1.1em;color:#f0c040;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #222}}
.card h3{{font-size:1em;color:#aaa;margin:12px 0 8px}}
.grid-3{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.grid-2{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}
@media(max-width:600px){{.grid-3,.grid-2{{grid-template-columns:1fr}}}}
.signal-box{{background:#1a1a25;border-radius:8px;padding:12px;text-align:center}}
.signal-box .label{{font-size:0.8em;color:#888}}
.signal-box .value{{font-size:1.4em;font-weight:bold;margin:4px 0}}
.signal-box .desc{{font-size:0.85em;color:#aaa}}
table{{width:100%;border-collapse:collapse;font-size:0.9em}}
th{{background:#1a1a2e;padding:8px 12px;text-align:left;border-bottom:2px solid #333;color:#888;font-weight:normal}}
td{{padding:8px 12px;border-bottom:1px solid #1a1a1a}}
tr.up td{{background:rgba(76,175,80,0.05)}}
tr.down td{{background:rgba(244,67,54,0.05)}}
tr:hover td{{background:rgba(240,192,64,0.05)}}
.signal-list{{list-style:none;padding:0}}
.signal-list li{{padding:6px 0}}
.signal-list li.bull:before{{content:'\\01f7e2';margin-right:8px}}
.signal-list li.bear:before{{content:'\\01f534';margin-right:8px}}
.target-bar{{display:flex;flex-direction:column;gap:8px}}
.target-item{{display:flex;align-items:center;gap:12px}}
.target-label{{width:40px;font-weight:bold}}
.target-line{{flex:1;height:24px;border-radius:4px;display:flex;align-items:center;padding:0 8px;font-size:0.8em}}
.target-line.up{{background:linear-gradient(90deg,rgba(76,175,80,0.3),rgba(76,175,80,0.6))}}
.target-line.down{{background:linear-gradient(90deg,rgba(244,67,54,0.3),rgba(244,67,54,0.6))}}
.wave-box{{background:#1a1a25;border-radius:8px;padding:16px;text-align:center;margin-bottom:12px}}
.wave-box .label{{font-size:0.8em;color:#888}}
.wave-box .value{{font-size:1.1em;font-weight:bold;margin:4px 0}}
.footer{{text-align:center;padding:20px;color:#555;font-size:0.8em}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>XAUUSD 黄金分析</h1>
<div class="price">${price:.2f}</div>
<div class="sub">混沌理论·鳄鱼线·分形·波浪 | {date_str}</div>
</div>

<div class="card">
<h2>市场概览</h2>
<div class="grid-3">
<div class="signal-box"><div class="label">D1 鳄鱼线</div><div class="value">{d1_name}</div></div>
<div class="signal-box"><div class="label">H4 鳄鱼线</div><div class="value">{h4_name}</div></div>
<div class="signal-box"><div class="label">H1 鳄鱼线</div><div class="value">{h1_name}</div></div>
</div>
<div class="grid-3" style="margin-top:12px">
<div class="signal-box"><div class="label">D1 AO</div><div class="value">{d1_ao_str}</div><div class="desc">{d1_ao_desc}</div></div>
<div class="signal-box"><div class="label">H4 AO</div><div class="value" style="color:{"#4caf50" if h4_ao is not None and h4_ao > 0 else "#f44336"}">{h4_ao_str}</div><div class="desc">{h4_ao_desc}</div></div>
<div class="signal-box"><div class="label">H1 AO</div><div class="value" style="color:{"#4caf50" if h1_ao is not None and h1_ao > 0 else "#f44336"}">{h1_ao_str}</div><div class="desc">{h1_ao_desc}</div></div>
</div>
</div>

<div class="card">
<h2>潮汐方向 & 波浪阶段</h2>
<div class="wave-box"><div class="label">大趋势方向</div><div class="value">{trend_desc}</div><div class="desc">D1: {d1_name} / H4: {h4_name}</div></div>
<div class="wave-box"><div class="label">当前波浪阶段</div><div class="value">{wave_stage}</div><div class="desc">基于分形高低点推算</div></div>
</div>

<div class="card">
<h2>多空信号汇总</h2>
<div class="grid-2">
<div><h3>看涨信号 ({len(bull_sh)})</h3><ul class="signal-list">{bull_html}</ul></div>
<div><h3>看空信号 ({len(bear_sh)})</h3><ul class="signal-list">{bear_html}</ul></div>
</div>
</div>

<div class="card">
<h2>波段高低点预测</h2>
<div class="grid-2">
<div>
<h3>上行目标</h3>
<div class="target-bar">
<div class="target-item"><span class="target-label">T1</span><div class="target-line up" style="width:60%">{t1_line}</div></div>
<div class="target-item"><span class="target-label">T2</span><div class="target-line up" style="width:75%">{t2_line}</div></div>
<div class="target-item"><span class="target-label">T3</span><div class="target-line up" style="width:100%">{t3_line}</div></div>
</div>
</div>
<div>
<h3>下行支撑</h3>
<div class="target-bar">
<div class="target-item"><span class="target-label">S1</span><div class="target-line down" style="width:60%">{s1_line}</div></div>
<div class="target-item"><span class="target-label">S2</span><div class="target-line down" style="width:75%">{s2_line}</div></div>
<div class="target-item"><span class="target-label">S3</span><div class="target-line down" style="width:100%">{s3_line}</div></div>
</div>
</div>
</div>
</div>

<div class="card">
<h2>关键阻力支撑位（基于分形）</h2>
<div class="grid-2">
<div><table><tr><th></th><th>点位</th><th>距当前</th></tr>{resist_rows}</table></div>
<div><table><tr><th></th><th>点位</th><th>距当前</th></tr>{support_rows}</table></div>
</div>
</div>

<div class="card">
<h2>D1 日线 (最近10根)</h2>
<table><tr><th>日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>成交量</th><th>涨跌幅</th></tr>{bars_rows}
</table>
</div>

<div class="card">
<h2>H4 4小时 (最近8根)</h2>
<table><tr><th>时间</th><th>开盘</th><th>收盘</th><th>涨跌幅</th></tr>{h4_rows}
</table>
</div>

<div class="card" style="border-color:#332200">
<h2>风险提示</h2>
<p style="color:#888;font-size:0.9em">
本分析基于比尔威廉姆混沌理论（鳄鱼线、分形、AO）和艾略特波浪理论，仅供参考，不构成投资建议。<br>
数据来源: MT5 (Exness) - XAUUSDm | 数据截至: {latest_time} | 生成时间: {date_str}
</p>
</div>

<div class="footer">小白 (Xiao Bai) · OpenClaw AI · {now_str}</div>
</div>
</body>
</html>'''
    
    out_path = os.path.join(REPO, OUTPUT_FILE)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'HTML report generated: {out_path}')
    return True

if __name__ == '__main__':
    if generate_html():
        print('\nGitHub Pages URL: https://goldland2021.github.io/openclaw_mt5/gold_analysis.html')
