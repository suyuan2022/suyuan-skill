from __future__ import annotations

import contextlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).parents[1] / "scripts" / "claude_cleanup.py"
SPEC = importlib.util.spec_from_file_location("claude_cleanup", SCRIPT)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cleanup
SPEC.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def home(self) -> pathlib.Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = pathlib.Path(temp.name)
        (home / ".claude").mkdir()
        (home / ".Trash").mkdir()
        return home

    def seed_protected(self, home: pathlib.Path) -> dict[str, str]:
        files = {
            "projects/session.jsonl": "session",
            "skills/demo/SKILL.md": "skill",
            "plugins/demo.json": "plugin",
            "hooks/guard.sh": "hook",
            "scheduled-tasks/daily/SKILL.md": "task",
        }
        for relative, content in files.items():
            target = home / ".claude" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return files

    def test_backup_contains_all_claude_data_and_identity(self):
        home = self.home()
        files = self.seed_protected(home)
        (home / ".claude.json").write_text('{"userID":"old"}', encoding="utf-8")
        backup = cleanup.create_backup(home)
        for relative, content in files.items():
            self.assertEqual((backup / "dot-claude" / relative).read_text(), content)
        self.assertEqual((backup / "claude.json").read_text(), '{"userID":"old"}')
        manifest = json.loads((backup / "manifest.json").read_text())
        self.assertGreaterEqual(manifest["files"], len(files))
        self.assertTrue(manifest["claudeJsonCopied"])

    def test_deletion_gate_rejects_protected_and_unknown_paths(self):
        home = self.home()
        claude, batch = home / ".claude", home / ".Trash/run"
        for name in cleanup.PROTECTED:
            with self.subTest(name=name), self.assertRaises(RuntimeError):
                cleanup.move_to_trash(claude / name, {claude / name}, claude, batch)
        with self.assertRaises(RuntimeError):
            cleanup.move_to_trash(home / "Documents", set(), claude, batch)

    def test_safe_cache_moves_without_touching_project(self):
        home = self.home()
        project = home / ".claude/projects/session.jsonl"
        project.parent.mkdir()
        project.write_text("keep")
        cache = home / ".claude/cache"
        cache.mkdir()
        (cache / "entry").write_text("cache")
        destination = cleanup.move_to_trash(cache, {cache}, home / ".claude", home / ".Trash/run")
        self.assertFalse(cache.exists())
        self.assertEqual((destination / "entry").read_text(), "cache")
        self.assertEqual(project.read_text(), "keep")

    def test_identity_rotation_syncs_internal_backups(self):
        home = self.home()
        cleanup.write_json(home / ".claude.json", {"userID": "old", "machineID": "old", "oauthAccount": {}, "keep": 1})
        internal = home / ".claude/backups/.claude.json.backup.1"
        internal.parent.mkdir()
        cleanup.write_json(internal, {"userID": "old", "machineID": "old", "oauthAccount": {}, "keepBackup": 1})
        self.assertEqual(cleanup.rotate_identity(home), 1)
        main, backup = cleanup.read_json(home / ".claude.json"), cleanup.read_json(internal)
        self.assertEqual((main["userID"], main["machineID"]), (backup["userID"], backup["machineID"]))
        self.assertNotIn("oauthAccount", main)
        self.assertNotIn("oauthAccount", backup)
        self.assertEqual((main["keep"], backup["keepBackup"]), (1, 1))

    def run_main(self, home: pathlib.Path, answers: list[str], processes: list[str] | None = None) -> tuple[int, list[str]]:
        prompts, iterator = [], iter(answers)

        def answer(prompt=""):
            prompts.append(prompt)
            return next(iterator)

        with (
            mock.patch.object(pathlib.Path, "home", return_value=home),
            mock.patch.object(cleanup.sys, "platform", "darwin"),
            mock.patch.object(cleanup, "running_under_claude", return_value=False),
            mock.patch.object(cleanup, "claude_processes", return_value=processes or []),
            mock.patch.object(cleanup, "current_timezone", return_value="Asia/Taipei"),
            mock.patch.object(sys.stdin, "isatty", return_value=True),
            mock.patch("builtins.input", side_effect=answer),
        ):
            return cleanup.main([]), prompts

    def test_safe_cleanup_is_not_a_question_and_cancel_writes_nothing(self):
        home = self.home()
        (home / ".claude/cache").mkdir()
        result, prompts = self.run_main(home, ["n", "n", "0", "NO"])
        self.assertEqual(result, 1)
        self.assertFalse((home / "ClaudeBackups").exists())
        self.assertTrue((home / ".claude/cache").exists())
        self.assertEqual(len(prompts), 4)
        self.assertFalse(any("自动清理" in prompt or "可再生缓存" in prompt for prompt in prompts))

    def test_running_claude_skips_safe_cleanup_without_exit_prompt(self):
        home = self.home()
        cache = home / ".claude/cache"
        cache.mkdir()
        result, prompts = self.run_main(home, ["n", "n", "0", "CONFIRM"], ["123 claude"])
        self.assertEqual(result, 0)
        self.assertTrue(cache.exists())
        self.assertFalse(any("退出后按 Enter" in prompt for prompt in prompts))

    def test_claude_agent_allows_audit_only(self):
        home = self.home()
        with (
            mock.patch.object(pathlib.Path, "home", return_value=home),
            mock.patch.object(cleanup.sys, "platform", "darwin"),
            mock.patch.object(cleanup, "running_under_claude", return_value=True),
            mock.patch.object(cleanup, "current_timezone", return_value="Asia/Taipei"),
            mock.patch.object(cleanup, "claude_processes", return_value=[]),
        ):
            self.assertEqual(cleanup.main([]), 2)
            self.assertEqual(cleanup.main(["--audit"]), 0)

    def test_isolated_full_run_preserves_protected_data_and_telemetry(self):
        home = self.home()
        protected = self.seed_protected(home)
        settings = {"env": {"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}, "hooks": {"x": ["keep"]}}
        cleanup.write_json(home / ".claude/settings.json", settings)
        cleanup.write_json(home / ".claude.json", {"userID": "old", "machineID": "old", "oauthAccount": {}, "keep": True})
        internal = home / ".claude/backups/.claude.json.backup.1"
        internal.parent.mkdir()
        cleanup.write_json(internal, {"userID": "old", "machineID": "old", "backupKeep": True})
        cache = home / ".claude/cache"
        cache.mkdir()
        (cache / "entry").write_text("cache")
        result, _ = self.run_main(home, ["y", "n", "0", "CONFIRM"])
        self.assertEqual(result, 0)
        self.assertEqual(cleanup.read_json(home / ".claude/settings.json"), settings)
        backups = list((home / "ClaudeBackups").glob("claude-cleanup-*"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / "dot-claude/projects/session.jsonl").exists())
        self.assertFalse(cache.exists())
        for relative, content in protected.items():
            self.assertEqual((home / ".claude" / relative).read_text(), content)
        final = cleanup.read_json(home / ".claude/settings.json")
        self.assertEqual(cleanup.telemetry(final), cleanup.telemetry(settings))
        self.assertEqual(final["hooks"], settings["hooks"])
        identity, saved = cleanup.read_json(home / ".claude.json"), cleanup.read_json(internal)
        self.assertEqual(identity["userID"], saved["userID"])
        self.assertTrue(identity["keep"] and saved["backupKeep"])


CONTEXT_SAMPLE = """## Context Usage

**Tokens:** 10.7k / 600k (2%)

### Estimated usage by category

| Category | Tokens | Percentage |
|----------|--------|------------|
| System tools | {tools} | 2.5% |
| System tools (deferred) | 19.6k | 3.3% |
| Skills | 917 | 0.2% |
| Free space | 500k | 80% |

### MCP Tools

| Tool | Server | Tokens |
|------|--------|--------|
| mcp__lsp__hover | lsp | 92 |
| mcp__lsp__health | lsp | 48 |

### Skills

| Skill | Source | Tokens |
|-------|--------|--------|
| alpha | User | ~70 |
| dataviz | Built-in | ~480 |
| tiny | User | < 20 |
"""


class ContextSlimTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        # 测试可能就在 Claude Code 会话里跑，宿主注入的这几个变量会影响结果
        for key in ("CLAUDE_CONFIG_DIR", "CLAUDE_USER_DATA_DIR", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SIMPLE"):
            os.environ.pop(key, None)

    def home(self) -> pathlib.Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = pathlib.Path(temp.name)
        (home / ".claude").mkdir()
        return home

    def run_quiet(self, home: pathlib.Path, argv: list[str], **patches) -> tuple[int, str]:
        printed = []
        with (
            mock.patch.object(pathlib.Path, "home", return_value=home),
            mock.patch("builtins.print", side_effect=lambda *a, **k: printed.append(" ".join(map(str, a)))),
        ):
            with mock.patch.multiple(cleanup, **patches) if patches else contextlib.nullcontext():
                return cleanup.main(argv), "\n".join(printed)

    @staticmethod
    def write_lines(path: pathlib.Path, entries: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")

    def test_scan_usage_counts_tools_skills_and_slash_commands(self):
        home = self.home()
        today = cleanup.dt.date.today().isoformat()
        project = home / ".claude/projects/demo"

        def tool(name: str, day: str = today, **inputs) -> dict:
            block = {"type": "tool_use", "id": "x", "name": name, "input": inputs}
            return {"type": "assistant", "timestamp": f"{day}T01:00:00Z", "message": {"content": [block]}}

        self.write_lines(project / "s1.jsonl", [
            tool("Skill", skill="alpha"),
            tool("Read", file_path="/home/u/.claude/skills/gamma/SKILL.md"),
            tool("Read", file_path="C:\\Users\\u\\.claude\\skills\\delta\\SKILL.md"),
            tool("mcp__lsp__hover"),
            tool("Bash", day="2000-01-01"),
            {"type": "user", "timestamp": f"{today}T02:00:00Z", "message": {"content": "<command-name>/beta</command-name>"}},
        ])
        self.write_lines(project / "s1/subagents/agent-1.jsonl", [tool("Bash")])
        usage = cleanup.scan_usage(home, 30)
        tools, skills = usage["tools"], usage["skills"]
        self.assertEqual(skills["alpha"]["calls"], 1)
        self.assertEqual(skills["beta"]["calls"], 1)
        self.assertEqual(skills["gamma"]["calls"], 1)
        self.assertEqual(skills["delta"]["calls"], 1)
        self.assertEqual(tools["mcp__lsp__hover"]["calls"], 1)
        self.assertEqual(tools["Bash"]["calls"], 1)
        self.assertEqual(tools["Bash"]["sessions"], tools["Skill"]["sessions"])
        self.assertEqual(skills["alpha"]["last"], today)

    def test_installed_skills_report_references_and_manual_only(self):
        home = self.home()
        skills = {
            "alpha": ("", "plain"),
            "beta": ("", "先用 `alpha` 再说"),
            "manual": ("disable-model-invocation: true\n", "只能手动触发"),
        }
        for name, (extra, body) in skills.items():
            target = home / ".claude/skills" / name / "SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text(f"---\nname: {name}\n{extra}---\n{body}\n", encoding="utf-8")
        task = home / ".claude/scheduled-tasks/nightly/SKILL.md"
        task.parent.mkdir(parents=True)
        task.write_text("每晚调用 beta skill", encoding="utf-8")
        found = {item["name"]: item for item in cleanup.installed_skills(home)}
        self.assertEqual(found["alpha"]["refs"], ["skill beta"])
        self.assertEqual(found["beta"]["refs"], ["定时任务 nightly"])
        self.assertEqual({name for name, item in found.items() if item["manual"]}, {"manual"})

    def test_parse_context_reads_tables_and_tokens(self):
        tables = cleanup.parse_context(CONTEXT_SAMPLE.format(tools="15.2k"))
        self.assertEqual(tables["Estimated usage by category"][0], ["System tools", "15.2k", "2.5%"])
        self.assertEqual([row[0] for row in tables["Skills"]], ["alpha", "dataviz", "tiny"])
        self.assertEqual([cleanup.parse_tokens(t) for t in ("15.2k", "~70", "< 20", "917")], [15200, 70, 20, 917])

    def test_measure_reports_savings_without_writing_settings(self):
        home = self.home()

        def fake_run(extra: list[str], cwd: str) -> str:
            overlay = pathlib.Path(extra[1]).read_text(encoding="utf-8") if extra else ""
            sample = CONTEXT_SAMPLE.replace("| dataviz | Built-in |", "| dataviz | undefined |")  # 旧版本内置 skill 不标来源
            return sample.format(tools="3.8k" if "enableArtifact" in overlay else "15.2k")

        with (
            mock.patch.object(pathlib.Path, "home", return_value=home),
            mock.patch.object(cleanup, "claude_exe", return_value="/fake/claude"),
            mock.patch.object(cleanup, "run_context", side_effect=fake_run),
        ):
            lines = cleanup.measure_report(home, {}, None)
        text = "\n".join(lines)
        self.assertIn("开局合计：10.7k", text)
        self.assertIn("测量用的 claude：/fake/claude", text)
        self.assertIn("估计真实开局：约 11.6k", text)  # 10.7k + Skills 917
        self.assertIn("- alpha（User）：~70", text)
        self.assertIn("- dataviz：~480", text)
        self.assertIn("关 Artifact（enableArtifact: false）：常驻省 11.4k", text)
        self.assertIn("禁用 ScheduleWakeup（permissions.deny）：当前没有加载，省不了", text)
        self.assertIn("- lsp：140（2 个工具）", text)
        self.assertFalse((home / ".claude/settings.json").exists())

    def test_measure_rejects_context_without_system_parts(self):
        # 没登录的 claude 跑 /context 只报 skill，不能当成开局合计
        home = self.home()
        partial = "### Estimated usage by category\n\n| Category | Tokens | Percentage |\n|---|---|---|\n| Skills | 618 | 0.3% |\n| Free space | 166.4k | 83.2% |\n"
        result, text = self.run_quiet(home, ["--measure"], run_context=mock.Mock(return_value=partial))
        self.assertEqual(result, 2)
        self.assertIn("只报了 Skills", text)
        self.assertNotIn("开局合计", text)

    def test_scratch_dir_removes_its_project_folder_only(self):
        home = self.home()
        projects = home / ".claude/projects"
        other = projects / "-Users-me-work"
        other.mkdir(parents=True)
        with mock.patch.object(pathlib.Path, "home", return_value=home):
            with cleanup.scratch_dir("claude-context-") as cwd:
                name = cleanup.re.sub(r"[^A-Za-z0-9]", "-", str(pathlib.Path(cwd).resolve()))
                leftover = projects / name / "memory"
                leftover.mkdir(parents=True)
                mcp_logs = home / "Library/Caches/claude-cli-nodejs" / name / "mcp-logs-notes"
                mcp_logs.mkdir(parents=True)
        self.assertFalse(leftover.parent.exists())
        self.assertFalse(mcp_logs.parent.exists())
        self.assertFalse(pathlib.Path(cwd).exists())
        self.assertTrue(other.exists())

    def test_claude_exe_falls_back_to_installer_locations(self):
        home = self.home()
        installed = home / ".local/bin" / ("claude.exe" if sys.platform == "win32" else "claude")
        installed.parent.mkdir(parents=True)
        installed.write_text("")
        with mock.patch.object(pathlib.Path, "home", return_value=home), mock.patch.object(cleanup.shutil, "which", return_value=None):
            self.assertEqual(cleanup.claude_exe(), str(installed))
            installed.unlink()
            with self.assertRaises(FileNotFoundError):
                cleanup.claude_exe()

    def test_context_report_and_settings_helpers_on_fresh_machine(self):
        home = self.home()
        result, text = self.run_quiet(home, ["--context"])
        self.assertEqual(result, 0)
        self.assertIn("近 60 天没有会话记录", text)
        self.assertEqual(cleanup.coverage((cleanup.dt.date.today() - cleanup.dt.timedelta(days=52)).isoformat(), 60)[-7:], "距今 52 天")
        self.assertIn("MCP 服务器（用户级配置的，加上日志里出现过的）：\n- 无", text)
        result, text = self.run_quiet(home, ["--backup-settings"])
        self.assertEqual((result, "还没有 settings.json" in text), (0, True))
        result, text = self.run_quiet(home, ["--check-settings"])
        self.assertEqual((result, "settings.json 不存在" in text), (2, True))
        self.assertFalse((home / ".claude/settings.json").exists())

    def test_claude_env_rereads_settings_inside_a_session(self):
        home = self.home()
        cleanup.write_json(home / ".claude/settings.json", {"env": {"ENABLE_TOOL_SEARCH": "true"}})
        cleanup.write_json(home / ".claude/settings.json.bak-20261026-100000", {"env": {"ENABLE_LSP_TOOL": "0", "CLAUDE_CODE_SIMPLE": "1"}})
        inherited = {"ENABLE_TOOL_SEARCH": "auto", "ENABLE_LSP_TOOL": "0", "CLAUDE_CODE_SIMPLE": "0", "HTTPS_PROXY": "http://p", "CLAUDE_CODE_ENTRYPOINT": "claude-desktop"}
        with mock.patch.object(pathlib.Path, "home", return_value=home):
            os.environ.update(inherited)
            self.assertEqual(cleanup.claude_env(), {**os.environ})  # 不在会话里：原样
            os.environ["CLAUDECODE"] = "1"
            env = cleanup.claude_env()
        # 会话启动时带进来的旧值去掉，子进程从文件重新读；桌面版设的 CLAUDE_CODE_SIMPLE=0 和其他变量保留
        self.assertNotIn("ENABLE_TOOL_SEARCH", env)
        self.assertNotIn("ENABLE_LSP_TOOL", env)
        self.assertNotIn("CLAUDECODE", env)
        self.assertEqual((env["CLAUDE_CODE_SIMPLE"], env["HTTPS_PROXY"], env["CLAUDE_CODE_ENTRYPOINT"]), ("0", "http://p", "claude-desktop"))

    def test_measure_labels_environment_and_simple_mode(self):
        home = self.home()
        sample = CONTEXT_SAMPLE.format(tools="900")
        for environ, settings, expect in [
            ({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "claude-desktop", "CLAUDE_CODE_SIMPLE": "0"}, {"env": {"CLAUDE_CODE_SIMPLE": "1"}}, ("按当前桌面版会话的环境测", False)),
            ({}, {"env": {"CLAUDE_CODE_SIMPLE": "1"}, "permissions": {"deny": ["ListAgents"]}}, ("按终端版测", True)),
        ]:
            with (
                mock.patch.dict(os.environ, environ),
                mock.patch.object(pathlib.Path, "home", return_value=home),
                mock.patch.object(cleanup, "claude_exe", return_value="/fake/claude"),
                mock.patch.object(cleanup, "run_context", return_value=sample),
            ):
                text = "\n".join(cleanup.measure_report(home, settings, None))
            self.assertIn(expect[0], text)
            self.assertEqual("开着最小模式" in text, expect[1])
            self.assertEqual("ListAgents：已经在 permissions.deny 里" in text, expect[1])
            self.assertEqual("禁用 ListAgents（permissions.deny）" in text, not expect[1])

    def test_measure_mounts_desktop_skills_only_in_desktop_sessions(self):
        home = self.home()
        manifest = home / "Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/a/b/manifest.json"
        cleanup.write_json(manifest, {"skills": [{"name": "docx", "enabled": True}]})
        for environ, mounted in [({}, False), ({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "claude-desktop"}, True)]:
            run = mock.Mock(return_value=CONTEXT_SAMPLE.format(tools="900"))
            with (
                mock.patch.dict(os.environ, environ),
                mock.patch.object(cleanup.sys, "platform", "darwin"),
                mock.patch.object(pathlib.Path, "home", return_value=home),
                mock.patch.object(cleanup, "claude_exe", return_value="/fake/claude"),
                mock.patch.object(cleanup, "run_context", run),
            ):
                text = "\n".join(cleanup.measure_report(home, {"enableArtifact": False, "permissions": {"deny": list(cleanup.WHAT_IF_DENY)}}, None))
            self.assertEqual("--plugin-dir" in run.call_args_list[0].args[0], mounted)
            self.assertIn("只在桌面版会话里加载" if not mounted else "已挂上一起测", text)

    def test_context_mode_runs_under_claude_and_is_read_only(self):
        home = self.home()
        settings = {"env": {"ENABLE_TOOL_SEARCH": "auto", "ANTHROPIC_BASE_URL": "http://proxy"}, "skillOverrides": {"alpha": "off"}}
        cleanup.write_json(home / ".claude/settings.json", settings)
        target = home / ".claude/skills/alpha/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\nname: alpha\n---\n", encoding="utf-8")
        printed = []
        with (
            mock.patch.object(pathlib.Path, "home", return_value=home),
            mock.patch.object(cleanup, "running_under_claude", return_value=True),
            mock.patch("builtins.print", side_effect=lambda *a, **k: printed.append(" ".join(map(str, a)))),
        ):
            self.assertEqual(cleanup.main(["--context"]), 0)
        text = "\n".join(printed)
        self.assertIn("env.ENABLE_TOOL_SEARCH：auto", text)
        self.assertIn("已设置（走自定义网关或代理）", text)
        self.assertNotIn("http://proxy", text)
        self.assertIn("alpha［off］：0 次", text)
        self.assertIn(f"用户设置：{home / '.claude' / 'settings.json'}", text)
        self.assertEqual(cleanup.read_json(home / ".claude/settings.json"), settings)

    def test_config_dir_follows_claude_config_dir(self):
        home = self.home()
        self.assertEqual(cleanup.config_dir(home), home / ".claude")
        self.assertEqual(cleanup.global_config(home), home / ".claude.json")
        os.environ["CLAUDE_CONFIG_DIR"] = str(home / "work")
        self.assertEqual(cleanup.config_dir(home), home / "work")
        self.assertEqual(cleanup.global_config(home), home / "work" / ".claude.json")

    def test_windows_desktop_skills_found_in_msix_package(self):
        home = self.home()
        os.environ["APPDATA"] = str(home / "AppData/Roaming")
        os.environ["LOCALAPPDATA"] = str(home / "AppData/Local")
        package = home / "AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/Claude"
        manifest = package / "local-agent-mode-sessions/skills-plugin/org/user/manifest.json"
        manifest.parent.mkdir(parents=True)
        cleanup.write_json(manifest, {"skills": [{"name": "docx", "enabled": True}]})
        with mock.patch.object(cleanup.sys, "platform", "win32"):
            self.assertIn(home / "AppData/Roaming/Claude", cleanup.desktop_data_dirs(home))
            self.assertEqual(cleanup.desktop_skill_plugin(home), (manifest.parent, [("docx", True)]))

    def test_backup_and_check_settings(self):
        home = self.home()
        path = home / ".claude/settings.json"
        cleanup.write_json(path, {"env": {"TOKEN": "secret"}})
        result, text = self.run_quiet(home, ["--backup-settings"])
        self.assertEqual(result, 0)
        backups = list(path.parent.glob("settings.json.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(cleanup.read_json(backups[0]), {"env": {"TOKEN": "secret"}})
        self.assertEqual(self.run_quiet(home, ["--check-settings"])[0], 0)
        path.write_text('﻿{"env": {}}', encoding="utf-8")  # 记事本存的带 BOM 的 UTF-8
        self.assertEqual(self.run_quiet(home, ["--check-settings"])[0], 0)
        path.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.run_quiet(home, ["--check-settings"])[0], 2)

    def test_probe_reports_failures(self):
        home = self.home()
        ok = subprocess.CompletedProcess([], 0, stdout="好\n", stderr="")
        bad = subprocess.CompletedProcess([], 1, stdout="", stderr="API Error: 400")
        self.assertEqual(self.run_quiet(home, ["--probe"], run_claude=mock.Mock(return_value=ok)), (0, "claude -p 正常回复：好"))
        self.assertEqual(self.run_quiet(home, ["--probe"], run_claude=mock.Mock(return_value=bad))[0], 2)

    def test_cleanup_refuses_outside_macos(self):
        home = self.home()
        with (
            mock.patch.object(cleanup.sys, "platform", "win32"),
            mock.patch.object(sys.stdout, "reconfigure", create=True),
            mock.patch.object(sys.stderr, "reconfigure", create=True),
        ):
            self.assertEqual(self.run_quiet(home, ["--audit"])[0], 2)


if __name__ == "__main__":
    unittest.main()
