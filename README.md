<p align="right">
  <strong>中文</strong> | <a href="./README_EN.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skills-8B5CF6?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDJMMyA3djEwbDkgNSA5LTVWN2wtOS01em0wIDIuMThsNi44MyAzLjhMMTIgMTEuOCA1LjE3IDcuOTggMTIgNC4xOHpNNSA5LjA2bDYgMy4zNHY2LjUzTDUgMTUuNnYtNi41M3ptMTQgNi41M2wtNiAzLjM0di02LjUzbDYtMy4zNHY2LjUzeiIvPjwvc3ZnPg==&logoColor=white" alt="Claude Code Skills">
</p>

<h1 align="center">Suyuan's Skill Collection</h1>

<p align="center">
  我在用 Claude Code 干活过程中积累的 Skill，开源出来给需要的人。
</p>

<p align="center">
  <a href="https://github.com/suyuan2022/suyuan-skill/stargazers"><img src="https://img.shields.io/github/stars/suyuan2022/suyuan-skill?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/network/members"><img src="https://img.shields.io/github/forks/suyuan2022/suyuan-skill?style=flat-square" alt="Forks"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
</p>

---

## Skill 列表

### 本仓库

| Skill | 说明 | 类型 |
|-------|------|------|
| [**task-triage**](./task-triage/) | 任务分诊。5+1 维度打分，帮你快速判断一件事值不值得做、该不该你做。 | 纯 Markdown |
| [**cc-shield**](./cc-shield/) | Claude Code 账号保护。关闭遥测、清理设备指纹、安全换号。 | 纯 Markdown |

### 独立仓库

| Skill | 说明 | 仓库 |
|-------|------|------|
| **GET-biji** | 自动同步 [Get Notes](https://biji.com)（24/7 录音卡）语音笔记到本地 Markdown 知识库。 | [suyuan2022/GET-biji](https://github.com/suyuan2022/GET-biji) |

---

## 安装

```bash
git clone https://github.com/suyuan2022/suyuan-skill.git

# 把想用的 skill 复制到 Claude Code skills 目录
cp -r suyuan-skill/task-triage ~/.claude/skills/task-triage
```

纯 Markdown 类型的 skill，只需要复制 `SKILL.md` 就够了。

---

## 贡献

欢迎 PR。要求：

- 一个 skill 一个目录
- 包含带 frontmatter 的 `SKILL.md`
- 不要硬编码个人路径或凭证
- PR 里简单说明它解决什么问题

---

## 许可证

MIT

---

<p align="center">
  <sub>Built by <a href="https://github.com/suyuan2022">Suyuan</a></sub>
</p>
