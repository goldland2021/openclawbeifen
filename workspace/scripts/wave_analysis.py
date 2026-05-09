"""
波浪分析与交易信号
功能：更新MT5数据 -> 分析波浪结构 -> 输出交易信号
用法：python wave_analysis.py
"""

import sqlite3, os, sys
from datetime import datetime, timedelta

# -- 路径 --
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(BASE_DIR, 'data', 'taskflow.db')
SYMBOL = 'XAUUSDm'

# -- 1. 更新MT5数据 --
def update_mt5_data():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f'[ERR] MT5初始化失败: {mt5.last_error()}')
        return False
    print(f'[OK] MT5连接成功: {mt5.account_info().login}')

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    total_new = 0

    c.execute("SELECT MAX(time) FROM kline_raw WHERE timeframe='D1'")
    r = c.fetchone()
    last_d1 = r[0] if r and r[0] else None
    if last_d1:
        from_dt = datetime.strptime(last_d1[:10], '%Y-%m-%d') - timedelta(days=3)
    else:
        from_dt = datetime(2022, 11, 1)

    now = datetime.now()
    print(f'[DL] 下载: {from_dt.date()} ~ {now.date()}')

    for tf_name in ['D1', 'H4', 'H1', 'M30', 'M15', 'M5']:
        mt5_tf = getattr(mt5, f'TIMEFRAME_{tf_name}')
        rates = mt5.copy_rates_range(SYMBOL, mt5_tf, from_dt, now)
        if rates is None or len(rates) == 0:
            print(f'  [{tf_name}] 无数据')
            continue

        new_count = 0
        for r in rates:
            ts = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("""INSERT OR IGNORE INTO kline_raw
                (timeframe, time, open, high, low, close, tick_volume, spread, real_volume, source_file)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (tf_name, ts, float(r['open']), float(r['high']), float(r['low']), float(r['close']),
                 int(r['tick_volume']), int(r['spread']), int(r['real_volume']), 'mt5_live'))
            if c.rowcount > 0:
                new_count += 1

        total_new += new_count
        conn.commit()
        c.execute("SELECT COUNT(*) FROM kline_raw WHERE timeframe=?", (tf_name,))
        cnt = c.fetchone()[0]
        print(f'  [{tf_name}] +{new_count:>5} -> 总计 {cnt:>6}')

    # 清理重复D1
    c.execute("""DELETE FROM kline_raw WHERE id NOT IN (
        SELECT MIN(id) FROM kline_raw WHERE timeframe='D1' GROUP BY time
    ) AND timeframe='D1'""")
    deleted = c.rowcount
    if deleted:
        print(f'  清理D1重复: {deleted} 条')

    conn.commit()
    print(f'[OK] 更新完成, 新增 {total_new} 条K线')
    mt5.shutdown()
    conn.close()
    return True


# -- 2. 波浪分析 --
def get_data(c, tf, limit=80):
    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw "
              "WHERE timeframe=? ORDER BY time DESC LIMIT ?", (tf, limit))
    rows = list(reversed(c.fetchall()))
    return rows

def find_swing_points(data, lookback=5):
    """识别波浪高低点"""
    swing_highs = []
    swing_lows  = []

    for i in range(lookback, len(data) - lookback):
        hi_val, lo_val = data[i][2], data[i][3]
        # 局部高点
        if all(data[i][2] >= data[i-k][2] for k in range(1, lookback+1)) and \
           all(data[i][2] >= data[i+k][2] for k in range(1, lookback+1)):
            swing_highs.append((i, hi_val, data[i][0]))
        # 局部低点
        if all(data[i][3] <= data[i-k][3] for k in range(1, lookback+1)) and \
           all(data[i][3] <= data[i+k][3] for k in range(1, lookback+1)):
            swing_lows.append((i, lo_val, data[i][0]))
    return swing_highs, swing_lows


def analyze(force_update=True):
    if force_update:
        print("=" * 55)
        print("  [1/3] 更新MT5数据")
        print("=" * 55)
        if not update_mt5_data():
            return

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    print("\n" + "=" * 55)
    print("  [2/3] 波浪分析")
    print("=" * 55)

    # 获取数据
    d1 = get_data(c, 'D1', 30)
    h4 = get_data(c, 'H4', 40)
    h1 = get_data(c, 'H1', 80)

    # --- D1 ---
    print("\n| D1 大框架")
    if d1:
        cur = d1[-1]
        chg = (cur[4] - cur[1]) / cur[1] * 100
        print(f"  当前: {cur[0]}  O:{cur[1]:.2f} H:{cur[2]:.2f} L:{cur[3]:.2f} C:{cur[4]:.2f}  ({chg:+.2f}%)")

    # --- H4 ---
    print("\n| H4 最近10根")
    for r in h4[-10:]:
        print(f"  {r[0]}  O:{r[1]:.2f} H:{r[2]:.2f} L:{r[3]:.2f} C:{r[4]:.2f}")

    # --- H1波浪 ---
    print("\n| H1 波浪分析")
    latest = h1[-1] if h1 else None
    latest_price = latest[4] if latest else 0
    print(f"  最新价格: ${latest_price:.2f}  ({latest[0] if latest else '?'})")

    sh, sl = find_swing_points(h1, lookback=4)
    print("\n  + H1 高点 (最近5个):")
    for pt in sh[-5:]:
        print(f"    {pt[2]}  ${pt[1]:.2f}")
    print("  - H1 低点 (最近5个):")
    for pt in sl[-5:]:
        print(f"    {pt[2]}  ${pt[1]:.2f}")

    # 波浪标注
    print("\n  [波浪标注] 从4500 C浪底起:")
    print("    1浪: 4500 -> 4586  (5/5)")
    print("    2浪: 4586 -> 4500  (5/5 双底)")
    print("    3浪: 4500 -> 4722  (5/6 主升)")
    print("    4浪: 4722 -> 4678  (5/7 01:00)")
    print("    5浪: 4678 -> 4764  (5/7 22:00 浪顶)")
    print("    ------------------------------")
    print("    A浪: 4764 -> 4704  (5/7 23:00~5/8 00:00)")
    print("    B浪: 4704 -> 4719  (5/8 01:00 弱反弹)")
    print("    C浪: 4719 -> 4681  (5/8 04:00~06:00)")

    # 斐波那契
    w5_h = 4764.74
    w4_l = 4678.72
    w3_h = 4722.96
    w_range = w5_h - w4_l
    fib_382 = w5_h - w_range * 0.382
    fib_500 = w5_h - w_range * 0.5
    fib_618 = w5_h - w_range * 0.618

    print(f"\n  [斐波那契] 5浪回调位:")
    print(f"    0.382= ${fib_382:.2f}  0.5= ${fib_500:.2f}  0.618= ${fib_618:.2f}")
    print(f"    4浪底= ${w4_l:.2f}  3浪顶= ${w3_h:.2f}")

    # 鳄鱼线 (H1 SMA)
    closes = [r[4] for r in h1]
    jaw  = sum(closes[-21:]) / 21 if len(closes) >= 21 else 0
    teeth = sum(closes[-13:]) / 13 if len(closes) >= 13 else 0
    lips = sum(closes[-8:]) / 8  if len(closes) >= 8 else 0

    print(f"\n  [鳄鱼线] H1 SMA:")
    print(f"    下巴(21)= {jaw:.2f}  牙齿(13)= {teeth:.2f}  嘴唇(8)= {lips:.2f}")
    if lips > teeth > jaw:
        status = "[多头] 多头排列 - 趋势向上"
    elif lips < teeth < jaw:
        status = "[空头] 空头排列 - 趋势向下"
    else:
        status = "[盘整] 缠绕 - 无明确方向"
    print(f"    状态: {status}")

    # 分形信号 (简单H1高低点突破)
    last_5_high = max(r[2] for r in h1[-5:])
    last_5_low  = min(r[3] for r in h1[-5:])
    print(f"\n  [分形] H1最近5根:")
    print(f"    上分形: ${last_5_high:.2f}  下分形: ${last_5_low:.2f}")

    # --- 3. 交易信号 ---
    print("\n" + "=" * 55)
    print("  [3/3] 交易信号")
    print("=" * 55)

    print(f"\n  当前位置: ${latest_price:.2f}")

    if latest_price < 4680:
        signal = "看空"
        action = "反弹做空或观望"
        entry_detail = "反弹至4700附近做空"
        tp1, tp2 = 4640, 4600
        sl_val = 4720
        reason = "跌破4浪底(4678)，5浪(4764)见顶后回调加深"
    elif latest_price > 4764:
        signal = "看多"
        action = "回调做多"
        entry_detail = "回踩4740附近做多"
        tp1, tp2 = 4800, 4850
        sl_val = 4720
        reason = "突破前高(4764)，推动浪延长"
    else:
        signal = "震荡观望"
        action = "等待方向确认"
        entry_detail = "回踩4680企稳做多 / 跌破4678反抽做空"
        tp1, tp2 = 4764, 4800
        sl_val = 4650
        reason = "5浪(4764)完成后的ABC回调中"

        if latest_price <= 4710:
            signal = "偏多观望"
            action = "逢低试多"
            entry_detail = "4680-4700区域企稳后做多"
            tp1, tp2 = 4740, 4764
            sl_val = 4660
            reason = "接近4浪底(4678)支撑，ABC回调C浪末端"

    print(f"\n  信号: {signal}")
    print(f"  策略: {action}")
    print(f"  入场: {entry_detail}")
    print(f"  目标1: ${tp1:.2f}  目标2: ${tp2:.2f}")
    print(f"  止损: ${sl_val:.2f}")
    print(f"  理由: {reason}")

    print(f"\n  [风险提示]")
    print(f"  * 此分析基于波浪理论，仅供参考")
    print(f"  * 关键位: 支撑 4678/4650  阻力 4764")
    print(f"  * 跌破4678 -> 看空至4600-4640")
    print(f"  * 突破4764 -> 看多至4800-4850")
    print(f"  * 仓位: 轻仓+止损")
    print(f"  * 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # 保存CSV
    try:
        ts = datetime.now().strftime('%Y%m%d_%H%M')
        csv_path = os.path.join(BASE_DIR, 'data', f'h1_latest_{ts}.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('time,open,high,low,close,volume\n')
            for r in h1[-40:]:
                f.write(f'{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]}\n')
        print(f"  H1数据已保存: {csv_path}")
    except Exception as e:
        print(f"  保存CSV失败: {e}")

    conn.close()
    print("\n" + "=" * 55)
    print("  分析完成 [OK]")
    print("=" * 55)


if __name__ == '__main__':
    analyze(force_update=True)
