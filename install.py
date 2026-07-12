"""
OmniDocs-RAG-CN — Quick Install Script
Installs dependencies, downloads models, and auto-configures your IDE.

Usage:
    python install.py              # detect existing deps, skip what's already installed
    python install.py --force      # reinstall everything from scratch
    python install.py --yes        # skip all interactive prompts (CI / scripted deploy)
    python install.py --force --yes
"""

import sys
import os
import json
import subprocess
import platform
import importlib.metadata
from pathlib import Path

# Fix Windows GBK terminal UnicodeEncodeError (e.g. ✓, ✗, 🎉)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

REQUIRED_PYTHON = (3, 10)

# All required pip packages
# (package_name, import_name) — import_name used for detection
PACKAGES = [
    ("chromadb", "chromadb"),
    ("sentence-transformers", "sentence_transformers"),
    ("fastmcp", "fastmcp"),
    ("rank-bm25", "rank_bm25"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("httpx", "httpx"),
    ("beautifulsoup4", "bs4"),
    ("html2text", "html2text"),
    ("lxml", "lxml"),
    ("trafilatura", "trafilatura"),
    ("pypdf", "pypdf"),
    ("python-docx", "docx"),
    ("openpyxl", "openpyxl"),
    ("python-pptx", "pptx"),
    ("watchdog", "watchdog"),
    ("jieba", "jieba"),                                 # 中文分词
    ("readability-lxml", "readability_lxml"),           # 网页正文提取
]

EMBED_MODEL = "BAAI/bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"

# Known MCP config paths per IDE (Windows / macOS / Linux)
CONFIG_LOCATIONS = {
    "Claude Code": {
        "Windows": os.path.expanduser("~/.claude/mcp.json"),
        "Darwin":  os.path.expanduser("~/.claude/mcp.json"),
        "Linux":   os.path.expanduser("~/.claude/mcp.json"),
    },
    "Claude Desktop": {
        "Windows": os.path.expandvars(r"%APPDATA%\Claude\claude_desktop_config.json"),
        "Darwin":  os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json"),
        "Linux":   os.path.expanduser("~/.config/Claude/claude_desktop_config.json"),
    },
    "Windsurf": {
        "Windows": os.path.expanduser("~/.codeium/windsurf/mcp_config.json"),
        "Darwin":  os.path.expanduser("~/.codeium/windsurf/mcp_config.json"),
        "Linux":   os.path.expanduser("~/.codeium/windsurf/mcp_config.json"),
    },
    "Antigravity": {
        "Windows": os.path.expandvars(r"%USERPROFILE%\.gemini\antigravity\mcp_config.json"),
        "Darwin":  os.path.expanduser("~/.gemini/antigravity/mcp_config.json"),
        "Linux":   os.path.expanduser("~/.gemini/antigravity/mcp_config.json"),
    },
}


# ──────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────

def _is_installed(import_name):
    """Check if a Python package is installed and importable."""
    try:
        importlib.metadata.version(import_name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def _model_cached(model_id):
    """Check if a HuggingFace model is already cached locally."""
    model_dir = model_id.replace("/", "--")
    cache_base = Path.home() / ".cache" / "huggingface" / "hub"
    model_path = cache_base / f"models--{model_dir}"
    if model_path.is_dir():
        snapshots = list(model_path.glob("snapshots/*"))
        if snapshots:
            return True
    return False


# ──────────────────────────────────────────────
# step 0: scan
# ──────────────────────────────────────────────

def scan_environment():
    """Pre-scan: check every dependency and report status.

    Returns a dict with all detection results, so subsequent steps
    can skip what's already installed.
    """
    print("Scanning environment...\n")

    status = {"packages": {}, "torch": False, "models": {}, "mcp": []}

    # --- pip packages ---
    print("  pip packages:")
    missing = []
    for pkg_name, import_name in PACKAGES:
        ok = _is_installed(import_name)
        status["packages"][pkg_name] = ok
        mark = "✓" if ok else "✗ (需要安装)"
        print(f"    [{mark}] {pkg_name}")
        if not ok:
            missing.append(pkg_name)

    # --- torch ---
    print()
    try:
        import torch  # noqa: F401
        status["torch"] = True
        device = "CUDA" if torch.cuda.is_available() else ("MPS" if torch.backends.mps.is_available() else "CPU")
        print(f"  [{chr(10003)}] PyTorch ({device})")
    except ImportError:
        status["torch"] = False
        print(f"  [✗] PyTorch (需要安装)")

    # --- AI models ---
    print()
    for model_id, label in [(EMBED_MODEL, "嵌入模型"), (RERANK_MODEL, "重排序模型")]:
        cached = _model_cached(model_id)
        status["models"][model_id] = cached
        mark = "✓ (已缓存)" if cached else "✗ (需要下载 ~1.1GB)"
        print(f"  [{mark}] {model_id}")

    # --- MCP config ---
    print()
    found = _detect_existing_configs()
    status["mcp"] = found
    if found:
        print(f"  [✓] 检测到 {len(found)} 个 IDE 配置文件")
        for ide, path in found:
            print(f"      - {ide}: {path}")
    else:
        print(f"  [!] 未检测到 IDE 配置文件（将在后续步骤手动配置）")

    return status, missing


# ──────────────────────────────────────────────
# step 1: python version
# ──────────────────────────────────────────────

def check_python():
    version = sys.version_info
    if version < REQUIRED_PYTHON:
        print(f"  ERROR: Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ required.")
        print(f"         You have Python {version.major}.{version.minor}")
        sys.exit(1)
    print(f"  [OK] Python {version.major}.{version.minor}.{version.micro}")


# ──────────────────────────────────────────────
# step 2: pip packages
# ──────────────────────────────────────────────

def install_packages(status, force=False):
    """Install pip packages. Skips already-installed ones unless --force."""
    print("\n[2/4] Installing Python packages...")

    if force:
        # Force reinstall everything
        req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
        if os.path.exists(req_file):
            print("  --force: reinstalling all packages...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", req_file, "--force-reinstall", "--quiet"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"FAILED\n{result.stderr}")
                sys.exit(1)
            print("  [OK] All packages force-reinstalled.")
            return

    # Collect missing packages
    missing = [name for name, _ in PACKAGES if not status["packages"].get(name, False)]

    if not missing:
        print("  [OK] All packages already installed — skipping.")
        return

    print(f"  {len(missing)} package(s) to install: {', '.join(missing)}")
    print()

    # Install missing via pip
    for pkg_name in missing:
        print(f"  Installing {pkg_name}...", end=" ", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_name, "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print("OK")
        else:
            print(f"FAILED\n{result.stderr}")
            sys.exit(1)

    print(f"\n  [OK] {len(missing)} package(s) installed.")


# ──────────────────────────────────────────────
# step 2.5: pytorch
# ──────────────────────────────────────────────

def try_install_torch_cuda(status, force=False):
    """Install PyTorch if missing. Detects GPU and picks CUDA/MPS/CPU."""
    print("\n[2.5/4] Checking PyTorch...")

    if status["torch"] and not force:
        print("  [OK] PyTorch already installed — skipping.")
        return

    if force and status["torch"]:
        print("  --force: reinstalling PyTorch...")

    try:
        import torch
        if torch.cuda.is_available() and not force:
            print("  [OK] PyTorch with CUDA already installed.")
            return
        elif torch.backends.mps.is_available() and not force:
            print("  [OK] PyTorch with MPS already installed.")
            return
    except ImportError:
        pass

    install_cuda = False
    torch_install_cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"]

    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["wmic", "path", "Win32_VideoController", "get", "Name"],
                capture_output=True, text=True, check=False
            )
            if "NVIDIA" in result.stdout:
                print("  NVIDIA GPU detected.")
                install_cuda = True
        except FileNotFoundError:
            pass
    elif platform.system() == "Linux":
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print("  NVIDIA GPU detected.")
                install_cuda = True
        except FileNotFoundError:
            pass
    elif platform.system() == "Darwin":
        print("  macOS — using MPS if available.")

    if install_cuda:
        torch_install_cmd += ["--index-url", "https://download.pytorch.org/whl/cu118"]
    else:
        torch_install_cmd += ["--index-url", "https://download.pytorch.org/whl/cpu"]

    torch_install_cmd += ["--quiet"]
    if force:
        torch_install_cmd.insert(4, "--force-reinstall")

    print(f"  Installing PyTorch ({'CUDA' if install_cuda else 'CPU'})...")
    result = subprocess.run(torch_install_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("  [OK] PyTorch installed.")
    else:
        print(f"  [WARN] PyTorch install failed:\n{result.stderr}")
        print("  CPU fallback will still work. GPU acceleration won't be available.")


# ──────────────────────────────────────────────
# step 3: AI models
# ──────────────────────────────────────────────

def _try_download_hf(model_id, status, force):
    """Try downloading a model from HuggingFace via sentence-transformers.

    Returns True on success, False on failure.
    """
    if status["models"].get(model_id, False) and not force:
        print(f"        {model_id} — cached, skipping.")
        return True

    from sentence_transformers import SentenceTransformer, CrossEncoder

    if "reranker" in model_id.lower():
        CrossEncoder(model_id)
    else:
        SentenceTransformer(model_id)
    return True


def _try_download_modelscope(model_id, cache_dir):
    """Try downloading a model from ModelScope (mirror accessible from mainland China).

    Downloads the model from modelscope.cn and symlinks/copies it into the
    HuggingFace cache directory so sentence-transformers can find it.

    Returns True on success, False on failure.
    """
    try:
        from modelscope import snapshot_download
    except ImportError:
        print("        modelscope not installed, trying pip install modelscope...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "modelscope", "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print("        Failed to install modelscope.")
            return False
        from modelscope import snapshot_download

    try:
        print(f"        Downloading from ModelScope: {model_id}...", flush=True)
        local_path = snapshot_download(model_id, cache_dir=cache_dir)
        if local_path:
            print(f"        Done. -> {local_path}")
            return True
    except Exception as e:
        print(f"        ModelScope download failed: {e}")
    return False


def _hf_cache_dir():
    """Return the HuggingFace cache directory."""
    return os.path.join(str(Path.home()), ".cache", "huggingface", "hub")


def download_models(status, force=False):
    """Download AI models. Tries HuggingFace first, falls back to ModelScope mirror.

    Skips cached models unless --force.
    """
    print("\n[3/4] AI models...")

    both_cached = all(status["models"].values())

    if both_cached and not force:
        print("  [OK] Both models already cached — skipping.")
        print(f"       {EMBED_MODEL}")
        print(f"       {RERANK_MODEL}")
        return

    if force:
        print("  --force: re-downloading models...")
        print()

    print("  Models to download (~2.3GB total, one-time):")
    for model_id, label in [(EMBED_MODEL, "嵌入"), (RERANK_MODEL, "重排序")]:
        cached = status["models"].get(model_id, False)
        skip_mark = " (已缓存 — 跳过)" if cached and not force else " (~1.1GB)"
        print(f"    - {model_id}  [{label}{skip_mark}]")

    print()
    print("  Download source priority: HuggingFace -> ModelScope (国内镜像)")
    print()

    # --- Try HuggingFace first ---
    hf_ok = True
    try:
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

        print("  [1/2] Trying HuggingFace...", flush=True)
        if not status["models"].get(EMBED_MODEL, False) or force:
            print(f"        Downloading {EMBED_MODEL}...", flush=True)
            _try_download_hf(EMBED_MODEL, status, force)
        else:
            print(f"        {EMBED_MODEL} — cached, skipping.")

        if not status["models"].get(RERANK_MODEL, False) or force:
            print(f"        Downloading {RERANK_MODEL}...", flush=True)
            _try_download_hf(RERANK_MODEL, status, force)
        else:
            print(f"        {RERANK_MODEL} — cached, skipping.")

        print("        HuggingFace download complete.")

    except Exception as e:
        hf_ok = False
        print(f"        HuggingFace failed: {e}")
        print()
        print("  [2/2] Falling back to ModelScope (国内镜像)...")

        hf_cache = _hf_cache_dir()
        ms_ok = True
        for model_id, label in [(EMBED_MODEL, "嵌入"), (RERANK_MODEL, "重排序")]:
            if status["models"].get(model_id, False) and not force:
                print(f"        {model_id} — cached, skipping.")
                continue
            print(f"        Downloading {model_id} [{label}]...", flush=True)
            if not _try_download_modelscope(model_id, hf_cache):
                ms_ok = False

        if ms_ok:
            print("        ModelScope download complete.")
        else:
            print()
            print("  ╔══════════════════════════════════════════════════════════╗")
            print("  ║  ⚠  自动下载失败 — 请手动下载模型                      ║")
            print("  ╠══════════════════════════════════════════════════════════╣")
            print("  ║                                                        ║")
            print("  ║  方法 1: 配置代理后重试                                 ║")
            print("  ║    set HTTP_PROXY=http://127.0.0.1:7890                 ║")
            print("  ║    set HTTPS_PROXY=http://127.0.0.1:7890                ║")
            print("  ║    python install.py --force                            ║")
            print("  ║                                                        ║")
            print("  ║  方法 2: 从 ModelScope 手动下载                         ║")
            print("  ║    https://modelscope.cn/models/BAAI/bge-m3             ║")
            print("  ║    https://modelscope.cn/models/BAAI/bge-reranker-v2-m3 ║")
            print("  ║    下载后放入:                                          ║")
            print(f"  ║    {hf_cache}                                          ║")
            print("  ║                                                        ║")
            print("  ╚══════════════════════════════════════════════════════════╝")
            return

    # If HuggingFace succeeded, we're done
    if hf_ok:
        return

    # Verify models are now cached
    for model_id in [EMBED_MODEL, RERANK_MODEL]:
        if not _model_cached(model_id):
            print(f"  [!] Warning: {model_id} may not be cached correctly.")
            print(f"       server.py will attempt to download on first start.")


# ──────────────────────────────────────────────
# step 4: MCP config
# ──────────────────────────────────────────────

def _build_server_entry():
    """Build the MCP config entry with real absolute paths."""
    server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "server.py"))
    python_path = sys.executable
    return {
        "command": python_path if platform.system() == "Windows" else "python",
        "args": [server_path],
    }


def _detect_existing_configs():
    """Detect which IDE config files already exist on disk."""
    system = platform.system()
    found = []
    for ide_name, paths in CONFIG_LOCATIONS.items():
        path = paths.get(system)
        if path and os.path.isfile(path):
            found.append((ide_name, path))
    return found


def _inject_into_config(config_path, entry):
    """Read existing MCP config, inject 'omnidocs-rag-cn' entry, write back."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["omnidocs-rag-cn"] = entry

    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return True


def auto_configure(status, yes_mode=False):
    """Auto-detect IDEs and offer to inject MCP config. Skips if already configured.

    Args:
        status: scan_environment() result dict
        yes_mode: if True, skip all interactive prompts (CI / scripted deploy)
    """
    print("\n[4/4] Configuring MCP connection...")

    entry = _build_server_entry()
    server_path = entry["args"][0]

    found = status.get("mcp", [])
    if not found:
        found = _detect_existing_configs()

    if found:
        print(f"\n  检测到 {len(found)} 个 IDE 配置文件:\n")
        for i, (ide, path) in enumerate(found, 1):
            print(f"    {i}. {ide}: {path}")

        print()
        for ide, path in found:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing_entry = existing.get("mcpServers", {}).get("omnidocs-rag-cn")

                if existing_entry:
                    existing_path = existing_entry.get("args", [""])[0]
                    if os.path.normpath(existing_path) == os.path.normpath(server_path):
                        print(f"  [OK] {ide} — 已配置，跳过.")
                        continue
                    print(f"  [!!] {ide} — 'omnidocs-rag-cn' 已存在但指向不同路径:")
                    print(f"       当前: {existing_path}")
                    print(f"       新的: {server_path}")
                    if yes_mode:
                        print(f"       --yes: 自动覆盖.")
                    else:
                        try:
                            answer = input(f"       覆盖? (y/N): ").strip().lower()
                        except (EOFError, OSError):
                            print("       非交互环境，跳过。使用 --yes 强制覆盖。")
                            continue
                        if answer != "y":
                            print(f"       跳过.")
                            continue
                else:
                    if yes_mode:
                        print(f"  [--yes] 添加 'omnidocs-rag-cn' 到 {ide}...")
                    else:
                        try:
                            answer = input(f"  添加 'omnidocs-rag-cn' 到 {ide}? (Y/n): ").strip().lower()
                        except (EOFError, OSError):
                            print("       非交互环境，跳过。使用 --yes 强制覆盖。")
                            continue
                        if answer == "n":
                            print(f"       跳过.")
                            continue

                _inject_into_config(path, entry)
                print(f"  [OK] {ide} — 配置已更新!")

            except Exception as e:
                print(f"  [!!] {ide} — 配置失败: {e}")
                print(f"       请手动添加到: {path}")
    else:
        print("  未自动检测到 IDE 配置文件。")

    # --- Always show manual config ---
    server_path = entry["args"][0]
    command = entry["command"]

    if platform.system() == "Windows":
        server_display = server_path.replace("\\", "\\\\")
        command_display = command.replace("\\", "\\\\")
    else:
        server_display = server_path
        command_display = command

    manual_config = f'''{{
  "mcpServers": {{
    "omnidocs-rag-cn": {{
      "command": "{command_display}",
      "args": ["{server_display}"]
    }}
  }}
}}'''

    print("\n" + "=" * 60)
    print("  安装完成!")
    print("=" * 60)

    if found:
        print(f"\n  MCP 配置已注入 {len(found)} 个 IDE。重启 IDE 即可使用!\n")
    else:
        print("\n  手动配置: 将以下内容复制到 IDE 的 MCP 配置文件中:\n")
        print(manual_config)
        print("\n  配置文件位置:")
        if platform.system() == "Windows":
            print(r"    Claude Code : %USERPROFILE%\.claude\mcp.json")
            print(r"    Claude      : %APPDATA%\Claude\claude_desktop_config.json")
            print(r"    Windsurf    : %USERPROFILE%\.codeium\windsurf\mcp_config.json")
        else:
            print("    Claude Code : ~/.claude/mcp.json")
            print("    Claude      : ~/Library/Application Support/Claude/claude_desktop_config.json")
            print("    Windsurf    : ~/.codeium/windsurf/mcp_config.json")
        print()

    print("  接下来做什么:")
    print("    1. 重启你的 IDE")
    print('    2. 对 AI Agent 说: "帮我索引我的文档目录"')
    print('    3. 然后说: "搜索: RAG 的搜索管道是怎么工作的?"')
    print()
    print("  💡 提示: python manage.py status 可查看索引进度")
    print("=" * 60)


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────

if __name__ == "__main__":
    force = "--force" in sys.argv
    yes_mode = "--yes" in sys.argv or "-y" in sys.argv

    print("=" * 60)
    print("  OmniDocs-RAG-CN — 一键安装")
    print("=" * 60)

    if force:
        print("\n  ⚡ --force 模式: 将强制重装所有依赖")
    if yes_mode:
        print("  🤖 --yes 模式: 跳过所有交互确认")

    if force or yes_mode:
        print()

    print("\n[0/4] 检测已安装的依赖...")
    status, missing = scan_environment()

    if not force and not missing and status["torch"] and all(status["models"].values()):
        print("\n" + "=" * 60)
        print("  🎉 所有依赖已就绪，无需安装!")
        print("=" * 60)
        print("\n  如需强制重装: python install.py --force")
        print()
        # Still run MCP config check
        auto_configure(status, yes_mode=yes_mode)
        sys.exit(0)

    print(f"\n  {'─' * 40}")
    print(f"  需要安装: {len(missing)} 个 pip 包"
          + ("" if status["torch"] else " + PyTorch")
          + (" + 模型下载" if not all(status["models"].values()) else ""))
    print(f"  {'─' * 40}")

    print("\n[1/4] Checking Python version...")
    check_python()
    install_packages(status, force=force)
    try_install_torch_cuda(status, force=force)
    download_models(status, force=force)
    auto_configure(status, yes_mode=yes_mode)
