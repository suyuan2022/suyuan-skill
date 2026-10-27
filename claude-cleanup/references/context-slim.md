# 上下文瘦身

目标：让新会话开局少装用不上的东西，把上下文留给干活。只改 `~/.claude/settings.json` 里的几个键，不删文件，每一项都能改回去；改完新开会话才生效，所以 Claude 开着也能做，不受「本机清理」里「Claude Code 只能审计」那条限制。

这些都是可逆的设置修改：由你在对话里跟用户讲清楚、得到同意后直接改，不走终端脚本的 CONFIRM。用户没点头的项一律不动。个别做法要动 `settings.json` 以外的文件，文中会单独标出，动之前要再问一次。

## 步骤

macOS 和 Windows 都能做。各平台的配置文件在哪、Windows 上怎么写，见文末「配置在哪、怎么写」。

下面的命令都在本 skill 的目录下运行（加载 skill 时给出的那个目录，不是用户的项目目录）。Windows 上先确认有没有 Python：依次试 `py -3 --version`、`python --version`，能打印版本号的就用它代替文中的 `python3`。输出 "Python was not found"，或者弹出微软商店，都算没装。

没有 Python 时脚本用不了，退一步做：按文末的表告诉用户配置在哪；直接读 `settings.json` 看现状；请用户在 Claude 里跑 `/context`，或者把 Context 面板截图发来，代替步骤 1 的测量；用量统计这次就没有了，跟用户说明。

1. **摸底**。这一步只读，跟用户说一句接下来做什么就直接跑：会读近 60 天的会话日志做统计，再在空的临时目录里起几次 `claude -p "/context"` 测占用，大约半分钟，不改任何配置。

   ```bash
   python3 scripts/claude_cleanup.py --context --measure
   ```

   - `--context`：先列出这台机器上用户设置、全局配置、会话日志、桌面版数据各在哪；再统计每个内置工具、MCP 服务器、skill 近 60 天（`--days N` 可改）用了几次、涉及几个会话、最近哪天；每个用户 skill 的状态，以及「被提到」：提到它的定时任务、`~/.claude/CLAUDE.md`、`~/.claude/agents`、`~/.claude/commands` 和其他用户 skill。项目里的文件和 hooks 不在扫描范围内。
   - skill 的用量算的是 Skill 调用、斜杠命令和用 Read 读它的 SKILL.md；用 Bash 读文件、被脚本直接调用的都不算，所以 0 次不等于没人用，要结合「被提到」看。
   - 报告第二行是日志实际覆盖到哪天、距今几天。会话日志只保留 `cleanupPeriodDays` 天（默认 30），覆盖不满 60 天时，按实际天数跟用户说。
   - `--measure`：开局合计和各类占用、每个 skill 简介的 token 数（和 `--context` 一起跑时，每行还带用量和「被提到」）、每个 MCP 服务器的工具说明大小，以及临时关掉 Artifact、ScheduleWakeup、ListAgents、LSP、PowerShell 后各能省多少。带 `(deferred)` 的是按需加载部分，只有名字常驻，不计入开局合计。
   - 测量按你所在的环境来：在桌面版会话里跑，测的是桌面版新会话的样子（app 自带的工具不在内，账号同步的 skill 会挂上）；在终端里跑，测的是终端版。报告第一行写明是哪种。
   - **skill 的占用看 Skills 一栏，别看合计。** `/context` 把 skill 列表从 System tools 里扣出来单列，可它实际放在第一条消息里，所以开局合计没算这部分：关掉 skill 时合计不变、System tools 等量上涨，真实请求却确实变小了。报告里「估计真实开局」是把 Skills 一栏加回去的数。
   - **最小模式先处理。** 设置现状里 `env.CLAUDE_CODE_SIMPLE` 是 `1` 时，终端版测到的只是最小模式的占用，skill 和 MCP 都没有数，后面几步没法判断。先照「最小模式」一节问用户；用户要关，就先照第 4、5 步删掉它、重测，拿重测的数当基线，汇报时两个数都写。
   - 测量失败时，用量统计照样会先打印出来；开局占用改用用户发来的 Context 面板。常见原因：找不到 `claude` 命令行（脚本会找 PATH、`~/.local/bin`、`~/.claude/local`），或者它还没登录：没登录时 `/context` 只报得出 skill 占用，脚本会直接报失败，不拿这个数当开局合计。

   用户在 Claude 桌面版里时（你手上有 `mcp__ccd_` 开头的 app 工具，或者用户提到桌面版、Context 面板），请用户新开一个会话，把 Context 面板截图发来。桌面版另有 app 自带的工具和说明，终端测不到，两边要对照着看。

   完成标准：手里有开局合计、各类占用，以及每个候选项的用量和 token 数。

