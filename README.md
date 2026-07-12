<div align="center">

# 🧠 OmniDocs-RAG-CN

**开箱即用的 AI Agent 个人知识库 — 原生中文支持 🇨🇳**

*索引本地文件、网页、GitHub 仓库、npm/PyPI 包 → 混合 AI 检索引擎 → IDE 聊天框内直接搜索。100% 本地运行，一条命令安装。*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-brightgreen.svg)](https://modelcontextprotocol.io/)
[![Chroma](https://img.shields.io/badge/Vector_DB-Chroma-orange.svg)](https://trychroma.com/)
[![BGE-M3](https://img.shields.io/badge/🤗_Model-BGE--M3-yellow.svg)](https://huggingface.co/BAAI/bge-m3)

[English](README_EN.md) | 中文

</div>

---

## 缘起

最初只是想搭个个人知识库，但很快发现 Obsidian 对 Agent 并不友好——目录树、双向链接、全文搜索，这些为人设计的功能在 Agent 眼里只是一堆需要遍历的文件路径。Agent 要的不是"翻文件"，而是"语义检索"：用自然语言问一个问题，从知识库中召回最相关的片段，再基于这些片段生成回答。

于是自然想到了向量数据库。把个人文档向量化存起来，Agent 用向量相似度来"找东西"，而不是翻文件夹。但翻遍 GitHub，没有一个现成的工具能直接做到这一点——要么缺 MCP 接口，要么对中文支持几乎为零（分句错、分词烂、BM25 失效）。

所以基于 [OmniDocs-RAG v3.4](https://github.com/ElvinBayramov/OmniDocs-RAG) 做了中文化适配和 MCP 接口封装，改出了 OmniDocs-RAG-CN。

最终的使用场景是这样的：

**人**通过 IDE（Claude Code / Cursor）跟 Agent 对话，问一个问题；**Agent** 通过 MCP 协议调用 OmniDocs-RAG-CN 的 `search_docs`，在个人向量知识库中做混合检索（语义 + 关键词 + 重排序），拿到最相关的文档片段后组织回答。

人和 Agent 从两个"端口"访问同一个个人数据库：人看到的是 IDE 聊天窗口里的自然语言回答，Agent 看到的是 chroma_db 里经过向量化的知识片段。人的入口是对话，Agent 的入口是 MCP 工具调用——同一份知识，两种访问方式。

这就是"人与 Agent 协作"的知识管理：不是人翻了文件喂给 Agent，也不是 Agent 替代人去读文档；而是人决定"哪些知识值得存"，Agent 负责"在需要的时候精准找到"，人再做最终的判断和创造。知识库从一个人的第二大脑，变成了人和 Agent 共享的外部记忆。

---

## 人-Agent 协作架构

```
┌─────────────────────────────────────────────────────────┐
│                      人 👤                              │
│   IDE 聊天框                                            │
│   "帮我查一下认证逻辑怎么实现的？"                          │
│   → 看到自然语言回答，做决策、创作                          │
└──────────────────────┬──────────────────────────────────┘
                       │ 自然语言对话
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Agent 🤖                              │
│   Claude Code / Cursor 等                                │
│   → 理解问题 → 调 MCP 工具 → 综合回答                     │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP 协议（search_docs）
                       ▼
┌─────────────────────────────────────────────────────────┐
│               OmniDocs-RAG-CN                            │
│   ┌───────────────────────────────────────────────┐     │
│   │  混合检索引擎                                    │     │
│   │  向量语义 + BM25 关键词(jieba) + RRF 融合        │     │
│   │  + Cross-Encoder 重排序 + 去重                   │     │
│   └───────────────────────────────────────────────┘     │
│                         │                                │
│                         ▼                                │
│   ┌───────────────────────────────────────────────┐     │
│   │  ChromaDB 向量数据库 (chroma_db/)               │     │
│   │  你的文档 → 向量化 → 语义可检索                   │     │
│   └───────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

> 两个端口，同一份知识。人从对话进去，Agent 从 MCP 进去。

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- `git`

### 2. 一键安装

```bash
git clone https://github.com/ybhuang995-dev/personal-data-for-agents.git
cd personal-data-for-agents
python install.py
```

`install.py` 自动完成一切：pip 依赖安装 → GPU 检测 + PyTorch 安装 → AI 模型下载（~2.3GB，仅首次）→ IDE 的 MCP 连接自动配置。

### 3. 使用

直接在 IDE 聊天框里说人话：

```
帮我索引我的文档目录
搜索：认证逻辑怎么实现的？
把 https://fastapi.tiangolo.com 的文档也加进知识库
用 rag_status 看看知识库状态
```

Agent 自动调用 MCP 工具，不需要你点任何按钮。

---

## ✨ 功能特性

### 🔍 混合搜索管道

| 阶段 | 技术 | 说明 |
|------|------|------|
| 查询扩展 | CN→EN 同义词映射 | 17 组中文→英文编程同义词，提升混合文档召回率 |
| 向量搜索 | ChromaDB + bge-m3 | 1024 维语义向量，支持 100+ 语言 |
| 关键词搜索 | BM25 + jieba 分词 | 中文用结巴分词，英文保持空格切分 |
| 融合排序 | RRF (k=60) | 向量排名 + 关键词排名数学融合 |
| 重排序 | bge-reranker-v2-m3 | 交叉编码器对候选集精确打分 |
| 去重 | >80% 相似度剔除 | 移除近重复结果 |

### 📁 多源摄入

- **40+ 文件格式** — `.md` `.py` `.js` `.pdf` `.docx` `.xlsx` `.pptx` 等
- **网页** — 异步 BFS 爬虫，支持 robots.txt、sitemap.xml
- **GitHub 仓库** — `github://owner/repo` 直接抓取
- **npm / PyPI / ZIP** — `npm://package` `pypi://package` `file:///path.zip`
- **JS 渲染页面** — 可选 Playwright 支持

### ⚡ 性能

- **GPU 加速** — CUDA 自动检测（索引速度提升 ~11x）
- **增量索引** — MD5 哈希，只处理变化的文件
- **BM25 持久化** — pickle 缓存，服务重启即恢复

### 🛠️ 管理

- **多集合** — 不同项目用不同知识库
- **自动分类** — YAML frontmatter → H1 标题 → 文件名
- **文件监控** — watchdog 监听变动，自动增量索引
- **100% 本地** — 无 API Key、无云服务、无月费

---

## 🛠️ MCP 工具（9 个）

| 工具 | 说明 |
|------|------|
| `index_documents(path, collection)` | 索引本地文件（40+ 格式，增量索引） |
| `index_url(uri, collection, ...)` | 索引网页、GitHub、npm、PyPI、ZIP |
| `search_docs(query, n, ...)` | 混合搜索（向量 + BM25 + 重排序） |
| `rag_status(collection)` | 系统状态：模型、GPU、BM25、分块数 |
| `list_collections()` | 列出所有知识库集合 |
| `list_indexed_files(collection)` | 列出集合中已索引的文件 |
| `remove_source(filename, collection)` | 从索引中删除指定文件 |
| `delete_collection(name, confirm)` | 删除整个集合 |
| `reindex_collection(path, collection)` | 强制全量重建索引 |

### `index_url()` 示例

```python
# 网页（异步 BFS 爬虫）
index_url("https://docs.python.org/3/library/asyncio.html")

# GitHub 仓库
index_url("github://tiangolo/fastapi/docs")

# npm 包
index_url("npm://axios@1.6")

# PyPI 包
index_url("pypi://fastapi")

# ZIP 压缩包
index_url("file:///path/to/docs.zip")
```

---

## 🇨🇳 中文适配（7 处改动）

| 优先级 | 文件 | 改动 |
|--------|------|------|
| P0 | `parsers.py` | 分句正则补中文标点（`。！？；`），空格改为可选 |
| P0 | `parsers.py` | 语言感知分块：中文按 2000 字符、英文按 700 词 |
| P0 | `store.py` | 网页重爬：按 source URL 清旧块再写入，防僵尸数据 |
| P1 | `search_engine.py` | BM25：中文用 **jieba** 分词替换空格切分 |
| P1 | `crawler.py` | 网页提取：新增 **Mozilla Readability** 为策略 1（语言无关） |
| P2 | `search_engine.py` | 查询扩展：17 组中文→英文同义词映射 |
| P3 | `parsers.py` | 重叠量：中文取前块最后 150 字，英文保持 2 句 |

> 所有改动在代码中以 `# [中文化]` 注释标记。详见 [CHANGES_CN.md](CHANGES_CN.md)。

---

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_DOCS_PATH` | server.py 父目录 | 扫描的文档目录 |
| `RAG_DB_PATH` | `./chroma_db` | ChromaDB 持久化路径 |
| `RAG_DEVICE` | `auto` | `cuda` / `cpu` / `auto`（有 CUDA 健康检查） |
| `RAG_EMBED_MODEL` | `BAAI/bge-m3` | 嵌入模型 |
| `RAG_RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | 交叉编码器重排序模型 |
| `RAG_DASHBOARD` | 不启用 | 设为 `true` 开启 Web 面板（端口 6280） |
| `RAG_WATCH_PATH` | 不启用 | 文件变动自动重索引 |
| `GITHUB_TOKEN` | — | GitHub API 令牌（提升速率限制） |

---

## ❓ 常见问题

**Q: 数据会发送到外部吗？**
A: 不会。100% 本地运行。模型从 HuggingFace 下载一次后离线使用，无 API Key，无云服务。

**Q: 需要 GPU 吗？**
A: 不必须，但有最好。CPU 搜索约 200ms，GPU 索引加速约 11x。设置 `RAG_DEVICE=cuda` 开启。

**Q: 如何更新索引？**
A: 增量索引——只有变化的文件会重新处理。再调一次 `index_documents()` 即可，或开启文件监控自动更新。

**Q: 首次搜索为什么慢？**
A: Cross-Encoder（~1.1GB）在首次搜索时惰性加载。后续搜索即时响应。

**Q: 支持中文吗？**
A: 这就是做这个项目的原因。原生 jieba 分词、中文分句、中文分块、CN→EN 查询扩展。bge-m3 还支持 100+ 其他语言。

**Q: 能建多个知识库吗？**
A: 可以。用 `collection` 参数区分：`index_documents(path, collection="项目A")`，搜索时指定 `collection="项目A"`。

---

## 📄 许可证

基于 **Apache License 2.0** 开源。详见 [LICENSE](LICENSE)。

原项目：[ElvinBayramov/OmniDocs-RAG](https://github.com/ElvinBayramov/OmniDocs-RAG)
