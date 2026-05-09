"""
混沌理论 + 波浪理论分析黄金行情
基于 Bill Williams 分形、鳄鱼线、AO 指标
"""

import sqlite3, os, json
from datetime import datetime, timedelta

DB = r'C:\Users\Administrator\.openclaw\workspace\data\taskflow.db'

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

RESULTS = {}

# ============ 1. 获取最新行情数据 ============
print("=" * 70)
print("  混沌理论 & 波浪理论 - XAUUSD 黄金分析")
print("  分析时间: 2026-05-06 13:36 CST")
print("=" * 70)

# D1 数据用于大趋势判断
c.execute("""
    SELECT time, open, high, low, close, tick_volume
    FROM kline_raw WHERE timeframe='D1'
    ORDER BY time ASC
""")
d1_rows = c.fetchall()
print(f"\n[D1] 日线数据: {len(d1_rows)} 根K线")

# H4 用于中期分析
c.execute("""
    SELECT time, open, high, low, close, tick_volume
    FROM kline_raw WHERE timeframe='H4'
    ORDER BY time ASC
""")
h4_rows = c.fetchall()

# H1 用于短期分析
c.execute("""
    SELECT time, open, high, low, close, tick_volume
    FROM kline_raw WHERE timeframe='H1'
    ORDER BY time ASC
""")
h1_rows = c.fetchall()

# ============ 2. 计算鳄鱼线 (Alligator) ============
def calc_sma(data, period, field='close'):
    """计算简单移动平均"""
    vals = [r[field] for r in data]
    result = [None] * len(vals)
    for i in range(period - 1, len(vals)):
        s = sum(vals[i - period + 1:i + 1]) / period
        result[i] = round(s, 2)
    return result

def calc_alligator(data):
    """鳄鱼线: Jaw(SMMA 13, shift 8), Teeth(SMMA 8, shift 5), Lips(SMMA 5, shift 3)"""
    closes = [r['close'] for r in data]
    n = len(closes)
    
    def smma(period):
        """Smoothed Moving Average"""
        result = [None] * n
        first_idx = period - 1
        result[first_idx] = sum(closes[:period]) / period
        for i in range(first_idx + 1, n):
            result[i] = (result[i-1] * (period - 1) + closes[i]) / period
        return result
    
    jaw = smma(13)    # 蓝色 - 颚线
    teeth = smma(8)   # 红色 - 齿线
    lips = smma(5)    # 绿色 - 唇线
    
    return jaw, teeth, lips

# 计算D1鳄鱼线
d1_jaw, d1_teeth, d1_lips = calc_alligator(d1_rows)
h4_jaw, h4_teeth, h4_lips = calc_alligator(h4_rows)
h1_jaw, h1_teeth, h1_lips = calc_alligator(h1_rows)

# ============ 3. 寻找分形 (Fractals) ============
def find_fractals(data, period=2):
    """
    比尔威廉姆分形:
    Up Fractal: 中间最高，左右各period根更低
    Down Fractal: 中间最低，左右各period根更高
    """
    n = len(data)
    up_fractals = []    # (idx, price, time)
    down_fractals = []  # (idx, price, time)
    
    valid_start = period  # 需要前period根 + 后period根
    valid_end = n - period
    
    for i in range(valid_start, valid_end):
        is_up = True
        is_down = True
        
        for j in range(1, period + 1):
            if data[i]['high'] <= data[i - j]['high'] or data[i]['high'] <= data[i + j]['high']:
                is_up = False
            if data[i]['low'] >= data[i - j]['low'] or data[i]['low'] >= data[i + j]['low']:
                is_down = False
        
        if is_up:
            up_fractals.append((i, data[i]['high'], data[i]['time']))
        if is_down:
            down_fractals.append((i, data[i]['low'], data[i]['time']))
    
    return up_fractals, down_fractals

def find_fractals_fast(data, field_high='high', field_low='low'):
    """更快的分形查找: 标准5根K线分形"""
    n = len(data)
    up = []
    down = []
    
    for i in range(2, n - 2):
        # Up Fractal: 中间高 > 左边2根 且 中间高 >= 右边2根
        if (data[i][field_high] > data[i-1][field_high] and
            data[i][field_high] > data[i-2][field_high] and
            data[i][field_high] >= data[i+1][field_high] and
            data[i][field_high] >= data[i+2][field_high]):
            up.append((i, data[i][field_high], data[i]['time']))
        
        # Down Fractal: 中间低 < 左边2根 且 中间低 <= 右边2根
        if (data[i][field_low] < data[i-1][field_low] and
            data[i][field_low] < data[i-2][field_low] and
            data[i][field_low] <= data[i+1][field_low] and
            data[i][field_low] <= data[i+2][field_low]):
            down.append((i, data[i][field_low], data[i]['time']))
    
    return up, down

