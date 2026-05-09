"""
从MT5拉取最新黄金K线数据，更新到taskflow.db
支持 D1/H4/H1/M30/M15/M5 六个周期
"""

import sqlite3, os, sys
from datetime import datetime, timedelta

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'taskflow.db')
SYMBOL = 'XAUUSDm'

TIMEFRAMES = {
    'D1':   'D1',
    'H4':   'H4',
    'H1':   'H1',
    'M30':  'M30',
    'M15':  'M15',
    'M5':   'M5',
}

def mt5_to_tf(name):
    """Convert timeframe string to MT5 constant"""
    import MetaTrader5 as mt5
    return getattr(mt5, f'TIMEFRAME_{name}')

def get_last_time(conn, tf):
    c = conn.cursor()
    c.execute("SELECT MAX(time) FROM kline_raw WHERE timeframe=?", (tf,))
    r = c.fetchone()
    return r[0] if r and r[0] else None

def main():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f'MT5初始化失败: {mt5.last_error()}')
        return False
    print(f'MT5连接成功: {mt5.account_info().login}')

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    total_new = 0

    # 先查H1最后时间（D1存的是"YYYY-MM-DD HH:MM:SS"，取前10字符得日期）
    last_d1 = get_last_time(conn, 'D1')
    if last_d1:
        from_dt = datetime.strptime(last_d1[:10], '%Y-%m-%d') - timedelta(days=5)
    else:
        from_dt = datetime(2022, 11, 1)
    
    now = datetime.now()
    print(f'\n下载时间范围: {from_dt.date()} ~ {now.date()}')
    print()

    # 下载各周期数据
    for tf_name in ['D1', 'H4', 'H1', 'M30', 'M15', 'M5']:
        mt5_tf = mt5_to_tf(tf_name)
        rates = mt5.copy_rates_range(SYMBOL, mt5_tf, from_dt, now)
        if rates is None or len(rates) == 0:
            print(f'  [{tf_name}] 无数据')
            continue
        
        new_count = 0
        for r in rates:
            time_str = datetime.fromtimestamp(r['time']).strftime('%Y-%m-%d %H:%M:%S')
            c.execute('''
                INSERT OR IGNORE INTO kline_raw 
                (timeframe, time, open, high, low, close, tick_volume, spread, real_volume, source_file)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tf_name, time_str,
                float(r['open']), float(r['high']), float(r['low']), float(r['close']),
                int(r['tick_volume']), int(r['spread']), int(r['real_volume']),
                'mt5_live'
            ))
            if c.rowcount > 0:
                new_count += 1
        
        total_new += new_count
        conn.commit()
        
        # 统计该周期总条数
        c.execute('SELECT COUNT(*), MIN(time), MAX(time) FROM kline_raw WHERE timeframe=?', (tf_name,))
        cnt, mint, maxt = c.fetchone()
        print(f'  [{tf_name}] 新增 {new_count:>6} 条 | 总计 {cnt:>6} 条 | {mint} ~ {maxt}')

    # 清理 - 删掉重复的D1时间戳（同一天多条只保留一条）
    c.execute('''
        DELETE FROM kline_raw WHERE id NOT IN (
            SELECT MIN(id) FROM kline_raw WHERE timeframe='D1' GROUP BY time
        ) AND timeframe='D1'
    ''')
    deleted = c.rowcount
    if deleted:
        print(f'\n清理重复D1数据: {deleted} 条')
    
    conn.commit()

    # 打印最新行情
    print(f'\n{"="*60}')
    print(f'最新行情 - D1')
    c.execute("SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe='D1' ORDER BY time DESC LIMIT 3")
    for r in c.fetchall():
        chg = ((r[4] - r[1]) / r[1] * 100) if r[1] else 0
        print(f'  {r[0]}  O:{r[1]:.2f} H:{r[2]:.2f} L:{r[3]:.2f} C:{r[4]:.2f}  Vol:{r[5]:,}  {"+" if chg>=0 else ""}{chg:.2f}%')

    print(f'\n共新增: {total_new} 条K线数据')
    db_size = os.path.getsize(DB) / 1024 / 1024
    print(f'数据库大小: {db_size:.1f} MB')
    
    mt5.shutdown()
    conn.close()
    return True

if __name__ == '__main__':
    main()
