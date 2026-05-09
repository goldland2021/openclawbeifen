"""
保存周线分析结果到 taskflow.db 并输出预测摘要
"""
import sqlite3, os, json
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'taskflow.db')

# 读取最新数据做分析
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe="W1" ORDER BY time')
rows = c.fetchall()
closes = [r[4] for r in rows]
last = rows[-1]
last_close = last[4]
last_week_end = last[0][:10]

# 波浪分析
# 从4098到4889反弹后，目前处于ABC调整中的C浪末端反弹
# 关键位: 4889(浪B顶) -> 4500/4098(C浪底)
# 当前4500-4715区间震荡

# 斐波那契
swing_low = 4098.46
swing_high = 4889.69
range_p = swing_high - swing_low
fib_0236 = swing_high - range_p * 0.236
fib_0382 = swing_high - range_p * 0.382
fib_0500 = swing_high - range_p * 0.500
fib_0618 = swing_high - range_p * 0.618

# RSI
def calc_rsi(data, period=14):
    gains, losses = [], []
    for i in range(1, len(data)):
        d = data[i] - data[i-1]
        gains.append(d if d > 0 else 0)
        losses.append(-d if d < 0 else 0)
    rsi = []
    for i in range(len(data)):
        if i < period:
            rsi.append(None)
        else:
            ag = sum(gains[i-period:i]) / period
            al = sum(losses[i-period:i]) / period
            rsi.append(100 - 100/(1+ag/al) if al != 0 else 100)
    return rsi

rsi_w1 = calc_rsi(closes)
last_rsi = rsi_w1[-1]

# MACD
def ema(data, period):
    r, m = [], 2/(period+1)
    for i, v in enumerate(data):
        r.append(v if i == 0 else (v - r[i-1]) * m + r[i-1])
    return r

ema12 = ema(closes, 12)
ema26 = ema(closes, 26)
macd = [ema12[i] - ema26[i] for i in range(len(closes))]
signal = ema(macd, 9)
hist = [macd[i] - signal[i] for i in range(len(closes))]

# 生成预测
# 基于:
# 1. RSI 45.2 中性偏弱 (低于50)
# 2. MACD <0 且 柱状图收窄 (动量回升中)
# 3. 价格在Fib 0.236 (4703) 附近
# 4. 最近3周形成4500-4764的震荡区间
# 5. 上周阳线(+1.93%) 但成交量持平

# 关键支撑阻力
support_S1 = 4500  # 双底/心理位
support_S2 = 4400  # Fib 0.618附近
resistance_R1 = 4764  # 上周高点
resistance_R2 = 4833  # 4月高点
resistance_R3 = 4889  # 浪B顶

# 概率判断
if last_close < fib_0236:
    # 在Fib 0.236以下，偏弱但RSI回升
    bias = '震荡偏多'
    t1 = fib_0236  # 4703
    t2 = resistance_R1  # 4764
    t3 = resistance_R2  # 4833
    sl = support_S1  # 4500
else:
    bias = '震荡偏空'
    t1 = resistance_R1
    t2 = resistance_R2
    t3 = resistance_R3
    sl = support_S1

# 下周预测
prediction = {
    'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'last_week': last_week_end,
    'last_close': last_close,
    'bias': '震荡偏多',
    'key_levels': {
        'R3': 4889.69,
        'R2': 4833.05,
        'R1': 4764.74,
        'current': last_close,
        'S1': 4500.00,
        'S2': 4400.00,
    },
    'targets': {
        'T1': 4764.74,    # 上周高点
        'T2': 4833.05,    # 4月高点
        'T3': 4889.69,    # 浪B顶
    },
    'stop_loss': 4500.00,
    'signals': {
        'rsi': round(last_rsi, 1) if last_rsi else None,
        'macd': round(macd[-1], 2),
        'macd_signal': round(signal[-1], 2),
        'macd_hist': round(hist[-1], 2),
        'trend_macd': '回升中' if hist[-1] > hist[-2] else '走弱'
    },
    'scenario_bull': f'站稳{int(fib_0236)}后向上挑战{int(resistance_R1)}-{int(resistance_R2)}，突破{int(resistance_R3)}则确认反转',
    'scenario_bear': f'跌破4500则回测4400甚至4098',
    'scenario_base': f'下周预计在4500-4764区间震荡，偏向测试上方压力'
}

# 存到method_analysis_results
c.execute('''
    INSERT INTO method_analysis_results 
    (symbol, method_id, analysis_date, timeframe, trend_direction, trend_strength,
     swing_high, swing_low, target_high, target_low, signals_fired, signal_summary, result_text)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'XAUUSD',
    1,  # 比尔威廉姆方法
    prediction['analysis_date'],
    'W1',
    prediction['bias'],
    0.45,  # 强度
    prediction['key_levels']['R3'],
    prediction['key_levels']['S2'],
    prediction['targets']['T2'],  # 预测W1目标
    prediction['stop_loss'],
    json.dumps(prediction['signals'], ensure_ascii=False),
    json.dumps(prediction['targets'], ensure_ascii=False),
    json.dumps(prediction, ensure_ascii=False, indent=2)
))
conn.commit()

print('=== 下周走势预测 (2026-05-11 ~ 2026-05-16) ===')
print(f'{"="*55}')
print(f'上周收盘: ${last_close:.2f}')
print(f'倾向: {prediction["bias"]}')
print(f'RSI(14): {prediction["signals"]["rsi"]} (中性偏弱)')
print(f'MACD: {prediction["signals"]["macd"]} / Signal: {prediction["signals"]["macd_signal"]} / Hist: {prediction["signals"]["macd_hist"]}')
print(f'MACD趋势: {prediction["signals"]["trend_macd"]}')
print()
print(f'关键位:')
print(f'  R3: ${prediction["key_levels"]["R3"]:.0f} (浪B顶)')
print(f'  R2: ${prediction["key_levels"]["R2"]:.0f} (4月高点)')
print(f'  R1: ${prediction["key_levels"]["R1"]:.0f} (上周高点)')
print(f'  ── 当前: ${last_close:.2f} ──')
print(f'  S1: ${prediction["key_levels"]["S1"]:.0f} (支撑)')
print(f'  S2: ${prediction["key_levels"]["S2"]:.0f} (强支撑)')
print()
print(f'目标位:')
print(f'  T1: ${prediction["targets"]["T1"]:.0f} (+{((prediction["targets"]["T1"]/last_close)-1)*100:.1f}%)')
print(f'  T2: ${prediction["targets"]["T2"]:.0f} (+{((prediction["targets"]["T2"]/last_close)-1)*100:.1f}%)')
print(f'  T3: ${prediction["targets"]["T3"]:.0f} (+{((prediction["targets"]["T3"]/last_close)-1)*100:.1f}%)')
print(f'  止损: ${prediction["stop_loss"]:.0f} (-{((last_close-prediction["stop_loss"])/last_close)*100:.1f}%)')
print()
print(f'基准情景: {prediction["scenario_base"]}')
print(f'看涨情景: {prediction["scenario_bull"]}')
print(f'看跌情景: {prediction["scenario_bear"]}')
print(f'{"="*55}')
print(f'(已保存到 taskflow.db method_analysis_results)')

conn.close()