# D1分形
d1_up, d1_down = find_fractals_fast(d1_rows)
h4_up, h4_down = find_fractals_fast(h4_rows)
h1_up, h1_down = find_fractals_fast(h1_rows)

print(f"\n[D1] 分形信号: 顶部 {len(d1_up)} 个, 底部 {len(d1_down)} 个")

# ============ 4. 计算 AO (Awesome Oscillator) ============
def calc_ao(data):
    """AO = SMA(5) median - SMA(34) median, median = (high+low)/2"""
    n = len(data)
    medians = [(r['high'] + r['low']) / 2 for r in data]
    ao = [None] * n
    
    for i in range(33, n):
        sma5 = sum(medians[i-4:i+1]) / 5
        sma34 = sum(medians[i-33:i+1]) / 34
        ao[i] = round(sma5 - sma34, 4)
    
    return ao

d1_ao = calc_ao(d1_rows)
h4_ao = calc_ao(h4_rows)
h1_ao = calc_ao(h1_rows)

# ============ 5. 波浪识别 ============
def identify_waves_elliott(up_fractals, down_fractals, data):
    """
    基于分形识别潜在波浪结构
    遵循规则:
    - 波浪2不破波浪1起点
    - 波浪3不是最短的
    - 波浪4不进入波浪1价格区间
    """
    waves = []
    
    # 交替使用顶底分形来识别波动
    # 简化: 取清晰的分形交替作为波浪边界
    all_points = []
    for idx, price, t in up_fractals:
        all_points.append(('top', idx, price, t))
    for idx, price, t in down_fractals:
        all_points.append(('bottom', idx, price, t))
    
    all_points.sort(key=lambda x: x[1])  # 按K线索引排序
    
    # 找显著的高低点
    significant_highs = []
    significant_lows = []
    
    for typ, idx, price, t in all_points:
        if typ == 'top':
            significant_highs.append((idx, price, t))
        else:
            significant_lows.append((idx, price, t))
    
    # 合并为交替的高低点序列
    sequence = []
    h_idx = l_idx = 0
    
    # 从第一个点开始
    if all_points:
        first = all_points[0]
        sequence.append(first)
        
        for i in range(1, len(all_points)):
            last = sequence[-1]
            curr = all_points[i]
            
            # 交替: top->bottom 或 bottom->top
            if curr[0] != last[0]:
                # 确保价格符合趋势方向
                if curr[0] == 'top' and curr[2] > last[2]:
                    sequence.append(curr)
                elif curr[0] == 'bottom' and curr[2] < last[2]:
                    sequence.append(curr)
                else:
                    # 如果不符合趋势，可能是在盘整，加入但标记
                    sequence.append(curr)
    
    return sequence

d1_sequence = identify_waves_elliott(d1_up, d1_down, d1_rows)

# ============ 6. 判断鳄鱼线状态 ============
def get_alligator_state(jaw, teeth, lips, idx):
    """判断鳄鱼线状态: sleeping, awakening, eating, satiated"""
    if idx < 0 or idx >= len(jaw):
        return 'unknown'
    j, t, l = jaw[idx], teeth[idx], lips[idx]
    if j is None or t is None or l is None:
        return 'unknown'
    
    # 鳄鱼睡觉: 三线缠绕
    spread = max(j, t, l) - min(j, t, l)
    if spread < 0.5:
        return 'sleeping'
    
    # 鳄鱼进食: 三线发散，价格在线之上(多头)或之下(空头)
    if l > t > j:
        return 'eating_up'
    elif j > t > l:
        return 'eating_down'
    elif l > j or t > j:
        return 'awakening_up'
    elif j > t or j > l:
        return 'awakening_down'
    
    return 'mixed'

# 获取最后几根的状态
last_idx_d1 = len(d1_rows) - 1
d1_state = get_alligator_state(d1_jaw, d1_teeth, d1_lips, last_idx_d1)
last_idx_h4 = len(h4_rows) - 1
h4_state = get_alligator_state(h4_jaw, h4_teeth, h4_lips, last_idx_h4)
last_idx_h1 = len(h1_rows) - 1
h1_state = get_alligator_state(h1_jaw, h1_teeth, h1_lips, last_idx_h1)

