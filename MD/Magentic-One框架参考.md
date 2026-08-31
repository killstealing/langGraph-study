# Magentic-One 框架参考

> 微软研究院开源的通才多智能体系统，基于 AutoGen。架构是中心化的 Orchestrator（编排者）模式，对应 LangGraph 的 Supervisor 模式。

## 一、是什么

**1 个 Orchestrator + 4 个专家智能体**：

| 智能体 | 职责 |
|---|---|
| **Orchestrator** | 拆解任务、分派、跟踪进度、卡死时重新规划 |
| **WebSurfer** | 控制浏览器，导航/点击/输入/总结网页 |
| **FileSurfer** | 读本地文件、列目录、浏览文件夹 |
| **Coder** | 写代码、分析数据、生成产物 |
| **ComputerTerminal** | 执行 shell 命令、装库、跑程序 |

核心机制是**双账本**：外层 **Task Ledger**（总计划）+ 内层 **Progress Ledger**（当前进度 + 自我反思"是不是卡住了、下一步谁发言"）。

## 二、安装

```bash
pip install "autogen-agentchat" "autogen-ext[magentic-one,openai]"
playwright install
```

或 CLI：
```bash
pip install magentic-one-cli
```

要求 Python 3.10+，需要 LLM 的 API key（默认 OpenAI，可配 Azure/其他）。

## 三、使用

```python
import asyncio
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne

async def main():
    client = OpenAIChatCompletionClient(model="gpt-4o")
    m1 = MagenticOne(client=client)
    task = "找出上个月关于多智能体强化学习的最新论文，并总结前三篇"
    await Console(m1.run_stream(task=task))

asyncio.run(main())
```

自定义团队 / 加人工审核：用 `MagenticOneOrchestrator` + 指定参与者 + `UserProxy(hil_mode=True)`。

## 四、优点

1. **编排者模式**：自动任务分解 + 动态调度 + 进度跟踪 + 卡死检测（连续无效迭代自动重规划）。
2. **模块化可插拔**：增删智能体不改核心结构。
3. **有状态可追踪**：Task/Progress 双账本，过程清晰、可恢复。
4. **通才能力强**：网页、文件、编码、终端都能干，适合开放式复杂任务。
5. **可选人工介入**：计划阶段可让人审批/改计划。

## 五、2026 现状（重要）

⚠️ **AutoGen 已进入维护模式，不再加新功能。** 微软 2026 年 Build 大会已宣布重心转向 **Microsoft Agent Framework（`Microsoft.Agents.AI`）**，Magentic-One 迁移成 MAF 里的一个编排模式。

- 学习架构思想可以（尤其对照 Supervisor 模式）；
- 上生产要谨慎，优先看 MAF 迁移指南，别在新项目里押 AutoGen。

⚠️ **安全**：会执行任意代码、访问真实网站，务必容器隔离、限制网络、留意 prompt injection。

## 六、与 LangGraph 对照

| | LangGraph | Magentic-One |
|---|---|---|
| 架构 | 图 + 状态机，可任意拓扑 | 中心化 Orchestrator |
| 多代理模式 | Supervisor / Network / 父子图都能搭 | 主要是 Supervisor 式 |
| 定位 | 通用框架，自己搭 | 开箱即用的通才团队 |

- **Network 多代理** = 去中心化的对等网络（agent 平级互发消息）。
- **Magentic-One / Supervisor** = 中心化编排者（一个 boss 调度一群工人）。
- 两者是相反的经典模式，可对照理解。
