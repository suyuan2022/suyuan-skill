#!/usr/bin/env python3
"""在 macOS 上审计并安全清理 Claude Code / Claude Desktop 本机状态。"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import contextlib
import datetime as dt
import glob
import json
import os
import pathlib
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile

TELEMETRY_KEYS = ("DISABLE_TELEMETRY", "DO_NOT_TRACK", "DISABLE_ERROR_REPORTING", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")
ACCOUNT_CACHE_KEYS = {
    "additionalModelCostsCache", "additionalModelOptionsCache", "anonymousId", "autoCompactWindowsCache",
    "cachedChromeExtensionInstalled", "cachedDynamicConfigs", "cachedExperimentData", "cachedExperimentFeatures",
    "cachedExtraUsageDisabledReason", "cachedGrowthBookFeatures", "cachedGrowthBookFeaturesAt", "cachedStatsigGates",
    "clientDataCache", "clientDataCacheSlots", "feedbackSurveyState", "groveConfigCache", "metricsStatusCache",
    "modelAccessCache", "oauthAccount", "orgModelDefaultCache", "passesEligibilityCache", "s1mAccessCache",
}
PROTECTED = {
    "CLAUDE.md", "agents", "backups", "commands", "debug", "file-history", "history.jsonl", "hooks",
    "mcp-servers", "plans", "plugins", "projects", "scheduled-tasks", "scripts", "session-env", "sessions", "settings.json",
    "settings.local.json", "skills", "tasks", "todos",
}
# usage-data 不在这里：官方文档说它存的是 /insights 生成的报告，不是纯缓存
CLI_CACHE = ("cache", "stats-cache.json", "telemetry", "usage.jsonl", "usage.with-fix.jsonl")
SAFE_RELATIVE = ("Library/Caches/claude-cli-nodejs", "Library/Logs/Claude")
SAFE_GLOBS = (
    "Library/Caches/com.anthropic.claudefordesktop*", "Library/Logs/DiagnosticReports/Claude*",
    "Library/Application Support/CrashReporter/Claude*",
)
DESKTOP_RELATIVE = (
    "Library/Application Support/Claude", "Library/Application Support/Claude-3p",
    "Library/Application Support/com.anthropic.claudefordesktop",
    "Library/HTTPStorages/com.anthropic.claudefordesktop",
    "Library/Preferences/com.anthropic.claudefordesktop.plist",
    "Library/Saved Application State/com.anthropic.claudefordesktop.savedState",
    "Library/WebKit/com.anthropic.claudefordesktop",
)
DESKTOP_GLOBS = ("Library/Preferences/ByHost/com.anthropic.claudefordesktop*.plist",)
APP = pathlib.Path("/Applications/Claude.app")
# 上下文瘦身只读报告用到的设置项；ANTHROPIC_BASE_URL 只报告有没有设，不打印值
CONTEXT_ENV_KEYS = (
    "ENABLE_TOOL_SEARCH", "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS", "ENABLE_LSP_TOOL",
    "ENABLE_CLAUDEAI_MCP_SERVERS", "CLAUDE_CODE_DISABLE_BUNDLED_SKILLS", "CLAUDE_CODE_SIMPLE",
)
SKILLS_PLUGIN_GLOB = "local-agent-mode-sessions/skills-plugin/*/*/manifest.json"
# Windows 商店（MSIX）版的包名：它写 %APPDATA% 会被重定向到 %LOCALAPPDATA%\Packages\<包名>\LocalCache\Roaming
MSIX_PACKAGES = ("Claude_pzs8sxrjxfjjc", "AnthropicPBC.Claude_fnn82j28hfe8t")
WHAT_IF_DENY = ("ScheduleWakeup", "ListAgents", "LSP", "PowerShell")


def read_json(path: pathlib.Path, default: object | None = None) -> object:
    if not path.exists() and default is not None:
        return default
    # utf-8-sig：Windows 记事本和 PowerShell 5.1 存的 UTF-8 常带 BOM
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: pathlib.Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = pathlib.Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def settings_env(data: object) -> dict[str, object]:
    if not isinstance(data, dict) or not isinstance(data.get("env", {}), dict):
        raise ValueError("settings.json 的顶层或 env 结构异常，拒绝修改")
    return data.get("env", {})


def telemetry(data: object) -> dict[str, object | None]:
    env = settings_env(data)
    return {key: env.get(key) for key in TELEMETRY_KEYS}


def discover(home: pathlib.Path) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    claude = home / ".claude"
    safe = [claude / name for name in CLI_CACHE]
    safe += [home / name for name in SAFE_RELATIVE]
    desktop = [home / name for name in DESKTOP_RELATIVE]
    for pattern in SAFE_GLOBS:
        safe += map(pathlib.Path, glob.glob(str(home / pattern)))
    for pattern in DESKTOP_GLOBS:
        desktop += map(pathlib.Path, glob.glob(str(home / pattern)))
    safe = {p for p in safe if p.exists() or p.is_symlink()}
    desktop = {p for p in desktop if p.exists() or p.is_symlink()}
    return sorted(safe, key=str), sorted(desktop, key=str)


def claude_processes() -> list[str]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,comm=,args="], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    found = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) < 2 or parts[0] == str(os.getpid()):
            continue
        command = pathlib.Path(parts[1]).name.lower()
        args = parts[2] if len(parts) == 3 else ""
        first = pathlib.Path(args.split(maxsplit=1)[0]).name.lower() if args else ""
        if command in {"claude", "claude-code"} or first in {"claude", "claude-code"} or "/Claude.app/" in args:
            found.append(line.strip())
    return found


def running_under_claude() -> bool:
    pid = os.getppid()
    for _ in range(12):
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "ppid=,comm=,args="], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
        parts = result.stdout.strip().split(maxsplit=2)
        if len(parts) < 2:
            return False
        command = pathlib.Path(parts[1]).name.lower()
        first = pathlib.Path(parts[2].split(maxsplit=1)[0]).name.lower() if len(parts) == 3 else ""
        if command in {"claude", "claude-code"} or first in {"claude", "claude-code"}:
            return True
        next_pid = int(parts[0])
        if next_pid <= 1 or next_pid == pid:
            return False
        pid = next_pid
    return False


def current_timezone() -> str:
    try:
        target = pathlib.Path("/etc/localtime").readlink().as_posix()
    except OSError:
        return "未知"
    return target.split("/zoneinfo/", 1)[1] if "/zoneinfo/" in target else "未知"


def create_backup(home: pathlib.Path) -> pathlib.Path:
    claude, identity = home / ".claude", home / ".claude.json"
    if not claude.is_dir():
        raise FileNotFoundError("~/.claude 不存在，无法满足先全量备份的硬要求")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    partial = home / "ClaudeBackups" / f"claude-cleanup-{stamp}.partial"
    final = partial.with_suffix("")
    partial.mkdir(parents=True)
    shutil.copytree(claude, partial / "dot-claude", symlinks=True)

    def stats(root: pathlib.Path) -> tuple[int, int]:
        regular = [p for p in root.rglob("*") if p.is_file() and not p.is_symlink()]
        return len(regular), sum(p.stat().st_size for p in regular)

    if stats(claude) != stats(partial / "dot-claude"):
        raise RuntimeError(f"~/.claude 备份校验失败，保留未完成副本：{partial}")
    copied_identity = False
    if identity.is_file():
        shutil.copy2(identity, partial / "claude.json")
        copied_identity = identity.stat().st_size == (partial / "claude.json").stat().st_size
        if not copied_identity:
            raise RuntimeError(f"~/.claude.json 备份校验失败，保留未完成副本：{partial}")
    files, bytes_ = stats(claude)
    write_json(partial / "manifest.json", {"files": files, "regularFileBytes": bytes_, "claudeJsonCopied": copied_identity})
    partial.rename(final)
    return final


def move_to_trash(target: pathlib.Path, allowed: set[pathlib.Path], claude: pathlib.Path, batch: pathlib.Path) -> pathlib.Path:
    absolute = target.absolute()
    protected = {claude / name for name in PROTECTED}
    if absolute == claude.absolute() or any(absolute == p.absolute() or p.absolute() in absolute.parents for p in protected):
        raise RuntimeError(f"拒绝触碰受保护路径：{target}")
    if absolute not in {path.absolute() for path in allowed}:
        raise RuntimeError(f"目标不在删除白名单：{target}")
    batch.mkdir(parents=True, exist_ok=True)
    destination = batch / f"{len(list(batch.iterdir())):02d}-{target.name}"
    shutil.move(str(target), str(destination))
    return destination


def rotate_identity(home: pathlib.Path) -> int:
    identity, backups = home / ".claude.json", home / ".claude/backups"
    if not identity.is_file():
        raise FileNotFoundError("~/.claude.json 不存在，无法轮换本地 ID")
    files = [identity]
    if backups.is_dir():
        files += sorted(p for p in backups.glob(".claude.json.backup.*") if p.is_file() and not p.is_symlink())
    ids, prepared = {"userID": secrets.token_hex(32), "machineID": secrets.token_hex(32)}, []
    for path in files:
        data = read_json(path)
        if not isinstance(data, dict):
            raise ValueError(f"身份文件不是 JSON object：{path}")
        updated = dict(data)
        updated.update(ids)
        for key in ACCOUNT_CACHE_KEYS:
            updated.pop(key, None)
        prepared.append((path, updated))
    for path, data in prepared:
        write_json(path, data)
    return len(files) - 1


def config_dir(home: pathlib.Path) -> pathlib.Path:
    """~/.claude 的实际位置（Windows 上 ~ 是 %USERPROFILE%）；设了 CLAUDE_CONFIG_DIR 就以它为准。"""
    custom = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return pathlib.Path(custom) if custom else home / ".claude"


def global_config(home: pathlib.Path) -> pathlib.Path:
    """存 MCP 服务器和账号状态的 .claude.json，跟着 CLAUDE_CONFIG_DIR 走，否则在主目录下。"""
    custom = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return (pathlib.Path(custom) if custom else home) / ".claude.json"


def desktop_data_dirs(home: pathlib.Path) -> list[pathlib.Path]:
    """Claude 桌面版数据目录（Electron 的 userData）的候选位置。"""
    dirs = [pathlib.Path(os.environ["CLAUDE_USER_DATA_DIR"])] if os.environ.get("CLAUDE_USER_DATA_DIR") else []
    if sys.platform == "win32":
        appdata, local = os.environ.get("APPDATA"), os.environ.get("LOCALAPPDATA")
        if appdata:
            dirs.append(pathlib.Path(appdata) / "Claude")
        if local:
            dirs.append(pathlib.Path(local) / "Claude-3p")
            dirs += [pathlib.Path(local) / "Packages" / package / "LocalCache" / "Roaming" / "Claude" for package in MSIX_PACKAGES]
        if appdata:
            dirs.append(pathlib.Path(appdata) / "Claude-3p")  # 旧版本放过这里
    else:
        support = home / "Library" / "Application Support"
        dirs += [support / "Claude", support / "Claude-3p"]
    return dirs


def scan_usage(home: pathlib.Path, days: int) -> dict:
    """统计近 days 天会话日志里每个工具和 skill 的调用次数、会话数和最近日期；first 是统计到的最早日期。"""
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    since = cutoff.strftime("%Y-%m-%d")
    usage: dict = {"tools": {}, "skills": {}, "first": ""}

    def record(kind: str, name: object, session: str, day: str) -> None:
        if not isinstance(name, str) or not name:
            return
        item = usage[kind].setdefault(name, {"calls": 0, "sessions": set(), "last": ""})
        item["calls"] += 1
        item["sessions"].add(session)
        item["last"] = max(item["last"], day)
        if day and (not usage["first"] or day < usage["first"]):
            usage["first"] = day

    root = config_dir(home) / "projects"
    for path in root.rglob("*.jsonl") if root.is_dir() else []:
        try:
            if path.stat().st_mtime < cutoff.timestamp():
                continue
        except OSError:
            continue
        parts = path.parts
        # 子 agent 日志在 <会话>/subagents/ 下，记到所属会话
        session = str(pathlib.Path(*parts[: parts.index("subagents")])) if "subagents" in parts else str(path.with_suffix(""))
        try:
            handle = path.open("rb")
        except OSError:  # 比如 Windows 上路径超长又没开长路径支持
            continue
        with handle:
            for raw in handle:
                if b'"tool_use"' not in raw and b"<command-name>" not in raw:
                    continue
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                day = str(entry.get("timestamp", ""))[:10]
                if day and day < since:
                    continue
                message = entry.get("message")
                content = message.get("content") if isinstance(message, dict) else None
                if entry.get("type") == "assistant" and isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name, inputs = block.get("name"), block.get("input")
                            record("tools", name, session, day)
                            if not isinstance(inputs, dict):
                                continue
                            if name == "Skill":
                                record("skills", inputs.get("skill"), session, day)
                            # 被别的 skill 照着读的，也算用过一次；Windows 路径用反斜杠
                            elif name == "Read":
                                file_path = str(inputs.get("file_path", "")).replace("\\", "/")
                                if file_path.endswith("/SKILL.md"):
                                    record("skills", file_path.rsplit("/", 2)[-2], session, day)
                elif entry.get("type") == "user":
                    text = content if isinstance(content, str) else next(
                        (b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text"), ""
                    )
                    if text.startswith("<command-name>"):
                        name = text[len("<command-name>"):].split("</command-name>", 1)[0].lstrip("/")
                        record("skills", name, session, day)
    return usage


def coverage(first: str, days: int) -> str:
    if not first:
        return f"近 {days} 天没有会话记录"
    return f"最早一条记录在 {first}，距今 {(dt.date.today() - dt.date.fromisoformat(first)).days} 天"


def usage_line(item: dict | None) -> str:
    if not item:
        return "0 次"
    return f"{item['calls']} 次 / {len(item['sessions'])} 个会话 / 最近 {item['last'] or '未知'}"


def skill_meta(skill_md: pathlib.Path) -> tuple[str, bool]:
    """返回 skill 名，以及它是否只能手动触发（disable-model-invocation，不占开局上下文）。"""
    front = skill_md.read_text(encoding="utf-8", errors="replace").split("\n---", 1)[0]
    match = re.search(r"^name:\s*(.+?)\s*$", front, re.M)
    manual = re.search(r"^disable-model-invocation:\s*true\s*$", front, re.M | re.I) is not None
    return (match.group(1).strip("'\"") if match else skill_md.parent.name), manual


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def reference_texts(home: pathlib.Path) -> tuple[dict[str, str], dict[str, str]]:
    """可能引用 skill 的文本。定时任务里名字出现就算；CLAUDE.md、agent、命令、skill 里要带 ` 或 / 才算。"""
    claude = config_dir(home)
    tasks = {f"定时任务 {p.parent.name}": read_text(p) for p in sorted((claude / "scheduled-tasks").glob("*/SKILL.md"))}
    others = {f"agent {p.stem}": read_text(p) for p in sorted((claude / "agents").glob("*.md"))}
    others.update({f"命令 {p.stem}": read_text(p) for p in sorted((claude / "commands").rglob("*.md"))})
    if (claude / "CLAUDE.md").is_file():
        others["CLAUDE.md"] = read_text(claude / "CLAUDE.md")
    others.update({f"skill {skill_meta(p)[0]}": read_text(p) for p in sorted((claude / "skills").glob("*/SKILL.md"))})
    return tasks, others


def find_refs(name: str, tasks: dict[str, str], others: dict[str, str]) -> list[str]:
    escaped = re.escape(name)
    hits = [label for label, text in tasks.items() if re.search(rf"(?<![\w-]){escaped}(?![\w-])", text)]
    hits += [label for label, text in others.items() if label != f"skill {name}" and re.search(rf"[`/]{escaped}(?![\w-])", text)]
    return hits


