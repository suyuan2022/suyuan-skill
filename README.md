<p align="right">
  <strong>中文</strong> | <a href="./README_EN.md">English</a>
</p>

# suyuan-skill

我是夙愿（X：[@suyuan1711](https://x.com/suyuan1711)），白天在一家 AI 创业公司做 Agent 产品。这里是我干活时用的几个 AI Skill，都是碰到具体的麻烦才写的。Claude Code 和 Codex 都能装。

Skill 就是一份写给 agent 的说明书：装上以后，你说到相关的事，agent 会照着它来干。

| 你碰到的事 | 用哪个 |
|---|---|
| 看不懂一个概念，或者 agent 甩过来一屏又一屏的字读不进去 | [whatis](#whatis) |
| AI 交出来的东西挑不出错，可也没什么用 | [break-ai-slop](#break-ai-slop) |
| 手上事太多，拿不准这件该不该接、该不该自己干 | [task-triage](#task-triage) |
| 录音卡录了一天，想把转写存到本地随时搜 | [get-biji](#get-biji) |
| 代码写完，想让另一家模型挑一遍刺 | [codex-review](#codex-review) |

## 安装

先装好 [Node.js](https://nodejs.org)，下面的 `npx` 是它自带的。

全装（会让你勾选要哪几个）：

```bash
npx skills add suyuan2022/suyuan-skill -g
```

只装一个，比如 whatis：

```bash
npx skills add suyuan2022/suyuan-skill -g --skill whatis
```

`-g` 是装到你的用户目录，所有项目都能用；不加就只装进当前项目。

也可以把这句话直接发给你的 agent，让它自己装：

> 帮我安装这个 skill：https://github.com/suyuan2022/suyuan-skill/tree/main/whatis

用不上的别装。agent 每次开工都会把装上的 skill 简介全读一遍，装多了白占它的注意力。

---

<a id="whatis"></a>
### whatis：看不懂的东西，画成图给你看

碰到不熟的概念，或者 agent 吐了一大段字读不进去，叫一下 whatis。它生成一个 HTML 页面，大图为主、字很少：流程图、时序图、架构图、前后对比，哪个合适画哪个。上下文不够，它会先去翻你的文件或上网查，图里每个框都得有依据，不瞎编。

```
/whatis 美联储加息为什么会让房贷变贵
```

<a href="./assets/whatis-demo.jpg"><img src="./assets/whatis-demo.jpg" alt="whatis 的三个出图：Claude Code 的 LSP 过期快照问题、worktree 的构建产物、git rebase 和 merge 的区别"></a>

<sub>三个真实出图，点开看大图：Claude Code 的 LSP 过期快照问题、worktree 的构建产物、git rebase 和 merge 的区别。</sub>

改自 Anthropic 的 [@trq212](https://x.com/trq212) 分享的 ELI5（Explain Like I'm Five，像讲给五岁小孩听）。原版只有一句话，大意是「讲给一个完全不懂的人听，用一个大图多字少的 HTML 页面」。我在这上面加了排版和信息层级的要求，出图更稳。

<a id="break-ai-slop"></a>
### break-ai-slop：动手前，先想清楚行家会怎么干

AI 交出来的东西，常常挑不出错，可换谁来写都差不多。break-ai-slop 让它动手前先回答四个问题：

1. 这活在现实里，是什么人、在什么场景下干得最好？
2. 新手或者 AI 做砸了，结果长什么样？
3. 常见错误都避开了还是不对，根本问题在哪？
4. 所以真正决定成败的约束是什么？

想清楚了再动手。我让它写「杭州老小区门口一家 20 平米面包店的开业朋友圈」，下面是它动笔前想的，原文摘录：

> 不是「文案专家」，而是在小区门口开过几年小店、朋友圈靠自己发出第一批熟客的老板。
>
> ……即使文笔漂亮，也可能失败，因为目标写错了。这条文案要的不是点赞，而是让周围 1 公里内的人下周六真的走进来买第一次，之后变成习惯。还有一个隐藏约束：20 平米的店装不下太多人，所以文案要引导错峰。

怎么叫它：任务前加一句「这个别敷衍，先想清楚再做」，或者直接打 `/break-ai-slop`。

适合写东西、出方案、做判断这类没有标准答案的活。查个事实、改个错别字用不着，它的输出会长一倍。

<a id="task-triage"></a>
### task-triage：这件事该不该接，该不该你干

事情一多，最容易的就是来一件接一件。把手上的事说给 task-triage，它从五个方面逐项打分，每项 0 到 3 分：

- 能不能让你在团队里的位置更稳
- 是不是非你不可
- 做一次能不能长期受益
- 不做会有什么后果
- 做完能不能被该看到的人看到

再看后续成本：做完还会不会一直牵扯你，最多扣 3 分。最后给你总分、一句理由和建议：12 分以上自己干；9 到 11 分值得做，但想想哪些能交出去；6 到 8 分交给别人或 AI；5 分以下认真考虑不做。

怎么叫它：「帮我判断一下这件事值不值得做：……」

<a id="get-biji"></a>
### get-biji：录音卡的转写，存到本地随时搜

Get 笔记（[biji.com](https://biji.com)）的录音卡录了一整天，转写都躺在 App 里，想找某人说过的一句话很难。get-biji 把转写同步成你电脑上的 Markdown 文件，按日期放好，agent 直接就能搜。

还附了一个脚本：把视频、播客链接或本地音视频交给 Get 转成逐字稿。转写要在 Get 里新建一条笔记，拿到原文后脚本只删这条，你别的笔记不碰。本地文件按音频时长扣 Get 每月的转写额度。

需要 Node.js。第一次运行会弹出浏览器登录 biji.com，之后大约 90 天不用再登。

基于 [skychentian/GET-biji](https://github.com/skychentian/GET-biji) 改的，经作者同意收录：同步部分是原作者写的，逐字稿脚本是我加的。

<a id="codex-review"></a>
### codex-review：让另一家模型给代码挑刺

同一个模型写、同一个模型审，盲区是一样的。codex-review 让 Claude 调用 OpenAI 的 Codex，开两个 GPT 模型各自审同一份代码，彼此看不到对方的结论，再由 Claude 对比两边、裁决分歧。

默认只看不改。也可以让它直接修、做一次全面的安全检查，或者在你不在的时候自己跑完。

需要能用 Codex 的 OpenAI 账号，先装好 Codex CLI 并登录：`npm install -g @openai/codex`，然后 `codex login`。

怎么叫它：「让 Codex 看看这段代码」「review 一下」

---

我平时用 AI 干活踩过的坑、这些 skill 为什么这么写，都在 X 上：[@suyuan1711](https://x.com/suyuan1711)。用着不顺或者有问题，开个 [issue](https://github.com/suyuan2022/suyuan-skill/issues)。

## 许可证

MIT。
