---
name: codex-review
description: Dual-model code review via Codex CLI. Two GPT models review independently, Claude arbitrates disagreements. Supports review (read-only), fix (write), audit (full security scan), and autopilot (unattended) modes. Triggers on "review", "let Codex check", "security audit", "OWASP", "full scan". Also auto-triggers after complex coding tasks.
---

## Prerequisites

- **Codex CLI** installed and authenticated: `npm install -g @openai/codex` then `codex login`
- An OpenAI account with access to GPT-5.4 and GPT-5.2 (or adjust model names below)

---

### Roles

- **Codex (Model A + Model B)**: Two independent reviewers examining the same code simultaneously, unaware of each other
- **Claude**: Controller + arbitrator. Constructs prompts, dispatches both models in parallel, compares findings, adjudicates disagreements, makes final decisions

---

### Modes

| Signal | Mode | Sandbox |
|--------|------|---------|
| review / check / look at | review | `read-only` |
| fix / modify / let Codex fix | fix | `workspace-write` |
| security audit / OWASP / full scan | audit | `read-only` |
| autopilot / unattended / long-running | autopilot | `read-only` |
| unclear | default to review | `read-only` |

**autopilot mode**: When the user is away and Claude is executing code tasks autonomously. After Codex review results come back, Claude arbitrates and decides whether to fix without asking the user. Decision criteria:
1. PRD documentation is the ultimate judge — if the PRD explicitly states something, follow the PRD
2. If the PRD doesn't cover it, check existing code behavior before deciding
3. Only record items needing confirmation when they involve product direction / business logic tradeoffs; batch-report at the end

Autopilot is not the default — requires explicit user request ("autopilot", "unattended", "run without me").

---

### Post-Arbitration Action Classification

After arbitration, Claude handles each finding by these rules:

