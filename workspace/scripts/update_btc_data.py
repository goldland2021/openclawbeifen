"""
从MT5拉取比特币BTCUSD最新5分钟K线数据，更新到taskflow.db
建议每小时执行一次
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
        return False
    print(f'MT5连接成功: {mt5.account_info().login}')
    print(f'正在下载 {SYMBOL} M5...')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 确保symbol列存在（kline_raw表可能没有，需要增加）
    # 先检查
    c.execute("PRAGMA table_info(kline_raw)")
    cols = [r[1] for r in c.fetchall()]
    if 'symbol' not in cols:
        c.execute("ALTER TABLE kline_raw ADD COLUMN symbol TEXT DEFAULT 'XAUUSD'")
        conn.commit()
        print('添加symbol列到kline_raw表')

    # 查最后更新时间
    last_time = get_last_time(conn, 'M5')
    if last_time:
        from_dt = datetime.strptime(last_time[:10], '%Y-%m-%d')
    else:
        from_dt = datetime(2026, 5, 1)

    now = datetime.now()
    print(f'下载范围: {from_dt.date()} ~ {now.date()}')

    # 拉M5
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M5, from_dt, now)
    if rates is None or len(rates) == 0:
        print('无M5数据')
        mt5.shutdown()
        conn.close()
        return

    new_count = 0
    for r in rates:
        time_str = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''
            INSERT OR IGNORE INTO kline_raw 
            (symbol, timeframe, time, open, high, low, close, tick_volume, spread, real_volume, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            SYMBOL, 'M5', time_str,
            float(r['open']), float(r['high']), float(r['low']), float(r['close']),
            int(r['tick_volume']), int(r['spread']), int(r['real_volume']),
            'mt5_live'
        ))
        if c.rowcount > 0:
            new_count += 1

    conn.commit()

    # 统计
    c.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM kline_raw WHERE timeframe='M5' AND symbol=?", (SYMBOL,))
    cnt, mint, maxt = c.fetchone()
    print(f'M5: 新增 {new_count} 条 | 总计 {cnt} 条 | {mint} ~ {maxt}')

    # 最新行情
    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe='M5' AND symbol=? ORDER BY time DESC LIMIT 3", (SYMBOL,))
    print(f'\nBTCUSD 最新3条M5:')
    for r2 in c.fetchall():
        chg = ((r2[4] - r2[1]) / r2[1] * 100) if r2[1] else 0
        print(f'  {r2[0]}  O:{r2[1]:.2f} H:{r2[2]:.2f} L:{r2[3]:.2f} C:{r2[4]:.2f}  Vol:{r2[5]:,}')

    db_size = os.path.getsize(DB) / 1024 / 1024
    print(f'数据库大小: {db_size:.1f} MB')

    mt5.shutdown()
    conn.close()
    return True

if __name__ == '__main__':
    main()