# ============ 7. 最新AO柱状图判断 ============
def get_ao_state(ao, idx):
    if idx < 0 or idx >= len(ao) or ao[idx] is None:
        return 'unknown'
    val = ao[idx]
    if idx > 0 and ao[idx-1] is not None:
        prev = ao[idx-1]
        if val > 0 and prev > 0 and val > prev:
            return 'double_green_up'  # 双绿上涨
        elif val > 0 and prev > 0 and val < prev:
            return 'double_green_down'  # 双绿减弱
        elif val < 0 and prev < 0 and val < prev:
            return 'double_red_down'  # 双红下跌
        elif val < 0 and prev < 0 and val > prev:
            return 'double_red_up'  # 双红减弱
        elif val > 0 >= prev:
            return 'green_cross'  # 穿过零轴向上
        elif val < 0 <= prev:
            return 'red_cross'  # 穿过零轴向下
    elif val > 0:
        return 'green'
    elif val < 0:
        return 'red'
    return 'zero'

d1_ao_state = get_ao_state(d1_ao, last_idx_d1)
h4_ao_state = get_ao_state(h4_ao, last_idx_h4)
h1_ao_state = get_ao_state(h1_ao, last_idx_h1)

# ============ 8. 波浪计数 ============
def count_elliott_waves(sequence, data):
    """
    尝试识别艾略特波浪 (1-2-3-4-5)
    这里不做完美识别，而是用分形高低点推断潜在结构
    """
    if len(sequence) < 5:
        return []
    
    # 取最近N个显著高低点分析
    recent = sequence[-15:] if len(sequence) > 15 else sequence
    
    # 识别上升趋势中的5浪结构
    potential_wave = []
    for i in range(1, len(recent)):
        typ, idx, price, t = recent[i]
        prev_typ, prev_idx, prev_price, prev_t = recent[i-1]
        
        potential_wave.append({
            'type': typ,
            'price': price,
            'time': t,
            'k_idx': idx,
        })
    
    return potential_wave

d1_waves = count_elliott_waves(d1_sequence, d1_rows)

# ============ 9. 输出分析报告 ============
print("\n" + "=" * 70)
print("  一、鳄鱼线状态 (Alligator)")
print("=" * 70)
state_names = {
    'sleeping': '睡觉 (盘整)',
    'eating_up': '进食 - 多头 (三线发散向上)',
    'eating_down': '进食 - 空头 (三线发散向下)',
    'awakening_up': '苏醒 - 偏多',
    'awakening_down': '苏醒 - 偏空',
    'mixed': '方向不明确',
    'unknown': '数据不足'
}
print(f"  D1  日线: {state_names.get(d1_state, d1_state)}")
print(f"  H4 4小时: {state_names.get(h4_state, h4_state)}")
print(f"  H1 1小时: {state_names.get(h1_state, h1_state)}")

print("\n" + "=" * 70)
print("  二、AO动量振荡器")
print("=" * 70)
ao_names = {
    'double_green_up': '双绿上涨 - 多头强势',
    'double_green_down': '双绿减弱 - 多头动能衰减',
    'double_red_down': '双红下跌 - 空头强势',
    'double_red_up': '双红减弱 - 空头动能衰减',
    'green_cross': '上穿零轴 - 转多信号',
    'red_cross': '下穿零轴 - 转空信号',
    'green': '零上绿色 - 多头',
    'red': '零下红色 - 空头',
    'zero': '零轴',
    'unknown': '数据不足',
}
print(f"  D1  AO: {ao_names.get(d1_ao_state, d1_ao_state)}  (值: {d1_ao[-1] if d1_ao[-1] else 'N/A'})")
print(f"  H4  AO: {ao_names.get(h4_ao_state, h4_ao_state)}  (值: {h4_ao[-1] if h4_ao[-1] else 'N/A'})")
print(f"  H1  AO: {ao_names.get(h1_ao_state, h1_ao_state)}  (值: {h1_ao[-1] if h1_ao[-1] else 'N/A'})")

print("\n" + "=" * 70)
print("  三、分形信号 (最近20个)")
print("=" * 70)

# D1最近分形
recent_d1_up = [x for x in d1_up if x[0] > len(d1_rows) - 60][-10:]
recent_d1_down = [x for x in d1_down if x[0] > len(d1_rows) - 60][-10:]
all_recent = []
for i, p, t in recent_d1_up:
    all_recent.append(('顶部', p, t))
