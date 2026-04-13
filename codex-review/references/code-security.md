# Code Review: Security-Sensitive

For auth, payments, data handling, encryption, access control, PII, secrets management.

## Review Dimensions

- **Auth/AuthZ**: Is authentication checked? Is authorization granular enough?
- **Input validation**: Is all external input validated and sanitized?
- **Injection**: SQL injection, command injection, XSS, template injection?
- **Secrets**: Are credentials hardcoded? Are they logged? Exposed in errors?
- **Data exposure**: Does the response leak internal state, stack traces, or other users' data?
- **Cryptography**: Appropriate algorithms? Proper key management? No homegrown crypto?
- **Race conditions**: Can concurrent requests bypass checks?
- **Audit trail**: Are security-relevant actions logged?

## Prompt Template

```xml
<task>
Security review. This code handles [auth/payment/user data/etc]. Review with adversarial mindset — assume an attacker is looking for weaknesses.
</task>

<context>
Changed files: [file list]
Diff: [diff content]
</context>

<instructions>
Think like an attacker. For each dimension, actively try to find an exploit:

1. Authentication: Can this endpoint be reached without valid credentials? Check middleware chain.
2. Authorization: Can user A access user B's data through this code path?
3. Input validation: What happens if input is malformed, oversized, or contains injection payloads?
4. Secrets: grep for hardcoded keys, tokens, passwords. Check if secrets appear in logs or error messages.
5. Data exposure: Does any response include fields the requester shouldn't see?
6. Race conditions: Can two concurrent requests produce an inconsistent state? (e.g. double-spend, TOCTOU)
7. Cryptography: Are algorithms current? (no MD5, SHA1 for security purposes, no ECB mode)
8. Audit: Are security events (login, permission change, data access) logged?

For each issue:
- Location: file:line
- Severity: critical / important / minor
- Attack scenario: how would an attacker exploit this
- Fix: concrete suggestion
</instructions>

<grounding_rules>
Ground every claim in the code.
If attacker behavior is an inference or theoretical risk, label it "Inference:" explicitly.
Do not confirm a vulnerability without identifying a concrete attack path.
</grounding_rules>

<verification_loop>
Before finalizing, verify each finding has a concrete, reproducible attack path — not just theoretical risk.
Remove findings that require unrealistic attacker prerequisites.
</verification_loop>

<default_follow_through_policy>
If you cannot verify a finding without runtime behavior or external service context, write "Cannot verify: [reason]" — do not guess.
</default_follow_through_policy>

<review_coverage>
Checked: [list of dimensions reviewed]
Not checked: [e.g., runtime behavior, external service responses — explain why]
</review_coverage>

<verdict>
Pass / Conditional pass (minor suggestions only) / Fail (must-fix issues present)
</verdict>
```

## Commonly Missed

- Authorization check on the route but not on the underlying service method (can be called internally without auth)
- Rate limiting absent on sensitive endpoints (brute force possible)
- Error messages that differ between "user not found" and "wrong password" (information leakage)
- JWT validation missing expiry check or audience check
- File upload without type/size validation
- Database query built with string concatenation instead of parameterized query