**Fix directly (don't ask the user)**:
- Code bugs, compile/runtime errors
- Documentation wording / phrasing contradictions (not direction choices)
- Inconsistencies with explicit PRD decisions
- Security vulnerabilities

**Must ask the user (don't skip any)**:
- Product/business decisions needed (feature tradeoffs, scope changes)
- User-provided information needed (credentials, domains, third-party service configs)
- Choices affecting user experience not covered by PRD
- Cost/budget decisions

In autopilot mode, "must ask" items are accumulated and batch-reported at the end without interrupting execution.

---

### Dual-Model Parallel Review

Each review dispatches **two parallel `codex exec` calls via Bash**, one per model:

```bash
# Model A (run in parallel with Model B)
codex exec -m "gpt-5.4" -s "read-only" -C "$REPO_DIR" \
  --skip-git-repo-check --ephemeral \
  -o /tmp/codex-review-a.md \
  - <<'PROMPT'
[constructed prompt here]
PROMPT

# Model B (run in parallel with Model A)
codex exec -m "gpt-5.2" -s "read-only" -C "$REPO_DIR" \
  --skip-git-repo-check --ephemeral \
  -o /tmp/codex-review-b.md \
  - <<'PROMPT'
[same prompt here]
PROMPT
```

**Both calls use the same prompt but different models.** Wait for both results before entering arbitration.

**For fix mode**, only one model executes the fix (default Model A), but the review phase still uses both models:

```bash
codex exec -m "gpt-5.4" -s "workspace-write" -C "$REPO_DIR" \
  --skip-git-repo-check --full-auto \
  -o /tmp/codex-fix.md \
  - <<'PROMPT'
[fix prompt here]
PROMPT
```

**To resume a session** (for review-fix-review cycles):

```bash
codex exec resume SESSION_ID "follow-up prompt here"
```

The session ID is printed in the codex exec output header (look for `session id: xxx`).

---

### Arbitration: Claude as Judge

When both sets of findings arrive, Claude processes them in three zones:

**Consensus zone** — Both models flagged the same issue. Essentially confirmed; adopt directly. If fix suggestions differ, pick the one with harder evidence (file:line + code quote > vague description).

**Single-source zone** — Only one model flagged it. Claude reads the code to verify:
- Hard evidence (specific line + reproducible logic chain) → adopt
- Soft evidence ("might be a problem" without pinpointing) → downgrade to suggestion, don't force fix
- Claude judges it's a false positive → discard, explain reasoning in output

**Conflict zone** — Two models disagree (A says problem, B says fine). Claude reads the code and rules. If unresolvable (e.g., business logic judgment), escalate to user.

**Output format**: Tag each finding with its source — `[A+B]` consensus, `[A]` or `[B]` single-source, `[Conflict→Claude]` conflict. User sees at a glance which findings are iron-clad vs. single opinions.

---

### Invocation Parameters

**`-C` must be set to the current working directory** (Codex needs access to the same codebase).

**Don't embed file contents in the prompt** — Codex can read files itself. Only provide absolute paths in the prompt and let Codex read them. Save the token budget for review requirements, context, and focus areas.

**Use `--ephemeral` for one-shot reviews** (no session persistence needed). Omit it when you plan to do review-fix-review cycles.

**Use `--skip-git-repo-check`** when the target directory isn't a git repo.

---

### Prompt Construction

Before constructing the prompt, **assess the scenario and read the corresponding reference file**:

| Scenario | Reference |
|----------|-----------|
| Security audit (full scan) | `references/security-audit.md` |
| Security-sensitive (auth/payment/data/crypto) | `references/code-security.md` |
| Non-code (docs/config/prompts) | `references/non-code.md` |
| Other | `references/general.md` |
| **Before every prompt** | Scan `references/experience-log.md` for known pitfalls |

#### XML Block Structure

All prompts sent to Codex use XML blocks, each with a fixed responsibility:

| XML Block | Purpose | Principle |
|-----------|---------|-----------|
| `<task>` | Define the task and review objective | One run = one task, no mixing |
| `<context>` | Code/content/diff/project background | Facts only, no judgments; paths for Codex to read |
| `<instructions>` | Review dimensions + per-finding output format | Require evidence: file:line + issue + reason + fix |
| `<grounding_rules>` | Inference vs. confirmation boundary | Inferences must be labeled "Inference:"; never stated as confirmed |
| `<verification_loop>` | Anti-rubber-stamp | Final check: each finding is material, supported, reproducible |
| `<dig_deeper_nudge>` | Second-order check list | Guide Codex to check cross-file impact, edge cases, error paths |
| `<review_coverage>` | Review scope declaration | Explicitly state what was and wasn't checked |
| `<verdict>` | Final judgment | Pass / Conditional pass / Fail |
| `<default_follow_through_policy>` | Behavior on missing context | Write "Cannot verify: [reason]" when uncertain; don't guess |
| `<action_safety>` | Fix mode only | Restrict change scope, no unrelated refactoring |

**Block selection by mode**: review/audit must include `grounding_rules + verification_loop + dig_deeper_nudge + review_coverage + verdict`; fix mode adds `action_safety`, removes `dig_deeper_nudge`.

**Anti-rubber-stamp**: If either model returns "No issues found", check `review_coverage` scope adequacy. If scope is too narrow, do one more round. Both models say clean + adequate scope → pass.

---

### Review-Fix Cycle

1. Claude finishes implementation → constructs prompt → **parallel dispatch to both models**
2. Both findings arrive → Claude arbitrates (consensus / single-source / conflict)
3. Adopted findings → Claude fixes
4. After fix → **parallel dispatch both models again** for re-review
5. Both pass + adequate review scope → cycle ends
6. **Max 3 rounds**. Beyond 3 → stop and report to user

**Re-review prompt** (new session, include diff):
```
Fixed the previous round's findings. Changes made:
- [Issue 1]: [what was done]
- [Issue 2]: [rejected, reason: ...]

Updated diff:
[diff]

Please re-review. Confirm fixes are correct and check for new issues.
```

---

### Session Continuity

After each review, report both session IDs to the user:

```
Model A session: SESSION_ID_A
Model B session: SESSION_ID_B
```

---

### When to Trigger

**Review needed**: New features (>=2 files or new functions), refactoring, complex bug fixes, user explicitly requests, high-risk scenarios.

**Skip**: Typos/naming/comments, single-line simple fixes, formatting adjustments, user asks for quick turnaround.

---

### Interaction Language

- To Codex: match the user's language (Chinese prompt → Chinese review)
- To user: match the user's language