def installed_skills(home: pathlib.Path) -> list[dict]:
    """列出 ~/.claude/skills 下的 skill，并找出提到它的定时任务、CLAUDE.md、agent、命令和其他 skill。"""
    root = config_dir(home) / "skills"
    found = []
    for child in sorted(root.iterdir()) if root.is_dir() else []:
        skill_md = child / "SKILL.md"
        if skill_md.is_file():
            name, manual = skill_meta(skill_md)
            found.append({"name": name, "path": skill_md, "manual": manual})
    tasks, others = reference_texts(home)
    for item in found:
        item["refs"] = find_refs(item["name"], tasks, others)
    return found


def desktop_skill_plugin(home: pathlib.Path) -> tuple[pathlib.Path | None, list[tuple[str, bool]]]:
    """桌面版把账号同步的 skill 挂成插件 anthropic-skills；返回最新的插件目录和清单。"""
    manifests = sorted((path for base in desktop_data_dirs(home) for path in base.glob(SKILLS_PLUGIN_GLOB)), key=os.path.getmtime)
    if not manifests:
        return None, []
    manifest = manifests[-1]
    data = read_json(manifest, {})
    entries = data.get("skills", []) if isinstance(data, dict) else []
    return manifest.parent, [(str(s.get("name")), bool(s.get("enabled"))) for s in entries if isinstance(s, dict)]


