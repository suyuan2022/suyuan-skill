<p align="right">
  <strong>中文</strong> | <a href="./README_EN.md">English</a>
</p>

<h1 align="center">让 AI 干活像个真干过的人</h1>

<p align="center">
  一组 Claude Code / Codex 的 Skill，解决同一个问题：<br>
  <strong>AI 的默认输出是统计平均值——正确但平庸、完整但空洞。</strong><br>
  这些 Skill 把它拉回到有判断力的人的水平。
</p>

<p align="center">
  <a href="https://github.com/suyuan2022/suyuan-skill/stargazers"><img src="https://img.shields.io/github/stars/suyuan2022/suyuan-skill?style=flat-square&color=yellow" alt="Stars"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/network/members"><img src="https://img.shields.io/github/forks/suyuan2022/suyuan-skill?style=flat-square" alt="Forks"></a>
  <a href="https://github.com/suyuan2022/suyuan-skill/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
</p>

---

## Skill 列表

| Skill | 解决什么 | 它做什么 |
|-------|---------|---------|
| [**break-ai-slop**](./break-ai-slop/) | AI 输出正确但平庸 | 执行前强制提取行家默会知识，4 步认知校准，把输出从"AI 味"拉到"真干过这事的人"的水平 |
| [**codex-review**](./codex-review/) | 单模型审查有盲区 | 两个 GPT 模型独立审查同一份代码，Claude 仲裁分歧。review / fix / audit / autopilot 四种模式 |
| [**task-triage**](./task-triage/) | 什么都想做，注意力被耗散 | 5+1 维度打分，帮你判断一件事值不值得做、该不该你做 |
| [**cc-shield**](./cc-shield/) | Claude Code 隐私泄露风险 | 关闭遥测、清理设备指纹、安全换号 |

### 独立仓库

| Skill | 解决什么 | 仓库 |
|-------|---------|------|
| **GET-biji** | 语音笔记躺在 App 里吃灰 | [suyuan2022/GET-biji](https://github.com/suyuan2022/GET-biji) |

---

## 安装

```bash
# 克隆仓库
git clone https://github.com/suyuan2022/suyuan-skill.git

# 把想用的 skill 复制到 Claude Code skills 目录
cp -r suyuan-skill/break-ai-slop ~/.claude/skills/break-ai-slop
```

每个 Skill 都是独立的 `SKILL.md`，纯 Markdown，复制就能用。

---

## 贡献

欢迎 PR。要求：

- 一个 skill 一个目录，包含带 frontmatter 的 `SKILL.md`
- 不要硬编码个人路径或凭证
- PR 里说清楚它**解决什么问题**

---

## 许可证

MIT

---

<p align="center">
  <sub>Built by <a href="https://github.com/suyuan2022">Suyuan</a> — 用 AI 干活的人，不是被 AI 干活的人</sub>
</p>
