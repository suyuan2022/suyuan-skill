---
name: claude-cleanup
description: 在 macOS 上安全审计、完整备份、清理或重置 Claude Code 与 Claude Desktop 本机状态；在 macOS 和 Windows 上给开局上下文瘦身。适用于清理可再生缓存和日志、轮换本地 ID、重置桌面端登录态、移除应用、继承现有遥测状态或修改台北时区；也适用于开局上下文太大，想关掉用不上的工具、MCP、skill、插件来省 token，或者想知道 Claude Code 的全局配置在哪、怎么改。不用于规避封禁或平台风控。
---

# Claude 本机清理与上下文瘦身

先分清用户要哪件事：

- **本机清理**（只支持 macOS）：清缓存和日志、轮换本地 ID、重置登录态、移除应用、改时区。照下面的「运行顺序」用随附脚本执行。
- **上下文瘦身**（macOS、Windows 都行）：开局上下文太大，想关掉用不上的工具、MCP、skill、插件来省 token；也包括问 Claude Code 的全局配置在哪、怎么写。读 [`references/context-slim.md`](references/context-slim.md) 照做。

怎么分工：高风险、不可逆的操作只在终端跑脚本，由用户自己输入 CONFIRM；可逆的设置修改由 agent 在对话里讲清楚、得到用户同意后直接改。

## 本机清理

使用随附脚本执行，不要临时拼接 `rm`。脚本采用窄白名单、完整备份、一次最终知情确认和失败即停止。

### 运行顺序

1. 如果当前执行者就是 Claude Code，只运行只读审计并提醒用户切换到 Codex 或普通终端。不要让正在使用 `~/.claude` 的 Claude Code 自己清理该目录。

   ```bash
   python3 scripts/claude_cleanup.py --audit
   ```

2. 如果由 Codex 或普通终端执行，先运行审计并向用户说明：
   - 第一个写操作是完整复制并校验 `~/.claude`，同时备份 `~/.claude.json`；
   - 可再生缓存和日志会自动纳入最终清单，不逐项询问；
   - 身份、钥匙串、桌面端登录态和数据、应用和时区属于风险操作，仍由用户选择；
   - 所有移除只进入时间戳废纸篓目录，不会永久删除或清空废纸篓；
   - 保护路径和遥测设置保持不变。

3. 用户明确要求继续后，在真实终端运行：

   ```bash
   python3 scripts/claude_cleanup.py
   ```

   不要用管道代答，不要增加跳过确认参数。若只有自动安全清理且 Claude 正在运行，脚本直接跳过安全目标，不要求退出；若用户选择风险操作，再交由用户正常退出并复检。脚本不能自动结束进程。

4. 脚本显示展开后的完整清单。用户输入一次 `CONFIRM` 后才开始写盘。若需要修改时区，开机密码只能由用户在 macOS 原生 `sudo` 隐藏提示中输入；不要让用户把密码发给执行者，也不要读取或保存。

5. 结束后报告备份路径、废纸篓批次、实际选择、遥测继承结果和时区。任何中途停止都报告为部分完成，不能笼统声称清理成功。

### 自动安全清理

在 Claude Code 和 Claude Desktop 都已退出后，自动把下列现存目标纳入最终清单，无需逐项提问：

```text
~/.claude/cache
~/.claude/stats-cache.json
~/.claude/telemetry
~/.claude/usage.jsonl
~/.claude/usage.with-fix.jsonl
~/Library/Caches/claude-cli-nodejs
~/Library/Caches/com.anthropic.claudefordesktop*
~/Library/Logs/Claude
~/Library/Logs/DiagnosticReports/Claude*
~/Library/Application Support/CrashReporter/Claude*
```

这些目标必须仍通过脚本白名单检查，并且只移入废纸篓。`~/.claude/usage-data` 存的是 `/insights` 生成的报告，不算缓存，不自动清。

### 绝对保护范围

绝不删除或移动：

```text
~/.claude/projects、sessions、history.jsonl、file-history、debug
~/.claude/skills、plugins、hooks、commands、scripts、agents、mcp-servers、scheduled-tasks
~/.claude/backups、CLAUDE.md、settings.json、settings.local.json
任何项目目录、Git 仓库、Codex 会话，以及未明确列入白名单的路径
```

`settings.json` 只允许结构化修改被用户明确选择的键。保留其他 env、hooks、plugins、权限、模型、MCP、状态栏和秘密。目标与保护路径重叠时立即停止。

### 风险操作

- **本地身份轮换**：轮换 `~/.claude.json` 的 `userID`、`machineID`，清除已知账号缓存字段，并把同一组新值同步到 `~/.claude/backups/.claude.json.backup.*`。仅用于隐私和排障，不宣称能改变平台关联判断。
- **钥匙串**：删除 `Claude Code-credentials` 会退出 CLI 登录，单独选择。
- **Claude Desktop**：可选择清登录态和全部桌面版数据，或连 `/Applications/Claude.app` 一并移入废纸篓。桌面版数据目录 `~/Library/Application Support/Claude` 里不只有登录态，还有 Code 标签页的会话列表、No folder 会话里写下的文件（`scratch-workspaces`）、Cowork 会话和虚拟机镜像，选之前要跟用户讲清楚这些会一起进废纸篓。不能自动结束应用进程。
- **台北时区**：仅在 macOS 当前不是 `Asia/Taipei` 时询问。使用 `sudo systemsetup` 修改并验证。

### 遥测继承

逐值保存以下键：

```text
DISABLE_TELEMETRY
DO_NOT_TRACK
DISABLE_ERROR_REPORTING
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC
```

当前关闭就保持关闭；当前未关闭就不主动关闭。改变遥测状态不属于本 skill 的清理范围。

本 skill 不用于规避封禁、支付检查、设备或 IP 信誉、浏览器指纹或任何平台风控。
