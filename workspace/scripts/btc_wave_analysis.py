"""
比特币BTCUSD波浪分析（比尔威廉姆混沌理论 + 艾略特波浪 + 传统技术分析）
"""
import sqlite3, json
from datetime import datetime

DB = r'C:\Users\Administrator\.openclaw\workspace\data\taskflow.db'
SYMBOL = 'BTCUSDm'

conn = sqlite3.connect(DB)
c = conn.cursor()

# --- 1. D1 数据分析 --- #
c.execute("""
    SELECT time, open, high, low, close, tick_volume 
    FROM kline_raw WHERE symbol=? AND timeframe='D1' 
    ORDER BY time
""", (SYMBOL,))
d1 = c.fetchall()

print(f'BTC D1: {len(d1)} 条, {d1[0][0]} ~ {d1[-1][0]}')
last = d1[-1]
print(f'最新日线: {last[0]} O={last[1]:.0f} H={last[2]:.0f} L={last[3]:.0f} C={last[4]:.0f} Vol={last[5]:,}')

# --- 2. 找出主要波段高低点 --- #
def find_pivots(data, window=5):
    """找波段高低点（简单分形）"""
    high_pivots, low_pivots = [], []
    for i in range(window, len(data) - window):
        # 高点
        if all(data[i][2] >= data[j][2] for j in range(i-window, i+window+1)):
            high_pivots.append((data[i][0], data[i][2]))
        # 低点
        if all(data[i][3] <= data[j][3] for j in range(i-window, i+window+1)):
            low_pivots.append((data[i][0], data[i][3]))
    return high_pivots, low_pivots

highs, lows = find_pivots(d1, window=3)
print(f'\n关键高点: {len(highs)} 个 | 关键低点: {len(lows)} 个')

# 取最近的主要高低点
recent_highs = [h for h in highs if h[0] >= '2025-03-01']
recent_lows = [l for l in lows if l[0] >= '2025-03-01']
print(f'2025年3月后: 高点 {len(recent_highs)} 个, 低点 {len(recent_lows)} 个')

# --- 3. 波浪标记 --- #
print('\n========== 波浪分析 ==========')

# 找出2025年以来的主要波动
def find_extremes(data):
    prices = [(r[0], r[2], 'high') for r in data]  # high是index 2
    prices += [(r[0], r[3], 'low') for r in data]   # low是index 3
    return sorted(prices, key=lambda x: x[0])

# 找出最高点和最低点
all_high = max(d1, key=lambda r: r[2])
all_low = min(d1, key=lambda r: r[3])
print(f'历史最高: {all_high[0]} -> ${all_high[2]:,.0f}')
print(f'历史最低: {all_low[0]} -> ${all_low[3]:,.0f}')

# 取最近一年数据做精细分析
d1_year = [r for r in d1 if r[0] >= '2025-06-01']

# 找最近一年的显著波段
highs1, lows1 = find_pivots(d1_year, window=4)
print(f'\n最近一年波段 ({len(d1_year)} 条日线):')
print(f'  波段高: {len(highs1)} 个')
# 按价格排序取前10高
highs1_sorted = sorted(highs1, key=lambda x: -x[1])
print(f'  前5高点:')
for h in highs1_sorted[:5]:
    print(f'    {h[0]} -> ${h[1]:,.0f}')

lows1_sorted = sorted(lows1, key=lambda x: x[1])
print(f'  前5低点:')
for l in lows1_sorted[:5]:
    print(f'    {l[0]} -> ${l[1]:,.0f}')

# --- 4. 斐波那契分析 --- #
# 2025年以来的主要波动范围
min_price = min(r[3] for r in d1_year)
max_price = max(r[2] for r in d1_year)
diff = max_price - min_price

fib_levels = {'0.236': max_price - diff*0.236,
              '0.382': max_price - diff*0.382,
              '0.500': max_price - diff*0.500,
              '0.618': max_price - diff*0.618,
              '0.786': max_price - diff*0.786}

current_price = d1[-1][4]  # close
print(f'\n========== 斐波那契回撤 (近一年) ==========')
print(f'  范围: ${min_price:,.0f} ~ ${max_price:,.0f} (差价 ${diff:,.0f})')
print(f'  当前位置: ${current_price:,.0f}')
for level, price in sorted(fib_levels.items(), key=lambda x: -x[1]):
    tag = ' ◀ 当前位置' if abs(price - current_price) / diff < 0.05 else ''
    print(f'  Fib {level}: ${price:,.0f}{tag}')

# --- 5. 技术指标 --- #
# MA20
ma20_prices = [r[4] for r in d1[-30:]]  # 最近30天
ma20 = sum(ma20_prices) / len(ma20_prices) if ma20_prices else 0
print(f'\n========== 技术指标 ==========')
print(f'  MA20: ${ma20:,.0f}')

