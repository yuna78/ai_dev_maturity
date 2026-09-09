# ai-collab-maturity

**How good is your team actually getting at building software with AI — and what to fix next.**

A [Claude Code](https://claude.com/claude-code) skill that scans your git history and agent
configuration, scores your team on 9 dimensions against published industry research, and produces
a shareable PDF report with a concrete improvement plan.

Works on any git project: single repo or multi-repo workspace, GitHub / GitLab / Gitee / CODING /
Bitbucket. No CI integration, no agent required, nothing sent anywhere — it reads your local clone.

> 中文完整使用手册：**[docs/USAGE.zh-CN.md](docs/USAGE.zh-CN.md)**

## Why this exists

Every team using AI coding tools eventually asks *"are we actually good at this, or just busy?"*
The usual answers are bad ones: vendor benchmarks measure someone else's team, and
"lines of code written by AI" measures activity, not outcome.

This tool answers a narrower, more useful question: **is your team's way of working with AI
built to survive scale — and where will it break first?** It scores the *harness* (specs,
context files, hooks, gates, review, measurement), not the people.

It is deliberately **not** an ROI calculator. See [What this is not](#what-this-is-not).

## What you get

| Output | Content |
|---|---|
| `scan.json` | ~40 metrics per repo: throughput, AI attribution, PR size, test ratio, CI gates, agent config, spec-layer health |
| Markdown analysis | Evidence → 9-dimension score → three-wave improvement plan, each item with an owner-ready landing point |
| HTML + A4 PDF | Charts (radar, J-curve, bars, donuts, roadmap), print-ready, auto-checked for pagination bugs |
| Baseline | Stored per project so the next run diffs against it (`--compare`) |

## Quickstart

```bash
git clone https://github.com/yuna78/ai_dev_maturity ~/.claude/skills/ai-collab-maturity
python3 -m playwright install chromium     # for PDF rendering

```

The clone target directory name (`ai-collab-maturity`) is the skill name Claude Code looks for —
keep it even though the repo is named `ai_dev_maturity`.

Then, from any git project:

```bash
S=~/.claude/skills/ai-collab-maturity/scripts

python3 $S/scan.py --root . --detect-only                  # 1. check what it detected
python3 $S/scan.py --root . --trend 12 > scan.json         # 2. scan (+ monthly J-curve data)
python3 $S/build_report.py report.json --out .             # 4. render HTML + PDF
```

Step 3 — turning `scan.json` into judgement — is what the skill file is for: open the project in
Claude Code and say *"评估一下我们的 AI 协作成熟度"* / *"assess our AI collaboration maturity"*.
The skill walks the model through scoring against the rubric and drafting the report.

Comparing two runs:

```bash
python3 $S/scan.py --compare baseline-2026Q1.json baseline-2026Q2.json
```

## The 9 dimensions

Intent & specs · Context engineering · Feed-forward constraints · Feedback & verification ·
Multi-agent orchestration · Scaling human oversight · Measurement & economics · Security by default ·
Adoption beyond engineering

Scored 1–5, where **3 is the watershed**: a mechanism that exists but relies on discipline scores 3;
one enforced deterministically by a hook or CI scores 4; enforced *and* measured scores 5.
Anchors and evidence sources: [`references/maturity-rubric.md`](references/maturity-rubric.md).

Grounded in: Anthropic's 2026 Agentic Coding Trends Report · DORA's *ROI of AI-assisted Software
Development* · Thoughtworks Technology Radar Vol.34 (cognitive debt) · OpenAI's harness engineering ·
Microsoft's CLI-agent rollout study · Stack Overflow Developer Survey.
Summarised in [`references/paradigms-2026.md`](references/paradigms-2026.md), with a refresh
checklist — **the summary has a shelf life; re-check it before trusting the scores.**

## What this is not

- **Not an ROI calculator.** A high score means you're likely doing it right, not that it paid off
  this quarter. How to measure returns yourself: [`references/measuring-roi.md`](references/measuring-roi.md).
- **Not a performance review.** The report names individuals (who writes, who merges, who signs
  commits with AI). That is deliberate — concentration of *merge* authority is a real risk signal.
  But commit share is an activity metric, and reading it as productivity is exactly the mistake the
  rubric warns against. Decide who sees the report before you run it.
- **Not a vendor benchmark.** The only target that matters is your own previous baseline.

## Caveats worth knowing

- **AI attribution is a floor, not a rate.** Only some tools leave a `Co-Authored-By` trailer.
  The scanner also mines branch names (`codex/*`), and reports both — a large gap between them
  means a tool in use is invisible to the trailer count.
- **Manual checks exist.** Server-side branch protection, actual tool usage, rework counts and
  non-engineering adoption can't be read from git. `--manual manual.json` keeps the answers
  across quarters instead of losing them in a chat log.

## Development

```bash
python3 scripts/selftest.py -v    # 28 assertions across 5 git platforms
```

Run it after touching any detection rule. It builds throwaway repos with GitHub / GitLab / Gitee /
CODING / Bitbucket merge conventions and asserts the scanner reads them correctly.

## License

MIT
