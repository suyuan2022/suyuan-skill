# Review: Non-Code Content

For documents, proposals, configs, schemas, prompts, skill definitions, API specs, user-facing content.

## Scenario-Specific Dimensions

### Technical Document / Proposal
- Accuracy: Are technical claims correct?
- Completeness: Are there gaps in the argument or missing sections?
- Assumptions: Are assumptions stated explicitly? Are any invalid?
- Feasibility: Is the proposed approach actually doable with stated constraints?
- Contradictions: Does any part contradict another?

### Configuration / Schema
- Validity: Is the syntax correct? Will it parse?
- Compatibility: Does this work with the target system version?
- Defaults: Are default values sensible?
- Edge cases: What happens with empty/missing/malformed values?
- Security: Are there overly permissive settings?

### Prompt / Skill Definition
- Trigger accuracy: Will this trigger when it should and not trigger when it shouldn't?
- Instruction clarity: Could the executing model misinterpret any instruction?
- Edge cases: What happens with unusual or adversarial inputs?
- Output format: Is the expected output clearly specified?
- Conflicts: Does this conflict with other skills or system instructions?

### User-Facing Content
- Accuracy: Are all facts correct?
- Clarity: Would the target audience understand this?
- Consistency: Are terms and formatting consistent throughout?
- Completeness: Is anything important missing?
- Tone: Does it match the intended voice?

## Prompt Template

```xml
<task>
Independently review this [document type]. Provide evidence-based findings only.
</task>

<context>
Content: [absolute file path — let Codex read the file itself]
Background: [purpose, audience, constraints]
</context>

<instructions>
Evaluate against the following dimensions:
[select relevant dimensions from the scenario list above]

For each issue:
- Location: section / paragraph / line
- Severity: critical (must fix) / important (should fix) / minor (suggestion)
- Issue: quote the specific text that's wrong
- Fix: provide the concrete replacement text
</instructions>

<grounding_rules>
Ground every claim in the document content.
If a point is an inference about the author's intent or audience interpretation, label it "Inference:" explicitly.
Do not present inferences as confirmed facts.
</grounding_rules>

<verification_loop>
Before finalizing, verify each finding is supported by the document content, not by assumptions about what the author intended.
Remove findings that require knowledge outside the provided document.
</verification_loop>

<default_follow_through_policy>
If you cannot verify a claim without knowing the target audience's background or external context, write "Cannot verify: [reason]" — do not guess.
</default_follow_through_policy>

<review_coverage>
Checked: [list of dimensions reviewed]
Not checked: [list skipped and why]
</review_coverage>

<verdict>
Pass / Conditional pass (minor suggestions only) / Fail (must-fix issues present)
</verdict>
```

## Commonly Missed

- Internal inconsistency (section A says X, section B implies not-X)
- Stale references (links to docs that no longer exist, outdated version numbers)
- Implicit assumptions that aren't shared by the target audience
- Missing error/failure guidance (doc explains happy path but not what to do when things break)
- Format/schema valid but semantically wrong (correct JSON but values don't make sense)
