# General Review Template

For all non-security scenarios. Use `code-security.md` for security-sensitive code.

---

## Prompt Template

Select context block based on whether there's a diff. Not every review has code changes.

```xml
<task>
Independently review [this code change / this plan / this document / this config]. Provide evidence-based findings only.
</task>

<context>
<!-- With diff -->
Changed files: [file list]
Diff: [diff content, or file paths for Codex to read]

<!-- Without diff (plan / design / architecture) -->
[plan content, or file paths for Codex to read]

User's original request: [verbatim, no interpretation]
Project context: [tech stack, relevant file paths, constraints — facts only, no commentary]
</context>

<instructions>
For each dimension below, explicitly state what you found — issues OR "checked, clean":

[select 5-7 dimensions from the scenario list below]

For each issue:
- Location: exact file:line or section
- Severity: critical (must fix) / important (should fix) / minor (suggestion)
- Evidence: quote the specific code or text that's wrong
- Why: why this is a problem, not just what's wrong
- Fix: concrete suggestion, not "consider improving"
</instructions>

<grounding_rules>
Ground every claim in the repository context or tool outputs.
If a point is an inference, label it "Inference:" explicitly. Do not present inferences as confirmed facts.
</grounding_rules>

<verification_loop>
Before finalizing, verify each finding is material and actionable.
Remove any finding that is vague, unsupported, or not reproducible from the provided context.
</verification_loop>

<dig_deeper_nudge>
Before finalizing, check for second-order failures:
- Cross-file impact (changed A, but B depends on A's old behavior)
- Empty-state and null handling
- Error paths (happy path correct but error path unhandled)
- Concurrent access or race conditions
- Stale state assumptions
- Rollback paths if partial failure occurs
</dig_deeper_nudge>

<default_follow_through_policy>
Keep going until you have enough evidence to assess each dimension.
If required context is absent, write "Cannot verify: [reason]" — do not guess.
</default_follow_through_policy>

<review_coverage>
Checked: [list of dimensions reviewed]
Not checked: [list of dimensions skipped and why]
</review_coverage>

<verdict>
Pass / Conditional pass (minor suggestions only) / Fail (must-fix issues present)
</verdict>
```

---

## Scenario Dimension List

Claude selects 5-7 dimensions from here to fill into `<instructions>`. Do not include all — pick the most relevant.

### Universal (include in almost every review)
- **Correctness**: Does the implementation match the stated request?
- **Edge cases**: Empty input, null, boundary values, unexpected types
- **Error handling**: Are failures caught? No silent swallowing?
- **Completeness**: Is anything from the user request unaddressed?

### New Feature
- **Entry points**: Are all entry points (routes, handlers, CLI commands) wired up?
- **Data flow**: Trace input → output. Every transformation stage handled?
- **Integration**: Does this work with existing code? Types, imports, interfaces consistent?
- **Side effects**: Could this break existing functionality?

### Bug Fix
- **Root cause**: Does this fix the actual cause or just the symptom?
- **Regression**: Could this change break something that was working?
- **Pattern search**: Does the same bug pattern exist elsewhere in the codebase?
- **Scope**: Is the fix minimal and targeted?

### Refactor
- **Behavioral equivalence**: For each modified function, same output for all inputs?
- **Interface preservation**: Public API signatures, return types, error formats unchanged?
- **Caller audit**: All callers of modified functions still compatible?
- **Removed code**: Confirm nothing depends on deleted pieces

### Infrastructure
- **Idempotency**: Safe to run twice? What happens on re-execution?
- **Rollback**: If fails halfway, what's the system state? How to recover?
- **Environment parity**: Works identically in dev, staging, prod?
- **Dependencies**: Versions pinned? Known vulnerabilities?

### Plan / Design / Architecture (no diff)
- **Feasibility**: Is this actually doable with stated constraints?
- **Alternatives**: Are there simpler or more proven approaches not considered?
- **Assumptions**: Are assumptions stated? Are any invalid or untested?
- **Failure modes**: What happens when things go wrong? Is there a fallback?
- **Scope creep**: Does the plan try to solve more than the stated problem?
- **Dependencies**: Are external dependencies identified and realistic?

### Non-Code (docs / config / prompts)
- **Accuracy**: Are technical claims and facts correct?
- **Internal consistency**: Does any section contradict another?
- **Audience fit**: Would the target audience understand this?
- **Missing guidance**: Happy path covered but what about error/failure cases?

---

## Common Misses (all scenarios)

These are the most frequently skipped areas. Claude also uses this list when evaluating whether Codex's review_coverage was sufficient:

- Cross-file impact (changed A but B depends on A's old behavior)
- Implicit assumptions (assumes input is always a certain format)
- Error paths (happy path correct but error path unhandled)
- Concurrency / race conditions (two calls modifying the same resource)
- Missing or unreasonable config defaults
- Interface behavior doesn't match documentation or comments
