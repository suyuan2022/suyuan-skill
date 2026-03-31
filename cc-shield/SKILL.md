---
name: cc-shield
description: |-
  Claude Code privacy & account protection. Close telemetry, clean device fingerprints,
  switch accounts safely. Use when user mentions: telemetry, privacy, ban, account switch,
  fingerprint, device ID, blocked, suspended, rate limit, or wants to protect their Claude Code account.
---

# CC Shield — Claude Code Account Protection

Protect your Claude Code account by managing telemetry, device identity, and safe account switching.

## Background Knowledge

Claude Code sends two types of telemetry data to Anthropic:

- **DataDog** — behavioral analytics (tool usage, errors, performance)
- **First-Party (1P)** — event logging to `api.anthropic.com/api/event_logging/batch`

Every API request also carries a **device ID** (random 64-char hex stored in `~/.claude.json` as `userID`), an **account UUID**, and a **session ID**. Anthropic can correlate accounts sharing the same device ID.

Ban decisions are made **server-side** based on account behavior, not device fingerprints. But device ID is used as an auxiliary signal to link accounts.

## Scenario 1: Daily Protection (Close Telemetry)

**When:** User wants to reduce data collection during normal use. No ban, no account switch.

**Action:** Add `DISABLE_TELEMETRY` to the user's Claude Code settings.

### Steps

1. Read the user's settings file. Check both paths:
   - `~/.claude/settings.json` (user-level)
   - `~/.claude/settings.local.json` (local override)

2. Add the environment variable to the `env` block:

```json
{
  "env": {
    "DISABLE_TELEMETRY": "1"
  }
}
```

If the `env` block already exists, merge — do NOT overwrite existing env vars.

3. Confirm to user: telemetry is now off. Takes effect on next Claude Code launch.

### What this does

- Kills both DataDog and 1P analytics channels
- API requests (your actual conversations) still work normally
- GrowthBook feature flags still load (new features still work)

### Optional: nuclear mode

If the user wants maximum privacy, also add:

```json
{
  "env": {
    "DISABLE_TELEMETRY": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
  }
}
```

This additionally disables: GrowthBook feature flag fetching, auto-update checks, release notes, and other non-essential network traffic. Tradeoff: some new features controlled by remote flags won't activate.

## Scenario 2: Account Switch After Ban

**When:** User's account was banned/suspended and they need to switch to a new account cleanly.

**IMPORTANT:** Exit Claude Code completely before running these steps.

### Steps

**Step 1 — Delete OAuth credentials from macOS Keychain:**

```bash
security delete-generic-password -a $USER -s "Claude Code-credentials" 2>/dev/null
```

On Linux, delete the plaintext fallback instead:
```bash
rm -f ~/.claude/.credentials.json
```

**Step 2 — Reset device ID and clear account caches:**

```bash
python3 -c "
import json, os, secrets
config_path = os.path.expanduser('~/.claude.json')
with open(config_path, 'r') as f:
    d = json.load(f)

# Generate new device ID
d['userID'] = secrets.token_hex(32)

# Clear old account identity
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

**Step 3 — Clear telemetry queue (failed events waiting to retry):**

```bash
rm -rf ~/.claude/telemetry/
```

**Step 4 — Launch Claude Code and log in with the new account:**

```bash
claude /login
```

### Verification

After login, verify the switch was clean:
```bash
python3 -c "
import json, os
d = json.load(open(os.path.expanduser('~/.claude.json')))
print(f'Device ID: {d.get(\"userID\", \"MISSING\")[:16]}...')
acct = d.get('oauthAccount', {})
print(f'Account: {acct.get(\"emailAddress\", \"not logged in\")}')
"
```

The device ID should be different from before, and the account should show the new email.

## Scenario 3: Privacy Audit

**When:** User wants to see what data Claude Code has stored locally.

### Steps

1. Show device ID:
```bash
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude.json'))); print(f'Device ID: {d.get(\"userID\",\"N/A\")}')"
```

2. Show account info:
```bash
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude.json'))); a=d.get('oauthAccount',{}); print(f'Email: {a.get(\"emailAddress\",\"N/A\")}'); print(f'Account UUID: {a.get(\"accountUuid\",\"N/A\")}'); print(f'Org UUID: {a.get(\"organizationUuid\",\"N/A\")}')"
```

3. Check if telemetry is disabled:
```bash
python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude/settings.json'))); env=d.get('env',{}); t=env.get('DISABLE_TELEMETRY','0'); n=env.get('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC','0'); print(f'Telemetry disabled: {\"YES\" if t==\"1\" else \"NO\"}'); print(f'Non-essential traffic disabled: {\"YES\" if n==\"1\" else \"NO\"}')"
```

4. Check for pending telemetry files:
```bash
ls -la ~/.claude/telemetry/ 2>/dev/null && echo "WARNING: Pending telemetry files found" || echo "No pending telemetry"
```

5. Check keychain (macOS):
```bash
security find-generic-password -a $USER -s "Claude Code-credentials" 2>/dev/null && echo "OAuth credentials found in Keychain" || echo "No Keychain credentials"
```

## Key Facts

- **Device ID** is NOT hardware-based. It's a random hex string in `~/.claude.json`. Delete it = new device.
- **Bans are account-level**, not device-level. But sharing a device ID across accounts lets Anthropic link them.
- **Telemetry** tracks: tool usage, errors, API calls, session duration, OS/platform info, memory/CPU usage. Disabling it stops all of this.
- **OAuth tokens** live in macOS Keychain (service: `Claude Code-credentials`) or `~/.claude/.credentials.json` on Linux.
- **Trusted device tokens** (90-day rolling) are also in the Keychain. They get cleared by `/logout`.
- The `DISABLE_TELEMETRY` env var is an **officially supported** privacy control in Claude Code's source, not a hack.

## Platform Notes

- **macOS**: Credentials are in Keychain. Use `security` commands.
- **Linux**: Credentials are in `~/.claude/.credentials.json` (plaintext, chmod 600).
- **Windows/WSL**: Follow Linux path for WSL, or check `%USERPROFILE%\.claude\` for native Windows.
