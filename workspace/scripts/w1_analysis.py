"""
从MT5拉取黄金周线(W1)数据并计算技术指标，用于下周走势预测
"""
import sqlite3, os, json
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'taskflow.db')
SYMBOL = 'XAUUSDm'

def main():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f'MT5初始化失败: {mt5.last_error()}')
        return
    
    from_dt = datetime(2022, 11, 1)
    now = datetime.now()

    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_W1, from_dt, now)
    if rates is None or len(rates) == 0:
        print('无W1数据')
        mt5.shutdown()
        return

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    new_count = 0
    for r in rates:
        time_str = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''
            INSERT OR IGNORE INTO kline_raw 
            (timeframe, time, open, high, low, close, tick_volume, spread, real_volume, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'W1', time_str,
            float(r['open']), float(r['high']), float(r['low']), float(r['close']),
            int(r['tick_volume']), int(r['spread']), int(r['real_volume']),
            'mt5_live'
        ))
        if c.rowcount > 0:
            new_count += 1
    conn.commit()

    # 读出所有W1数据做分析
    c.execute('SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe="W1" ORDER BY time')
    rows = c.fetchall()
    
    print(f'W1共{len(rows)}条周线, 新增{new_count}条')
    print()

    # 计算技术指标
    closes = [r[4] for r in rows]
    highs = [r[3] for r in rows]
    lows = [r[2] for r in rows]
    times = [r[0][:10] for r in rows]
    volumes = [r[5] for r in rows]

    # MA5, MA10, MA20
    def sma(data, period):
        result = []
        for i in range(len(data)):
            if i < period-1:
                result.append(None)
            else:
                result.append(sum(data[i-period+1:i+1])/period)
        return result

    ma5 = sma(closes, 5)
    ma10 = sma(closes, 10)
    ma20 = sma(closes, 20)

    # 最新10条完整数据
    print(f'{"="*90}')
    print(f'{"日期":<12} {"开盘":<8} {"最高":<8} {"最低":<8} {"收盘":<8} {"MA5":<8} {"MA10":<8} {"MA20":<8} {"成交量":<10}')
    print(f'{"="*90}')
    
    for i in range(max(0, len(rows)-15), len(rows)):
        r = rows[i]
        m5 = f'{ma5[i]:.2f}' if ma5[i] else '-'
        m10 = f'{ma10[i]:.2f}' if ma10[i] else '-'
        m20 = f'{ma20[i]:.2f}' if ma20[i] else '-'
        vol = f'{r[5]:>10,}' if r[5] else '0'
        print(f'{r[0][:10]:<12} {r[1]:<8.2f} {r[2]:<8.2f} {r[3]:<8.2f} {r[4]:<8.2f} {m5:<8} {m10:<8} {m20:<8} {vol}')

    print()

    # 艾略特波浪分析
    print('=== 波浪分析 ===')
    # 从2022年11月到现在，看主要结构
    # 高点5393 (2025年3月附近), 低点4098 (2026年3月)
    # 找最后几周的高低点
    
    last10 = rows[-10:]
    print(f'最近10周范围: 最高={max(r[2] for r in last10):.2f} 最低={min(r[3] for r in last10):.2f}')
    
    # 最近3周走势
    w3 = rows[-3:]
    print(f'最近3周: ', end='')
    for r in w3:
        chg = ((r[4]-r[1])/r[1]*100)
        print(f'{r[0][:10]} O{r[1]:.0f} H{r[2]:.0f} L{r[3]:.0f} C{r[4]:.0f} ({chg:+.2f}%)', end=' | ')

    print()
    
    # 斐波那契回撤位（从4098到4889）
    swing_low = 4098.46
    swing_high = 4889.69
    range_price = swing_high - swing_low
    
    fib_levels = {
        '0.236': swing_high - range_price * 0.236,
        '0.382': swing_high - range_price * 0.382,
        '0.500': swing_high - range_price * 0.500,
        '0.618': swing_high - range_price * 0.618,
        '0.786': swing_high - range_price * 0.786,
    }
    
    last_close = rows[-1][4]
    print(f'\n=== 斐波那契分析 (4098→4889) ===')
    print(f'当前价格: {last_close:.2f}')
    for k, v in fib_levels.items():
        dist = ((v - last_close) / last_close) * 100
        marker = '← 当前位置' if abs(dist) < 2 else ''
        print(f'  Fib {k}: {v:.2f} (距当前 {dist:+.2f}%) {marker}')

    # RSI计算
    def calc_rsi(closes, period=14):
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(-diff if diff < 0 else 0)
        
        rsi = []
        for i in range(len(closes)):
            if i < period:
                rsi.append(None)
            else:
                avg_gain = sum(gains[i-period:i]) / period
                avg_loss = sum(losses[i-period:i]) / period
                if avg_loss == 0:
                    rsi.append(100)
                else:
                    rs = avg_gain / avg_loss
                    rsi.append(100 - 100/(1+rs))
        return rsi

    rsi_w1 = calc_rsi(closes)
    last_rsi = rsi_w1[-1] if rsi_w1[-1] else 0
    print(f'\n=== RSI(14) ===')
    print(f'最新RSI: {last_rsi:.1f}')
    
    # RSI趋势
    if len(rows) > 20:
        print(f'RSI前值: {rsi_w1[-2]:.1f}' if rsi_w1[-2] else '')

    # MACD计算
    def ema(data, period):
        result = []
        multiplier = 2 / (period + 1)
        for i in range(len(data)):
            if i == 0:
                result.append(data[i])
            else:
                result.append((data[i] - result[i-1]) * multiplier + result[i-1])
        return result

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal_line = ema(macd_line, 9)
    histogram = [macd_line[i] - signal_line[i] for i in range(len(closes))]

    print(f'\n=== MACD ===')
    print(f'MACD: {macd_line[-1]:.2f}  Signal: {signal_line[-1]:.2f}  Hist: {histogram[-1]:.2f}')
    if len(rows) > 5:
        print(f'MACD趋势: {"上升" if histogram[-1] > histogram[-2] else "下降"}')
    
    mt5.shutdown()
    conn.close()

if __name__ == '__main__':
    main()
