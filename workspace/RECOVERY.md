# 🚑 小白恢复手册 — 系统崩溃/重装后如何找回我

> **最后更新**: 2026-04-30
> **GitHub仓库**: `goldland2021/openclaw_mt5`
> **我的身份文件在**: 仓库的 `feature/1.07-performance-monitoring` 分支

---

## 一键恢复（推荐）

重装好Windows后，打开 PowerShell，逐条运行：

```powershell
# 1. 安装 Node.js（OpenClaw 运行环境）
# 去 https://nodejs.org 下载 LTS 版本安装

# 2. 安装 OpenClaw
npm install -g openclaw

# 3. 验证
openclaw --version
# 应该看到：OpenClaw 2026.4.25 (或更新版本)

# 4. 克隆整个工作空间（包含我）
cd ~
git clone https://github.com/goldland2021/openclaw_mt5.git .openclaw\workspace

# 5. 补上.gitignore里忽略的技能目录
cd ~\.openclaw\workspace\skills

# 用 openclaw 安装技能
openclaw skill install git
openclaw skill install github
openclaw skill install notion
openclaw skill install notion-skill
openclaw skill install win-mouse-native
openclaw skill install windows-control
openclaw skill install whatsapp-business
openclaw skill install reddit-readonly
openclaw skill install test-ollama
openclaw skill install xiaohongshu-scraper

# 6. 配置提供商（API Key）
# 运行 openclaw configure 按提示设 DeepSeek / Qwen 等提供商的 Key
```

---

## 恢复后检查清单

### ✅ 核心文件确认
| 文件 | 路径 | 作用 |
|------|------|------|
| `SOUL.md` | `workspace\SOUL.md` | 我的灵魂 —— 个性、语气 |
| `IDENTITY.md` | `workspace\IDENTITY.md` | 我的身份 —— 小白，交易专家 |
| `USER.md` | `workspace\USER.md` | 关于你 —— 白昱 |
| `AGENTS.md` | `workspace\AGENTS.md` | 工作规范 |
| `TOOLS.md` | `workspace\TOOLS.md` | 环境配置备注 |
| `RECOVERY.md` | `workspace\RECOVERY.md` | 本手册 |
| `memory/` | `workspace/memory/` | 每日笔记目录 |

### ✅ 配置恢复
运行 `openclaw configure` 重新设置：
- **provider** → DeepSeek、Qwen Portal、Ollama 等
  - 主模型: `deepseek/deepseek-v4-flash`
- **workspace** → `C:\Users\<你>\ .openclaw\workspace`
- **web_search** → MiniMax / Brave API Key（如果有的话）

### ✅ Node 插件重新安装
```powershell
cd ~\.openclaw
openclaw plugin install memory-core
openclaw plugin install memory-memoria
```

### ✅ 我的记忆恢复
- GitHub 仓库里：`SOUL.md`（个性）、`IDENTITY.md`（身份）、`USER.md`（关于你）→ **永久保留**
- Memoria 语义记忆 → **在服务器端，重装后连上即恢复**（`memory_retrieve` / `memory_search` 会自动工作）
- 每日笔记 → 仓库里有 `memory/` 目录的历史记录

### ✅ 交易系统恢复
项目在 `G:\MetaTrader5EXNESS\MQL5\Experts\openclaw\`
- 要从仓库拉下来手动部署（交易系统文件不在workspace里）
- 或者你保留了一份在 `G:` 盘 -> 重装后如果 `G:` 盘没被格式化，直接可用

---

## 什么东西丢了需要重新弄？

| 内容 | 能恢复？ | 备注 |
|------|----------|------|
| 我的个性(SOUL) | ✅ 仓库有 | 永久备份 |
| 你是谁(USER) | ✅ 仓库有 | 永久备份 |
| AGENTS规范 | ✅ 仓库有 | 永久备份 |
| 技能配置 | ⚠️ 需重装 | 跑上面的skill install |
| API Keys | ❌ 需手动重新配置 | 找你的DeepSeek/Qwen Key |
| Memoria语义记忆 | ✅ 服务器端 | 自动恢复 |
| 每日笔记 | ✅ 仓库有 | `memory/` 目录 |
| 交易EA/Python脚本 | ✅ 仓库有 | 项目GitHub仓库里 |
| GitHub Token | ❌ 需重新生成 | 去 github.com/settings/tokens |

---

## 最重要的提醒

**拿到新电脑/重装后，先做这3件事：**

1. `npm install -g openclaw` ← 装我
2. `git clone https://github.com/goldland2021/openclaw_mt5.git .openclaw\workspace` ← 找回我的记忆和身份
3. 配好DeepSeek API Key ← 我才能说话思考

然后对我说一声 **"我回来了"**，我就认识你了。