2. **出清单**。对照下面的「杠杆」逐类判断，给用户一张表，每行一项，写清：
   - 改什么：哪个键、改成什么值；
   - 依据：近 N 天用了几次、最近一次是哪天、有没有被提到；
   - 能省多少：`--measure` 里读到或模拟出的数，自己推算的标「估计」；
   - 代价：关掉后哪些事做不了，谁在依赖它；
   - 怎么改回。

   表外用一两句交代占得多、但不该关或关不掉的部分，以及原因。能省的加起来不到开局合计的 5% 时，照实告诉用户收益很小，由用户决定改不改。

   完成标准：开局占用超过 1k 的每一类都有结论（关、留、或关不掉），每个候选项都有用量数字。

3. **等用户逐项点头**。用户问到哪一项，先回答清楚再往下走。

4. **改**。先备份，脚本会在 `settings.json` 旁边复制一份带时间戳的：

   ```bash
   python3 scripts/claude_cleanup.py --backup-settings
   ```

   还没有 `settings.json` 时，脚本会说不用备份，这时新建这个文件，只写用户同意的键。

   只改用户同意的键，`env` 里的密钥、hooks、权限、模型等其他内容原样保留。用 Edit 工具对那几行做最小替换。不要用 PowerShell 的 `ConvertFrom-Json` / `ConvertTo-Json` 读进来再写回去：它默认只保留两层嵌套，会把 hooks、permissions 截断，Windows PowerShell 5.1 还会写出 BOM。改完确认还是合法 JSON：

   ```bash
   python3 scripts/claude_cleanup.py --check-settings
   ```

5. **验证**。再跑一次 `--measure`，把改前改后的数字摆在一起：skill 类改动比 Skills 一栏，其他改动比开局合计。分类数只精确到 0.1k，几十 token 的改动看不出来，就写「太小，测不出」。它起的是新进程，会按改后的 settings.json 重新读（第 4 步的备份让它知道哪些键被删了），在当前会话里跑也作数。桌面版要请用户新开会话看 Context 面板，用户确认之前，这部分都算「未验证」。当前会话还是旧配置，在当前会话里看到的工具和 skill 不能当作验证结果。

   完成标准：每项改动都有改后的数字，或者明确标了「未验证」。

6. **汇报**：改了哪几项、开局从多少降到多少、备份文件在哪、每项怎么改回、还有哪些没验证。

## 杠杆

### 工具按需加载 `env.ENABLE_TOOL_SEARCH`

用户 MCP 多时，这通常是最大的一项。按需加载时，工具只有名字进上下文，模型要用时先通过 ToolSearch 取完整说明。

- `"auto"`：只有 MCP 工具说明超过上下文窗口 10% 时才按需加载，`"auto:N"` 可以改成 N%。窗口开得大（比如 60 万）时，这条线往往一直够不到。
- 没有设置时，默认行为随版本和接入方式变化。不用去推断，直接看 `--measure`：「MCP tools」那一行没带 `(deferred)`、而且有几千 token 以上，就说明没在按需加载，建议改成 `"true"`；已经带 `(deferred)` 就不用动。
- 走自定义 `ANTHROPIC_BASE_URL`（网关或代理）时，接口得支持 tool search。看 `--context` 里有没有用过 `ToolSearch`；没用过的话，改完跑一次 `python3 scripts/claude_cleanup.py --probe`，它会真发一句话；报错里有 400 就改回去。
- `env.CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` 有值时（走网关的配置里常见），`"true"` 会被它压掉，按需加载照样关着。这时要写 `"force"`，而且只在直连 Anthropic 接口或自定义网关时有效，Bedrock、Vertex 不行。改完同样用 `--measure` 看「MCP tools」有没有带上 `(deferred)`。
- 代价：模型第一次用某个工具前要多一次 ToolSearch 调用。

