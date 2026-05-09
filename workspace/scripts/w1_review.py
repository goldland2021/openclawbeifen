"""
下周回顾脚本：对比预测走势和实际走势
下周六（2026-05-16）手动或定时运行
"""
import sqlite3, os, json

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'taskflow.db')
conn = sqlite3.connect(DB)
c = conn.cursor()

# 读取预测
c.execute('SELECT id, summary, price_at_analysis, key_levels, signals, result_text, created_at FROM analysis_history WHERE symbol="XAUUSD" AND analysis_type="W1_predict" ORDER BY id DESC LIMIT 1')
r = c.fetchone()
if not r:
    print('无预测记录')
    exit()

pred_id, summary, price, key_levels, signals, result_text, created_at = r
pred = json.loads(result_text)

print(f'{"="*60}')
print(f'周线预测回顾 (2026-05-09预测 → 本周实盘)')
print(f'{"="*60}')
print()
print(f'预测日期: {created_at}')
print(f'预测倾向: {pred["bias"]}')
print(f'预测时价格: ${price:.2f}')
print()

# 对比实际走势
c.execute('SELECT time, open, high, low, close, tick_volume FROM kline_raw WHERE timeframe="W1" AND time >= "2026-05-10" ORDER BY time')
actual = c.fetchall()

if not actual:
    print('⚠️ 本周数据尚未拉取，请先运行 update_mt5_data.py')
else:
    for r2 in actual:
        dt = r2[0][:10]
        chg = ((r2[4]-r2[1])/r2[1])*100
        print(f'  {dt}: O={r2[1]:.2f} H={r2[2]:.2f} L={r2[3]:.2f} C={r2[4]:.2f} ({chg:+.2f}%) Vol={r2[5]:,}')
    
    # 本周最高最低
    week_high = max(r2[2] for r2 in actual)
    week_low = min(r2[3] for r2 in actual)
    week_close = actual[-1][4]
    
    print()
    print(f'本周实际: 高={week_high:.2f} 低={week_low:.2f} 收={week_close:.2f}')
    print()
    
    # 对照预测
    print(f'{"="*40}')
    print(f'目标对比:')
    print(f'{"="*40}')
    
    targets = pred['targets']
    for k, v in targets.items():
        hit = '✅ 达成' if week_high >= v else '❌ 未到'
        print(f'  {k}: ${v:.0f} ({hit})')
    
    print(f'  止损: ${pred["stop_loss"]:.0f} ({"✅ 未触及" if week_low > pred["stop_loss"] else "❌ 已击穿"})')
    print()
    
    # 关键位
    print(f'关键位对照:')
    levels = pred['key_levels']
    for k, v in levels.items():
        if k in ['current', 'R1', 'R2', 'R3', 'S1', 'S2']:
            marked = ''
            if k.startswith('R') and v <= week_high:
                marked = '✅ 触及'
            elif k.startswith('S') and v >= week_low:
                marked = '✅ 触及'
            print(f'  {k}: ${v:.0f} {marked}')
    
    print()
    print(f'情景判断:')
    # 判断哪个情景
    if week_high > levels['R2']:
        print(f'  看涨情景: 突破R2，确认反转趋势 ✅')
    elif week_high > levels['R1']:
        print(f'  看涨部分触发: 站上R1')
    elif week_low < levels['S1']:
        print(f'  看跌情景: 跌破4500 ⚠️')
    else:
        print(f'  基准情景: {pred["scenario_base"]}')
    
    print()
    # 评分
    print(f'{"="*40}')
    print(f'预测评分')
    print(f'{"="*40}')
    
    score = 0
    # 方向判断
    if (pred['bias'] == '震荡偏多' and week_close > price) or (pred['bias'] == '震荡偏空' and week_close < price):
        print(f'  方向判断: ✅ 正确 (+2分)')
        score += 2
    else:
        print(f'  方向判断: ❌ 相反 (+0分)')
    
    # 目标达成
    hit_count = sum(1 for k, v in targets.items() if week_high >= v)
    print(f'  目标达成: {hit_count}/3 ({hit_count}分)')
    score += hit_count
    
    # 止损判断
    if week_low > pred['stop_loss']:
        print(f'  风险控制: ✅ 止损未触发 (+1分)')
        score += 1
    
    print(f'  总分: {score}/6')

conn.close()
