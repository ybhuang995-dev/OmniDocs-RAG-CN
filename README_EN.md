<div align="center">

# 🧠 OmniDocs-RAG-CN

**Universal RAG Knowledge Base for AI Agents — Native Chinese Support 🇨🇳**

*Index local files, websites, GitHub repos, npm/PyPI packages — search with hybrid AI-powered retrieval through your IDE chat. 100% local, one-command install.*

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-brightgreen.svg)](https://modelcontextprotocol.io/)
[![Chroma](https://img.shields.io/badge/Vector_DB-Chroma-orange.svg)](https://trychroma.com/)
[![BGE-M3](https://img.shields.io/badge/🤗_Model-BGE--M3-yellow.svg)](https://huggingface.co/BAAI/bge-m3)

English | [中文](README.md)

</div>

---

## The Story

I started out wanting to build a personal knowledge base. But I quickly realized Obsidian isn't Agent-friendly — directory trees, backlinks, full-text search… all designed for humans. An Agent doesn't need to "browse files"; it needs **semantic retrieval**: ask a question in natural language, get the most relevant snippets from the knowledge base, then compose an answer.

The natural answer was a vector database. Vectorize your documents, let the Agent find things by semantic similarity instead of file paths. But after scouring GitHub, nothing worked out of the box — either no MCP interface, or Chinese language support was effectively broken (sentence splitting failures, tokenization chaos, BM25 useless on CJK text).

So I forked [OmniDocs-RAG v3.4](https://github.com/ElvinBayramov/OmniDocs-RAG), fixed Chinese support end-to-end, and wrapped it with clean MCP interfaces. That's OmniDocs-RAG-CN.

Here's how it works:

The **human** talks to an Agent through their IDE (Claude Code / Cursor), asking a question. The **Agent** calls OmniDocs-RAG-CN's `search_docs` via the MCP protocol, runs hybrid retrieval (semantic + keyword + reranking) against the personal vector knowledge base, and composes an answer from the most relevant document chunks.

Human and Agent access the same personal database through two different "ports": the human sees natural language responses in the IDE chat window; the Agent sees vectorized knowledge fragments inside chroma_db. The human's entry point is conversation; the Agent's entry point is MCP tool calls — **one knowledge base, two access modes**.

This is "Human-Agent collaboration" in knowledge management: not the human browsing files to feed the Agent, nor the Agent replacing the human as reader. The human decides *what knowledge is worth keeping*; the Agent handles *finding the right piece at the right moment*; the human makes the final judgment and creates. A knowledge base evolves from a single-person second brain into **shared external memory for human and Agent**.

---

## Human-Agent Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Human 👤                             │
│   IDE Chat                                               │
│   "How does our auth system work?"                       │
│   → Gets natural language answers; decides, creates       │
└──────────────────────┬──────────────────────────────────┘
                       │ Natural language dialogue
                       ▼
┌─────────────────────────────────────────────────────────┐
│                     Agent 🤖                             │
│   Claude Code / Cursor / Windsurf                        │
│   → Understands query → Calls MCP tool → Synthesizes     │
└──────────────────────┬──────────────────────────────────┘
                       │ MCP Protocol (search_docs)
                       ▼
┌─────────────────────────────────────────────────────────┐
│               OmniDocs-RAG-CN                            │
│   ┌───────────────────────────────────────────────┐     │
│   │  Hybrid Search Pipeline                        │     │
│   │  Vector + BM25(jieba) + RRF + Cross-Encoder    │     │
│   └───────────────────────────────────────────────┘     │
│                         │                                │
│                         ▼                                │
│   ┌───────────────────────────────────────────────┐     │
│   │  ChromaDB (chroma_db/)                         │     │
│   │  Your docs → vectorized → semantically searchable │  │
│   └───────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

> Two ports, one knowledge base. Human enters through conversation; Agent enters through MCP.

---

## 🚀 Quickstart

### 1. Prerequisites

- Python 3.10+
- `git`

### 2. Install

```bash
git clone https://github.com/ybhuang995-dev/OmniDocs-RAG-CN.git
cd OmniDocs-RAG-CN
python install.py
```

The installer handles everything: pip dependencies → GPU detection + PyTorch → AI model download (~2.3GB, one-time) → IDE MCP auto-configuration.

> **⚠️ GPU Acceleration:** On Windows, pip may default to CPU PyTorch. To unlock your NVIDIA GPU:
> ```bash
> pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --upgrade --force-reinstall
> ```

### 3. Use

Just talk to your AI assistant:

```
> Index my project docs
> Search: how does authentication work?
> Index the FastAPI docs from https://fastapi.tiangolo.com
> Show me the knowledge base status with rag_status
```

The AI calls MCP tools automatically — no UI, no buttons, just chat.

---

## ✨ Features

### 🔍 Search Pipeline

| Stage | Technology | Description |
|-------|-----------|-------------|
| Query Expansion | CN→EN synonym mapping | 17 synonym groups for cross-language recall |
| Vector Search | ChromaDB + bge-m3 | 1024-dim semantic vectors, 100+ languages |
| Keyword Search | BM25 + jieba | Chinese word segmentation, English whitespace |
| Fusion | RRF (k=60) | Mathematical rank combination |
| Reranking | bge-reranker-v2-m3 | Cross-encoder precision scoring |
| Dedup | >80% similarity filter | Near-duplicate removal |

### 📁 Universal Ingestion
- **40+ file formats** — `.md` `.py` `.js` `.pdf` `.docx` `.xlsx` `.pptx` and more
- **Websites** — async BFS crawler, robots.txt, sitemap.xml
- **GitHub / npm / PyPI / ZIP** — `github://` `npm://` `pypi://` `file://`
- **JS-rendered sites** — optional Playwright support

### ⚡ Performance
- **GPU acceleration** — CUDA auto-detect (~11x indexing speedup)
- **Incremental indexing** — MD5 hash, only changed files re-indexed
- **BM25 persistence** — survives server restarts

### 🛠️ Management
- **Multi-collection** — separate KBs per project
- **Auto-categorization** — YAML frontmatter → H1 → filename
- **File Watcher** — auto-reindex on filesystem changes
- **100% Local & Free** — no API keys, no Docker, no monthly fees

---

## 🛠️ MCP Tools (9)

| Tool | Description |
|------|-------------|
| `index_documents(path, collection)` | Index local files (40+ formats, incremental) |
| `index_url(uri, collection, ...)` | Index websites, GitHub, npm, PyPI, ZIP |
| `search_docs(query, n, ...)` | Hybrid search with reranking |
| `rag_status(collection)` | Full system status: models, GPU, BM25, chunks |
| `list_collections()` | List all knowledge base collections |
| `list_indexed_files(collection)` | List files in a collection |
| `remove_source(filename, collection)` | Remove a file from the index |
| `delete_collection(name, confirm)` | Delete an entire collection |
| `reindex_collection(path, collection)` | Force full rebuild |

### `index_url()` Examples

```python
index_url("https://docs.python.org/3/library/asyncio.html")  # Website
index_url("github://tiangolo/fastapi/docs")                   # GitHub
index_url("npm://axios@1.6")                                  # npm
index_url("pypi://fastapi")                                   # PyPI
index_url("file:///path/to/docs.zip")                         # ZIP
```

---

## 🇨🇳 Chinese Support

This fork adds native Chinese language support with 7 targeted improvements:

| Priority | Module | Change |
|----------|--------|--------|
| P0 | `parsers.py` | Chinese sentence splitting (`。！？；`) + language-aware chunking (2000 chars vs 700 words) |
| P0 | `store.py` | Web re-crawl deduplication by source URL |
| P1 | `search_engine.py` | BM25 tokenization via **jieba** (Chinese word segmentation) |
| P1 | `crawler.py` | **Mozilla Readability** as primary extraction strategy (language-agnostic) |
| P2 | `search_engine.py` | CN→EN query expansion (17 synonym groups) |
| P3 | `parsers.py` | Chinese chunk overlap (150 chars vs 2 sentences) |

All changes marked with `# [中文化]` in source. See [CHANGES_CN.md](CHANGES_CN.md) ([中文](CHANGES_CN.md)).

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_DOCS_PATH` | parent directory | Folder to scan for files |
| `RAG_DB_PATH` | `./chroma_db` | ChromaDB storage location |
| `RAG_DEVICE` | `auto` | `cuda` / `cpu` / `auto` |
| `RAG_EMBED_MODEL` | `BAAI/bge-m3` | Embedding model |
| `RAG_RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` | Cross-Encoder model |
| `RAG_DASHBOARD` | off | Set `true` for web UI (port 6280) |
| `RAG_WATCH_PATH` | off | Watch directory for auto-reindex |
| `GITHUB_TOKEN` | — | GitHub API token (higher rate limits) |

---

## ❓ FAQ

**Q: Does this send my data anywhere?**
A: No. 100% local. Models download once from HuggingFace, then everything runs offline.

**Q: Do I need a GPU?**
A: No, but it helps. CPU search ~200ms. GPU accelerates indexing ~11x.

**Q: How do I update the index?**
A: Incremental indexing — only changed files are re-processed. Just call `index_documents()` again.

**Q: Why is the first search slow?**
A: The Cross-Encoder (~1.1GB) loads lazily on first query. Subsequent searches are instant.

**Q: Does it support Chinese?**
A: Yes — that's the point. Native jieba tokenization, Chinese sentence splitting, CN→EN query expansion, language-aware chunking. bge-m3 also supports 100+ other languages.

**Q: Can I have separate knowledge bases per project?**
A: Yes. Use `collection` parameter: `index_documents(path, collection="my-project")`.

---

## 📄 License

Apache License 2.0. See [LICENSE](LICENSE).

Original project: [ElvinBayramov/OmniDocs-RAG](https://github.com/ElvinBayramov/OmniDocs-RAG)