def context_report(home: pathlib.Path, settings_data: dict, days: int, usage: dict) -> list[str]:
    env = settings_env(settings_data)
    tools, skills = usage["tools"], usage["skills"]
    plugins = settings_data.get("enabledPlugins") or {}
    deny = (settings_data.get("permissions") or {}).get("deny") or []
    retention = settings_data.get("cleanupPeriodDays", "未设置（默认 30 天）")
    claude = config_dir(home)
    desktop_dir = next((path for path in desktop_data_dirs(home) if path.is_dir()), None)
    lines = [
        f"上下文瘦身只读报告（近 {days} 天会话日志）",
        f"日志实际覆盖：{coverage(usage['first'], days)}；日志保留期 cleanupPeriodDays：{retention}",
        "",
        "配置位置：",
        f"- 用户设置：{claude / 'settings.json'}",
        f"- 全局配置（MCP 服务器、账号）：{global_config(home)}",
        f"- 会话日志：{claude / 'projects'}",
        f"- 桌面版数据：{desktop_dir or '没找到'}",
        "",
        "设置现状：",
    ]
    lines += [f"- env.{key}：{env.get(key, '未设置')}" for key in CONTEXT_ENV_KEYS]
    lines.append(f"- env.ANTHROPIC_BASE_URL：{'已设置（走自定义网关或代理）' if env.get('ANTHROPIC_BASE_URL') else '未设置'}")
    lines.append(f"- enableArtifact：{settings_data.get('enableArtifact', '未设置')}")
    lines.append(f"- disableClaudeAiConnectors：{settings_data.get('disableClaudeAiConnectors', '未设置')}")
    lines.append(f"- enabledPlugins：{json.dumps(plugins, ensure_ascii=False) if plugins else '无'}")
    lines.append(f"- permissions.deny：{', '.join(map(str, deny)) or '无'}")

    servers: dict[str, dict] = collections.defaultdict(lambda: {"calls": 0, "sessions": set(), "last": ""})
    for name, item in tools.items():
        if name.startswith("mcp__") and name.count("__") >= 2:
            server = servers[name.split("__")[1]]
            server["calls"] += item["calls"]
            server["sessions"] |= item["sessions"]
            server["last"] = max(server["last"], item["last"])
    identity = read_json(global_config(home), {})
    configured = set((identity.get("mcpServers") or {}) if isinstance(identity, dict) else {})
    lines += ["", "MCP 服务器（用户级配置的，加上日志里出现过的）："]
    for name in sorted(configured | set(servers)):
        source = "用户级配置" if name in configured else "app 或项目提供"
        lines.append(f"- {name}（{source}）：{usage_line(servers.get(name))}")
    if not configured | set(servers):
        lines.append("- 无")

    lines += ["", "内置工具调用（按会话数从多到少）："]
    builtin = sorted(((n, i) for n, i in tools.items() if not n.startswith("mcp__")), key=lambda pair: -len(pair[1]["sessions"]))
    lines += [f"- {name}：{usage_line(item)}" for name, item in builtin] or ["- 无"]

    overrides = settings_data.get("skillOverrides") or {}
    found = installed_skills(home)
    found.sort(key=lambda s: (len((skills.get(s["name"]) or {}).get("sessions", ())), (skills.get(s["name"]) or {}).get("last", "")))
    lines += [
        "",
        "用户 skill（~/.claude/skills，按会话数从少到多）：",
        "［］里是 skillOverrides 状态；用量 = Skill 调用 + 斜杠命令 + 用 Read 读它的 SKILL.md；「被提到」= 提到它的定时任务、CLAUDE.md、agent、命令和其他 skill",
    ]
    for item in found:
        state = overrides.get(item["name"]) or ("仅手动触发，不占开局" if item["manual"] else "on")
        refs = f"；被提到：{', '.join(item['refs'])}" if item["refs"] else ""
        lines.append(f"- {item['name']}［{state}］：{usage_line(skills.get(item['name']))}{refs}")

    _, desktop = desktop_skill_plugin(home)
    if desktop:
        disabled = plugins.get("anthropic-skills@inline") is False
        state = "整个插件已关，下面这些都不加载" if disabled else "插件开着"
        lines += ["", f"桌面版账号同步的 skill（插件 anthropic-skills@inline，{state}；［］里是 app 设置里的开关）："]
        for name, enabled in desktop:
            lines.append(f"- {name}［app 里{'开着' if enabled else '关了'}］：{usage_line(skills.get('anthropic-skills:' + name))}")
    return lines


