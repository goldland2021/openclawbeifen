"""
从MT5拉取黄金周线(W1)数据，保存到taskflow.db
"""
import sqlite3, os
from datetime import datetime, timedelta

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'taskflow.db')
SYMBOL = 'XAUUSDm'

def main():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f'MT5初始化失败: {mt5.last_error()}')
        return False
    print(f'MT5连接成功: {mt5.account_info().login}')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 从2022年开始拉周线
    from_dt = datetime(2022, 11, 1)
    now = datetime.now()
    print(f'下载W1周线: {from_dt.date()} ~ {now.date()}')

    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_W1, from_dt, now)
    if rates is None or len(rates) == 0:
        print('无W1数据')
        mt5.shutdown()
        conn.close()
        return

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

    c.execute('SELECT COUNT(*), MIN(time), MAX(time) FROM kline_raw WHERE timeframe="W1"')
    cnt, mint, maxt = c.fetchone()
    print(f'W1: 新增 {new_count} 条 | 总计 {cnt} 条 | {mint} ~ {maxt}')

    print(f'\n{"="*40}')
    print('W1最新行情:')
    c.execute('SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe="W1" ORDER BY time DESC LIMIT 10')
    for r in c.fetchall():
        chg = ((r[4] - r[1]) / r[1] * 100) if r[1] else 0
        print(f'  {r[0][:10]}  O:{r[1]:.2f} H:{r[2]:.2f} L:{r[3]:.2f} C:{r[4]:.2f} Vol:{r[5]:,} {"+" if chg>=0 else ""}{chg:.2f}%')

    db_size = os.path.getsize(DB) / 1024 / 1024
    print(f'\n数据库大小: {db_size:.1f} MB')
    
    mt5.shutdown()
    conn.close()
    return True

if __name__ == '__main__':
    main()
