"""
导入黄金K线数据到 taskflow.db
从 raw/ processed/ indicators/ 目录导入各周期CSV数据
"""

import sqlite3, os, csv, glob

DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'taskflow.db')
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'gold_trading')

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # K线数据表 - 存储所有周期的原始OHLC数据
    c.execute('''
        CREATE TABLE IF NOT EXISTS kline_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            tick_volume INTEGER DEFAULT 0,
            spread INTEGER DEFAULT 0,
            real_volume INTEGER DEFAULT 0,
            source_file TEXT,
            imported_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(timeframe, time)
        )
    ''')

    # K线技术指标数据表
    c.execute('''
        CREATE TABLE IF NOT EXISTS kline_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            -- 鳄鱼线指标
            alligator_jaw REAL,
            alligator_teeth REAL,
            alligator_lips REAL,
            -- 分形指标
            fractal_up REAL,
            fractal_down REAL,
            -- AO指标
            ao REAL,
            -- AC指标
            ac REAL,
            -- 其他
            gator_upper REAL,
            gator_lower REAL,
            source_file TEXT,
            imported_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(timeframe, time)
        )
    ''')
    
    # 处理/回测数据表
    c.execute('''
        CREATE TABLE IF NOT EXISTS kline_processed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timeframe TEXT NOT NULL,
            time TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            -- 其他计算字段（动态扩展）
            data TEXT,
            source_file TEXT,
            imported_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(timeframe, time)
        )
    ''')

    conn.commit()
    return conn

def import_raw_csv(conn, filepath):
    filename = os.path.basename(filepath)
    parts = filename.replace('.csv', '').split('_')
    if len(parts) >= 3:
        timeframe = parts[1]  # D1, H1, H4, M15, etc
    else:
        timeframe = 'UNKNOWN'
    
    c = conn.cursor()
    count = 0
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                c.execute('''
                    INSERT OR IGNORE INTO kline_raw 
                    (timeframe, time, open, high, low, close, tick_volume, spread, real_volume, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timeframe,
                    row.get('time', ''),
                    float(row.get('open', 0)),
                    float(row.get('high', 0)),
                    float(row.get('low', 0)),
                    float(row.get('close', 0)),
                    int(row.get('tick_volume', 0)),
                    int(row.get('spread', 0)),
                    int(row.get('real_volume', 0)),
                    filename
                ))
                if c.rowcount > 0:
                    count += 1
            except (ValueError, KeyError) as e:
                pass  # skip bad rows
    conn.commit()
    return count, timeframe

def import_indicators_csv(conn, filepath):
    filename = os.path.basename(filepath)
    parts = filename.replace('.csv', '').split('_')
    timeframe = parts[1] if len(parts) >= 3 else 'UNKNOWN'
    
    c = conn.cursor()
    count = 0
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                time_val = row.get('time', '')
                c.execute('''
                    INSERT OR IGNORE INTO kline_indicators 
                    (timeframe, time, open, high, low, close, tick_volume, spread,
                     alligator_jaw, alligator_teeth, alligator_lips,
                     fractal_up, fractal_down, ao, ac, gator_upper, gator_lower,
                     source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timeframe, time_val,
                    float(row.get('open', 0)),
                    float(row.get('high', 0)),
                    float(row.get('low', 0)),
                    float(row.get('close', 0)),
                    int(row.get('tick_volume', 0)),
                    int(row.get('spread', 0)),
                    safe_float(row.get('Alligator_Jaw')),
                    safe_float(row.get('Alligator_Teeth')),
                    safe_float(row.get('Alligator_Lips')),
                    safe_float(row.get('Fractal_Up')),
                    safe_float(row.get('Fractal_Down')),
                    safe_float(row.get('AO')),
                    safe_float(row.get('AC')),
                    safe_float(row.get('Gator_Upper')),
                    safe_float(row.get('Gator_Lower')),
                    filename
                ))
                if c.rowcount > 0:
                    count += 1
            except Exception as e:
                pass
    conn.commit()
    return count, timeframe

def import_processed_csv(conn, filepath):
    filename = os.path.basename(filepath)
    parts = filename.replace('.csv', '').split('_')
    timeframe = parts[1] if len(parts) >= 3 else 'UNKNOWN'
    
    c = conn.cursor()
    count = 0
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                time_val = row.get('time', '')
                # Store all extra columns as JSON
                import json
                extra = {k: v for k, v in row.items() if k not in ['time','open','high','low','close','tick_volume','spread','real_volume']}
                c.execute('''
                    INSERT OR IGNORE INTO kline_processed 
                    (timeframe, time, open, high, low, close, tick_volume, spread, data, source_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    timeframe, time_val,
                    safe_float(row.get('open')),
                    safe_float(row.get('high')),
                    safe_float(row.get('low')),
                    safe_float(row.get('close')),
                    safe_int(row.get('tick_volume')),
                    safe_int(row.get('spread')),
                    json.dumps(extra, ensure_ascii=False),
                    filename
                ))
                if c.rowcount > 0:
                    count += 1
            except Exception as e:
                pass
    conn.commit()
    return count, timeframe

def safe_float(v):
    try:
        return float(v) if v and v.strip() else None
    except:
        return None

def safe_int(v):
    try:
        return int(v) if v and v.strip() else 0
    except:
        return 0

def main():
    conn = init_db()
    total_raw = total_ind = total_proc = 0

    print('导入原始K线数据...')
    for f in sorted(glob.glob(os.path.join(DATA_DIR, 'raw', '*.csv'))):
        n, tf = import_raw_csv(conn, f)
        total_raw += n
        print(f'  [{tf}] {os.path.basename(f)} -> {n} 条')

    print('\n导入技术指标数据...')
    for f in sorted(glob.glob(os.path.join(DATA_DIR, 'indicators', '*.csv'))):
        n, tf = import_indicators_csv(conn, f)
        total_ind += n
        print(f'  [{tf}] {os.path.basename(f)} -> {n} 条')

    print('\n导入回测/处理数据...')
    for f in sorted(glob.glob(os.path.join(DATA_DIR, 'processed', '*.csv'))):
        n, tf = import_processed_csv(conn, f)
        total_proc += n
        print(f'  [{tf}] {os.path.basename(f)} -> {n} 条')

    # 统计
    c = conn.cursor()
    c.execute('SELECT timeframe, COUNT(*) FROM kline_raw GROUP BY timeframe ORDER BY timeframe')
    raw_stats = c.fetchall()
    c.execute('SELECT timeframe, COUNT(*) FROM kline_indicators GROUP BY timeframe ORDER BY timeframe')
    ind_stats = c.fetchall()
    c.execute('SELECT timeframe, COUNT(*) FROM kline_processed GROUP BY timeframe ORDER BY timeframe')
    proc_stats = c.fetchall()

    print(f'\n{"="*50}')
    print(f'导入完成!')
    print(f'  kline_raw:       {total_raw} 条')
    for tf, cnt in raw_stats:
        print(f'    - {tf}: {cnt} 条')
    print(f'  kline_indicators: {total_ind} 条')
    for tf, cnt in ind_stats:
        print(f'    - {tf}: {cnt} 条')
    print(f'  kline_processed:  {total_proc} 条')
    for tf, cnt in proc_stats:
        print(f'    - {tf}: {cnt} 条')
    print(f'  数据库大小: {os.path.getsize(DB) / 1024:.1f} KB')

    conn.close()

if __name__ == '__main__':
    main()
