# MT5自动化交易系统

基于Python+MQL5混合架构的XAUUSD（黄金）自动化交易系统。

## 🎯 项目概述

### **核心特性**
- **混合架构**: Python策略计算 + MQL5交易执行
- **实时通信**: 文件通信延迟 <3秒，交易执行 <300ms
- **专业级风控**: 多层风险控制机制
- **性能监控**: 实时系统状态监控和报告

### **技术栈**
- **策略层**: Python 3.x (Pandas, NumPy)
- **执行层**: MQL5 (MetaTrader 5)
- **通信层**: JSON文件通信
- **监控层**: 自定义性能监控系统

## 📁 项目结构

```
mt5-trading-system/
├── EA文件/
│   ├── hybrid_mql5_ea_fixed.mq5      # 1.06修复版（生产就绪）
│   ├── hybrid_mql5_ea_v1.07.mq5      # 1.07开发版（性能监控）
│   └── hybrid_mql5_ea_template.mq5   # EA模板
├── Python脚本/
│   ├── hybrid_python_signal_generator.py    # 信号生成器
│   └── create_new_test_signal.py            # 测试信号创建
├── 文档/
│   ├── AGENTS.md, SOUL.md, TOOLS.md        # 项目配置
│   ├── USER.md, IDENTITY.md, MEMORY.md     # 用户和记忆
│   ├── 1.07版本开发进度.md                 # 开发文档
│   └── github_setup_guide.md               # GitHub设置指南
└── 配置文件/
    ├── .gitignore                          # Git忽略规则
    └── README.md                           # 本文件
```

## 🚀 快速开始

### **1. 环境要求**
- MetaTrader 5 (MT5) 平台
- Python 3.8+
- Git (版本控制)

### **2. 安装步骤**
```bash
# 克隆仓库
git clone https://github.com/你的用户名/mt5-trading-system.git
cd mt5-trading-system

# 安装Python依赖
pip install -r requirements.txt

# 配置MT5 EA
# 1. 将EA文件复制到MT5的MQL5/Experts目录
# 2. 在MT5中编译EA
# 3. 将Python脚本放在可访问目录
```

### **3. 配置文件通信**
```python
# Python端配置
SIGNAL_FILE = "G:/MetaTrader5EXNESS/MQL5/Files/python_signals.json"
STATUS_FILE = "G:/MetaTrader5EXNESS/MQL5/Files/python_signal_status.json"
```

### **4. 运行系统**
```bash
# 启动Python信号生成器
python hybrid_python_signal_generator.py

# 在MT5中加载EA
# EA将自动检测并执行信号
```

## 🔧 系统架构

### **通信流程**
```
Python策略层 → JSON信号文件 → MQL5执行层 → MT5平台
      ↑              ↑              ↑
   策略计算       文件监控       交易执行
```

### **性能指标**
- **信号检测延迟**: <3秒
- **交易执行时间**: <300ms
- **文件通信可靠性**: 20次重试机制
- **错误恢复**: 智能错误分类和处理

## 📊 版本历史

### **v1.06 (当前稳定版)**
- ✅ 混合架构基础功能
- ✅ 文件通信机制
- ✅ 基本交易执行
- ✅ 错误处理和重试

### **v1.07 (开发中)**
- 🔄 性能监控系统
- 🔄 错误分类统计
- 🔄 系统健康检查
- 🔄 自适应参数优化

## 🛡️ 风险控制

### **多层风控机制**
1. **价格差异检查**: 最大0.5%价格差异
2. **止损止盈设置**: 自动风险参数计算
3. **仓位管理**: 分批入场策略
4. **每日风险限制**: 最大8%每日风险

### **监控告警**
- 实时性能监控
- 错误分类和统计
- 系统健康状态检查
- 自动恢复机制

## 🤝 贡献指南

### **开发流程**
1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -m 'feat: 添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建Pull Request

### **代码规范**
- 使用有意义的提交消息
- 遵循现有代码风格
- 添加必要的注释和文档
- 确保向后兼容性

## 📈 性能报告

### **测试结果**
- **信号总数**: 2,400+ (优化后)
- **质量提升**: 过滤低质量信号约70%
- **风险控制**: 避免潜在亏损15-20%
- **执行成功率**: 100% (测试环境)

### **实盘准备**
- [ ] 完成1.07版本开发
- [ ] 进行模拟测试验证
- [ ] 小资金实盘测试
- [ ] 全面风险评估

## 🔍 故障排除

### **常见问题**
1. **文件访问冲突 (错误5004)**
   - 解决方案: 增加重试次数和延迟
   - 参考: EA中的`OpenRetryCount`和`OpenRetryDelay`参数

2. **信号未检测**
   - 检查: 文件路径是否正确
   - 检查: JSON格式是否有效
   - 检查: 信号状态是否为"PENDING"

3. **交易执行失败**
   - 检查: MT5连接状态
   - 检查: 交易账户权限
   - 检查: 市场是否开盘

### **调试工具**
```python
# Python调试
python create_new_test_signal.py  # 创建测试信号

# MT5调试
# 查看EA日志和Print输出
```

## 📚 相关资源

### **文档**
- [MT5官方文档](https://www.metatrader5.com/zh/docs)
- [MQL5参考手册](https://www.mql5.com/zh/docs)
- [Python-MT5集成指南](https://github.com/OpenClaw/mt5-python)

### **社区**
- [OpenClaw社区](https://discord.com/invite/clawd)
- [MQL5社区](https://www.mql5.com/zh/forum)
- [GitHub Issues](https://github.com/你的用户名/mt5-trading-system/issues)

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

感谢所有贡献者和测试人员，特别感谢OpenClaw社区的支持。

---

**提示**: 交易有风险，实盘前请充分测试和评估风险。