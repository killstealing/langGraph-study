# LangGraph 八大要点 · 文件索引

> 把 LLM Agent 开发的八大能力点，逐条对应到本工作空间的练习文件，方便按点复习。

## 总览表

| # | 要点 | 层级 | 一句话概括 | 对应文件 |
|---|---|---|---|---|
| 1 | 外部调用 | 接入层 | 如何被外部系统使用 | 底层原理入门、快速入门、输入输出类型 md |
| 2 | 人机交互 | 交互层 | 需要用户参与时如何处理 | 断点系列 `43/44/45/46` |
| 3 | 多轮对话 | 记忆层 | 如何记住历史聊天内容 | `12/13` 消息传递机制 |
| 4 | 规划逻辑 | 决策层 | 如何拆解任务并调用工具 | Router/Tool Calling/ReAct `17~28` |
| 5 | 流式输出 | 体验层 | 如何逐字输出答案 | `32/33` 事件流 |
| 6 | 多 Agent | 协作层 | 如何让多个 Agent 分工合作 | 父子图/Network/Supervisor/综合实战 `50~62` |
| 7 | 短期/长期记忆 | 记忆层 | 会话内和跨会话的记忆 | `37/38` 短期、`40` 长期 |
| 8 | Debug 和监控 | 运维层 | 追踪和保障 Agent 健康运行 | `15` LangSmith、事件流、可视化 |

---

## 1. 外部调用（接入层）

外部系统如何调起 agent —— `graph.invoke / astream / batch`、`config`、`thread_id` 等入口。

- `LangGraph 底层原理与入门.ipynb` / `0802` —— 图结构、编译、调用的最基础入口
- `08 LangGrpah基础之LangGraph快速入门案例实践.ipynb` —— 第一次把 agent 跑通
- `06/07 LangGrpah基础之LangGprah结构-*` —— GraphState、Nodes/Edges 类设计
- `LangChain组件输入类型与智能体生态.md` —— llm / agent / ToolNode 的 invoke 输入、返回类型（专门讲"怎么被调用"）

## 2. 人机交互（交互层）

需要用户参与时，用 `interrupt` / 断点暂停等用户确认或输入。

- `43 LangGraph进阶之人机交互-Graph中添加断点实践.ipynb`
- `44 LangGraph进阶之人机交互-Graph中添加动态断点实践.ipynb`
- `45 LangGraph进阶之人机交互-Graph中添加动态断点代码编写.ipynb`
- `46 LangGraph进阶之人机交互-Graph中添加动态断点测试.ipynb`
- `LangGraph动态断点-人机交互.md` —— 断点/`Command(resume=...)` 的总结

## 3. 多轮对话（记忆层）

靠 State 里的 `messages` 列表 + `add_messages` reducer，在单次图运行内累积对话历史。

- `12 LangGraph进阶之State核心-基于State构建消息传递机制.ipynb`
- `13 LangGraph进阶之State核心-MessageGraph实践.ipynb`
- `LangGraph消息与LLM调用基础.md`

> ⚠️ 区分「多轮对话」和「短期/长期记忆」：
> - **多轮对话**：`messages` 列表在**单次图运行内**累积历史（见本点）
> - **短期/长期记忆**：`checkpointer` / `Store` 在**会话之间**持久化（见第 7 点）

## 4. 规划逻辑（决策层）

拆解复杂任务并调用工具，对应单代理三大范式。

**Router（路由到不同分支）**
- `17 LangGraph进阶之单代理-Router Agent-逻辑初探.ipynb`
- `18 ...-应用程序构建map.ipynb`
- `19 ...-结构化输出-提示词工程.ipynb`
- `20 ...-结构化输出-基于内置工具.ipynb` / `..._TypedDict.ipynb`
- `21 ...-基于结构化输出构建Router图.ipynb` / `..._练习.ipynb`
- `复习/16 LangGraph进阶之单代理-Router Agent-LangGraph四大代理架构.ipynb`