def parse_tokens(text: str) -> int:
    match = re.search(r"([\d.]+)\s*([km]?)", text.lower())
    return int(float(match.group(1)) * {"": 1, "k": 1000, "m": 1000000}[match.group(2)]) if match else 0


def format_tokens(tokens: int) -> str:
    return f"{tokens / 1000:.1f}k" if abs(tokens) >= 1000 else str(tokens)


def parse_context(text: str) -> dict[str, list[list[str]]]:
    """把 /context 的 Markdown 表格按小节拆成行，去掉表头和分隔行。"""
    tables: dict[str, list[list[str]]] = collections.defaultdict(list)
    section = ""
    for line in text.splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
        elif line.startswith("|") and not re.fullmatch(r"\|[\s|:-]+\|", line.strip()):
            tables[section].append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return {name: rows[1:] for name, rows in tables.items()}


@contextlib.contextmanager
def scratch_dir(prefix: str):
    """新建的空目录；删不掉也不报错（Windows 上 claude 起的子进程可能还占着它）。"""
    path = tempfile.mkdtemp(prefix=prefix)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
        # claude 会给这个目录在 projects 下建同名文件夹（开着自动记忆时至少有个空的 memory），
        # 在缓存目录里记 MCP 日志，一起删掉。文件夹名是把路径里非字母数字换成 -，按 mkdtemp 的随机后缀匹配，不会碰到别的会话
        suffix = re.sub(r"[^A-Za-z0-9]", "-", pathlib.Path(path).name)
        home = pathlib.Path.home()
        roots = [config_dir(home) / "projects", home / "Library/Caches/claude-cli-nodejs", home / ".cache/claude-cli-nodejs"]
        if os.environ.get("LOCALAPPDATA"):
            roots.append(pathlib.Path(os.environ["LOCALAPPDATA"]) / "claude-cli-nodejs/Cache")
        for root in roots:
            for leftover in root.glob(f"*{suffix}") if root.is_dir() else ():
                shutil.rmtree(leftover, ignore_errors=True)


