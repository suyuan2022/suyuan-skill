# Security Audit: Full Codebase Scan

For proactive security audits of the entire codebase. Not diff-based — scans everything.

## When to Use

User says "安全审计" "security audit" "全量安全扫描" "OWASP" "帮我扫一遍安全问题".

## Workflow

Claude scans → collects findings → Codex independently verifies each finding (adversarial).

### Phase 1: Architecture Map (Claude)

Before scanning, map the attack surface:
- Entry points (API routes, webhooks, public endpoints)
- Auth boundaries (what's protected, what's not)
- Data stores (DB, cache, file system, external APIs)
- Trust boundaries (user input → server → DB → external service)

### Phase 2: OWASP Top 10 Scan (Claude via Grep)

For each category, run the specific patterns. Only report findings with confidence >= 8/10.

**A01 Broken Access Control**
- Missing auth middleware on routes
- Horizontal privilege escalation: `params[:id]` or `req.params.id` used without ownership check
- Direct object references without authorization

**A02 Cryptographic Failures**
- Grep: `MD5`, `SHA1`, `DES`, `ECB`, `Math.random` (for security), `crypto.createCipher` (deprecated)
- Hardcoded encryption keys, secrets in source
- HTTP for sensitive data transport

**A03 Injection**
- SQL: string concatenation in queries, template literals in SQL, `${}` in query strings
- Command: `exec(`, `system(`, `child_process`, `subprocess.call` with shell=True
- XSS: `dangerouslySetInnerHTML`, `v-html`, `innerHTML =`, unescaped template output
- Template: user input in template engine calls

**A04 Insecure Design**
- Missing rate limiting on auth/sensitive endpoints
- No account lockout mechanism
- Client-side-only validation without server-side mirror

**A05 Security Misconfiguration**
- CORS: `Access-Control-Allow-Origin: *` or wildcard with credentials
- Missing security headers (CSP, X-Frame-Options, HSTS)
- Debug mode in production config
- Default credentials in config files

**A07 Auth Failures**
- JWT: missing expiry check, missing audience validation, weak secret
- Session: no timeout, no invalidation on password change
- Password: no minimum complexity, no bcrypt/argon2

**A09 Logging Failures**
- Auth events not logged
- Admin actions not audited
- Sensitive data in logs (passwords, tokens, PII)

**A10 SSRF**
- User-controlled URLs in server-side HTTP requests
- No allowlist for internal service calls
- DNS rebinding possible

### Phase 3: Secrets Archaeology (Claude via Grep + Bash)

```bash
# Scan current code
grep -rn "AKIA\|sk-\|ghp_\|gho_\|github_pat_\|xoxb-\|xoxp-\|-----BEGIN.*PRIVATE" --include="*.{js,ts,py,go,rb,java,yaml,yml,json,env}" .

# Scan git history (last 100 commits)
git log -p --all -S "AKIA" --since="6 months ago" -- . | head -50
git log -p --all -S "sk-" --since="6 months ago" -- . | head -50
```

### Phase 4: Dependency Supply Chain (Claude via Bash)

- `npm audit` / `pip audit` / `bundle audit`
- Check for postinstall scripts in production dependencies
- Lockfile integrity (exists and committed)
- Pinned versions vs floating ranges in production deps

### Phase 5: CI/CD Pipeline (Claude via Grep)

- GitHub Actions: `pull_request_target` without restrictions
- Script injection: `${{ github.event.issue.title }}` in run blocks
- Unpinned actions (using `@main` instead of SHA)
- Secrets exposed to PR workflows from forks

### Phase 6: LLM/AI Security (if applicable)

- User input concatenated into system prompts (prompt injection)
- LLM output rendered as HTML without sanitization
- `eval()` or dynamic code execution on LLM output
- No token/cost limits on user-triggered LLM calls

## Phase 7: Codex Adversarial Verification

For every finding from Phases 2-6 with confidence >= 8/10:

```xml
<task>
Independent security finding verification. I found potential vulnerabilities in this codebase. For each finding below, independently verify:
1. Is this a real vulnerability or a false positive?
2. What is the actual exploitable attack path?
3. What is the actual severity (critical / high / medium / low)?

DO NOT trust my assessment. Read the code yourself and form your own conclusion.
</task>

<context>
Findings to verify: [list findings with file:line, description, and claimed severity]
Codebase context: [relevant file contents around findings]
</context>

<grounding_rules>
Ground every conclusion in code you have read directly.
If exploitability is an inference, label it "Inference:" explicitly.
Do not confirm a vulnerability without identifying a concrete, reproducible attack path.
</grounding_rules>

<structured_output_contract>
For each finding:
- Verdict: Confirmed / False positive / Needs more context
- Reasoning: independent of my assessment
- If confirmed: concrete exploit scenario
- If false positive: why the original assessment was wrong, grounded in the code
</structured_output_contract>

<verification_loop>
Before finalizing, verify that confirmed findings have a concrete attack path and that false positives have a clear rebuttal grounded in the code — not just "I didn't see a problem."
</verification_loop>
```

## False Positive Filters (skip these)

- `console.log` in development-only files
- Test files importing sensitive-looking strings
- Comments containing example credentials
- Disabled code behind feature flags
- Dependencies that include their own test fixtures with dummy secrets
- `innerHTML` used only with static/developer-controlled content
- CORS wildcards on truly public APIs with no credentials

## Output Format

```markdown
## Security Audit Report

**Scope**: [what was scanned]
**Date**: [date]
**Auditor**: Claude (scan) + Codex (verification)

### Critical
[findings confirmed by Codex, with exploit scenario]

### High
[findings confirmed by Codex]

### Medium
[findings confirmed by Codex]

### Disputed
[findings where Claude and Codex disagree — user decides]

### Not Checked
[areas that could not be scanned and why]
```
