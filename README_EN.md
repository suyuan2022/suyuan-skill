<p align="right">
  <a href="./README.md">中文</a> | <strong>English</strong>
</p>

<h1 align="center">Make AI Work Like Someone Who's Actually Done It</h1>

<p align="center">
  A set of Skills for Claude Code / Codex that solve one problem:<br>
  <strong>AI defaults to statistical averages — correct but mediocre, comprehensive but hollow.</strong><br>
  These Skills pull it back to the level of someone with real judgment.
</p>

<p align="center">
  <a href="https://github.com/suyuan2022/suyuan-skill/stargazers"><img src="https://img.shields.io/github/stars/suyuan2022/suyuan-skill?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/network/members"><img src="https://img.shields.io/github/forks/suyuan2022/suyuan-skill?style=flat-square" alt="Forks"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
</p>

---

## What Each Skill Fights

| Skill | The Enemy | What It Does |
|-------|-----------|-------------|
| [**break-ai-slop**](./break-ai-slop/) | AI slop (correct but generic output) | Forces expert tacit knowledge extraction before execution. 4-step cognitive calibration that turns "AI-flavored" output into "someone who's done this before" output |
| [**codex-review**](./codex-review/) | Single-model review blind spots | Two GPT models review the same code independently, Claude arbitrates. Supports review / fix / audit / autopilot modes |
| [**task-triage**](./task-triage/) | The "do everything" attention trap | 5+1 dimension scoring to decide if a task is worth doing and whether YOU should do it |
| [**cc-shield**](./cc-shield/) | Claude Code privacy leaks | Disable telemetry, clean device fingerprints, safe account switching |

### Standalone Repos

| Skill | The Enemy | Repo |
|-------|-----------|------|
| **GET-biji** | Voice notes rotting inside an app | [suyuan2022/GET-biji](https://github.com/suyuan2022/GET-biji) |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/suyuan2022/suyuan-skill.git

# Copy the skill you want into your Claude Code skills directory
cp -r suyuan-skill/break-ai-slop ~/.claude/skills/break-ai-slop
```

Each Skill is a standalone `SKILL.md` — pure Markdown, just copy and go.

---

## Contributing

PRs welcome.

- One skill per directory with a frontmatter `SKILL.md`
- No hardcoded personal paths or credentials
- Describe what your skill's **enemy** is (what problem it fights)

---

## License

MIT

---

<p align="center">
  <sub>Built by <a href="https://github.com/suyuan2022">Suyuan</a> — someone who works with AI, not for AI</sub>
</p>
