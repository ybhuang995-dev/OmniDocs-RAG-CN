# 🧠 OmniDocs-RAG-CN — 开箱即用的 Agent 个人知识库

> 基于 [OmniDocs-RAG v3.4](https://github.com/ElvinBayramov/OmniDocs-RAG) 的中文增强版。专为 AI Agent 设计：一键安装、本地运行、原生中文支持。Apache 2.0 开源。

## 改造目标

原始版本在处理中文文档时有多个适配问题（分句正则不匹配、分块不触发、BM25 分词失效、网页正文提取质量差等）。本项目逐一修复这些问题，同时保持对英文的完全兼容。

## 改动总览

| 优先级 | 数量 | 涉及文件 |
|--------|------|---------|
| P0 必须改 | 3 | `parsers.py`×2, `store.py`×1 |
| P1 建议改 | 2 | `search_engine.py`×1, `crawler.py`×1 |
| P2 锦上添花 | 1 | `search_engine.py`×1 |
| P3 可选 | 1 | `parsers.py`×1 |

## 如何定位所有改动

```bash
grep -rn "\[中文化\]" .
```

所有改动都标记了 `# [中文化]` 注释，共约 12-15 处（4 个文件）。

## 新增依赖

```bash
pip install jieba readability-lxml
```

两个库均为纯 Python，无原生编译依赖，跨平台兼容。

## 改造要点

### P0 — 影响中文搜索质量的必须修复

1. **分句正则** (`parsers.py`): `(?<=[.?!。])\s+` → `(?<=[.?!。！？；])\s*`
2. **分块阈值** (`parsers.py`): 中文按 2000 字符切分，英文保持 700 词
3. **网页重爬去重** (`store.py`): 按 URL 清理旧块后再写入

### P1 — 提升中文搜索质量

4. **BM25 中文分词** (`search_engine.py`): jieba 分词替代空格切分
5. **网页正文提取** (`crawler.py`): 新增 Readability 策略 1

### P2/P3 — 锦上添花

6. **中文查询扩展** (`search_engine.py`): 17 组中→英同义词映射
7. **重叠量调整** (`parsers.py`): 中文取 150 字重叠

详见 [CHANGES_CN.md](CHANGES_CN.md)