**Tool Calling（拆解调工具）**
- `22 LangGraph进阶之单代理-Tool Calling Agent-核心原理.ipynb`
- `23 ...-完整案例.ipynb` / `...-lianxi.ipynb`
- `24 ...-手动构建Tool Calling Agent.ipynb`

**ReAct（思考-行动循环）**
- `28 LangGraph进阶之单代理-ReAct Agent-实操-工具准备(1).ipynb`
- `复习/26 ...-ReAct Agent-LangChain实现方式.ipynb`
- `复习/29 ...-ReAct Agent-实操-原理剖析.ipynb`

## 5. 流式输出（体验层）

逐字输出答案，`astream` / `stream_mode` / `astream_events`。

- `32 LangGraph进阶之事件流-流输出模式测试.ipynb`
- `33 LangGraph进阶之事件流-事件流应用.ipynb`

## 6. 多 Agent（协作层）

多个 Agent 分工合作。

**父子图（Hierarchical）**
- `50 LangGraph实战之多代理-父子图之间的消息传递(上).ipynb`
- `51 ...(下).ipynb`
- `LangGraph父子图消息传递.md`

**Network（去中心化对等）**
- `52 LangGraph实战之多代理-Network多代理需求分析(1).ipynb`

**Supervisor（中心化）**
- `56 LangGraph实战之多代理-Supervisor原理剖析与代码实践.ipynb`
- `57 ...-基于Supervisor架构实现多代理系统.ipynb` / `... copy 2.ipynb`
- `LangGraph-Supervisor多代理模式.md`
- `复习/LangGraph Supervisor死循环控制方法.md`

**综合实战（多 Agent + 工具入库）**
- `59 LangGraph实战之多代理-Multi Agent综合实战-Neo4J入库(2).ipynb`
- `61 ...-向量数据入库(4).ipynb`
- `62 ...-最终效果验证(5).ipynb`
- `Magentic-One框架参考.md` —— 参考的多代理编排框架

## 7. 短期/长期记忆（记忆层）

**短期记忆（会话内 / 跨会话持久化）**
- `37 LangGraph进阶之长短期记忆-基于MemorySaver实现短期记忆.ipynb`
- `38 ...-基于SqliteSaver实现短期记忆.ipynb`
- `复习/39 ...-实现带有记忆的智能天气助手.ipynb`

**长期记忆（跨会话）**
- `40 LangGraph进阶之长短期记忆-基于Store实现长期记忆.ipynb`

## 8. Debug 和监控（运维层）

追踪与保障 agent 健康运行。

- `15 LangGraph进阶之State核心-LangGraph与LangSmith整合.ipynb` —— LangSmith 追踪
- `32/33 事件流` —— `astream_events` 观测中间步骤（见第 5 点）
- `复习/10 LangGraph进阶之State核心-Graph可视化.ipynb`
- `LangGraph图可视化-mermaid渲染.md` —— 图结构排查
- `复习/LangGraph Supervisor死循环控制方法.md` —— 避免死循环，保障稳定运行

---

## 速查：按文件编号排序

```
06/07/08        → 1 外部调用（基础结构 + 快速入门）
09/10/11/12/13  → 3 多轮对话（State / Reducer / 消息传递）
15              → 8 Debug（LangSmith）
16/17/18/19/20/21 → 4 规划（Router）
22/23/24        → 4 规划（Tool Calling）
26/28/29        → 4 规划（ReAct）
32/33           → 5 流式输出 + 8 Debug（事件流）
37/38/39        → 7 短期记忆
40              → 7 长期记忆
43/44/45/46     → 2 人机交互（断点）
50/51           → 6 多 Agent（父子图）
52              → 6 多 Agent（Network）
56/57           → 6 多 Agent（Supervisor）
59/61/62        → 6 多 Agent（综合实战）
```

> 注：`复习/` 子目录是主目录部分文件的副本，另有若干主目录没有的补充练习（如 `16/26/29/39`），已一并纳入对应要点。