def claude_exe() -> str:
    """PATH 里没有时，再看安装器的默认位置：新开的终端不一定带上它们。"""
    exe = shutil.which("claude")
    if exe:
        return exe
    home = pathlib.Path.home()
    name = "claude.exe" if sys.platform == "win32" else "claude"
    for candidate in (home / ".local/bin" / name, home / ".claude/local" / name):
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError("找不到 claude 命令（PATH、~/.local/bin、~/.claude/local 都没有）")


def simple_mode(settings_data: dict) -> bool:
    """settings.json 里开了最小模式、而且当前环境没有另行指定（桌面版 app 会把 CLAUDE_CODE_SIMPLE 设成 0）。"""
    value = settings_data.get("env", {}).get("CLAUDE_CODE_SIMPLE") if isinstance(settings_data.get("env"), dict) else None
    return str(value).lower() in {"1", "true", "yes", "on"} and "CLAUDE_CODE_SIMPLE" not in os.environ


def claude_env() -> dict[str, str]:
    """子进程的环境变量。去掉 CLAUDECODE，否则在 Claude Code 里起的子进程会被嵌套保护拦下。
    在 Claude Code 会话里跑时，环境里还带着这个会话启动时套用的 settings env：settings 里改过的值会覆盖它，
    但用户之后删掉的键会带着旧值留下来。所以把当前 settings 和最近一份备份里出现过的键都去掉，让子进程从文件重新读。
    CLAUDE_CODE_SIMPLE 不去掉：桌面版 app 自己设成 0，settings 里的值在桌面版本来就不生效。"""
    env = {key: value for key, value in os.environ.items() if key != "CLAUDECODE"}
    if "CLAUDECODE" not in os.environ:
        return env
    path = config_dir(pathlib.Path.home()) / "settings.json"
    for source in [path, *sorted(path.parent.glob("settings.json.bak-*"))[-1:]]:
        try:
            keys = set(settings_env(read_json(source, {})))
        except (OSError, ValueError):
            continue
        for key in keys - {"CLAUDE_CODE_SIMPLE"}:
            env.pop(key, None)
    return env