for i, p, t in recent_d1_down:
    all_recent.append(('底部', p, t))
all_recent.sort(key=lambda x: x[2])

print(f"  D1 最近分形:")
for typ, p, t in all_recent[-12:]:
    print(f"    [{typ}] {t[:10]}  价格: {p:.2f}")

# 最后10个H4分形
recent_h4_up = [x for x in h4_up if x[0] > len(h4_rows) - 40][-5:]
recent_h4_down = [x for x in h4_down if x[0] > len(h4_rows) - 40][-5:]
print(f"\n  H4 最近分形:")
for i, p, t in recent_h4_up[-5:]:
    print(f"    [顶部] {t}  价格: {p:.2f}")
for i, p, t in recent_h4_down[-5:]:
    print(f"    [底部] {t}  价格: {p:.2f}")

print("\n" + "=" * 70)
print("  四、波浪结构分析 (基于分形高低点)")
print("=" * 70)

if len(d1_sequence) > 4:
    print(f"\n  D1 波浪序列 (最近10个显著高低点):")
    recent_seq = d1_sequence[-10:]
    for i, (typ, idx, price, t) in enumerate(recent_seq):
        marker = '^' if typ == 'top' else 'v'
        print(f"    {marker} {t[:10]}  {price:.2f}  ({typ})")
else:
    print("\n  D1 数据不足以形成完整波浪结构")

# 识别当前可能的波浪位置
print(f"\n  --- 潜在波浪推算 ---")

# ============ 10. 关键支撑阻力位 ============
print("\n" + "=" * 70)
print("  五、关键支撑阻力位 (基于分形)")
print("=" * 70)

# 取最近的分形高点作为阻力，低点作为支撑
key_resistances = sorted([p for i, p, t in d1_up if i > len(d1_rows) - 250], reverse=True)[:5]
key_supports = sorted([p for i, p, t in d1_down if i > len(d1_rows) - 250])[:5]

# 当前价格
latest_close = d1_rows[-1]['close']
latest_high = d1_rows[-1]['high']
latest_low = d1_rows[-1]['low']
latest_time = d1_rows[-1]['time']

# 今日盘中数据 (H1最新)
h1_last = h1_rows[-1] if h1_rows else d1_rows[-1]

# 市场状态汇总
print(f"\n  当前价格: {h1_last['close']:.2f}  (数据截至 {h1_last['time']})")
print(f"\n  阻力位 (基于D1分形顶部):")
for i, p in enumerate(key_resistances[:5], 1):
    dist = ((p - latest_close) / latest_close * 100) if latest_close else 0
    emoji = '!' if dist < 2 else ''
    print(f"    R{i}: {p:.2f}  (距当前 {dist:+.2f}%)")

print(f"\n  支撑位 (基于D1分形底部):")
for i, p in enumerate(key_supports[:5], 1):
    dist = ((p - latest_close) / latest_close * 100) if latest_close else 0
    emoji = '!' if abs(dist) < 2 else ''
    print(f"    S{i}: {p:.2f}  (距当前 {dist:+.2f}%)")

# ============ 11. 综合分析结论 ============
print("\n" + "=" * 70)
print("  六、综合研判")
print("=" * 70)

# 判断趋势
trend_signals = []
bearish_signals = []

# 鳄鱼线信号（全周期）
if 'eating_up' in d1_state:
    trend_signals.append('D1鳄鱼线多头进食')
elif 'sleeping' in d1_state:
    trend_signals.append('D1鳄鱼线盘整')

# H4/H1鳄鱼线多头信号
if h4_state == 'eating_up':
    trend_signals.append('H4鳄鱼线多头进食')
if h1_state == 'eating_up':
    trend_signals.append('H1鳄鱼线多头进食')

# 空头信号补充
if h4_state == 'eating_down':
    bearish_signals.append('H4鳄鱼线空头进食')
if h1_state == 'eating_down':
    bearish_signals.append('H1鳄鱼线空头进食')

# AO信号（全周期）
if 'green' in d1_ao_state or 'double_green' in d1_ao_state:
    trend_signals.append('D1 AO处于多头区域')
elif 'red' in d1_ao_state or 'double_red' in d1_ao_state:
    bearish_signals.append('D1 AO处于空头区域')

if 'green' in h4_ao_state or 'double_green' in h4_ao_state:
    trend_signals.append('H4 AO上穿零轴偏多')
