"""
H1 XAUUSD 黄金分析 - 比尔威廉姆混沌理论
基于H1周期鳄鱼线、分形、AO进行分析
"""

import sqlite3, json, os, math
from datetime import datetime

DB = r'C:\Users\Administrator\.openclaw\workspace\data\taskflow.db'
REPO = r'C:\Users\Administrator\.openclaw\workspace'
OUTPUT_FILE = 'gold_h1_analysis.html'

def sma(data, period):
    if len(data) < period: return [None] * len(data)
    result = [None] * (period - 1) + [sum(data[i - period + 1:i + 1]) / period for i in range(period - 1, len(data))]
    return result

def shifted_sma_props(data, period, shift):
    raw = sma(data, period)
    return [None] * shift + raw[:len(raw) - shift] if len(raw) > shift else [None] * len(data)

def analyze_h1():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe='H1' ORDER BY time ASC")
    raw_rows = c.fetchall()
    if len(raw_rows) < 100:
        print('H1 data insufficient')
        return False

    rows = []
    for r in raw_rows:
        rows.append({'time': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]})

    prices = [r['close'] for r in rows]
    highs = [r['high'] for r in rows]
    lows = [r['low'] for r in rows]
    n = len(rows)

    jaw = shifted_sma_props(prices, 13, 8)
    teeth = shifted_sma_props(prices, 8, 5)
    lips = shifted_sma_props(prices, 5, 3)

    last_j = jaw[-1] if jaw[-1] is not None else 0
    last_t = teeth[-1] if teeth[-1] is not None else 0
    last_l = lips[-1] if lips[-1] is not None else 0
    last_c = prices[-1]

    eating_up = last_c > last_l > last_t > last_j
    eating_down = last_c < last_j < last_t < last_l
    if eating_up:
        state = 'eating_up'
    elif eating_down:
        state = 'eating_down'
    else:
        spread_jt = abs(last_j - last_t) if last_j and last_t else 0
        spread_tl = abs(last_t - last_l) if last_t and last_l else 0
        sleep_thresh = 0.001 * last_c
        if spread_jt < sleep_thresh and spread_tl < sleep_thresh:
            state = 'sleeping'
        else:
            state = 'mixed'

    # Fractals
    up_fractals = []
    down_fractals = []
    for i in range(2, n - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            up_fractals.append((i, highs[i], rows[i]['time']))
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            down_fractals.append((i, lows[i], rows[i]['time']))

    print(f'H1 fractals: {len(up_fractals)} up, {len(down_fractals)} down')

    # AO
    med_prices = [(r['high'] + r['low']) / 2 for r in rows]
    ao5 = sma(med_prices, 5)
    ao34 = sma(med_prices, 34)
    ao = []
    for i in range(n):
        if ao5[i] is not None and ao34[i] is not None:
            ao.append(ao5[i] - ao34[i])
        else:
            ao.append(None)

    ao_last = ao[-1]
    ao_prev = ao[-2] if len(ao) > 1 else 0

    # AO color logic (red/green for CSS, then state)
    ao_is_green = ao_last is not None and ao_last > 0
    ao_is_rising = ao_last is not None and ao_prev is not None and ao_last > ao_prev

    if ao_last is not None and ao_prev is not None:
        if ao_last > 0 > ao_prev:
            ao_state = 'green_cross'
        elif ao_last < 0 < ao_prev:
            ao_state = 'red_cross'
        elif ao_last > 0 and ao_is_rising:
            ao_state = 'double_green_up'
        elif ao_last > 0 and not ao_is_rising:
            ao_state = 'double_green_down'
        elif ao_last < 0 and not ao_is_rising:
            ao_state = 'double_red_down'
        elif ao_last < 0 and ao_is_rising:
            ao_state = 'double_red_up'
        elif ao_last > 0:
            ao_state = 'green'
        elif ao_last < 0:
            ao_state = 'red'
        else:
            ao_state = 'zero'
    else:
        ao_state = 'unknown'

    recent_idx = n - 200
    recent_up = [(i, p, t) for i, p, t in up_fractals if i >= recent_idx]
    recent_down = [(i, p, t) for i, p, t in down_fractals if i >= recent_idx]

    # Wave / fractal direction
    all_fractals = []
    for i, p, t in recent_up:
        all_fractals.append((i, p, t, 'top'))
    for i, p, t in recent_down:
        all_fractals.append((i, p, t, 'bottom'))
    all_fractals.sort(key=lambda x: x[0])

    # Targets
    recent_window = 120
    current_high = max(r['high'] for r in rows[-recent_window:])
    current_low = min(r['low'] for r in rows[-recent_window:])
    wave_range = current_high - current_low

    last_3_tops = sorted([p for i, p, t in recent_up], reverse=True)[:3]
    last_3_bottoms = sorted([p for i, p, t in recent_down])[:3]

    is_bearish = 'eating_down' in state
    is_bullish = 'eating_up' in state

    if len(last_3_tops) >= 2 and wave_range > 0:
        if is_bearish:
            t1 = last_c + wave_range * 0.236
            t2 = last_c + wave_range * 0.382
            t3 = last_c + wave_range * 0.618
        else:
            t1 = current_high + wave_range * 0.382
            t2 = current_high + wave_range * 0.618
            t3 = current_high + wave_range * 1.0
    else:
        t1 = last_c * 1.01
        t2 = last_c * 1.02
        t3 = last_c * 1.03

    if len(last_3_bottoms) >= 2 and wave_range > 0:
        s1 = current_high - wave_range * 0.618
        s2 = current_low
        s3 = current_low - (wave_range * 0.5 if is_bearish else wave_range * 0.382)
    else:
        s1 = last_c * 0.99
        s2 = last_c * 0.98
        s3 = last_c * 0.97

    # === Signals (fixed logic) ===
    bullish = []
    bearish = []

    if eating_up:
        bullish.append('H1鳄鱼线多头进食：价格 > 唇线 > 齿线 > 颚线')
    elif eating_down:
        bearish.append('H1鳄鱼线空头进食：价格 < 颚线 < 齿线 < 唇线')

    if 'green' in ao_state or 'double_green' in ao_state:
        bullish.append(f'H1 AO零上偏多（值: {ao_last:.2f}）')
    elif 'red' in ao_state or 'double_red' in ao_state:
        bearish.append(f'H1 AO零下偏空（值: {ao_last:.2f}）')

    if 'cross' in ao_state:
        if ao_last > 0:
            bullish.append('H1 AO上穿零轴 - 转强信号')
        else:
            bearish.append('H1 AO下穿零轴 - 转弱信号')

    # Fractal direction: last fractal tells us
    if recent_up and recent_down:
        last_up = max(recent_up, key=lambda x: x[0])
        last_down = max(recent_down, key=lambda x: x[0])
        if last_up[0] > last_down[0]:
            # Last signal is a TOP (resistance)
            if last_c < last_up[1] * 0.995:
                bearish.append(f'最近分形为顶部（${last_up[1]:.2f}），价格承压')
        else:
            # Last signal is a BOTTOM (support)
            if last_c > last_down[1] * 1.005:
                bullish.append(f'最近分形为底部（${last_down[1]:.2f}），反弹已突破')
            else:
                bullish.append(f'最近分形为底部（${last_down[1]:.2f}），当前价格接近底部')

    # Key SR levels
    resistances = sorted([p for i, p, t in up_fractals if i > n - 500], reverse=True)[:5]
    supports = sorted([p for i, p, t in down_fractals if i > n - 500])[:5]

    analysis = {
        'time': rows[-1]['time'],
        'latest_price': round(last_c, 2),
        'current_high': round(current_high, 2),
        'current_low': round(current_low, 2),
        'wave_range': round(wave_range, 2),
        'alligator_state': state,
        'ao_value': round(ao_last, 2) if ao_last else None,
        'ao_is_green': ao_is_green,
        'ao_state': ao_state,
        'jaw': round(last_j, 2),
        'teeth': round(last_t, 2),
        'lips': round(last_l, 2),
        'targets': {'T1': round(t1, 2), 'T2': round(t2, 2), 'T3': round(t3, 2)},
        'supports': {'S1': round(s1, 2), 'S2': round(s2, 2), 'S3': round(s3, 2)},
        'bullish_signals': bullish,
        'bearish_signals': bearish,
        'is_bearish_trend': is_bearish,
        'is_bullish_trend': is_bullish,
        'up_fractals': [(t, round(p, 2)) for i, p, t in recent_up[-8:]],
        'down_fractals': [(t, round(p, 2)) for i, p, t in recent_down[-8:]],
        'resistances_list': [round(p, 2) for p in resistances[:3]],
        'sr_supports_list': [round(p, 2) for p in supports[:3]],
    }

    # Print summary
    state_names = {
        'eating_up': '多头进食', 'eating_down': '空头进食',
        'sleeping': '盘整睡觉', 'mixed': '交叉盘整', 'unknown': '数据不足'
    }
    ao_names = {
        'double_green_up': '双绿上涨（多头强势）',
        'double_green_down': '双绿减弱（多头衰减）',
        'double_red_down': '双红下跌（空头强势）',
        'double_red_up': '双红减弱（空头衰减）',
        'green_cross': '上穿零轴（转多）',
        'red_cross': '下穿零轴（转空）',
        'green': '零上绿色', 'red': '零下红色', 'zero': '零轴', 'unknown': '数据不足'
    }

    print(f'\n{"="*60}')
    print(f'  H1 XAUUSD 混沌理论分析')
    print(f'  数据截至: {rows[-1]["time"]}  价格: {last_c:.2f}')
    print(f'{"="*60}')
    print(f'  鳄鱼线: {state_names.get(state, state)}')
    print(f'  AO: {ao_names.get(ao_state, ao_state)} ({ao_last:.2f})')
    print(f'  Jaw={last_j:.2f} Teeth={last_t:.2f} Lips={last_l:.2f}')
    print(f'  看涨{len(bullish)} / 看空{len(bearish)}')
    print(f'  目标: T1={t1:.2f} T2={t2:.2f} T3={t3:.2f}')
    print(f'  支撑: S1={s1:.2f} S2={s2:.2f} S3={s3:.2f}')

    return analysis

def generate_html(analysis):
    if not analysis:
        return

    price = analysis['latest_price']
    targets = analysis['targets']
    supports = analysis['supports']
    bull = analysis['bullish_signals']
    bear = analysis['bearish_signals']

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe='H1' ORDER BY time DESC LIMIT 20")
    h1_bars = c.fetchall()
    conn.close()

    bars_rows = ''
    for r in h1_bars:
        chg = ((r[4] - r[1]) / r[1] * 100) if r[1] else 0
        color = 'up' if chg >= 0 else 'down'
        clazz = 'green' if chg >= 0 else 'red'
        bars_rows += f'\n        <tr class="{color}"><td>{r[0][:16]}</td><td>{r[1]:.2f}</td><td>{r[2]:.2f}</td><td>{r[3]:.2f}</td><td><strong>{r[4]:.2f}</strong></td><td>{r[5]:,}</td><td class="{clazz}">{"+" if chg>=0 else ""}{chg:.2f}%</td></tr>'

    state_names = {
        'eating_up': '多头进食',
        'eating_down': '空头进食',
        'sleeping': '盘整睡觉',
        'mixed': '交叉盘整',
        'unknown': '数据不足'
    }
    ao_descriptions = {
        'double_green_up': '双绿上涨（多头强势）',
        'double_green_down': '双绿减弱（多头衰减）',
        'double_red_down': '双红下跌（空头强势）',
        'double_red_up': '双红减弱（空头衰减）',
        'green_cross': '上穿零轴（转多）',
        'red_cross': '下穿零轴（转空）',
        'green': '零上绿色',
        'red': '零下红色',
        'zero': '零轴',
        'unknown': '数据不足'
    }

    alligator_state = analysis['alligator_state']
    ao_state_val = analysis['ao_state']
    ao_val = analysis['ao_value']
    ao_is_green = analysis.get('ao_is_green', False)
    is_bear = analysis['is_bearish_trend']
    is_bull = analysis['is_bullish_trend']

    def calc_pct(val, base):
        if not val or not base or not isinstance(val, (int, float)):
            return ''
        return f"{'+' if val >= base else ''}{(val/base-1)*100:.2f}%"

    def fmt_target(val, pct_str):
        if pct_str:
            return f'${val} ({pct_str})'
        return f'${val}' if isinstance(val, (int, float)) else str(val)

    t1_line = fmt_target(targets['T1'], calc_pct(targets['T1'], price))
    t2_line = fmt_target(targets['T2'], calc_pct(targets['T2'], price))
    t3_line = fmt_target(targets['T3'], calc_pct(targets['T3'], price))
    s1_line = fmt_target(supports['S1'], calc_pct(supports['S1'], price))
    s2_line = fmt_target(supports['S2'], calc_pct(supports['S2'], price))
    s3_line = fmt_target(supports['S3'], calc_pct(supports['S3'], price))

    bull_html = ''.join(f'<li class="bull">{s}</li>\n' for s in bull)
    bear_html = ''.join(f'<li class="bear">{s}</li>\n' for s in bear)

    trend_desc = '空头主导' if is_bear else ('多头主导' if is_bull else '方向不明确')
    trend_emoji = '🔴' if is_bear else ('🟢' if is_bull else '🔄')

    # Fractal table - CORRECTED: top=red (resistance), bottom=green (support)
    fractal_rows = ''
    for t, p in analysis['up_fractals']:
        fractal_rows += f'<tr class="down"><td>🔴 顶部</td><td>{t[:16]}</td><td class="red">${p:.2f}</td></tr>\n'
    for t, p in analysis['down_fractals']:
        fractal_rows += f'<tr class="up"><td>🟢 底部</td><td>{t[:16]}</td><td class="green">${p:.2f}</td></tr>\n'

    # Key SR
    resistances = analysis['resistances_list'] if isinstance(analysis.get('resistances_list'), list) else []
    supports_sr = analysis['sr_supports_list'] if isinstance(analysis.get('sr_supports_list'), list) else []

    resist_rows = ''
    for i, p in enumerate(resistances[:3], 1):
        dist = ((p - price) / price * 100) if price else 0
        resist_rows += f'<tr><td>R{i}</td><td class="red">${p:.2f}</td><td class="red">{dist:+.2f}%</td></tr>'
    support_rows = ''
    for i, p in enumerate(supports_sr[:3], 1):
        dist = ((p - price) / price * 100) if price else 0
        support_rows += f'<tr><td>S{i}</td><td class="green">${p:.2f}</td><td class="green">{dist:+.2f}%</td></tr>'

    # Alligator order description
    jaw_val = analysis['jaw']
    teeth_val = analysis['teeth']
    lips_val = analysis['lips']
    order_desc = ''
    if 'eating_up' in alligator_state:
        order_desc = f'📈 多头排列：价格(${price:.0f}) > 唇线({lips_val:.0f}) > 齿线({teeth_val:.0f}) > 颚线({jaw_val:.0f})'
    elif 'eating_down' in alligator_state:
        order_desc = f'📉 空头排列：价格(${price:.0f}) < 颚线({jaw_val:.0f}) < 齿线({teeth_val:.0f}) < 唇线({lips_val:.0f})'
    else:
        order_desc = f'🔄 交叉缠绕：颚线({jaw_val:.0f}) / 齿线({teeth_val:.0f}) / 唇线({lips_val:.0f})'

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>XAUUSD H1 黄金分析 | {analysis["time"][:10]}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0a0a0f;color:#e0e0e0;line-height:1.6}}
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
.signal-list{{list-style:none;padding:0}}
.signal-list li{{padding:6px 0}}
.signal-list li.bull:before{{content:"\\01f7e2";margin-right:8px}}
.signal-list li.bear:before{{content:"\\01f534";margin-right:8px}}
table{{width:100%;border-collapse:collapse;font-size:0.9em}}
th{{background:#1a1a2e;padding:8px 12px;text-align:left;border-bottom:2px solid #333;color:#888;font-weight:normal}}
td{{padding:8px 12px;border-bottom:1px solid #1a1a1a}}
tr.up td{{background:rgba(76,175,80,0.05)}}
tr.down td{{background:rgba(244,67,54,0.05)}}
tr:hover td{{background:rgba(240,192,64,0.05)}}
.target-bar{{display:flex;flex-direction:column;gap:8px}}
.target-item{{display:flex;align-items:center;gap:12px}}
.target-label{{width:40px;font-weight:bold}}
.target-line{{flex:1;height:24px;border-radius:4px;display:flex;align-items:center;padding:0 8px;font-size:0.8em}}
.target-line.up{{background:linear-gradient(90deg,rgba(76,175,80,0.3),rgba(76,175,80,0.6))}}
.target-line.down{{background:linear-gradient(90deg,rgba(244,67,54,0.3),rgba(244,67,54,0.6))}}
.footer{{text-align:center;padding:20px;color:#555;font-size:0.8em}}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h1>XAUUSD H1 黄金分析</h1>
<div class="price">${price:.2f}</div>
<div class="sub">混沌理论·H1周期 | {analysis["time"][:16]}</div>
</div>

<div class="card">
<h2>H1 鳄鱼线状态</h2>
<div class="grid-3">
<div class="signal-box"><div class="label">鳄鱼线</div><div class="value">{state_names.get(alligator_state, alligator_state)}</div></div>
<div class="signal-box"><div class="label">AO振荡器</div><div class="value" style="color:{"#4caf50" if ao_val is not None and ao_val > 0 else "#f44336"}">{ao_val:.2f}</div><div class="desc">{ao_descriptions.get(ao_state_val, ao_state_val)}</div></div>
<div class="signal-box"><div class="label">周期方向</div><div class="value">{trend_emoji} {trend_desc}</div></div>
</div>
<p style="color:#aaa;font-size:0.85em;margin-top:12px;padding:8px;background:#1a1a25;border-radius:6px">
{order_desc}
</p>
</div>

<div class="card">
<h2>多空信号</h2>
<div class="grid-2">
<div><h3>看涨信号 ({len(bull)})</h3><ul class="signal-list">{bull_html}</ul></div>
<div><h3>看空信号 ({len(bear)})</h3><ul class="signal-list">{bear_html}</ul></div>
</div>
</div>

<div class="card">
<h2>波段预测 (H1)</h2>
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
<div><table><tr><th></th><th>阻力</th><th>距当前</th></tr>{resist_rows}</table></div>
<div><table><tr><th></th><th>支撑</th><th>距当前</th></tr>{support_rows}</table></div>
</div>
</div>

<div class="card">
<h2>最近分形信号 (H1)</h2>
<table><tr><th></th><th>时间</th><th>价格</th></tr>
{fractal_rows}
</table>
</div>

<div class="card">
<h2>H1 K线 (最近20根)</h2>
<table><tr><th>时间</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>成交量</th><th>涨跌幅</th></tr>{bars_rows}
</table>
</div>

<div class="card" style="border-color:#332200">
<h2>风险提示</h2>
<p style="color:#888;font-size:0.9em">
本分析基于比尔威廉姆混沌理论（鳄鱼线、分形、AO），仅供参考，不构成投资建议。<br>
数据来源: MT5 (Exness) - XAUUSDm | H1周期 | {now_str}
</p>
</div>

<div class="footer">小白 (Xiao Bai) · OpenClaw AI · {now_str}</div>
</div>
</body>
</html>'''

    out_path = os.path.join(REPO, OUTPUT_FILE)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\nH1 analysis saved: {out_path}')
    print(f'URL: https://goldland2021.github.io/openclaw_mt5/{OUTPUT_FILE}')

if __name__ == '__main__':
    result = analyze_h1()
    generate_html(result)
