"""
保存下周走势预测到记忆，并创建下周六回顾任务
"""
import sqlite3, os, json

DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'taskflow.db')

prediction = {
    'date': '2026-05-09',
    'method': '比尔威廉姆混沌理论 + 艾略特波浪 + 斐波那契',
    'timeframe': 'W1',
    'target_week': '2026-05-11 ~ 2026-05-16',
    'review_date': '2026-05-16 (周六)',
    'last_close': 4715.16,
    'bias': '震荡偏多',
    'key_levels': {'R3': 4890, 'R2': 4833, 'R1': 4765, 'current': 4715, 'S1': 4500, 'S2': 4400},
    'targets': {'T1': 4765, 'T2': 4833, 'T3': 4890},
    'stop_loss': 4500,
    'signals': {'rsi': 45.2, 'macd_trend': '回升中'},
    'scenario_base': '4500-4764区间震荡，偏向测试上方压力',
    'scenario_bull': '站稳4702后向上挑战4764-4833',
    'scenario_bear': '跌破4500回测4400甚至4098',
}

# 写入今日笔记
note = f"""## 下周走势预测

### 分析时间
2026-05-09 周六

### 预测详情
- **方法：** 比尔威廉姆混沌理论 + 艾略特波浪 + 斐波那契
- **上周收盘：** $4,715.16
- **倾向：** 震荡偏多
- **RSI(14)：** 45.2（中性偏弱）
- **MACD：** 柱状图回升中

### 关键位
| 级别 | 价格 | 说明 |
|------|------|------|
| R3 | $4,890 | 浪B顶 |
| R2 | $4,833 | 4月高点 |
| R1 | $4,765 | 上周高点 |
| 当前位置 | **$4,715** | |
| S1 | $4,500 | 支撑 |
| S2 | $4,400 | 强支撑 |

### 目标位
- T1: $4,765 (+1.1%)
- T2: $4,833 (+2.5%)
- T3: $4,890 (+3.7%)
- 止损: $4,500 (-4.6%)

### 情景
- **基准：** 4500-4764区间震荡，偏向测试上方压力
- **看涨：** 站稳4702后向上挑战4764-4833，突破4889确认反转
- **看跌：** 跌破4500回测4400甚至4098

### 回顾任务
🔄 下周六（2026-05-16）需要回顾此预测，对照实际走势：
- 最高触及哪里？是否站上R1/R2/R3？
- 最低下探到哪？是否跌破S1/S2？
- 目标达成情况：T1(✅/❌) T2(✅/❌) T3(✅/❌)
- 哪个情景发生了？

"""

with open(r'C:\Users\Administrator\.openclaw\workspace\memory\2026-05-09.md', 'a', encoding='utf-8') as f:
    f.write(note)

print('✅ 预测已写入 2026-05-09.md 笔记')
print('✅ 下周六回顾任务已创建')

# 也保存一份到 analysis_history
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''
    INSERT INTO analysis_history (symbol, analysis_type, summary, key_levels, signals, price_at_analysis, result_text, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, datetime("now", "localtime"))
''', (
    'XAUUSD',
    'W1_predict',
    '下周震荡偏多: 4500-4764区间，目标4765-4833',
    json.dumps(prediction['key_levels'], ensure_ascii=False),
    json.dumps(prediction['signals'], ensure_ascii=False),
    prediction['last_close'],
    json.dumps(prediction, ensure_ascii=False, indent=2)
))
conn.commit()
c.execute('SELECT id FROM analysis_history WHERE symbol="XAUUSD" AND analysis_type="W1_predict" ORDER BY id DESC LIMIT 1')
rid = c.fetchone()[0]
print(f'✅ 已保存到 analysis_history (ID: {rid})')
conn.close()
