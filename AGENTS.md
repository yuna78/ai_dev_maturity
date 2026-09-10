# ai-collab-maturity · Agent 操作说明

> 这份文件是给**任何**编码 agent 读的跨工具入口（Codex / Cursor / Copilot / Gemini CLI / Cline / Amp / Claude Code …）。
> Claude Code 用户读 [`SKILL.md`](SKILL.md)——内容一致，那份带 Claude Code 的 skill frontmatter。
> 完整量表锚点在 [`references/maturity-rubric.md`](references/maturity-rubric.md)。

## 这是什么

评估一个软件项目的「AI 协作开发成熟度」：扫 git 历史与 agent 配置 → 对照公开行业研究按 **9 个维度**打分 → 产出可发给团队的报告和分三波的优化方案。

**运行时依赖只有 `git` 和 `python3` 3.9+**（扫描只用标准库）。出 PDF 才需要 `playwright` + chromium。
**不调用任何模型 API，不上传任何数据，不需要联网。** 打分那一步由**你**（读这份文件的 agent）完成。

## 安装

仓库 clone 到哪里都行：

```bash
git clone https://github.com/yuna78/ai_dev_maturity
```

Claude Code 用户想让它被自动发现，clone 成 `~/.claude/skills/ai-collab-maturity`（目录名要用这个，仓名叫 `ai_dev_maturity` 不影响）。其它 agent 不需要特定路径——把仓库路径记作 `$ACM` 即可。

## 执行流程（五步）

### ① 预检

```bash
python3 $ACM/scripts/scan.py --root <项目目录> --detect-only
```

打印自动识别结果：单仓/多仓、每个仓的默认分支、合并约定、规格层、agent 配置文件、CI 文件。**先跟用户核对一遍**，常见要人工改的是作者别名、要排除的仓、主线分支。

### ② 扫描

```bash
python3 $ACM/scripts/scan.py --root <项目目录> --trend 12 > scan.json
```

输出约 40 项指标。**stderr 上的自检警告必须看。**

### ③ 打分（这一步是你干的）

**硬规矩：先看 `scan.json` 的 `warnings[]`。非空就停下来问人，不许直接打分。**

自检会报五种情况：`stale_remote`（远端主线超 30 天没动）、`unpushed`（本地 HEAD 领先远端）、`empty_window`（窗口内 0 提交）、`guessed_branch`（主线是猜的）、`no_remote`。命中任何一条，吞吐、署名率、作者分布**会全是 0 或严重偏低，但 JSON 结构完全正常、看不出异常**——照这样打分会得出「这个团队没在用 AI」的错误结论，而报告排版精美，用户没有理由怀疑它。

按类型跟用户确认：

- `unpushed` / `stale_remote` → 「要不要先 `git fetch` / `git push` 再重扫？还是就按远端主线的口径评？」
- `guessed_branch` → 「主线是不是 `<branch>`？不是的话告诉我正确的。」
- `empty_window` → 「这个窗口内确实没提交，还是要放宽 `--since`？」
- `no_remote` → 告知：扫的是本地分支，口径跟走评审的远端主线不同。

确认后**把口径写进报告开头的「基线」一栏**。

然后对照 [`references/maturity-rubric.md`](references/maturity-rubric.md) 的锚点逐维打分（1–5 分，**3 分是分水岭**：有机制但靠自觉 = 3，hook/CI 拦得住 = 4，拦得住且有度量 = 5）。**每一分必须指回一个具体文件或一条提交记录**，指不回去的就别打。

### ④ 写分析

按 [`references/report-template.md`](references/report-template.md) 的结构写，产出 `report.json`。
每条建议都要有**落点**（哪个文件 / 哪个人）和**验收指标**；写不出这两样的建议不要写。
必须有一栏「明确不做的事」——改进方案本身也会制造维护负担。

### ⑤ 出报告 + 存基线

```bash
python3 $ACM/scripts/build_report.py report.json --out <输出目录>
```

渲染 HTML + A4 PDF。基线存进项目的 `.claude/ai-collab-maturity/`，下次对比用：

```bash
python3 $ACM/scripts/scan.py --compare baseline-2026Q1.json scan.json
```

## 边界

- **不是 ROI 计算器**：分数高说明「把事情做对的概率高」，不等于「这季度赚回来了」。
- **不是绩效考核**：报告会点名谁写谁合。commit 占比是**活动量**，读成生产力是量表反复警告的误读。跑之前先想清楚这份报告给谁看。
- **不是厂商跑分**：唯一有意义的对照是这个项目自己的上一次基线。
- 有些事 git 里读不到（服务端分支保护、实际用的工具、返工次数、非工程角色使用量），`--manual manual.json` 让这些答案跨季度留存。

## 自检

改了任何识别规则后必跑：

```bash
python3 $ACM/scripts/selftest.py -v
```

36 条断言，覆盖 GitHub / GitLab / Gitee / CODING / Bitbucket 五种合并约定。
