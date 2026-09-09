<div align="center">

# ai-dev-maturity

**How good is your team actually getting at building software with AI — and what to fix next.**

**你们团队用 AI 做开发，到底到了什么水平，下一步该修什么。**

[![selftest](https://github.com/yuna78/ai_dev_maturity/actions/workflows/selftest.yml/badge.svg)](https://github.com/yuna78/ai_dev_maturity/actions/workflows/selftest.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-skill-D97757)](https://claude.com/claude-code)

[![platforms](https://img.shields.io/badge/git-GitHub%20%7C%20GitLab%20%7C%20Gitee%20%7C%20CODING%20%7C%20Bitbucket-1F3A5F)](scripts/selftest.py)
[![assertions](https://img.shields.io/badge/selftest-28%20assertions-2A9D8F)](scripts/selftest.py)
[![deps](https://img.shields.io/badge/runtime%20deps-git%20%2B%20python3-lightgrey)](#requirements--依赖)
[![offline](https://img.shields.io/badge/data-stays%20local-2A9D8F)](#privacy--隐私)

[English](#english) · [中文](#中文) · [使用手册](docs/USAGE.zh-CN.md)

<img src="docs/images/report-cover.png" width="620" alt="Report cover with 9-dimension radar chart">

</div>

---

<a name="english"></a>

## English

A [Claude Code](https://claude.com/claude-code) skill that reads your git history and agent
configuration, scores your team on **9 dimensions** against published industry research, and
produces a shareable PDF report with a concrete, landable improvement plan.

Works on **any git project** — single repo or multi-repo workspace; GitHub, GitLab, Gitee, CODING
or Bitbucket. No CI integration required, nothing uploaded anywhere: it reads your local clone.

### Why this exists

Every team adopting AI coding tools eventually asks *"are we actually good at this, or just busy?"*
The usual answers are poor ones — vendor benchmarks measure someone else's team, and
"lines written by AI" measures activity, not outcome.

This answers a narrower, more useful question: **is your way of working with AI built to survive
scale, and where will it break first?** It scores the *harness* — specs, context, gates, review,
measurement — not the people.

### What you get

| Output | Content |
|---|---|
| `scan.json` | ~40 metrics per repo: throughput, AI attribution, PR size, test ratio, CI gates, agent config, spec-layer health |
| Markdown analysis | Evidence → 9-dimension score → three-wave plan, every item with a concrete landing point and an acceptance metric |
| HTML + A4 PDF | Radar, J-curve, bars, donuts, roadmap. Print-ready, with automatic pagination self-check |
| Baseline | Stored per project, so the next run diffs against it (`--compare`) |

<img src="docs/images/report-evidence.png" width="760" alt="Evidence page with charts">

### The J-curve — the chart most teams are missing

DORA describes AI adoption as a J-curve: things get worse before they get better, and the dip is
paid in **verification cost**. One 90-day snapshot cannot show you where you are on that curve.
`--trend 12` buckets the same git history by month so you can see it:

<img src="docs/images/jcurve.png" width="820" alt="J-curve chart: throughput vs rework">

*Illustrative, synthetic data.* Read the two lines **together**: throughput up with rework flat is
real gain; throughput up with rework up means you are buying speed with rework, and the question is
only how much of the gain survives.

> This is not hypothetical. On the project this tool was first built for, the 90-day snapshot said
> "past the bottom of the J-curve." The 14-month view said the opposite — rework in two long-lived
> repos had gone from a 10–20% baseline to over 60%, in the same month. Same data, opposite
> conclusion, purely because of window length.

### Quickstart

```bash
git clone https://github.com/yuna78/ai_dev_maturity ~/.claude/skills/ai-collab-maturity
python3 -m playwright install chromium     # only needed for PDF rendering
```

The clone target directory name (`ai-collab-maturity`) is the skill name Claude Code looks for —
keep it, even though the repo is named `ai_dev_maturity`.

Then, from any git project:

```bash
S=~/.claude/skills/ai-collab-maturity/scripts

python3 $S/scan.py --root . --detect-only              # 1. sanity-check what it detected
python3 $S/scan.py --root . --trend 12 > scan.json     # 2. scan (+ monthly J-curve data)
python3 $S/build_report.py report.json --out .         # 4. render HTML + PDF
```

Step 3 — turning `scan.json` into judgement — is what the skill file is for. Open the project in
Claude Code and ask it to *assess our AI collaboration maturity*; the skill walks the model through
scoring against the rubric and drafting the report.

Comparing quarters:

```bash
python3 $S/scan.py --compare baseline-2026Q1.json scan.json
```

<img src="docs/images/report-roadmap.png" width="760" alt="Three-wave roadmap">

### The 9 dimensions

Intent & specs · Context engineering · Feed-forward constraints · Feedback & verification ·
Multi-agent orchestration · Scaling human oversight · Measurement & economics · Security by default ·
Adoption beyond engineering

Scored 1–5, where **3 is the watershed**: a mechanism that exists but relies on discipline scores 3;
one enforced deterministically by a hook or CI scores 4; enforced *and* measured scores 5.
Anchors and evidence sources in [`references/maturity-rubric.md`](references/maturity-rubric.md).

Grounded in Anthropic's 2026 Agentic Coding Trends Report · DORA's *ROI of AI-assisted Software
Development* · Thoughtworks Technology Radar Vol.34 (cognitive debt) · OpenAI's harness engineering ·
Microsoft's CLI-agent rollout study · Stack Overflow Developer Survey — summarised in
[`references/paradigms-2026.md`](references/paradigms-2026.md), **with a refresh checklist, because
the summary has a shelf life.**

### What this is not

- **Not an ROI calculator.** A high score means you are likely doing it right, not that it paid off
  this quarter. How to measure returns yourself, and which metrics will mislead you:
  [`references/measuring-roi.md`](references/measuring-roi.md).
- **Not a performance review.** The report names individuals — who writes, who merges, who signs
  commits with AI. Concentration of *merge* authority is a real risk signal and anonymising it hides
  the finding. But commit share is an activity metric, and reading it as productivity is the exact
  mistake the rubric warns against. **Decide who sees the report before you run it.**
- **Not a vendor benchmark.** The only target that matters is your own previous baseline.

### Known limits

- **AI attribution is a floor, not a rate.** Only some tools leave a `Co-Authored-By` trailer. The
  scanner also mines branch names (`codex/*`) and reports both — a wide gap means a tool in use is
  invisible to the trailer count.
- **Manual checks exist.** Server-side branch protection, real tool usage, rework counts and
  non-engineering adoption cannot be read from git. `--manual manual.json` keeps those answers
  across quarters instead of losing them in a chat log.
- **Self-check the scanner's own output.** `spec.time_source_warning`, an `unlinked` count equal to
  0 or to the total, a wide `ai_by_branch` / `ai_by_tool` gap — suspiciously tidy numbers are
  usually a rule that failed to match, not reality.

<a name="privacy--隐私"></a>
### Privacy · 隐私

Everything runs locally against your own clone. Nothing is uploaded, no telemetry, no network calls
except the optional Chromium download for PDF rendering.

<a name="requirements--依赖"></a>
### Requirements · 依赖

`git` · `python3` (3.9+, standard library only for scanning) · `playwright` + chromium for PDF ·
`pdf2image` optional, adds orphan-page detection to the layout self-check.

### Development

```bash
python3 scripts/selftest.py -v    # 28 assertions across 5 git platforms
```

Run it after touching any detection rule. It builds throwaway repos with GitHub / GitLab / Gitee /
CODING / Bitbucket merge conventions and asserts the scanner reads them correctly.

---

<a name="中文"></a>

## 中文

一个 [Claude Code](https://claude.com/claude-code) skill：扫描 git 历史与 agent 配置，对照公开的
行业研究按 **9 个维度**打分，产出一份能发给团队的 PDF 报告和一套落得下去的优化方案。

**任何 git 项目都能跑**——单仓或多仓 workspace，GitHub / GitLab / Gitee / CODING / Bitbucket 都支持。
不需要接 CI，不上传任何东西，只读你本地的 clone。

### 为什么做这个

团队用上 AI 编码工具之后，早晚会问一句：**「我们到底是真的变强了，还是只是变忙了？」**

常见答案都不太可信——厂商报告量的是别人的团队，「AI 写了多少行代码」量的是活动量不是产出，
个人感觉则普遍高估。

本工具回答一个更窄、也更有用的问题：**你们这套跟 AI 协作的方式，撑不撑得住规模化，
以及最先会从哪里裂开。** 它打的是**协作机制**的分——规格、上下文、门禁、评审、度量——不是打人的分。

### 产出什么

| 产出 | 内容 |
|---|---|
| `scan.json` | 每仓约 40 项指标：吞吐、AI 归属、PR 体量、测试比、CI 门禁、agent 配置、规格层健康度 |
| markdown 分析 | 证据 → 九维度打分 → 三波方案，每条都有确定性落点和验收指标 |
| HTML + A4 PDF | 雷达图、J 曲线、柱状、环图、路线图，可直接打印，自带分页自检 |
| 基线 | 按项目存档，下次用 `--compare` 直接出差异 |

### J 曲线——多数团队缺的就是这张图

DORA 把 AI 采用描述成一条 J 曲线：先变差再变好，下沉的部分是用**验证成本**付的。
一个 90 天快照看不出你在曲线的哪个位置。`--trend 12` 把同一份 git 历史按月分桶，就能看见。

**两条线要一起读**：吞吐涨、返工平 = 真实收益；吞吐涨、返工也涨 = 在用返工换速度，
剩下的问题只是收益还剩多少。

> 这不是假设。本工具最早服务的那个项目，90 天快照的结论是「已越过 J 曲线谷底」，
> 14 个月的视角结论正好相反——两个有 AI 之前历史的老仓，返工率在同一个月里从 10–20% 的基线
> 冲到 60% 以上。同一份数据，只因为窗口长度不同，结论相反。

### 快速上手

```bash
git clone https://github.com/yuna78/ai_dev_maturity ~/.claude/skills/ai-collab-maturity
python3 -m playwright install chromium     # 只有出 PDF 才需要
```

clone 的目标目录名要用 `ai-collab-maturity`（Claude Code 认的 skill 名），仓名叫
`ai_dev_maturity` 不影响。

然后在任意 git 项目里：

```bash
S=~/.claude/skills/ai-collab-maturity/scripts

python3 $S/scan.py --root . --detect-only              # 1. 先看识别对不对
python3 $S/scan.py --root . --trend 12 > scan.json     # 2. 扫描（含 J 曲线数据）
python3 $S/build_report.py report.json --out .         # 4. 出 HTML + PDF
```

第 3 步——把 `scan.json` 变成判断——是 skill 文件的活。在 Claude Code 里打开项目说
「评估一下我们的 AI 协作成熟度」，它会按量表逐维打分并起草报告。

季度对比：

```bash
python3 $S/scan.py --compare baseline-2026Q1.json scan.json
```

完整流程、字段说明、常见问题见 **[使用手册](docs/USAGE.zh-CN.md)**。

### 九个维度

意图与规格 · 上下文工程 · 前馈约束 · 反馈验证 · 多 Agent 编排 · 人类监督规模化 ·
度量与经济账 · 安全前置 · 工程之外的扩散

1–5 分，**3 分是分水岭**：有机制但靠自觉 = 3；hook / CI 拦得住 = 4；拦得住且有度量 = 5。
锚点与证据来源见 [`references/maturity-rubric.md`](references/maturity-rubric.md)。

参照 Anthropic《2026 Agentic Coding 趋势报告》、DORA《ROI of AI-assisted Software Development》、
Thoughtworks Technology Radar Vol.34（认知债）、OpenAI harness engineering、
Microsoft CLI Agent 推广研究、Stack Overflow 开发者调查——摘要在
[`references/paradigms-2026.md`](references/paradigms-2026.md)，**并附刷新清单，因为摘要有保质期。**

### 这不是什么

- **不是 ROI 计算器。** 分数高说明「你把事情做对的概率高」，不等于「这季度赚回来了」。
  想自己量回报、以及哪些指标会骗你，看 [`references/measuring-roi.md`](references/measuring-roi.md)。
- **不是绩效考核。** 报告会点名——谁写、谁合、谁的提交带 AI 署名。合并权集中在一个人是真实的
  风险信号，匿掉就看不见了。但 commit 占比是活动量，读成生产力正是量表反复警告的误读。
  **跑之前先想清楚这份报告给谁看。**
- **不是厂商跑分。** 唯一有意义的对照是你自己的上一次基线。

### 已知局限

- **AI 归属率是下限，不是使用率。** 只有部分工具会留 `Co-Authored-By`。脚本同时从分支名
  （`codex/*`）取证并把两个数并排给出——落差大说明有工具在用但署名统计看不见。
- **有人工核对项。** 服务端分支保护、实际用的工具、返工次数、非工程角色使用量，git 里读不到。
  `--manual manual.json` 让这些答案跨季度留存，而不是只活在一次对话里。
- **要自检脚本自己的输出。** `spec.time_source_warning`、`unlinked` 等于 0 或等于总数、
  `ai_by_branch` 与 `ai_by_tool` 落差大——**数字太整齐往往不是真的整齐，是规则没匹配上。**

### 隐私

全程在本地跑，只读你自己的 clone。不上传、无遥测，除了可选的 Chromium 下载之外没有网络请求。

### 开发

```bash
python3 scripts/selftest.py -v    # 28 条断言，覆盖 5 种 git 平台
```

改了任何识别规则后必跑。它会造临时仓，分别用 GitHub / GitLab / Gitee / CODING / Bitbucket
的合并约定，断言脚本读得对。

---

## License

MIT
