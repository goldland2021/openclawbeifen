import sqlite3
import pandas as pd
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\Administrator\.openclaw\workspace\data\taskflow.db')

# D1
d1 = pd.read_sql("SELECT * FROM kline_raw WHERE timeframe='D1' ORDER BY time", conn)
d1['time'] = pd.to_datetime(d1['time'], format='ISO8601')
print('=== D1 近期 ===')
print(d1.tail(15)[['time','open','high','low','close']].to_string(index=False))
print()

# H1
h1 = pd.read_sql("SELECT * FROM kline_raw WHERE timeframe='H1' ORDER BY time", conn)
h1['time'] = pd.to_datetime(h1['time'], format='ISO8601')
today = datetime.now().strftime('%Y-%m-%d')
td = h1[h1['time'].dt.strftime('%Y-%m-%d') == today].copy()
print(f'=== H1 今日 ({today}) ===')
print(td[['time','open','high','low','close']].to_string(index=False))
print()

# 统计
recent = h1.tail(72)
print(f'H1近3天: 最高={recent["high"].max():.2f}  最低={recent["low"].min():.2f}  最新={recent["close"].iloc[-1]:.2f}')
ma20 = recent['close'].rolling(20).mean()
ma60 = recent['close'].rolling(60).mean()
print(f'MA20={ma20.iloc[-1]:.2f}  MA60={ma60.iloc[-1]:.2f}  差值={ma20.iloc[-1]-ma60.iloc[-1]:.2f}')

# 鳄鱼线
blue = recent['close'].rolling(13).mean().shift(8)
red = recent['close'].rolling(8).mean().shift(5)
green = recent['close'].rolling(5).mean().shift(3)
print(f'鳄鱼: 蓝(颚)={blue.iloc[-1]:.2f}  红(齿)={red.iloc[-1]:.2f}  绿(唇)={green.iloc[-1]:.2f}')

# 分形
def find_fractals(df, lookback=200):
    df = df.tail(lookback).reset_index(drop=True)
    up, down = [], []
    for i in range(2, len(df)-2):
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
            df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and 
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            up.append((df['time'].iloc[i], df['high'].iloc[i]))
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and 
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            down.append((df['time'].iloc[i], df['low'].iloc[i]))
    return up, down

up_f, down_f = find_fractals(h1, 200)
print('\n最近向上分形:')
for t, p in up_f[-5:]:
    print(f'  {t}  {p:.2f}')
print('最近向下分形:')
for t, p in down_f[-5:]:
    print(f'  {t}  {p:.2f}')

conn.close()