# RSI
def calc_rsi(data, period=14):
    closes = [r[4] for r in data]
    if len(closes) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        chg = closes[i] - closes[i-1]
        if chg >= 0:
            gains += chg
        else:
            losses -= chg
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

rsi = calc_rsi(d1, 14)
print(f'  RSI(14): {rsi:.1f}')

# --- 6. 波浪判断 --- #
print('\n========== 波浪结构判断 ==========')
# 基于D1数据判断当前处在什么浪型

# 找出2026年的完整波段
d1_2026 = [r for r in d1 if r[0] >= '2026-01-01']
highs_2026, lows_2026 = find_pivots(d1_2026, window=3)

print('2026年波段结构:')
# 从最近一个高/低点开始反向找5波
if highs_2026 and lows_2026:
    # 合并排序
    events = []
    for h in highs_2026:
        events.append((h[0], h[1], 'H'))
    for l in lows_2026:
        events.append((l[0], l[1], 'L'))
    events.sort(key=lambda x: x[0])

    print(f'  2026年共 {len(events)} 个关键节点:')
    for e in events[-12:]:  # 最近12个
        emoji = '🔴' if e[2] == 'H' else '🟢'
        print(f'    {emoji} {e[0]} ${e[1]:,.0f}')

    # 尝试5浪标记（从最近一个波段起点倒推）
    sorted_events = sorted(events, key=lambda x: x[0])
    recent = sorted_events[-12:]  # 取最近12个事件

    # 艾略特波浪解读
    print('\n  艾略特波浪解读（D1视角）:')

    # 找出相邻高低点差值
    waves = []
    for i in range(1, len(recent)):
        prev = recent[i-1]
        curr = recent[i]
        direction = '上涨' if curr[1] > prev[1] else '下跌'
        change = abs(curr[1] - prev[1])
        pct = change / prev[1] * 100
        waves.append((prev[0], curr[0], direction, change, pct, prev[1], curr[1]))

    # 识别驱动浪和调整浪
    print(f'    最近 {len(recent)} 个关键节点, 构成 {len(waves)} 段波动:')
    for w in waves[-8:]:
        emoji = '📈' if w[2] == '上涨' else '📉'
        print(f'    {emoji} {w[0]} → {w[1]}  {w[2]} ${w[5]:,.0f}→${w[6]:,.0f} (${w[3]:,.0f}, {w[4]:.1f}%)')

    # 用比尔威廉姆鳄鱼线简化分析
    # 鳄鱼线蓝线(13周期SMA)判断趋势方向
    closes = [r[4] for r in d1]
    sma13 = sum(closes[-13:]) / 13 if len(closes) >= 13 else sum(closes)/len(closes)
    sma8 = sum(closes[-8:]) / 8 if len(closes) >= 8 else sum(closes)/len(closes)
    sma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else sum(closes)/len(closes)

    print(f'\n  鳄鱼线（简化版SMA）:')
    print(f'    蓝线(SMA13): ${sma13:,.0f}')
    print(f'    红线(SMA8):  ${sma8:,.0f}')
    print(f'    绿线(SMA5):  ${sma5:,.0f}')

    if sma5 > sma8 > sma13:
        print(f'    ➡️ 鳄鱼张嘴向上 → 多头趋势')
    elif sma5 < sma8 < sma13:
        print(f'    ➡️ 鳄鱼张嘴向下 → 空头趋势')
    else:
        print(f'    ➡️ 鳄鱼线交叉纠缠 → 震荡/整理')

# --- 7. 总结 --- #
print(f'\n{"="*60}')
print('BTCUSD 波浪分析总结')
print(f'{"="*60}')
print(f'  分析时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
print(f'  当前价格: ${current_price:,.2f} (D1收盘)')
print(f'  1年范围: ${min_price:,.0f} ~ ${max_price:,.0f}')
print(f'  当前位置相对范围: {(current_price - min_price)/(max_price - min_price)*100:.1f}%')

# 判断趋势倾向
trend_score = 0
if current_price > ma20:
    trend_score += 1
if rsi > 50:
    trend_score += 1
if sma5 > sma8 > sma13:
    trend_score += 2
elif sma5 > sma8:
    trend_score += 1
elif sma5 < sma8 < sma13:
    trend_score -= 2

print(f'\n  趋势评分: {trend_score} (正=偏多, 负=偏空)')
if trend_score >= 2:
    print(f'  倾向: 📈 多头 (D1看涨)')
elif trend_score >= 0:
    print(f'  倾向: 📊 震荡偏多')
elif trend_score >= -1:
    print(f'  倾向: 📊 震荡偏空')
else:
    print(f'  倾向: 📉 空头 (D1看跌)')

conn.close()
