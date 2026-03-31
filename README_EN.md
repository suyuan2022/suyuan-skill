<p align="right">
  <a href="./README.md">中文</a> | <strong>English</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skills-8B5CF6?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDJMMyA3djEwbDkgNSA5LTVWN2wtOS01em0wIDIuMThsNi44MyAzLjhMMTIgMTEuOCA1LjE3IDcuOTggMTIgNC4xOHpNNSA5LjA2bDYgMy4zNHY2LjUzTDUgMTUuNnYtNi41M3ptMTQgNi41M2wtNiAzLjM0di02LjUzbDYtMy4zNHY2LjUzeiIvPjwvc3ZnPg==&logoColor=white" alt="Claude Code Skills">
</p>

<h1 align="center">Suyuan's Skill Collection</h1>

<p align="center">
  <strong>AI-native productivity tools built by a real practitioner, not a prompt engineer.</strong><br>
  <sub>Every skill here was born from actual work — shipping products, managing teams, making decisions under pressure.</sub>
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
| [**task-triage**](./task-triage/) | 5+1 dimension scoring system for task prioritization. Helps you decide what's worth doing, what to delegate, and what to cut. | Pure Markdown |

### Standalone Repos

| Skill | Description | Repo |
|-------|-------------|------|
| **GET-biji** | Auto-sync voice notes from [Get Notes](https://biji.com) (24/7 recording card) to local Markdown knowledge base. | [suyuan2022/GET-biji](https://github.com/suyuan2022/GET-biji) |

---

## Installation

```bash
# Clone the repo
git clone https://github.com/suyuan2022/suyuan-skill.git

# Copy the skill you want into your Claude Code skills directory
cp -r suyuan-skill/task-triage ~/.claude/skills/task-triage
```

Or just copy the `SKILL.md` file — that's all you need for pure Markdown skills.

---

## What Makes These Different

These aren't prompt templates or toy demos. They come from running a startup with AI:

- **task-triage** was born from a late-night roundtable discussion about why smart people stay busy but never move the needle. The "Tail Cost" dimension came from realizing that some tasks look productive but actually drain your capacity for the important stuff — like doom-scrolling dressed up as "research".

- **GET-biji** exists because a 24/7 recording device generates gigabytes of unstructured voice data, and the only way to make it useful is a pipeline that syncs, transcribes, and organizes it into searchable Markdown.

---

## Philosophy

> Your time and attention are the scarcest resources. Every low-value task you accept is a high-value task you reject.

These skills follow three principles:

- **Opinionated over flexible** — They make judgments, not menus. A triage skill that says "it depends" is useless.
- **Born from pain** — Every skill solves a problem I actually had, not a problem I imagined someone might have.
- **AI-native** — Designed for Claude Code's skill system, not retrofitted from something else.

---

## Contributing

Got a skill that was born from real work? PRs welcome.

- One skill per directory
- Must include a `SKILL.md` with proper frontmatter
- No hardcoded personal paths or credentials
- Brief description of the problem it solves in your PR

---

## License

MIT

---

<p align="center">
  <sub>Built by <a href="https://github.com/suyuan2022">Suyuan</a> · AI practitioner, not just an AI user</sub>
</p>
