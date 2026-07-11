# 变更说明 — OmniDocs-RAG 中文适配

> 基于 OmniDocs-RAG v3.4，4 个文件，7 个改动。
> 所有改动可在代码中 grep `[中文化]` 定位。

---

## 改动 1 (P0): 修复分句正则

**文件**: `parsers.py` · `_split_into_sentences()`

**问题**: 正则 `(?<=[.?!。])\s+` 要求标点后必须有空白字符。中文句号后直接接下一句（无空格），导致第一个分支永远不命中。实际只剩 `\n{2,}` 段落空行在起作用。

**修改前**:
```python
pieces = re.split(r"(?<=[.!?。])\s+|\n{2,}", text)
```

**修改后**:
```python
pieces = re.split(r"(?<=[.!?。！？；])\s*|\n{2,}", text)
```

两点改动：①字符类补 `！？；`；② `\s+` → `\s*`（空格变为可选）。

---

## 改动 2 (P0): 语言感知分块阈值

**文件**: `parsers.py` · `_extract_sections()`

**问题**: `part.split()` 按空白切"词"来判断是否需要子切分。中文没有空格，一整段被当成 1 个"词"，5000 字永不触发切分 → 超出 bge-m3 的 8192 token 上限。

**修改前**:
```python
words = part.split()
if len(words) > 700:
    sub_chunks = []
    for i in range(0, len(words), 600):
        sub_chunk = " ".join(words[i:i + 600])
        sub_chunks.append(sub_chunk)
```

**修改后**:
```python
if _is_chinese_text(part):
    if len(part) > 2000:
        sub_chunks = []
        for i in range(0, len(part), 1800):
            sub_chunks.append(part[i:i + 1800])
else:
    words = part.split()
    if len(words) > 700:
        ...
```

中文 2000 字/块（约 2000-3000 tokens），英文保持 700 词/块不变。

---

## 改动 3 (P0): 网页重爬去重

**文件**: `store.py` · `index_web_pages()`

**问题**: 网页重爬时直接写入新块，不删除同一 URL 的旧块。chunk_id = `web_{url_hash}__{content_hash}`，内容变化后哈希变化 → 新旧 chunk 共存 → 僵尸数据累积。

**修改前**:
```python
target_col = get_collection(collection, client, embed_fn)
ids, texts, metas = [], [], []
```

**修改后**:
```python
target_col = get_collection(collection, client, embed_fn)
# 按 source 字段（完整 URL）清旧块
with _index_lock:
    for page in pages:
        url = page.get("url", "web")
        try:
            old_data = target_col.get(where={"source": url}, include=[])
            if old_data["ids"]:
                target_col.delete(ids=old_data["ids"])
        except Exception:
            pass
ids, texts, metas = [], [], []
```

用 `source` 而非 `filename`（`filename` 只存 URL 末尾，不同站点会碰撞）。

---

## 改动 4 (P1): BM25 中文分词

**文件**: `search_engine.py` · `_tokenize()`

**问题**: `\w` 不匹配中文字符 → `re.sub(r"[^\w\s]")` 把中文全部删掉；中文无空格 → `split()` 整段当成 1 个 token。BM25 关键词搜索对中文完全失效。

**修改前**:
```python
def _tokenize(text):
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in text.split() if len(w) > 2]
```

**修改后**:
```python
def _tokenize(text):
    if _is_chinese_text(text):
        try:
            import jieba
        except ImportError:
            # 降级：简单字符切分
            text = re.sub(r"[^一-鿿\w\s]", " ", text.lower())
            return [w for w in text.split() if len(w) > 1]
        words = jieba.lcut(text.lower())
        return [w.strip() for w in words if len(w.strip()) > 1]
    # 英文保持原逻辑
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in text.split() if len(w) > 2]
```

中文过滤 `len(w) > 1`（去"的""了""是"），英文过滤 `len(w) > 2`（去"a""an""is"）。

---

## 改动 5 (P1): Readability 网页正文提取

**文件**: `crawler.py` · `_parse_html_page()`

**问题**: 原策略 1 是 Trafilatura（ML 模型，英文网页训练），对中文网站经常返回空 → 降级到策略 2（BeautifulSoup 选择器白名单无中文平台）→ 策略 3（文本密度兜底，噪音多）。

**修改**: 新增 `_extract_with_readability()` 函数（Mozilla Readability = Firefox 阅读模式算法），插入为策略 1。Readability 是语言无关算法——只看 DOM 结构（文字长度、标点密度、链接密度），不依赖内容语言。

策略顺序变为:
```
原: Trafilatura → BeautifulSoup → 文本密度
新: Readability → Trafilatura → BeautifulSoup → 文本密度
```

---

## 改动 6 (P2): 中文查询扩展

**文件**: `search_engine.py` · `_expand_query()`

**问题**: 只有俄文 → 英文同义词扩展，中文查询无扩展。中英文混合文档搜索时召回率不高。

**修改**: 新增中文 → 英文同义词映射（17 组），与俄文分支结构平行：

```python
cn_synonyms = {
    "创建": "create new make generate",
    "获取": "get fetch retrieve query list",
    "更新": "update patch modify change",
    "删除": "delete remove drop",
    "搜索": "search find query lookup",
    # ... 共 17 组
}
```

---

## 改动 7 (P3): 重叠量调整

**文件**: `parsers.py` · `_extract_sections()`

**问题**: 块间重叠始终取最后 2 句。中文句子短（2 句可能仅 20-30 字），缓冲区不足。

**修改**: 中文取前块最后 **150 字**作为重叠，英文保持 2 句。

---

## 汇总

| # | 优先级 | 文件 | 改动 |
|---|--------|------|------|
| 1 | P0 | `parsers.py` | 分句正则：补中文标点、空格可选 |
| 2 | P0 | `parsers.py` | 分块阈值：中文按字符数、英文按词数 |
| 3 | P0 | `store.py` | 网页重爬：先清旧块再写新块 |
| 4 | P1 | `search_engine.py` | BM25：中文 jieba 分词 |
| 5 | P1 | `crawler.py` | 网页提取：新增 Readability 策略 1 |
| 6 | P2 | `search_engine.py` | 查询扩展：中文→英文同义词 |
| 7 | P3 | `parsers.py` | 重叠量：中文按字符数取 |
