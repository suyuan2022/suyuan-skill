---
name: cc-shield
description: |-
  Claude Code account protection — disable telemetry, clean device fingerprints, safe account switching after ban.
  Trigger this skill whenever the user mentions ANY of these: telemetry, privacy, ban, account switch,
  fingerprint, device ID, blocked, suspended, rate limit, data collection, analytics tracking,
  or Chinese equivalents: 遥测, 隐私, 封号, 换号, 指纹, 设备ID, 被封, 被ban, 限流, 数据收集,
  关闭追踪, 账号保护, 防封, 清理设备信息, 隐私审查, 隐私检查.
  Also trigger when the user says things like "protect my account", "stop tracking",
  "Claude Code is collecting data", "I got banned", "switch to a new account",
  "what does Claude Code know about me", "帮我关掉遥测", "我被封了", "怎么换号",
  "Claude Code 收集了什么数据", "帮我查一下隐私", even if they don't mention this skill by name.
---

# CC Shield — Claude Code Account Protection

## How to use this skill

When a user asks for help, figure out which scenario they need based on their message:

- Mentions **telemetry, tracking, data collection, privacy, 关遥测, 隐私保护** → **Scenario 1** (daily protection)
- Mentions **banned, blocked, suspended, switch account, 被封, 换号, 新账号** → **Scenario 2** (account switch)
- Mentions **audit, check, inspect, what data, 查一下, 检查, 审查** → **Scenario 3** (privacy audit)
- If unclear, ask one question to clarify: "You want to disable tracking, switch accounts, or check what's stored?"

## Background

Claude Code collects telemetry through two channels:

- **DataDog** (third-party analytics) — tool usage, errors, performance metrics
- **Anthropic's own servers** — event logging to `api.anthropic.com/api/event_logging/batch`

Each API request carries a **device ID** (random 64-char hex in `~/.claude.json`), **account UUID**, and **session ID**. Anthropic can see when multiple accounts share the same device ID.

Bans are **account-level** — they target your account based on behavior, not your hardware. But device ID is a linking signal: if a banned account and a new account share the same device ID, the new one is at risk.

The `DISABLE_TELEMETRY` env var is an officially supported privacy control built into Claude Code's source — not a hack or exploit.

## Scenario 1: Disable Telemetry (Daily Protection)

For users who want to stop data collection during normal use. No ban, no account switch.

### Steps

1. Read `~/.claude/settings.json`. If it doesn't exist, create it with `{}`.

2. Merge `DISABLE_TELEMETRY` into the `env` block — preserve any existing env vars:

```json
{
  "env": {
    "DISABLE_TELEMETRY": "1"
  }
}
```

3. Tell the user: telemetry is now off, takes effect on next Claude Code launch.

### What changes

- Both DataDog and first-party analytics channels stop sending data
- Conversations and tool use work exactly the same
- GrowthBook feature flags still load (new features still appear)

### Nuclear mode (optional)

If the user wants maximum privacy, also add `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"` to the env block. This additionally kills feature flag fetching, auto-update checks, and release notes. Tradeoff: remote feature flags won't activate.

## Scenario 2: Safe Account Switch (After Ban)

For users whose account was banned/suspended and need to log in with a different account without leaving traces that link the two.

Tell the user to **exit Claude Code completely** before starting.

### Step 1 — Delete OAuth credentials

**macOS:**
```bash
security delete-generic-password -a $USER -s "Claude Code-credentials" 2>/dev/null
```

**Linux:**
```bash
rm -f ~/.claude/.credentials.json
```

### Step 2 — Reset device ID and clear caches

```bash
python3 -c "
import json, os, secrets
config_path = os.path.expanduser('~/.claude.json')
with open(config_path, 'r') as f:
    d = json.load(f)
d['userID'] = secrets.token_hex(32)
for key in ['anonymousId', 'oauthAccount', 'cachedGrowthBookFeatures',
            'cachedStatsigGates', 'cachedDynamicConfigs', 'groveConfigCache',
            'metricsStatusCache', 'feedbackSurveyState', 'passesEligibilityCache',
            's1mAccessCache', 'cachedExtraUsageDisabledReason', 'clientDataCache']:
    d.pop(key, None)
with open(config_path, 'w') as f:
    json.dump(d, f, indent=2)
print(f'New device ID: {d[\"userID\"][:16]}...')
"
```

### Step 3 — Clear pending telemetry

```bash
rm -rf ~/.claude/telemetry/
```

These are failed telemetry events queued for retry. If not deleted, they'll be sent on next launch — potentially carrying the old account's identity.

### Step 4 — Log in

Tell the user to launch Claude Code and run `/login` with the new account.

### Verification

```bash
python3 -c "
import json, os
d = json.load(open(os.path.expanduser('~/.claude.json')))
print(f'Device ID: {d.get(\"userID\", \"MISSING\")[:16]}...')
acct = d.get('oauthAccount', {})
print(f'Account: {acct.get(\"emailAddress\", \"not logged in\")}')
"
```

Device ID should differ from before. Account should show the new email.

## Scenario 3: Privacy Audit

Show the user what Claude Code has stored locally about them.

Run these checks and present the results:

```bash
# 1. Device ID
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude.json'))); print(f'Device ID: {d.get(\"userID\",\"N/A\")}')"

# 2. Account info
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude.json'))); a=d.get('oauthAccount',{}); print(f'Email: {a.get(\"emailAddress\",\"N/A\")}'); print(f'Account UUID: {a.get(\"accountUuid\",\"N/A\")}'); print(f'Org UUID: {a.get(\"organizationUuid\",\"N/A\")}')"

# 3. Telemetry status
python3 -c "
import json,os
try:
    d=json.load(open(os.path.expanduser('~/.claude/settings.json')))
except: d={}
env=d.get('env',{})
t=env.get('DISABLE_TELEMETRY','0')
n=env.get('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC','0')
print(f'Telemetry disabled: {\"YES\" if t==\"1\" else \"NO\"}')
print(f'Non-essential traffic disabled: {\"YES\" if n==\"1\" else \"NO\"}')
"

# 4. Pending telemetry files
ls -la ~/.claude/telemetry/ 2>/dev/null && echo "WARNING: Pending telemetry files found — run 'rm -rf ~/.claude/telemetry/' to clear" || echo "No pending telemetry"

# 5. Keychain credentials (macOS only)
security find-generic-password -a $USER -s "Claude Code-credentials" 2>/dev/null && echo "OAuth credentials found in Keychain" || echo "No Keychain credentials"
```

Summarize findings in plain language. If telemetry is still on, recommend Scenario 1.

## Platform Reference

| Item | macOS | Linux | WSL |
|------|-------|-------|-----|
| Config | `~/.claude.json` | same | same |
| Settings | `~/.claude/settings.json` | same | same |
| Credentials | Keychain (`Claude Code-credentials`) | `~/.claude/.credentials.json` | same as Linux |
| Telemetry cache | `~/.claude/telemetry/` | same | same |
