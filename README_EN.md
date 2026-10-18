<p align="right">
  <a href="./README.md">中文</a> | <strong>English</strong>
</p>

# suyuan-skill

I'm Suyuan (X: [@suyuan1711](https://x.com/suyuan1711)), and by day I build agent products at an AI startup. These are the AI skills I use in my own work. Each one started with a specific problem I kept running into. They install in both Claude Code and Codex.

A skill is a manual written for your agent: once it's installed, the agent follows it whenever you bring up something it covers.

| When you… | Use |
|---|---|
| can't get your head around a concept, or your agent dumps screens of text you can't take in | [whatis](#whatis) |
| get AI output you can't fault, yet can't use either | [break-ai-slop](#break-ai-slop) |
| have too much on your plate and can't tell whether to take something on, or do it yourself | [task-triage](#task-triage) |
| record all day on a voice recorder and want the transcripts searchable on your own machine | [get-biji](#get-biji) |
| finish some code and want a different model to pick it apart | [codex-review](#codex-review) |

## Install

Install [Node.js](https://nodejs.org) first; the `npx` command below comes with it.

Everything (you'll get to pick which ones):

```bash
npx skills add suyuan2022/suyuan-skill -g
```

Just one, e.g. whatis:

```bash
npx skills add suyuan2022/suyuan-skill -g --skill whatis
```

`-g` installs to your user directory so every project can use it; without it, the skill goes into the current project only.

Or send this line to your agent and let it install the skill itself:

> Install this skill for me: https://github.com/suyuan2022/suyuan-skill/tree/main/whatis

Skip the ones you won't use. Your agent reads the description of every installed skill each time it starts, so extra skills just take up its attention.

---

<a id="whatis"></a>
### whatis: turn what you don't understand into pictures

When you hit an unfamiliar concept, or your agent spits out a wall of text you can't take in, call whatis. It builds an HTML page that's mostly big diagrams with very little text: flowcharts, sequence diagrams, architecture diagrams, before/after comparisons, whichever fits. If it doesn't have enough context, it goes through your files or searches the web first. Every box in a diagram has to be backed by something; nothing is made up.

```
/whatis why rate hikes make mortgages more expensive
```

<a href="./assets/whatis-demo.jpg"><img src="./assets/whatis-demo.jpg" alt="Three whatis pages: Claude Code's stale LSP snapshot problem, worktree build artifacts, and git rebase vs. merge"></a>

<sub>Three real outputs (click for full size): Claude Code's stale LSP snapshot problem, worktree build artifacts, and git rebase vs. merge.</sub>

Adapted from ELI5 (Explain Like I'm Five), shared by [@trq212](https://x.com/trq212) at Anthropic. The original is one line: "explain like I'm someone who knows nothing about this topic, using a HTML artifact with big pictures and few words". I added layout and information-hierarchy rules on top so the results come out more consistently.

<a id="break-ai-slop"></a>
### break-ai-slop: before doing anything, work out how a real pro would do it

AI output is often hard to fault, yet anyone could have written it. break-ai-slop makes the AI answer four questions before it starts:

1. In the real world, who does this best, and in what setting?
2. When a beginner or an AI gets it wrong, what does the result look like?
3. If every common mistake is avoided and it's still wrong, what's the root cause?
4. So what's the one constraint that actually decides success?

Only then does it get to work. I asked it to write an opening-day WeChat Moments post for a 20 m² bakery at the gate of an old residential compound in Hangzhou. Here's what it worked out before writing (translated from its Chinese output):

> Not "a copywriting expert", but someone who has run a small shop at a compound gate for a few years and won their first regulars through their own Moments posts.
>
> …Even with good writing, it can still fail, because the goal is wrong. This post isn't after likes; it needs people within a kilometre to actually walk in and buy something next Saturday, and then make it a habit. There's also a hidden constraint: a 20 m² shop can't hold many people, so the post should spread visits out.

How to call it: add "don't phone this in, think it through first" before your task, or type `/break-ai-slop`.

It's for work with no single right answer: writing, plans, judgment calls. For looking up a fact or fixing a typo, skip it; its output runs about twice as long.

<a id="task-triage"></a>
### task-triage: should you take this on, and should it be you?

With too much going on, the easy thing is to say yes to whatever comes next. Describe a task to task-triage and it scores it on five things, 0 to 3 each:

- Does it strengthen your position on the team?
- Does it have to be you?
- Will doing it once keep paying off?
- What happens if you don't do it?
- Will the right people see the result?

Then it looks at the tail cost: will this keep pulling at you after it's done? That's up to 3 points off. You get a total, a one-line reason, and a suggestion: 12 or more, do it yourself; 9 to 11, worth doing, but think about what to hand off; 6 to 8, hand it to someone else or to AI; 5 or under, seriously consider not doing it.

How to call it: "Help me decide whether this is worth doing: …"

<a id="get-biji"></a>
### get-biji: voice-recorder transcripts, searchable on your machine

You record all day with a Get Notes ([biji.com](https://biji.com)) voice recorder, the transcripts sit inside the app, and finding one thing someone said is hard. get-biji syncs the transcripts to Markdown files on your computer, organised by date, so your agent can search them directly.

It also comes with a script that sends a video link, podcast link, or local audio/video file to Get and returns the full transcript. Transcribing means creating a note in Get; once the script has the text, it deletes that one note and leaves your other notes alone. Local files count against Get's monthly transcription minutes, based on audio length.

Requires Node.js. The first run opens a browser to log in to biji.com; after that you won't need to log in again for about 90 days.

Built on [skychentian/GET-biji](https://github.com/skychentian/GET-biji) and included with the author's permission: the sync part is theirs, the transcript script is mine.

<a id="codex-review"></a>
### codex-review: have a different model pick your code apart

If the same model writes and reviews the code, it has the same blind spots both times. codex-review has Claude call OpenAI's Codex and run two GPT models on the same code, each reviewing on its own without seeing the other's findings. Claude then compares both sides and settles the disagreements.

By default it only reviews and changes nothing. You can also have it fix things directly, run a full security check, or finish on its own while you're away.

You need an OpenAI account with Codex access. Install the Codex CLI and log in first: `npm install -g @openai/codex`, then `codex login`.

How to call it: "Have Codex look at this code", "review this".

---

The mistakes I've made working with AI, and why these skills are written the way they are, are on X: [@suyuan1711](https://x.com/suyuan1711). If something doesn't work well, open an [issue](https://github.com/suyuan2022/suyuan-skill/issues).

## License

MIT.
