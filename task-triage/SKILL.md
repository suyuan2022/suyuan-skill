---
name: task-triage
description: |-
  Task triage with position-based thinking. 5+1 scoring dimensions (15 max + -3 penalty).
  Helps you decide whether a task is worth doing, and whether YOU should be the one doing it.
  Use when evaluating new tasks, prioritizing your backlog, or deciding what to cut.
---

# Task Triage

Your problem isn't a lack of ability — it's too many things on the plate and doing everything yourself.
This skill helps you intercept before you take on low-value work, or see clearly what to offload after you already have.

## Core Logic

**First principle: your time and attention are the scarcest resources. Every low-value task you accept is a high-value task you reject.**

- What determines your value isn't how much you do, but what position you hold (Sun Tzu — positional advantage)
- Spending time on work anyone could do dilutes your irreplaceability (Adam Smith — market pricing)
- Working too smoothly and quietly = zero visibility (Drucker — knowledge worker's dilemma)

## Scoring System (5 positive + 1 negative dimension)

### 1. Positional Value (Does this make your position stronger?)

- **3** — Directly builds or reinforces your decision-making authority, architectural ownership, or irreplaceability
- **2** — Indirectly related, accumulates capability or relationships needed for your position
- **1** — Maintenance work — losing points if not done, but no gain if done
- **0** — Completely unrelated to your core positioning

### 2. Only-You (Must YOU do this by hand?)

- **3** — Only you can do it: unique knowledge, unique judgment, unique relationships
- **2** — You're best, but someone else could reach 70% with some guidance
- **1** — Anyone could do roughly the same, you're just convenient
- **0** — Anyone can do it / AI can handle it directly

### 3. Compound Returns (One-time drain or lasting payoff?)

- **3** — Do once, benefit for a long time: skill-ification, architecture design, relationship building, workflow creation
- **2** — Medium-term returns, sustained value for weeks
- **1** — Short-term one-off, done and forgotten
- **0** — Pure drain, time spent with nothing to show

### 4. Cost of Not Doing (How bad is it if you cut this?)

- **3** — Direct damage: client loss, system crash, missing an irreversible window
- **2** — Delays other critical items
- **1** — Some impact but survivable
- **0** — Nobody notices if you don't do it

### 5. Visibility (Can the right people see it?)

- **3** — Output directly perceived by decision-makers / external market
- **2** — Visible within team, builds professional reputation
- **1** — Only you and direct collaborators know
- **0** — Heads-down grind, invisible even when done

### 6. Tail Cost (What price do you pay AFTER doing it?)

> Opportunity cost: doing A means no time for B. Maintenance cost: you have to keep feeding it. Attention black hole: once you start, you can't stop.

- **0** — Clean cut, done is done, no follow-up resources needed
- **-1** — Occasional maintenance/follow-up needed, but manageable
- **-2** — Continuously drains attention, or squeezes out time for higher-value work
- **-3** — Generates more tasks after completion, triggers chain reactions, or creates an attention black hole (scrolling feeds, joining groups — once started, can't stop)

## Verdict

| Score | Verdict | Action |
|-------|---------|--------|
| **12-15** | 🔴 Your work | Prioritize, do it yourself, make sure the right people see the output |
| **9-11** | 🟡 Worth doing | Do it, but think about which parts to delegate |
| **6-8** | 🟢 Delegate | Hand off to colleagues / AI / outsource, you review at most |
| **0-5** | ⚪ Cut | Seriously consider not doing it. The courage to say no is rarer than the ability to finish |

## Output Format

For each task evaluated:

```
【Task】XXX
Position X | Only-You X | Compound X | Cost X | Visibility X | Tail X → Net XX
Verdict: 🔴/🟡/🟢/⚪
One-liner: (Why this score — key reasoning)
Suggestion: (Do / delegate / cut / how to boost the score)
```

## Score Boosters

If a task scores low but you must do it anyway, think about how to boost the score:
- Low visibility → Write a recap after completion so decision-makers see it (+visibility)
- Only-You=0 → Do it this time but teach someone else, so next time you don't have to (+compound)
- Position=0 → Can you establish a new information node while doing it? (+position)
