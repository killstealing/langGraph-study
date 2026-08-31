# LangGraph 图可视化（mermaid 渲染报错解决）

## 一、问题根源

`draw_mermaid_png()` 默认走 `MermaidDrawMethod.API`，会把整个图编码成 URL 请求 `https://mermaid.ink` 在线渲染。图太大（尤其 `xray=True` 展开子图）、或有特殊字符，服务会返回 **400**：

```
ValueError: Failed to reach https://mermaid.ink API ... Status code: 400.
```

**这不是代码问题，是 mermaid.ink 在线服务渲染不了复杂图。**

## 二、三种解决方案

### 方案 A：不画图，直接看 mermaid 源码（最快，零依赖）

```python
print(parent_graph.get_graph(xray=True).draw_mermaid())
```

把输出粘到 [mermaid.live](https://mermaid.live)，或存成 `.md` 文件用 ```mermaid 代码块包起来，VSCode 的 Markdown 预览（Ctrl+Shift+V）能直接渲染。

### 方案 B：本地渲染成图片（PYPPETEER）

```python
from langchain_core.runnables.graph import MermaidDrawMethod

display(Image(
    parent_graph.get_graph(xray=True).draw_mermaid_png(
        draw_method=MermaidDrawMethod.PYPPETEER
    )
))
```

依赖：
```bash
pip install pyppeteer
pyppeteer-install        # 首次需要下载 Chromium
```

### 方案 C：`nest_asyncio` 解决 asyncio 冲突（方案 B 报错时）

PYPPETEER 内部用 `asyncio.run()`，在 Jupyter 里会报：

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

修复——先执行 `nest_asyncio.apply()`：

```python
import nest_asyncio
nest_asyncio.apply()          # ✅ 必须在这之后才画图

from langchain_core.runnables.graph import MermaidDrawMethod
display(Image(
    parent_graph.get_graph(xray=True).draw_mermaid_png(
        draw_method=MermaidDrawMethod.PYPPETEER
    )
))
```

## 三、为什么"同一份代码一个能跑一个报错"？

很可能是**缓存输出 vs 实时渲染**的假象。判断方法：看单元格的 output_type——

- `output_type=display_data` + `image/png` → 是**之前保存的缓存图片**（不是现在跑通的）
- `output_type=error` → 是**当场跑失败**

把"能跑"那个单元格清空输出、重新跑一遍，大概率一样报错。

## 四、关键对比

| 图 | 现象 |
|---|---|
| 子图 `subgraph`（小） | 396 字符，能渲染 |
| 父图 `parent_graph`（xray 展开子图） | 542 字符，含 `subgraph\3asubgraph_node1`（`:` 被转义成 `\3a`），mermaid.ink 解析不了 |

`xray=True` 会把子图展开进父图，出现跨子图的节点引用 `subgraph\3asubgraph_node1`，这种语法 mermaid.ink 服务端吃不下。

## 五、结论

- 学习阶段：用 `draw_mermaid()` 看源码就够，零依赖、永不报错。
- 要在 notebook 里留图：`nest_asyncio.apply()` + `PYPPETEER` 完整链路。
- 别在 PNG 渲染上死磕，三个坑（mermaid.ink 400 → asyncio 冲突 → chromium 缺失）都是渲染侧问题，跟图逻辑无关。
