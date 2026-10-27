"""在给定 HOME 下造一个像真实用户用了两三个月的 Claude Code 环境，并把用量标准答案写到 expected.json。

用法：python3 make_home.py <HOME> <kit 目录> <假网关端口> <expected.json>
"""
import datetime as dt
import json
import os
import pathlib
import random
import sys
import uuid

home, kit, port, expected_path = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3]), pathlib.Path(sys.argv[4])
random.seed(7)
now = dt.datetime.now(dt.timezone.utc)
claude = home / ".claude"
WINDOW = 60  # 报告默认统计近 60 天；会话避开 57–63 天这段，免得卡在边界上


def w(path: pathlib.Path, text: str) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def wj(path: pathlib.Path, data) -> pathlib.Path:
    return w(path, json.dumps(data, ensure_ascii=False, indent=2))


def stamp(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def touch(path: pathlib.Path, t: dt.datetime) -> None:
    os.utime(path, (t.timestamp(), t.timestamp()))


# ---------- 用户 skill ----------
SKILLS = {
    "commit-msg": ("Write a Conventional Commits message for the staged diff. Use when the user asks to commit, write a commit message, or says 提交.", ""),
    "weekly-report": ("把这周的提交、PR 和笔记整理成周报，按「完成 / 进行中 / 下周」三段输出。用户说写周报、weekly report 时用。", ""),
    "pdf-tools": ("Extract text and tables from PDFs, merge or split files, and fill simple forms with pypdf. Use whenever a .pdf is involved.",
                  "处理之前先读 `helper-lib` 的说明，里面有共用的 Python 环境。\n"),
    "helper-lib": ("Shared Python helpers (venv path, retry wrapper, logging setup) used by other skills. Not meant to be triggered directly.", ""),
    "api-style": ("REST API design rules for the shop-api service: resource naming, pagination, error envelopes, versioning. Use when adding or reviewing endpoints.", ""),
    "standup": ("Summarize yesterday's commits and open PRs across ~/work into a three-line standup update.", ""),
    "db-migrate": ("Generate and check a Prisma migration for the shop-api database.", "disable-model-invocation: true\n"),
    "old-report": ("（旧）季度报告模板，2026 年 Q2 以后不用了。", ""),
    "unused-thing": ("Experimental helper for converting Figma exports into React components. Use when the user pastes a Figma link or asks to turn a design into code. "
                     "Handles auto-layout, variants and design tokens; outputs TypeScript with Tailwind classes and Storybook stories.", ""),
}
for name, (desc, extra) in SKILLS.items():
    front = f"---\nname: {name}\ndescription: {desc}\n"
    body = ""
    if extra.startswith("disable-model-invocation"):
        front += extra
    else:
        body = extra
    w(claude / "skills" / name / "SKILL.md", front + "---\n\n# " + name + "\n\n" + body + "照步骤做，完成后简短汇报。\n")
w(claude / "skills/pdf-tools/scripts/extract.py", "print('extract')\n")

# ---------- CLAUDE.md、agent、命令、定时任务、输出风格 ----------
w(claude / "CLAUDE.md", "\n".join([
    "# 个人偏好", "", "- 回复用中文，代码注释用英文。", "- 改 shop-api 的接口前先照 `api-style` 检查命名和错误格式。",
    "- 提交前跑 `npm test`，不要跳过 hooks。", "- 不要自动 push。", "", "## 常用路径", "", "- 工作目录：~/work", "- 笔记：~/notes", "",
    *[f"- 约定 {i}：保持函数短小，单个文件不超过 400 行，复杂逻辑先写测试再实现。" for i in range(1, 25)], ""]))
w(claude / "agents/reviewer.md", "---\nname: reviewer\ndescription: Review a diff for bugs and style issues.\ntools: Read, Grep, Glob\n---\n\n照 `api-style` 的规则看接口改动，只报问题不改代码。\n")
w(claude / "agents/doc-writer.md", "---\nname: doc-writer\ndescription: Draft README and API docs from code.\n---\n\n先读代码再写文档。\n")
w(claude / "commands/deploy.md", "部署 shop-api 到 staging：先用 /commit-msg 提交，再跑 `npm run deploy:staging`。\n")
w(claude / "scheduled-tasks/daily-standup/SKILL.md", "---\nname: daily-standup\ndescription: 每天早上生成站会摘要\n---\n\n每天 9 点用 standup skill 汇总昨天的提交，发到笔记里。\n")
w(claude / "output-styles/terse.md", "---\nname: terse\ndescription: 尽量短\n---\n\n回答控制在三句话以内。\n")
w(claude / "statusline.sh", "#!/bin/sh\necho \"$(basename \"$PWD\")\"\n").chmod(0o755)

# ---------- settings.json（假网关、假 token、旧版本本 skill 留下的 CLAUDE_CODE_SIMPLE） ----------
wj(claude / "settings.json", {
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "env": {
        "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
        "ANTHROPIC_AUTH_TOKEN": "sk-fake-gateway-0000000000000000000000000000",
        "ANTHROPIC_MODEL": "claude-opus-5-5",
        "DISABLE_TELEMETRY": "1",
        "CLAUDE_CODE_SIMPLE": "1",
    },
    "model": "opus",
    "cleanupPeriodDays": 90,
    "includeCoAuthoredBy": False,
    "outputStyle": "terse",
    "permissions": {
        "allow": ["Bash(npm run test:*)", "Bash(git status)", "Bash(git diff:*)", "mcp__notes__search_notes"],
        "deny": ["Read(./.env)", "Read(./secrets/**)"],
        "defaultMode": "acceptEdits",
    },
    "hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATHS\" >/dev/null 2>&1 || true"}]}]},
    "statusLine": {"type": "command", "command": "~/.claude/statusline.sh"},
    "skillOverrides": {"old-report": "off"},
})