if 'green' in h1_ao_state or 'double_green' in h1_ao_state:
    trend_signals.append('H1 AO多头强势')

if 'red' in h4_ao_state or 'double_red' in h4_ao_state:
    bearish_signals.append('H4 AO处于空头区域')
if 'red' in h1_ao_state or 'double_red' in h1_ao_state:
    bearish_signals.append('H1 AO处于空头区域')

# 均线排序 (最新鳄鱼线位置)
last_c = d1_rows[-1]['close']
last_j = d1_jaw[-1] if d1_jaw[-1] else 0
last_t = d1_teeth[-1] if d1_teeth[-1] else 0
last_l = d1_lips[-1] if d1_lips[-1] else 0

print(f"\n  鳄鱼线位置 (D1最新):")
print(f"    价格: {last_c:.2f}")
print(f"    颚线(Jaw):   {last_j:.2f}  ")
print(f"    齿线(Teeth): {last_t:.2f}  ")
print(f"    唇线(Lips):  {last_l:.2f}  ")

if last_c > last_l > last_t > last_j:
    print(f"   → 多头排列: 价格 > 唇线 > 齿线 > 颚线")
    trend_signals.append('D1多头排列')
elif last_c < last_j < last_t < last_l:
    print(f"   → 空头排列: 价格 < 颚线 < 齿线 < 唇线")
    bearish_signals.append('D1空头排列')
else:
    print(f"   → 交叉盘整")

print(f"\n  多空信号汇总:")
print(f"  看涨信号 ({len(trend_signals)}):")
for s in trend_signals:
    print(f"    + {s}")
print(f"  看空信号 ({len(bearish_signals)}):")
for s in bearish_signals:
    print(f"    - {s}")

# ============ 12. 波段高低点预测 ============
print("\n" + "=" * 70)
print("  七、波段高低点预测 (混沌+波浪)")
print("=" * 70)

# 基于分形和波浪结构预测
# 使用最近30根K线的分形（当前波段，避免历史极值干扰）
recent_window = 30
last_3_tops = sorted([p for i, p, t in d1_up if i > len(d1_rows) - recent_window], reverse=True)[:3]
last_3_bottoms = sorted([p for i, p, t in d1_down if i > len(d1_rows) - recent_window])[:3]

# 当前波段区间
current_high = max(r['high'] for r in d1_rows[-recent_window:])
current_low = min(r['low'] for r in d1_rows[-recent_window:])
wave_range = current_high - current_low

# 根据趋势方向选择优先目标方向
# 趋势偏空 → 优先下行目标；趋势偏多 → 优先上行目标
is_bearish_trend = 'eating_down' in d1_state or 'awakening_down' in d1_state
is_bullish_trend = 'eating_up' in d1_state or 'awakening_up' in d1_state

# 上行目标（基于当前波段的斐波那契扩展）
if len(last_3_tops) >= 2 and wave_range > 0:
    proj_target1 = current_high + wave_range * 0.382
    proj_target2 = current_high + wave_range * 0.618
    proj_target3 = current_high + wave_range * 1.0
else:
    proj_target1 = last_c * 1.02
    proj_target2 = last_c * 1.05
    proj_target3 = last_c * 1.08

# 下行支撑（基于当前波段的斐波那契回调/扩展）
if len(last_3_bottoms) >= 2 and wave_range > 0:
    proj_support1 = current_high - wave_range * 0.618  # 0.618回调位
    proj_support2 = current_low  # 前低支撑
    proj_support3 = current_low - wave_range * 0.382  # 破位延伸
else:
    proj_support1 = last_c * 0.98
    proj_support2 = last_c * 0.95
    proj_support3 = last_c * 0.92

# 偏空趋势下，缩小上行目标（作为反弹压力位而非主方向）
if is_bearish_trend:
    # 上行作为反弹压力而非主目标，更保守
    proj_target1 = current_high + wave_range * 0.236  # 弱反弹
    proj_target2 = current_high + wave_range * 0.382  # 中等反弹
    proj_target3 = current_high + wave_range * 0.618  # 强反弹
    # 下行扩展更激进
    proj_support2 = current_low
    proj_support3 = current_low - wave_range * 0.5  # 破位延伸更远

# 偏多趋势下，缩小下行支撑
if is_bullish_trend:
    proj_support1 = current_high - wave_range * 0.382  # 浅回调
    proj_support2 = current_low  # 前低
    proj_support3 = current_low - wave_range * 0.236  # 浅破位