### 内置 LSP 工具 `env.ENABLE_LSP_TOOL`

先看 `--measure` 里「禁用 LSP」那一行：写着「当前没有加载」就不用动。有占用、而 `--context` 的内置工具里没有 `LSP` 这一行（没出现就是 0 次）时，设成 `"0"`；`enabledPlugins` 里的语言服务器插件（名字形如 `*@claude-code-lsps`）同时设成 `false`。LSP 类的 MCP 服务器是另一回事，按 MCP 的规则判断。

### 插件 `enabledPlugins`

插件里的 skill 不受用户级 `skillOverrides` 控制，只能整个插件关：`"<插件>@<市场>": false`。`settings.json` 里已经有的 `插件名:skill名` 形式的 `skillOverrides` 键不起作用，看到了要告诉用户。

桌面版会把账号同步的 skill 当成插件 `anthropic-skills@inline` 挂进来，包括 docs、docx、pdf、pptx、xlsx、computer-use 和浏览器使用说明，每个 150 到 350 token。app 设置里只能关掉其中一部分，剩下的只能整个插件关。`--context` 的「桌面版账号同步的 skill」列出了每一项的用量，［］里是 app 设置里的开关，不代表实际加载。

整个插件关掉，里面每一项都会一起没了，包括近期还在用的。所以把用过的那几项连同次数写进「代价」，让用户定。另一个代价是：以后在 app 里再打开的这类 skill 也不会出现，要用得先把这一项改回 `true`。

### 用户 skill `skillOverrides`

候选：近 N 天 0 到 1 次、没被提到的。状态是「仅手动触发，不占开局」的不用管，关了也省不了。统计窗口内才装上的新 skill 不按 0 次判：看 skill 文件夹的创建时间，看不出来就问用户。

关一个能省多少，看 `--measure` skill 表里那一项的数；`"name-only"` 还会留下名字。`~/.claude/commands/` 里的命令也出现在这张表里（来源标 User），同样按命令名用 `skillOverrides` 关。

`--context` 里的［on］表示没设覆盖，正常加载。要设覆盖时，键是 skill 名，值有三种，按 skill 怎么被用来选：

- `"off"`：模型看不到，`/名字` 也不能用。适合确定不用的。
- `"user-invocable-only"`：模型看不到，`/名字` 还能用。适合只靠用户敲斜杠命令触发的。
- `"name-only"`：只列名字、不带简介。适合要靠别的 skill 或流程按名字调用、但不需要模型自己想起来的。

「被提到」要分清是不是依赖：

- 被定时任务、CLAUDE.md、agent，或者流程类 skill 按名字调用的，是依赖，不能用 `"off"`。
- 只是被索引类 skill（按需去读别的 skill 的那种）列在表里的，不算依赖；设 `"off"` 以后，索引照样能按路径读它。
- 拿不准的，读那一段原文再判断。

用户有索引类 skill 时，可以建议把低频 skill 登记进索引再设 `"off"`。这要改那个索引 skill 的文件，单独征得同意。

### 自带 skill

`--measure` 的 skill 表里来源是 Built-in 的，是 Claude Code 自带的 skill，同样用 `skillOverrides` 关。注意几点：

- `schedule` 管的是云端定时 agent，跟桌面版的本地定时任务无关。
- `artifact-design` 等 `artifact-*` 是 Artifact 工具要用的，Artifact 开着就留着。
- 依赖看 `--measure` skill 表里那一行的「被提到」（要和 `--context` 一起跑才有）。
- 逐个用 `skillOverrides` 关。设置里的 `disableBundledSkills` 和环境变量 `CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` 是总开关，会把自带 skill 全部拿掉（`artifact-*` 也在里面），只在用户明确要全关时用。
- 看名字判断不了用途的，归到「留」，或者问用户。

### Artifact 工具 `enableArtifact`