# ---------- 本地插件市场（安装由外面的 claude plugin 命令做） ----------
market = home / "dev/team-market"
wj(market / ".claude-plugin/marketplace.json", {"name": "team-market", "owner": {"name": "Platform Team"},
                                                 "plugins": [{"name": "team-tools", "source": "./plugins/team-tools", "description": "团队共用的发布和值班工具"}]})
plugin = market / "plugins/team-tools"
wj(plugin / ".claude-plugin/plugin.json", {"name": "team-tools", "version": "1.2.0", "description": "团队共用的发布和值班工具"})
w(plugin / "skills/release-notes/SKILL.md", "---\nname: release-notes\ndescription: Draft release notes from merged PRs since the last tag. Use when preparing a release.\n---\n\n按 PR 标签分组。\n")
w(plugin / "skills/oncall/SKILL.md", "---\nname: oncall\ndescription: Triage an alert: find the dashboard, recent deploys and the runbook, then propose next steps.\n---\n\n先看最近一次部署。\n")
w(plugin / "commands/standup-sync.md", "把站会摘要同步到团队频道。\n")

# ---------- ~/.claude.json ----------
work = {p: home / "work" / p for p in ("shop-api", "admin-web")}
work["notes"] = home / "notes"
for path in work.values():
    path.mkdir(parents=True, exist_ok=True)
first_start = now - dt.timedelta(days=95)
mcp = {"notes": {"type": "stdio", "command": "/usr/bin/python3", "args": [str(kit / "fake_mcp.py"), "notes"], "env": {}},
       "jira": {"type": "stdio", "command": "/usr/bin/python3", "args": [str(kit / "fake_mcp.py"), "jira"], "env": {"JIRA_TOKEN": "fake-jira-token-123"}},
       "old-server": {"type": "stdio", "command": str(home / "bin/old-mcp-server"), "args": []}}
