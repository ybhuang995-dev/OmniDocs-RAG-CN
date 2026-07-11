# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是 [OmniDocs-RAG v3.4](https://github.com/ElvinBayramov/OmniDocs-RAG) 的中文适配分支，一个基于 MCP (Model Context Protocol) 的本地 RAG 知识库服务器。通过 Claude Code 的 MCP 集成，让 AI Agent 能搜索本地文档、网页、GitHub 仓库等。

**教学项目，不用于生产环境。**

## 常用命令

### 环境与依赖

```bash
# 安装全部依赖（含中文支持：jieba、readability-lxml）
pip install -r requirements.txt

# 验证依赖是否就绪
python -c "import fastmcp, chromadb, sentence_transformers, jieba; print('All OK')"
```

### CLI 管理（manage.py）

```bash
python manage.py status                          # 查看索引状态
python manage.py list                            # 列出所有集合
python manage.py files [collection]              # 列出集合中的文件
python manage.py index <path>                    # 索引本地目录
python manage.py index-url <url>                 # 索引网页/GitHub/npm/PyPI
python manage.py search "<query>" -n 5           # 搜索
python manage.py remove <filename>               # 从索引中移除文件
python manage.py delete <collection>             # 删除集合
python manage.py reindex [collection]            # 强制全量重建索引
```

### 启动方式

服务通过 MCP 协议运行，不需要手动启动。在 `~/.claude/mcp.json` 中配置后，Claude Code 重启即自动加载。配置模板见 `mcp_config_cn.json`。

### 定位中文适配改动

```bash
grep -rn "\[中文化\]" .
```

所有中文化改动都以此注释标记，分布在 4 个文件中，共约 12-15 处。

## 核心架构

```
server.py        ← FastMCP 入口：9 个 MCP 工具、配置、设备检测、模型初始化
parsers.py       ← 文档解析：40+ 格式读取、分句/分块、自动分类
search_engine.py ← 搜索管道：BM25 分词/建索引、查询扩展、混合检索 + Cross-Encoder 重排序
store.py         ← 数据层：ChromaDB 集合管理、增量索引（MD5 哈希缓存）、增删改
crawler.py       ← 网页爬虫：异步 BFS、4 策略正文提取、GitHub/npm/PyPI/ZIP 加载器
dashboard.py     ← Web 管理面板（FastAPI，端口 6280），可选启用
watcher.py       ← 文件监听（watchdog），自动增量重索引
exceptions.py    ← 自定义异常类
manage.py        ← CLI 命令行工具
install.py       ← 一键安装脚本（含 IDE 自动配置）
```

### 搜索管道（5 阶段）

1. **查询扩展** — 中文→英文同义词扩展（17 组映射），提升中英文混合文档召回率
2. **混合检索** — 向量搜索（bge-m3, 1024 维）+ BM25 关键词（jieba 中文分词），RRF 融合（k=60）
3. **Cross-Encoder 重排序** — `bge-reranker-v2-m3` 对候选集精确打分
4. **去重** — 移除相似度 >80% 的近重复结果
5. **输出** — 带面包屑的结构化结果

### 数据流

```
文件/URL → parsers._read_file_to_text() → _extract_sections_smart()
         → store.index_documents() → ChromaDB + BM25 缓存
         → search_engine.search_docs() → 5 阶段管道 → 格式化结果
```

### 两个模型（自动下载，各约 1.1GB）

- `BAAI/bge-m3` — 多语言嵌入模型，1024 维向量，8192 token 上下文，支持 100+ 语言
- `BAAI/bge-reranker-v2-m3` — 交叉编码器，首次搜索时惰性加载

## 中文适配核心改动（7 处）

所有改动在代码中以 `# [中文化]` 注释标记：

| 优先级 | 文件 | 改动 |
|--------|------|------|
| P0 | `parsers.py` `_split_into_sentences()` | 分句正则：补中文标点（！？；）、`\s+`→`\s*` |
| P0 | `parsers.py` `_extract_sections()` | 分块阈值：中文按 2000 字符切，英文保持 700 词 |
| P0 | `store.py` `index_web_pages()` | 网页重爬去重：按 source（完整 URL）清旧块再写入 |
| P1 | `search_engine.py` `_tokenize()` | BM25 分词：中文用 jieba.lcut，英文保持空格切分 |
| P1 | `crawler.py` `_parse_html_page()` | 网页正文提取：新增 Readability 为策略 1（语言无关算法） |
| P2 | `search_engine.py` `_expand_query()` | 查询扩展：新增 17 组中文→英文同义词映射 |
| P3 | `parsers.py` `_extract_sections()` | 重叠量：中文取前块最后 150 字符，英文保持 2 句 |

`parsers.py` 中的 `_is_chinese_text()` 是共享工具函数，检测前 100 个字符中是否含 CJK 字符。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RAG_DOCS_PATH` | server.py 父目录 | 扫描的文档目录 |
| `RAG_DB_PATH` | `./chroma_db` | ChromaDB 持久化路径 |
| `RAG_DEVICE` | `auto` | `cuda` / `cpu` / `auto`（带 CUDA 健康检查，15s 超时） |
| `RAG_DASHBOARD` | 不启用 | 设为 `true` 开启 Web 面板（端口 6280） |
| `RAG_WATCH_PATH` | 不启用 | 设为目录路径，文件变动时自动重索引（2s 防抖） |
| `GITHUB_TOKEN` | — | GitHub API 令牌，提升速率限制 |

## 关键实现细节

- **线程安全**：`store.py` 使用 `threading.RLock()` (`_index_lock`) 保护 ChromaDB 写操作，watcher、API、MCP 可能并发访问
- **增量索引**：`store.py` 通过 `data/file_hashes.json` 缓存 MD5 哈希，只重索引变化的文件
- **BM25 持久化**：`data/bm25_cache.pkl` 保存分词后的 BM25 语料，服务重启后自动恢复（`load_bm25_on_startup()`）
- **设备检测**：`server.py` 的 `_detect_device()` 不仅检测 CUDA 可用性，还通过 15 秒超时的 encode 测试验证 GPU 确实可用，不可用时自动降级 CPU
- **代码感知分块**：Python 文件通过 AST 按 class/function 切分，JS/TS 通过正则，Markdown 按 `##`/`###` 标题切分
- **自动分类**：YAML frontmatter `category:` > 第一个 H1 标题 > 文件名 stem
- **网页正文提取链**：Readability → Trafilatura → BeautifulSoup → 文本密度分析（4 策略降级）