print(f"\n  📈 上行目标 (基于波浪延伸):")
print(f"    T1 (弱阻力):  {proj_target1:.2f}  ({(proj_target1/last_c - 1)*100:+.2f}%)")
print(f"    T2 (中阻力):  {proj_target2:.2f}  ({(proj_target2/last_c - 1)*100:+.2f}%)")
print(f"    T3 (强阻力):  {proj_target3:.2f}  ({(proj_target3/last_c - 1)*100:+.2f}%)")

print(f"\n  📉 下行支撑 (基于分形结构):")
print(f"    S1 (弱支撑):  {proj_support1:.2f}  ({(proj_support1/last_c - 1)*100:+.2f}%)")
print(f"    S2 (中支撑):  {proj_support2:.2f}  ({(proj_support2/last_c - 1)*100:+.2f}%)")
print(f"    S3 (强支撑):  {proj_support3:.2f}  ({(proj_support3/last_c - 1)*100:+.2f}%)")

# 波浪阶段判断
print(f"\n  🔮 波浪阶段判断:")
current_wave_stage = "数据不足"
# 从最近的分形高低点判断
if d1_up and d1_down:
    latest_up = max(d1_up[-3:], key=lambda x: x[0]) if len(d1_up) >= 3 else d1_up[-1]
    latest_down = max(d1_down[-3:], key=lambda x: x[0]) if len(d1_down) >= 3 else d1_down[-1]
    
    if latest_up[0] > latest_down[0]:
        # 最后是顶部，可能在回调
        print(f"    - 最后分形信号: 顶部 ({latest_up[1]:.2f})")
        print(f"    - 当前处于: 潜在回调/波浪4或B浪")
        current_wave_stage = "回调阶段（波浪4/B浪）"
        if last_c > last_l:
            print(f"    - 价格在唇线上方, 回调后看涨")
        else:
            print(f"    - 价格跌破唇线, 回调可能加深")
    else:
        # 最后是底部，可能在反弹
        print(f"    - 最后分形信号: 底部 ({latest_down[1]:.2f})")
        print(f"    - 当前处于: 潜在反弹/波浪3或C浪")
        current_wave_stage = "反弹阶段（波浪3/C浪）"
        if last_c > last_l:
            print(f"    - 价格站上唇线, 反弹有望延续")
        else:
            print(f"    - 价格仍在唇线下方, 反弹力度待确认")

print(f"\n  风险提示: 混沌理论本质是概率分析, 不构成投资建议")
print(f"  建议结合基本面和其他指标综合判断")

# ============ 保存分析结果 ============
analysis = {
    'time': '2026-05-06 13:36',
    'symbol': 'XAUUSD',
    'latest_price': round(h1_last['close'], 2),
    'd1_state': d1_state,
    'h4_state': h4_state,
    'h1_state': h1_state,
    'd1_ao': round(d1_ao[-1], 4) if d1_ao[-1] else None,
    'h4_ao': round(h4_ao[-1], 4) if h4_ao[-1] else None,
    'h1_ao': round(h1_ao[-1], 4) if h1_ao[-1] else None,
    'targets': {
        'T1': round(proj_target1, 2),
        'T2': round(proj_target2, 2),
        'T3': round(proj_target3, 2),
    },
    'supports': {
        'S1': round(proj_support1, 2),
        'S2': round(proj_support2, 2),
        'S3': round(proj_support3, 2),
    },
    'bullish_signals': trend_signals,
    'bearish_signals': bearish_signals,
    'wave_stage': current_wave_stage,
    'wave_range': round(wave_range, 2),
    'key_resistances': [round(p, 2) for p in key_resistances[:3]],
    'key_supports': [round(p, 2) for p in key_supports[:3]],
    'latest_time': h1_last['time'],
    'is_bearish_trend': is_bearish_trend,
    'is_bullish_trend': is_bullish_trend,
}

# 存回数据库(加个分析记录表)
c.execute('''
    CREATE TABLE IF NOT EXISTS analysis_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        analysis_type TEXT NOT NULL DEFAULT 'chaos_wave',
        content TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )
''')
c.execute('INSERT INTO analysis_log (symbol, analysis_type, content) VALUES (?, ?, ?)',
          ('XAUUSD', 'chaos_wave', json.dumps(analysis, ensure_ascii=False)))
conn.commit()
print(f"\n  分析结果已保存到数据库")

conn.close()