wj(home / ".claude.json", {
    "numStartups": 214, "installMethod": "npm-global", "autoUpdates": True, "theme": "dark",
    "userID": uuid.uuid4().hex + uuid.uuid4().hex, "firstStartTime": stamp(first_start), "hasCompletedOnboarding": True,
    "lastOnboardingVersion": "2.1.200", "oauthAccount": {"accountUuid": str(uuid.uuid4()), "emailAddress": "lin@example.com", "organizationUuid": str(uuid.uuid4())},
    "projects": {str(p): {"allowedTools": [], "mcpServers": {}, "hasTrustDialogAccepted": True, "lastCost": round(random.uniform(0.1, 3), 2)} for p in work.values()},
    "mcpServers": mcp, "skillUsage": {"commit-msg": {"usageCount": 41, "lastUsedAt": int(now.timestamp() * 1000)}},
    "tipsHistory": {"new-user-warmup": 7, "plan-mode-for-complex-tasks": 30},
})
for i in (1, 2):
    wj(claude / f"backups/.claude.json.backup.{int((now - dt.timedelta(days=i * 10)).timestamp() * 1000)}",
       {"userID": "old" + str(i), "numStartups": 200 - i, "mcpServers": mcp})

# ---------- 会话日志 ----------
since = (dt.datetime.now() - dt.timedelta(days=WINDOW)).strftime("%Y-%m-%d")
truth: dict = {"tools": {}, "skills": {}}


def note(kind: str, name: str, session: str, day: str) -> None:
    if day < since:
        return
    item = truth[kind].setdefault(name, {"calls": 0, "sessions": set(), "last": ""})
    item["calls"] += 1
    item["sessions"].add(session)
    item["last"] = max(item["last"], day)


PROMPTS = ["修一下订单列表分页的 bug", "加一个导出 CSV 的接口", "看看这个测试为什么挂了", "重构 auth 中间件", "给 README 补上本地开发步骤",
           "把这周的笔记整理一下", "查一下 SHOP-412 是什么情况", "升级一下依赖", "写个脚本批量改文件名", "解释一下这段正则"]
COMMON = ["Bash", "Read", "Read", "Edit", "Grep", "Glob", "Bash", "Read", "Write", "TodoWrite", "WebSearch", "WebFetch"]


def tool_input(name: str, cwd: pathlib.Path) -> dict:
    return {"Bash": {"command": random.choice(["npm test", "git status", "git diff", "ls -la", "npm run lint"]), "description": "Run command"},
            "Read": {"file_path": str(cwd / random.choice(["src/index.ts", "package.json", "README.md"]))},
            "Edit": {"file_path": str(cwd / "src/index.ts"), "old_string": "a", "new_string": "b"},
            "Write": {"file_path": str(cwd / "scripts/tmp.sh"), "content": "echo hi\n"},
            "Grep": {"pattern": "TODO", "path": str(cwd)}, "Glob": {"pattern": "**/*.ts"},
            "TodoWrite": {"todos": [{"content": "fix", "status": "in_progress"}]},
            "WebSearch": {"query": "prisma migrate reset"}, "WebFetch": {"url": "https://example.com", "prompt": "summarize"}}.get(name, {})