def run_claude(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    exe = claude_exe()
    env = claude_env()
    return subprocess.run(
        [exe, "-p", *args, "--no-session-persistence"], capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300, env=env, cwd=cwd, stdin=subprocess.DEVNULL, check=False,
    )


def run_context(extra: list[str], cwd: str) -> str:
    result = run_claude(["/context", *extra], cwd)
    if "### Estimated usage by category" not in result.stdout:
        raise RuntimeError(f"/context 输出异常：{(result.stderr or result.stdout).strip()[:300]}")
    return result.stdout


def probe() -> str:
    """真发一句话，确认当前接口（尤其是自定义网关）能正常回复。"""
    with scratch_dir("claude-probe-") as cwd:
        result = run_claude(["回一个字"], cwd)
    if result.returncode != 0:
        raise RuntimeError(f"claude -p 失败（退出码 {result.returncode}）：{(result.stderr or result.stdout).strip()[:300]}")
    return result.stdout.strip()[:100]


def backup_settings(home: pathlib.Path) -> pathlib.Path | None:
    path = config_dir(home) / "settings.json"
    if not path.exists():
        return None
    settings_env(read_json(path))  # 原文件本身坏了就不备份，先让用户知道
    target = path.with_name(f"settings.json.bak-{dt.datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(path, target)
    return target


def measure_report(home: pathlib.Path, settings_data: dict, usage: dict | None) -> list[str]:
    # 在哪个环境里跑就按哪个环境测：桌面版会话里起的子进程带着 app 注入的环境变量，工具和终端版不一样；
    # 账号同步的 skill 也只在桌面版里挂上
    desktop = "CLAUDECODE" in os.environ and os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "claude-desktop"
    plugin_dir, _ = desktop_skill_plugin(home)
    base = ["--plugin-dir", str(plugin_dir)] if plugin_dir and desktop else []
    permissions = settings_data.get("permissions") if isinstance(settings_data.get("permissions"), dict) else {}
    denied = [tool for tool in WHAT_IF_DENY if tool in (permissions.get("deny") or [])]
    overlays: dict[str, dict] = {}
    artifact_off = settings_data.get("enableArtifact") is False
    if not artifact_off:
        overlays["关 Artifact（enableArtifact: false）"] = {"enableArtifact": False}
    for tool in (tool for tool in WHAT_IF_DENY if tool not in denied):
        overlays[f"禁用 {tool}（permissions.deny）"] = {"permissions": {"deny": [tool]}}
    # 在新建的空目录里跑：直接用系统临时目录本身时有的 MCP 不启动。
    # 基线单独先跑，几个 claude 同时启动时 MCP 可能来不及连上；模拟项只比内置工具，可以并行。
    # Windows 上串行：几个 claude 同时写 .claude.json 时，文件被占用更容易失败。
    with scratch_dir("claude-context-") as cwd:
        whatifs = {}
        for index, (label, overlay) in enumerate(overlays.items()):
            # 叠加设置写成文件再传路径，避免 claude.cmd 经 cmd.exe 转发时 JSON 引号出问题
            overlay_file = pathlib.Path(cwd) / f"whatif-{index}.json"
            overlay_file.write_text(json.dumps(overlay), encoding="utf-8")
            whatifs[label] = ["--settings", str(overlay_file)]
        baseline_text = run_context(base, cwd)
        results = {"基线": parse_context(baseline_text)}
        with concurrent.futures.ThreadPoolExecutor(1 if sys.platform == "win32" else max(1, len(whatifs))) as pool:
            futures = {label: pool.submit(run_context, base + extra, cwd) for label, extra in whatifs.items()}
            results.update({label: parse_context(future.result()) for label, future in futures.items()})

    def categories(label: str) -> dict[str, int]:
        return {row[0]: parse_tokens(row[1]) for row in results[label].get("Estimated usage by category", []) if len(row) >= 2}

    baseline = categories("基线")
    if "System prompt" not in baseline and "System tools" not in baseline:
        shown = "、".join(name for name in baseline if name not in {"Free space", "Autocompact buffer"}) or "空"
        raise RuntimeError(f"/context 只报了 {shown}，没有系统提示词和工具占用，多半是这个 claude 还没登录（--probe 能确认）")
    total = re.search(r"\*\*Tokens:\*\*\s*([\d.]+\s*[km]?)", baseline_text, re.I)
    where = "按当前桌面版会话的环境测；app 自带的工具和说明不在内，以 Context 面板为准" if desktop else "按终端版测；桌面版另有 app 自带的工具和说明，以它的 Context 面板为准"
    lines = [
        f"开局占用（在空的临时目录里测，不含项目级配置；{where}）：",
        f"- 开局合计：{total.group(1) if total else '未知'}（带 (deferred) 的是按需加载部分，只有名字常驻，不计入合计）",
    ]
    if total and baseline.get("Skills"):
        # /context 把 skill 列表从 System tools 里扣出来单列，可它实际放在第一条消息里，合计里等于没算；
        # 所以关 skill 时合计不变、System tools 等量上涨，省下的只能看 Skills 一栏
        lines.append(f"- 估计真实开局：约 {format_tokens(parse_tokens(total.group(1)) + baseline['Skills'])}（合计没算 skill 列表，"
                     "这里把 Skills 一栏加回去；关 skill 省下多少看 Skills 一栏，合计不会变）")
    lines.append(f"- 测量用的 claude：{claude_exe()}")
    if simple_mode(settings_data):
        lines.append("- 注意：settings.json 开着最小模式（env.CLAUDE_CODE_SIMPLE），终端版只加载几个基本工具，不加载 skill、MCP、CLAUDE.md，下面是最小模式的数")
    if plugin_dir and not desktop:
        lines.append("- 桌面版同步的 skill 插件：只在桌面版会话里加载，终端版没算")
    elif plugin_dir:
        plugins = settings_data.get("enabledPlugins") or {}
        disabled = plugins.get("anthropic-skills@inline") is False
        lines.append("- 桌面版同步的 skill 插件：" + ("已在 enabledPlugins 里关掉，下面不会出现" if disabled else "已挂上一起测"))
    lines += [f"- {name}：{format_tokens(tokens)}" for name, tokens in baseline.items() if name not in {"Free space", "Autocompact buffer", "Messages"}]

    servers: dict[str, list[int]] = collections.defaultdict(list)
    for row in results["基线"].get("MCP Tools", []):
        if len(row) >= 3:
            servers[row[1]].append(parse_tokens(row[2]))
    if servers:
        lines += ["", "MCP 工具说明（按服务器；按需加载时只有名字进上下文）："]
        lines += [f"- {name}：{format_tokens(sum(sizes))}（{len(sizes)} 个工具）" for name, sizes in sorted(servers.items(), key=lambda kv: -sum(kv[1]))]

    rows = [row for row in results["基线"].get("Skills", []) if len(row) >= 3]
    if rows:
        lines += ["", "每个 skill 的简介占用（从多到少）" + ("，带用量和「被提到」：" if usage is not None else "：")]
        tasks, others = reference_texts(home) if usage is not None else ({}, {})
        for name, source, tokens in sorted((row[:3] for row in rows), key=lambda row: -parse_tokens(row[2])):
            extra = ""
            if usage is not None:
                refs = find_refs(name, tasks, others)
                extra = f"；{usage_line(usage['skills'].get(name))}" + (f"；被提到：{', '.join(refs)}" if refs else "")
            label = f"{name}（{source}）" if source and source != "undefined" else name
            lines.append(f"- {label}：{tokens}{extra}")

    lines += ["", "模拟关掉以后能省多少（用 --settings 临时叠加，不改文件）："]
    if artifact_off:
        lines.append("- Artifact：enableArtifact 已经是 false，不用测")
    lines += [f"- {tool}：已经在 permissions.deny 里，不用测" for tool in denied]
    for label in whatifs:
        whatif = categories(label)
        loaded = baseline.get("System tools", 0) - whatif.get("System tools", 0)
        deferred = baseline.get("System tools (deferred)", 0) - whatif.get("System tools (deferred)", 0)
        if loaded <= 0 and deferred <= 0:
            lines.append(f"- {label}：当前没有加载，省不了")
            continue
        warning = "；没装 Git for Windows 时它是唯一能跑命令的工具，不能关" if "PowerShell" in label else ""
        lines.append(f"- {label}：常驻省 {format_tokens(loaded)}，按需部分省 {format_tokens(deferred)}{warning}")
    return lines


def ask_yes(prompt: str) -> bool:
    return input(f"{prompt} [y/N]：").strip().lower() == "y"


def ask_choice(prompt: str, allowed: set[int]) -> int:
    value = input(prompt).strip() or "0"
    if not value.isdigit() or int(value) not in allowed:
        raise ValueError("输入不在允许范围内，已停止且未修改")
    return int(value)


def main(argv: list[str] | None = None) -> int:
    if sys.platform == "win32":
        # 中文 Windows 默认 GBK，被 agent 捕获输出时中文会报错或乱码；放在解析参数前，--help 也用 UTF-8
        for stream in (sys.stdout, sys.stderr):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="安全审计和清理 Claude 本机状态，或给开局上下文瘦身")
    parser.add_argument("--audit", action="store_true", help="只读审计（本机清理，仅 macOS）")
    parser.add_argument("--context", action="store_true", help="上下文瘦身只读报告：配置位置，各工具、MCP、skill 的用量")
    parser.add_argument("--measure", action="store_true", help="用 claude -p /context 测开局占用，并模拟关掉几项能省多少")
    parser.add_argument("--days", type=int, default=60, help="--context 统计最近多少天，默认 60")
    parser.add_argument("--backup-settings", action="store_true", help="改 settings.json 之前，在旁边复制一份带时间戳的备份")
    parser.add_argument("--check-settings", action="store_true", help="改完以后确认 settings.json 还是合法 JSON")
    parser.add_argument("--probe", action="store_true", help="真发一句话，确认 claude -p 能正常回复")
    args = parser.parse_args(argv)
    home, app = pathlib.Path.home(), APP
    claude, identity, settings = home / ".claude", home / ".claude.json", home / ".claude/settings.json"
    errors = (OSError, ValueError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError)
    if args.backup_settings or args.check_settings or args.probe:
        # 上下文瘦身的辅助步骤，各平台通用
        try:
            if args.backup_settings:
                target = backup_settings(home)
                print(f"已备份：{target}" if target else f"还没有 settings.json，不用备份；要改时新建 {config_dir(home) / 'settings.json'}，内容是一个 JSON 对象")
            if args.check_settings:
                if not (config_dir(home) / "settings.json").exists():
                    raise FileNotFoundError(f"settings.json 不存在：{config_dir(home) / 'settings.json'}")
                settings_env(read_json(config_dir(home) / "settings.json"))
                print(f"settings.json 是合法 JSON：{config_dir(home) / 'settings.json'}")
            if args.probe:
                print(f"claude -p 正常回复：{probe()}")
        except errors as error:
            print(f"失败：{error}", file=sys.stderr)
            return 2
        return 0
    if args.context or args.measure:
        # 只读，Claude Code 里也可以跑；用量先打印，测量失败也不丢
        try:
            settings_data = read_json(config_dir(home) / "settings.json", {})
            settings_env(settings_data)
            usage = scan_usage(home, args.days) if args.context else None
            if usage is not None:
                print("\n".join(context_report(home, settings_data, args.days, usage)), flush=True)
        except errors as error:
            print(f"上下文报告失败：{error}", file=sys.stderr)
            return 2
        if args.measure:
            try:
                print(("\n" if usage is not None else "") + "\n".join(measure_report(home, settings_data, usage)))
            except errors as error:
                print(f"测量失败：{error}。用量统计不受影响，开局占用请改看 Context 面板。", file=sys.stderr)
                return 2
        return 0
    if sys.platform != "darwin":
        print("本机清理目前只支持 macOS；上下文瘦身（--context、--measure）各平台都能用。", file=sys.stderr)
        return 2
    if running_under_claude() and not args.audit:
        print("拒绝执行：当前脚本由 Claude Code 启动。请改用 Codex 或普通终端；这里只允许 --audit。", file=sys.stderr)
        return 2
    try:
        settings_data = read_json(settings, {})
        env = settings_env(settings_data)
        safe, desktop = discover(home)
        processes = claude_processes()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"审计失败：{error}", file=sys.stderr)
        return 2
    disabled = [key for key in TELEMETRY_KEYS if str(env.get(key, "")).lower() in {"1", "true", "yes", "on"}]
    print("Claude Cleanup 会自动清理明确可再生的缓存/日志；风险操作仍由你选择。")
    print("输入最终 CONFIRM 前不会写盘；所有移除只进入废纸篓。\n\n只读审计：")
    print(f"- ~/.claude：{'存在' if claude.is_dir() else '不存在'}；~/.claude.json：{'存在' if identity.is_file() else '不存在'}")
    print(f"- 可自动清理缓存/日志：{len(safe)} 项；Claude Desktop 持久数据：{len(desktop)} 项")
    print(f"- Claude.app：{'存在' if app.exists() else '不存在'}；相关进程：{len(processes)} 个")
    print(f"- 遥测关闭键：{', '.join(disabled) if disabled else '未检测到'}（脚本不会改变）")
    print(f"- 时区：{current_timezone()}")
    if str(env.get("CLAUDE_CODE_SIMPLE", "")).lower() in {"1", "true", "yes", "on"}:
        print("- settings.json 开着最小模式（env.CLAUDE_CODE_SIMPLE）：终端版不加载 skill、MCP、CLAUDE.md，"
              "用订阅登录（OAuth）的终端会显示没登录；桌面版不受影响。不是有意开的，删掉这一项即可（本脚本不改它）")
    if args.audit:
        return 0
    if not sys.stdin.isatty():
        print("拒绝执行：需要真实 TTY 完成知情确认。", file=sys.stderr)
        return 2

    try:
        print("\n只询问有风险的操作；可再生缓存和日志不逐项询问。")
        rotate = ask_yes("轮换本地 userID/machineID，并清除已知账号缓存字段？")
        keychain = ask_yes("删除钥匙串 Claude Code-credentials（会退出 CLI 登录）？")
        desktop_mode = ask_choice(
            "Claude Desktop：0 保留；1 清登录态和全部桌面版数据（含 Code 会话列表、No folder 会话里的文件、Cowork 数据）；"
            "2 再移除应用。选择 [0]：", {0, 1, 2},
        )
        set_timezone = current_timezone() != "Asia/Taipei" and ask_yes("把 macOS 时区改为 Asia/Taipei？")
        risky = rotate or keychain or desktop_mode
        clean_safe = not processes
        if processes and risky:
            print("\n所选风险操作要求由你正常退出所有 Claude Code / Claude Desktop；脚本不会 kill 进程。")
            input("退出后按 Enter 重新检查：")
            if claude_processes():
                print("仍检测到 Claude 进程，已取消且未写盘。", file=sys.stderr)
                return 2
            clean_safe = True
        targets = (safe if clean_safe else []) + (desktop if desktop_mode else [])
        if desktop_mode == 2 and app.exists():
            targets.append(app)

        print("\n最终执行清单：")
        print("1. 第一个写操作：完整备份并校验 ~/.claude，同时备份 ~/.claude.json。")
        action = "自动清理" if clean_safe else "因 Claude 正在运行而跳过"
        print(f"2. {action} {len(safe)} 项缓存/日志。")
        for target in targets:
            print(f"   - {target}")
        print(f"3. 身份轮换：{'是' if rotate else '否'}；删除钥匙串：{'是' if keychain else '否'}；修改时区：{'是' if set_timezone else '否'}")
        print("绝不清理 sessions、projects、history、skills、plugins、hooks、commands、agents、MCP、设置文件或任何项目/Git/Codex 数据。")
        print("所有移除只进废纸篓；遥测键逐值保持不变。")
        if input("完全理解后输入 CONFIRM 开始；其他输入取消：").strip() != "CONFIRM":
            print("已取消，没有修改任何内容。")
            return 1

        before_telemetry = telemetry(read_json(settings, {}))
        protected_before = [claude / name for name in PROTECTED if (claude / name).exists() or (claude / name).is_symlink()]
        backup = create_backup(home)  # 第一个写操作
        print(f"\n[1/5] 全量备份已校验：{backup}")
        if set_timezone:
            print("[人工步骤] 仅在终端原生 sudo 隐藏提示中输入 Mac 开机密码；脚本不会读取或保存密码。")
            subprocess.run(["sudo", "-v"], check=True)
        print(f"[2/5] 身份轮换：同步 {rotate_identity(home)} 份内部备份" if rotate else "[2/5] 身份保持不变")
        if keychain:
            result = subprocess.run(["security", "delete-generic-password", "-s", "Claude Code-credentials"], capture_output=True, text=True, check=False)
            if result.returncode not in {0, 44}:
                raise RuntimeError(f"钥匙串处理失败：{result.stderr.strip()}")
        print(f"[3/5] 钥匙串：{'已处理' if keychain else '保持不变'}")
        batch = home / ".Trash" / f"claude-cleanup-{dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
        moved = [move_to_trash(target, set(targets), claude, batch) for target in targets]
        print(f"[4/5] 已移入废纸篓：{len(moved)} 项")
        if set_timezone:
            subprocess.run(["sudo", "/usr/sbin/systemsetup", "-settimezone", "Asia/Taipei"], check=True)
            if current_timezone() != "Asia/Taipei":
                raise RuntimeError("时区修改后验证失败")
        if telemetry(read_json(settings, {})) != before_telemetry:
            raise RuntimeError("遥测设置发生变化，已停止")
        missing = [path for path in protected_before if not (path.exists() or path.is_symlink())]
        if missing:
            raise RuntimeError("受保护路径丢失：" + ", ".join(map(str, missing)))
        print(f"[5/5] 遥测状态未变；时区：{current_timezone()}\n\n完成。未清空废纸篓。\n备份：{backup}")
        if moved:
            print(f"废纸篓批次：{batch}")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"停止：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
