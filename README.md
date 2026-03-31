<p align="right">
  <strong>中文</strong> | <a href="./README_EN.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-Skills-8B5CF6?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDJMMyA3djEwbDkgNSA5LTVWN2wtOS01em0wIDIuMThsNi44MyAzLjhMMTIgMTEuOCA1LjE3IDcuOTggMTIgNC4xOHpNNSA5LjA2bDYgMy4zNHY2LjUzTDUgMTUuNnYtNi41M3ptMTQgNi41M2wtNiAzLjM0di02LjUzbDYtMy4zNHY2LjUzeiIvPjwvc3ZnPg==&logoColor=white" alt="Claude Code Skills">
</p>

<h1 align="center">Suyuan's Skill Collection</h1>

<p align="center">
  <strong>从真实工作中长出来的 AI 生产力工具，不是提示词模板。</strong><br>
  <sub>每个 Skill 都来自实战：做产品、带团队、在压力下做决策。</sub>
</p>

<p align="center">
  <a href="https://github.com/suyuan2022/suyuan-skill/stargazers"><img src="https://img.shields.io/github/stars/suyuan2022/suyuan-skill?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/network/members"><img src="https://img.shields.io/github/forks/suyuan2022/suyuan-skill?style=flat-square" alt="Forks"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
</p>

---

## Skills

### 本仓库内

| Skill | 说明 | 类型 |
|-------|------|------|
| [**task-triage**](./task-triage/) | 任务分诊：5+1 维度打分系统，帮你判断一件事值不值得做、该不该你做、做完会不会拖你下水。 | 纯 Markdown |

### 独立仓库

| Skill | 说明 | 仓库 |
|-------|------|------|
| **GET-biji** | 自动同步 [Get Notes](https://biji.com)（24/7 录音卡）的语音笔记到本地 Markdown 知识库。 | [suyuan2022/GET-biji](https://github.com/suyuan2022/GET-biji) |

---

## 安装

```bash
# 克隆仓库
git clone https://github.com/suyuan2022/suyuan-skill.git

# 把你想要的 skill 复制到 Claude Code 的 skills 目录
cp -r suyuan-skill/task-triage ~/.claude/skills/task-triage
```

纯 Markdown 类型的 skill，只需要复制 `SKILL.md` 就够了。

---

## 这些 Skill 有什么不同

不是提示词模板，不是 demo。它们来自真实的创业场景：

- **task-triage** 诞生于一次深夜圆桌讨论：为什么聪明人总是很忙，却推不动真正重要的事？"尾巴成本"这个维度来自一个发现——有些任务看起来在产出，实际上在消耗你做大事的容量，就像刷信息流伪装成"调研"。

- **GET-biji** 的存在是因为一个 24 小时录音设备会产生海量的非结构化语音数据，唯一让它有用的方式是建一条管道：同步、转录、整理成可搜索的 Markdown。

---

## 理念

> 你的时间和注意力是最稀缺的资源。每接一个低价值任务，就是在拒绝一个高价值任务。

三条原则：

- **给判断，不给菜单** — 一个说"看情况"的分诊工具毫无价值。
- **从痛点中长出来** — 每个 skill 解决的都是我真正遇到过的问题，不是想象中别人可能有的问题。
- **AI 原生** — 为 Claude Code 的 skill 系统设计，不是从别的地方硬塞进来的。

---

## 贡献

如果你也有从实战中长出来的 skill，欢迎 PR。

- 一个 skill 一个目录
- 必须包含带 frontmatter 的 `SKILL.md`
- 不要硬编码个人路径或凭证
- PR 里简单说明它解决什么问题

---

## 许可证

MIT

---

<p align="center">
  <sub>Built by <a href="https://github.com/suyuan2022">Suyuan</a> · AI practitioner, not just an AI user</sub>
</p>