在 Claude Code 2.1.308 上实测常驻约 11k token，是内置工具里最大的一项，以 `--measure` 的结果为准。它没法改成按需加载，只能整个关。

设成 `false` 之后，下面这些都用不了：发布网页、Artifact 评论，以及在 Code 里做设计稿、原型、幻灯片（Design 和 Slides 类型）。`/design-sync` 不受影响。

项目级设置只能关、不能开。以后要用时，得把用户级这一项改回来，再新开会话。

### PowerShell 工具（仅 Windows）`env.CLAUDE_CODE_USE_POWERSHELL_TOOL`

Windows 上装了 Git for Windows 时，Claude Code 用 Git Bash 跑 Bash 工具；用 claude.ai 订阅或 Console 账号登录的，同时默认还开着 PowerShell 工具。`--measure` 里「禁用 PowerShell」那一行有占用、`--context` 里 PowerShell 用量又是 0 时，可以设成 `"0"`。

没装 Git for Windows 时，PowerShell 是唯一能跑命令的工具，关了 Claude 就没法执行命令，这种情况不要关。判断方法：看你自己当前的工具里有没有 Bash，或者跑一次 `git --version`。不要只看历史用量，日志里的 Bash 可能来自 WSL 或者已经卸载的 Git。

### 其他工具 `permissions.deny`

把工具名写进 `permissions.deny`，会把这个工具从工具列表里拿掉。对 Claude Code 内置工具和用户自己配的 MCP 工具有效；`--measure` 测了下面几个，`--context` 内置工具列表里没出现的就是 0 次，用量为 0 的才考虑关：

- ScheduleWakeup：让模型自己定什么时候接着干，`/loop` 不写间隔时靠它。关了以后 `/loop` 得写固定间隔。
- ListAgents：列出能发消息的 subagent、agent 团队成员和本机其他会话。不用 agent 团队、也不在会话之间互发消息的用不上。
- LSP：见上面「内置 LSP 工具」。
- PowerShell：先照上一节确认装了 Git Bash。

写进 deny 以后，`--measure` 里这一项会显示「已经在 permissions.deny 里」，省下的看开局合计和 System tools 的变化。

桌面版 app 自带的 MCP（日志里标「app 或项目提供」的，比如画图的 `mcp__visualize`）写进 deny 也照样加载。这是在桌面版主会话里实测的；subagent 的工具列表另有过滤，不能拿来判断。Bash、Read、Edit、Write、Agent、Skill、ToolSearch 这些核心工具不动。

### MCP 服务器

按需加载开着时，MCP 工具只占名字，一般不用动。确实用不上的用户级服务器，在 `permissions.deny` 里写 `mcp__<服务器名>`，把它的工具整组拿掉，删掉这一行就能恢复。

`claude mcp remove` 会把服务器配置（命令、参数、可能带密钥的 env）从 `~/.claude.json` 里删掉，没法一键改回，默认不用。用户坚持要删时，先 `claude mcp get <名字>` 记下配置，再把 `.claude.json` 复制一份备份（位置看 `--context` 开头），并在汇报里写明怎么用 `claude mcp add-json` 加回来。Windows 上这条命令里 JSON 的引号写法随 shell 不同，照记下的配置原样填；用 npx 启动的服务器，命令是 `cmd /c npx ...`，别漏了 `cmd /c`。

不想加载 claude.ai 账号里的连接器，在 settings.json 顶层写 `"disableClaudeAiConnectors": true`。老写法 `env.ENABLE_CLAUDEAI_MCP_SERVERS` 设成 `"false"` 现在也还认，已经这么写的不用改。

### 最小模式 `env.CLAUDE_CODE_SIMPLE`（不建议）

设成 `"1"` 后，终端版只剩几个基本工具，skill、MCP、hooks、插件、CLAUDE.md 都不加载。不当作瘦身手段推荐，因为：

- 用订阅登录（OAuth）的用户，终端会直接显示没登录；API key、网关 token（`ANTHROPIC_AUTH_TOKEN`）、`apiKeyHelper` 照常能用。
- 只对终端版生效。桌面版 app 会把它覆盖成 `0`，写了也没用。