def session(project: str, cwd: pathlib.Path, start: dt.datetime, extras: list[tuple]) -> None:
    """extras：("skill", 名) / ("slash", 名) / ("readskill", 名) / ("mcp", 工具名) / ("agent",)"""
    sid = str(uuid.uuid4())
    pdir = claude / "projects" / "".join(c if c.isalnum() else "-" for c in str(cwd))
    path, key = pdir / f"{sid}.jsonl", str(pdir / sid)
    lines, t, parent = [], start, None
    version = "2.1.290" if start > now - dt.timedelta(days=30) else "2.1.240"
    base = {"isSidechain": False, "userType": "external", "cwd": str(cwd), "sessionId": sid, "version": version, "gitBranch": "main"}

    def add(entry: dict) -> None:
        nonlocal t, parent
        t += dt.timedelta(seconds=random.randint(3, 90))
        u = str(uuid.uuid4())
        lines.append(json.dumps({"parentUuid": parent, **base, **entry, "uuid": u, "timestamp": stamp(t)}, ensure_ascii=False))
        parent = u

    def use(name: str, inputs: dict, sink: list = None) -> None:
        tid = "toolu_" + uuid.uuid4().hex[:24]
        add({"type": "assistant", "message": {"id": "msg_" + uuid.uuid4().hex[:24], "type": "message", "role": "assistant", "model": "claude-opus-5-5",
                                              "content": [{"type": "tool_use", "id": tid, "name": name, "input": inputs}], "stop_reason": "tool_use",
                                              "usage": {"input_tokens": 1200, "output_tokens": 80}}, "requestId": "req_" + uuid.uuid4().hex[:20]})
        add({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok"}]}})

    day = lambda: stamp(t)[:10]  # noqa: E731
    def extra(kind: str, *rest) -> None:
        if kind == "slash":
            add({"type": "user", "message": {"role": "user", "content": f"<command-name>/{rest[0]}</command-name>\n<command-message>{rest[0]}</command-message>\n<command-args></command-args>"}})
            note("skills", rest[0], key, day())
        elif kind == "skill":
            use("Skill", {"skill": rest[0]})
            note("tools", "Skill", key, day()), note("skills", rest[0], key, day())
        elif kind == "readskill":
            use("Read", {"file_path": str(claude / "skills" / rest[0] / "SKILL.md")})
            note("tools", "Read", key, day()), note("skills", rest[0], key, day())
        elif kind == "mcp":
            use(rest[0], {"query": "订单"})
            note("tools", rest[0], key, day())
        elif kind == "agent":
            tool = "Agent" if version == "2.1.290" else "Task"
            use(tool, {"description": "Search codebase", "prompt": "find all callers", "subagent_type": "Explore"})
            note("tools", tool, key, day())
            sub = pdir / sid / "subagents" / f"agent-{uuid.uuid4().hex[:8]}.jsonl"
            sub_lines = []
            for name in ("Grep", "Read", "Read"):
                t2 = t + dt.timedelta(seconds=5)
                sub_lines.append(json.dumps({"parentUuid": None, **base, "isSidechain": True, "type": "assistant", "message": {
                    "role": "assistant", "content": [{"type": "tool_use", "id": "toolu_" + uuid.uuid4().hex[:24], "name": name, "input": tool_input(name, cwd)}]},
                    "uuid": str(uuid.uuid4()), "timestamp": stamp(t2)}))
                note("tools", name, key, stamp(t2)[:10])
            w(sub, "\n".join(sub_lines) + "\n")
            touch(sub, t + dt.timedelta(seconds=5))

    pending = list(extras)
    for _ in range(random.randint(2, 4)):
        prompt = random.choice(PROMPTS)
        add({"type": "user", "message": {"role": "user", "content": prompt}})
        w_history.append(json.dumps({"display": prompt, "pastedContents": {}, "timestamp": int(t.timestamp() * 1000), "project": str(cwd)}, ensure_ascii=False))
        for _ in range(random.randint(2, 6)):
            name = random.choice(COMMON)
            use(name, tool_input(name, cwd))
            note("tools", name, key, day())
        while pending and random.random() < 0.7:
            extra(*pending.pop(0))
        add({"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5-5", "content": [{"type": "text", "text": "改好了。"}]}})
    for item in pending:  # 没轮到的补在最后
        extra(*item)
    w(path, "\n".join(lines) + "\n")
    touch(path, t)


w_history: list[str] = []
plan = []  # (项目, 几天前, extras)
for age in (2, 5, 9, 13, 17, 22, 26, 31, 36, 41, 46, 52, 66, 79):
    extras = [("skill", "commit-msg")] if age % 2 else []
    if age in (5, 26):
        extras.append(("skill", "api-style"))
    if age == 22:
        extras.append(("slash", "db-migrate"))
    if age in (36, 41, 46):
        extras.append(("mcp", "mcp__jira__get_issue"))
    if age in (9, 31, 52):
        extras.append(("agent",))
    if age == 13:
        extras += [("readskill", "pdf-tools"), ("skill", "team-tools:release-notes")]
    if age == 79:
        extras += [("skill", "old-report"), ("mcp", "mcp__jira__search_issues")]
    if age in (2, 17):
        extras.append(("slash", "compact"))
    plan.append(("shop-api", age, extras))
for age in (1, 4, 8, 15, 24, 33, 44, 70):
    extras = [("skill", "commit-msg")] if age % 3 else [("slash", "clear")]
    if age == 8:
        extras.append(("readskill", "pdf-tools"))
    plan.append(("admin-web", age, extras))
for age in (0, 7, 14, 21, 28):
    plan.append(("notes", age, [("slash", "weekly-report"), ("mcp", "mcp__notes__search_notes"), ("mcp", "mcp__notes__create_note")]))
for project, age, extras in plan:
    start = now - dt.timedelta(days=age, hours=random.randint(1, 8))
    session(project, work[project], start, extras)
w(claude / "history.jsonl", "\n".join(w_history) + "\n")

# 一条写了一半的行和一段坏字节：真实日志里崩溃时会有
broken = next((claude / "projects").rglob("*.jsonl"))
mtime = broken.stat().st_mtime
with broken.open("ab") as handle:
    handle.write(b'{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash"\n')
    handle.write(b'{"note":"\xff\xfe bad bytes"}\n')
os.utime(broken, (mtime, mtime))

# ---------- 其他会长出来的目录 ----------
sid = str(uuid.uuid4())
for rel, text in {
    f"file-history/{sid}/3f2a9c1e@v1": "old content\n", f"todos/{sid}-agent-{sid}.json": "[]",
    "shell-snapshots/snapshot-zsh-1790000000000-abc123.sh": "export PATH=/usr/bin\n",
    "statsig/statsig.cached.evaluations.1a2b3c": "{}", f"debug/{sid}.txt": "[DEBUG] start\n", "plans/curious-fox.md": "# Plan\n",
    f"session-env/{sid}/env": "", "ide/12345.lock": "{}", "cache/changelog.md": "# Changelog\n", "stats-cache.json": '{"version":2}',
    "telemetry/1p_failed_events.a.json": "[]", "usage-data/report-2026-09-30.html": "<html>insights</html>",
}.items():
    w(claude / rel, text)
lib = home / "Library"
w(lib / f"Caches/claude-cli-nodejs/{'-'.join(str(work['shop-api']).split('/'))}/mcp-logs-notes/2026-10-20.txt", "connected\n")

# ---------- 桌面版数据（没装 app，只造数据目录） ----------
desk = lib / "Application Support/Claude"
w(desk / "config.json", '{"locale":"zh-CN"}')
w(desk / f"claude-code-sessions/{uuid.uuid4()}/{uuid.uuid4()}.json", '{"title":"修分页"}')
w(desk / f"scratch-workspaces/{uuid.uuid4()}/draft.md", "# 草稿\n")
w(desk / f"local-agent-mode-sessions/{uuid.uuid4()}/session.json", "{}")
sp = desk / f"local-agent-mode-sessions/skills-plugin/{uuid.uuid4()}/{uuid.uuid4()}"
desk_skills = {"pdf": "Read, merge, split and fill PDF files.", "docx": "Create and edit Word documents with tracked changes.",
               "xlsx": "Build spreadsheets with formulas and charts.", "pptx": "Create slide decks.", "skill-creator": "Create or improve skills."}
wj(sp / ".claude-plugin/plugin.json", {"name": "anthropic-skills", "version": "1.0.0", "description": "Anthropic-managed skills for Claude Desktop"})
wj(sp / "manifest.json", {"lastUpdated": int(now.timestamp() * 1000), "skills": [
    {"skillId": n, "name": n, "description": d, "creatorType": "anthropic", "updatedAt": stamp(now), "enabled": n != "pptx"} for n, d in desk_skills.items()]})
for n, d in desk_skills.items():
    w(sp / "skills" / n / "SKILL.md", f"---\nname: {n}\ndescription: {d}\n---\n\n# {n}\n")
w(lib / "Logs/Claude/main.log", "app started\n")
w(lib / "Caches/com.anthropic.claudefordesktop/Cache.db", "x")

wj(expected_path, {kind: {n: {"calls": v["calls"], "sessions": len(v["sessions"]), "last": v["last"]} for n, v in items.items()} for kind, items in truth.items()})
print(f"造好了：{len(plan)} 个会话，{len(SKILLS)} 个 skill，3 个 MCP 服务器；标准答案 {expected_path}")
