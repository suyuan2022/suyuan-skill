<p align="right">
  <strong>中文</strong> | <a href="./README_EN.md">English</a>
</p>

# suyuan-skill

我是夙愿（X：[@suyuan1711](https://x.com/suyuan1711)），在一家 AI 创业公司做 Agent 产品。这里是我干活时用的几个 AI Skill，都是碰到具体的麻烦才写的。

Skill 就是一份写给 agent 的说明书：装上以后，你说到相关的事，agent 会照着它来干。

| 你碰到的事 | 用哪个 |
|---|---|
| 看不懂一个概念，或者 agent 甩过来一屏又一屏的字读不进去 | [whatis](#whatis) |
| AI 交出来的东西挑不出错，可也没什么用 | [break-ai-slop](#break-ai-slop) |
| 想把 Get 笔记里的录音和笔记整个搬到自己电脑上 | [get-biji](#get-biji) |
| 想把一个视频、播客或者手机里的录音转成文字 | [get-biji](#get-biji) |

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

<a id="get-biji"></a>
### get-biji：把 Get 笔记搬到你电脑上，再用它的额度转逐字稿

[Get 笔记](https://biji.com)用户的两件事。

**把 Get 笔记整个搬到你电脑上。** 录音、存过的链接、随手记的文字，全部同步成本地的 Markdown 文件，按日期放好；以后有新的，再跑一次就补上。录音的逐字稿带说话人和时间，长的单独存一个文件。变成你自己的文件以后，agent 能跟你别的笔记一起搜，Get 改版或者断网，东西也还在你手里。

**用 Get 的转写额度转逐字稿。** 丢一个抖音、小红书、B 站、小宇宙的链接，Get 免费解析成文字；别的网站的视频、手机里的录音，上传给 Get 转，按音频时长扣你每月的转写额度，扣之前 agent 会先告诉你大概扣多少。转写要在 Get 里建一条临时笔记，拿到文字后只删这一条，你别的笔记不碰。

只想在对话里存笔记、搜笔记，装 Get 官方的 [MCP](https://www.npmjs.com/package/@getnote/mcp) 就够了，它能按意思搜。get-biji 管的是官方不做的那两件：整个搬到本地，和上传音视频转写。

装完要在 skill 目录里跑一次 `npm install && npx playwright install chromium`（会下载约 250MB 的浏览器，只用来登录），跟 agent 说一声它会自己跑。第一次用会弹出浏览器登录 biji.com，所以得在你自己的电脑上，之后大约 90 天不用再登。转本地音视频还要装 [ffmpeg](https://ffmpeg.org)。笔记存在你指定的目录，登录态存在 `~/.config/get-biji/`，重装或更新 skill 都不会丢。

基于 [skychentian/GET-biji](https://github.com/skychentian/GET-biji) 改的，经作者同意收录：同步部分是原作者写的，逐字稿脚本是我加的。

---

我平时用 AI 干活踩过的坑、这些 skill 为什么这么写，都在 X 上：[@suyuan1711](https://x.com/suyuan1711)。用着不顺或者有问题，开个 [issue](https://github.com/suyuan2022/suyuan-skill/issues)。

## 许可证

MIT。
