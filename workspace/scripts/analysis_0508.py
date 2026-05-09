import pandas as pd
import numpy as np

# 加载数据
h1 = pd.read_csv('data/XAUUSD_H1.csv')
h4 = pd.read_csv('data/XAUUSD_H4.csv')
d1 = pd.read_csv('data/XAUUSD_D1.csv')

h1['time'] = pd.to_datetime(h1['time'])
h4['time'] = pd.to_datetime(h4['time'])
d1['time'] = pd.to_datetime(d1['time'])

print('=== D1 近期数据 ===')
print(d1.tail(15)[['time','open','high','low','close']].to_string(index=False))

print('\n=== H1 今日数据 ===')
today = pd.Timestamp.now().strftime('%Y-%m-%d')
today_h1 = h1[h1['time'].dt.strftime('%Y-%m-%d') == today]
print(today_h1[['time','open','high','low','close']].to_string(index=False))

print('\n=== H1 近3天统计 ===')
recent = h1.tail(72)
print(f'最高: {recent["high"].max():.2f}')
print(f'最低: {recent["low"].min():.2f}')
print(f'当前: {recent["close"].iloc[-1]:.2f}')

# 简单均线
ma20 = recent['close'].rolling(20).mean()
ma60 = recent['close'].rolling(60).mean()
print(f'MA20: {ma20.iloc[-1]:.2f}')
print(f'MA60: {ma60.iloc[-1]:.2f}')
print(f'MA20-MA60: {ma20.iloc[-1] - ma60.iloc[-1]:.2f}')

# 鳄鱼线（简化版：蓝=13期均线，红=8期，绿=5期，各自前移）
blue = recent['close'].rolling(13).mean().shift(8)
red = recent['close'].rolling(8).mean().shift(5)
green = recent['close'].rolling(5).mean().shift(3)
print(f'\n=== 鳄鱼线（简化） ===')
print(f'蓝(颚线,13期移8): {blue.iloc[-1]:.2f}')
print(f'红(齿线,8期移5): {red.iloc[-1]:.2f}')
print(f'绿(唇线,5期移3): {green.iloc[-1]:.2f}')

# 分形识别（简单版：连续5根K线，中间最高/最低）
def find_fractals(df, lookback=100):
    df = df.tail(lookback).copy()
    up_fractals = []
    down_fractals = []
    for i in range(2, len(df)-2):
        # 向上分形：中间高点 > 两边各两个高点
        if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
            df['high'].iloc[i] > df['high'].iloc[i-2] and
            df['high'].iloc[i] > df['high'].iloc[i+1] and 
            df['high'].iloc[i] > df['high'].iloc[i+2]):
            up_fractals.append((df['time'].iloc[i], df['high'].iloc[i]))
        # 向下分形：中间低点 < 两边各两个低点
        if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['low'].iloc[i] < df['low'].iloc[i+1] and 
            df['low'].iloc[i] < df['low'].iloc[i+2]):
            down_fractals.append((df['time'].iloc[i], df['low'].iloc[i]))
    return up_fractals, down_fractals

up_f, down_f = find_fractals(h1, 200)
print(f'\n=== H1最新分形 ===')
print(f'最近向上分形（前5）:')
for t, p in up_f[-5:]:
    print(f'  {t}  {p:.2f}')
print(f'最近向下分形（前5）:')
for t, p in down_f[-5:]:
    print(f'  {t}  {p:.2f}')
