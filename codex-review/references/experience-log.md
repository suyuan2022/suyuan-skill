# Experience Log

### [2026-04-03] 文件内容嵌入 prompt 浪费 token

**场景**：审查 ROADMAP.md + prd.md，Claude 先 Read 两个文件再把全文贴进 Codex prompt，Codex 又自己读了一遍。双倍 token 消耗，prompt 空间被挤占。
**根因**：SKILL.md 没有关于文件处理的指令，Claude 默认行为是嵌入内容。
**改动**：SKILL.md 新增"调用参数"段，明确 cd 设为主线程工作目录 + 文件只给路径不嵌入内容。
**效果**：Codex prompt 更短，token 省给审查要求和上下文补充，Codex 还能顺手看文件周边的其他代码。
