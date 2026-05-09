"""
从MT5拉取比特币BTCUSD的D1/H4数据（用于波浪分析）
"""
import sqlite3, os
from datetime import datetime, timedelta

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'taskflow.db')
SYMBOL = 'BTCUSDm'

def get_last_time(conn, tf):
    c = conn.cursor()
    c.execute("SELECT MAX(time) FROM kline_raw WHERE timeframe=? AND symbol=?", (tf, SYMBOL))
    r = c.fetchone()
    return r[0] if r and r[0] else None

def main():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f'MT5初始化失败: {mt5.last_error()}')
        return
    print(f'MT5连接成功: {mt5.account_info().login}')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    for tf_name, mt5_tf in [('D1', mt5.TIMEFRAME_D1), ('H4', mt5.TIMEFRAME_H4)]:
        last = get_last_time(conn, tf_name)
        if last:
            from_dt = datetime.strptime(last[:10], '%Y-%m-%d') - timedelta(days=30)
        else:
            from_dt = datetime(2025, 1, 1)

        rates = mt5.copy_rates_range(SYMBOL, mt5_tf, from_dt, datetime.now())
        if rates is None or len(rates) == 0:
            print(f'[{tf_name}] 无数据')
            continue

        new = 0
        for r in rates:
            ts = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
            c.execute('''INSERT OR IGNORE INTO kline_raw
                (symbol, timeframe, time, open, high, low, close, tick_volume, spread, real_volume, source_file)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (SYMBOL, tf_name, ts, float(r['open']), float(r['high']), float(r['low']),
                 float(r['close']), int(r['tick_volume']), int(r['spread']), int(r['real_volume']), 'mt5_live'))
            if c.rowcount > 0:
                new += 1
        conn.commit()
        c.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM kline_raw WHERE symbol=? AND timeframe=?", (SYMBOL, tf_name))
        cnt, mint, maxt = c.fetchone()
        print(f'[{tf_name}] 新增 {new} 条 | 总计 {cnt} 条 | {mint} ~ {maxt}')

    mt5.shutdown()
    conn.close()

if __name__ == '__main__':
    main()