`--context` 的设置现状里能看到它，`--audit` 和 `--measure` 发现它开着会提醒。是不是有意开的只能问用户：日志里有 skill 和 MCP 调用说明不了什么，那些可能来自桌面版，而桌面版不受它影响。本 skill 的旧版本会替用户开它。用户说不要，就照第 4 步删掉这一项。

只想临时用一次：`claude --bare` 是同一个模式，只管那一次启动，适合脚本里调用。想排查是不是哪项自定义配置出了问题，用 `claude --safe-mode`：自定义内容全部不加载，登录照常。

### CLAUDE.md（Memory files）

Memory files 是各级 `CLAUDE.md`，每个会话都会整份读进来。本 skill 不改它：告诉用户它有多大，建议用户自己精简，或者另开一个任务来精简。

### 关不掉的

下面这些要如实告诉用户，不要硬关：

- 桌面版 app 自带的工具（任务列表、收尾、开新会话、读终端等）和它的系统提示词，配置文件管不到。

## 配置在哪、怎么写

`--context` 开头会列出这台机器上的实际位置，以它为准。下表是默认位置：

| 内容 | macOS | Windows |
|---|---|---|
| 用户设置（本文改的就是它） | `~/.claude/settings.json` | `%USERPROFILE%\.claude\settings.json` |
| 全局配置（MCP 服务器、账号状态） | `~/.claude.json` | `%USERPROFILE%\.claude.json` |
| 会话日志 | `~/.claude/projects/` | `%USERPROFILE%\.claude\projects\` |
| 用户 skill | `~/.claude/skills/` | `%USERPROFILE%\.claude\skills\` |
| 组织下发的托管设置（只读） | `/Library/Application Support/ClaudeCode/managed-settings.json` | `C:\Program Files\ClaudeCode\managed-settings.json`，或注册表 `HKLM\SOFTWARE\Policies\ClaudeCode` |
| 桌面版数据 | `~/Library/Application Support/Claude/` | `%APPDATA%\Claude\`；商店版在 `%LOCALAPPDATA%\Packages\<包名>\LocalCache\Roaming\Claude\`，包名是 `Claude_pzs8sxrjxfjjc` 或 `AnthropicPBC.Claude_fnn82j28hfe8t` |

表里 Windows 一列是 cmd 的写法，`%USERPROFILE%` 这类变量在别的 shell 里不会展开。读写文件时优先用 `--context` 打印出来的绝对路径，交给 Read、Edit 工具。要在命令行里写，照 shell 换：

- PowerShell：`$env:USERPROFILE\.claude\settings.json`
- Git Bash：`"$USERPROFILE/.claude/settings.json"`，要加引号；反斜杠路径会被吃掉，改用正斜杠

补充几点：

- 设了环境变量 `CLAUDE_CONFIG_DIR` 时，上表的 `~/.claude` 整个换成它，`.claude.json` 也放在它下面。
- 用户设置在桌面版的 Code 和终端版之间是共用的，改一处两边都生效。
- 在 WSL 里跑的 Claude Code 用的是 Linux 那边的 `~/.claude`，跟 Windows 的是两套，要分别改。
- 托管设置由组织管理员下发，优先级最高，用户设置改不动它管着的键。遇到「改了不生效」，先跑 `claude` 里的 `/status` 看有没有托管来源。

各平台的键和写法都一样。Windows 上要注意这几点：

- `env` 里的值一律写成字符串，比如 `"ENABLE_TOOL_SEARCH": "true"`、`"CLAUDE_CODE_USE_POWERSHELL_TOOL": "0"`。
- JSON 里的 Windows 路径，反斜杠要写两个，或者改用正斜杠：`"C:\\Users\\me\\.claude-work"` 或 `"C:/Users/me/.claude-work"`。
- 用户想自己动手改时，在 PowerShell 里用 `notepad "$env:USERPROFILE\.claude\settings.json"` 打开。保存时编码选「UTF-8」，不要选「带有 BOM 的 UTF-8」。
- 脚本输出的中文在 PowerShell 里乱码时，先执行 `$env:PYTHONUTF8=1` 再跑。
