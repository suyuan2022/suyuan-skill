<p align="right">
  <a href="./README.md">中文</a> | <strong>English</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skills-8B5CF6?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDJMMyA3djEwbDkgNSA5LTVWN2wtOS01em0wIDIuMThsNi44MyAzLjhMMTIgMTEuOCA1LjE3IDcuOTggMTIgNC4xOHpNNSA5LjA2bDYgMy4zNHY2LjUzTDUgMTUuNnYtNi41M3ptMTQgNi41M2wtNiAzLjM0di02LjUzbDYtMy4zNHY2LjUzeiIvPjwvc3ZnPg==&logoColor=white" alt="Claude Code Skills">
</p>

<h1 align="center">Suyuan's Skill Collection</h1>

<p align="center">
  Skills I built while working with Claude Code daily. Open-sourced for anyone who finds them useful.
</p>

<p align="center">
  <a href="https://github.com/suyuan2022/suyuan-skill/stargazers"><img src="https://img.shields.io/github/stars/suyuan2022/suyuan-skill?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/network/members"><img src="https://img.shields.io/github/forks/suyuan2022/suyuan-skill?style=flat-square" alt="Forks"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
</p>

---

## Skills

### In This Repo

| Skill | Description | Type |
|-------|-------------|------|
| [**break-ai-slop**](./break-ai-slop/) | Break AI Slop. Forces expert-level tacit knowledge extraction before execution — turns "statistical average" output into "someone who's actually done this" output. | Pure Markdown |
| [**task-triage**](./task-triage/) | Task triage. 5+1 dimension scoring to quickly decide if a task is worth doing and whether you should be the one doing it. | Pure Markdown |
| [**cc-shield**](./cc-shield/) | Claude Code account protection. Disable telemetry, clean device fingerprints, safe account switching. | Pure Markdown |
| [**codex-review**](./codex-review/) | Dual-model code review. Two GPT models review the same code independently, Claude arbitrates disagreements. Supports review / fix / audit / autopilot modes. | Markdown + Codex CLI |

### Standalone Repos

| Skill | Description | Repo |
|-------|-------------|------|
| **GET-biji** | Auto-sync voice notes from [Get Notes](https://biji.com) (24/7 recording card) to local Markdown knowledge base. | [suyuan2022/GET-biji](https://github.com/suyuan2022/GET-biji) |

---

## Installation

```bash
git clone https://github.com/suyuan2022/suyuan-skill.git

# Copy the skill you want into your Claude Code skills directory
cp -r suyuan-skill/task-triage ~/.claude/skills/task-triage
```

For pure Markdown skills, just copy the `SKILL.md` file.

---

## Contributing

PRs welcome.

- One skill per directory
- Must include a `SKILL.md` with proper frontmatter
- No hardcoded personal paths or credentials
- Brief description of the problem it solves in your PR

---

## License

MIT

---

<p align="center">
  <sub>Built by <a href="https://github.com/suyuan2022">Suyuan</a></sub>
</p>
