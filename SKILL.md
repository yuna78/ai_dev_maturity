---
name: ai-collab-maturity
description: 评估任一软件项目的「AI 协作开发成熟度」并给出优化方案——自动识别单仓 / 多仓、默认分支、合并约定（GitHub / Gitee / GitLab / squash），扫描吞吐、按作者的 AI 署名率（Claude / Codex / Copilot / Cursor 等）、PR 体量、测试比、CI 门禁、CLAUDE.md / AGENTS.md / cursor rules / hooks / skills 等 agent 配置、规格层（OpenSpec / Spec Kit / ADR）健康度，对照 Anthropic 趋势报告、DORA、Thoughtworks Radar、OpenAI harness engineering 等权威范式按 9 维度打分，产出 markdown 分析 + 带图表的 HTML 与 A4 PDF 报告，并把每次结果存成项目基线供下次对比。当用户问"我们用 AI 开发到什么水平 / AI 协作成熟度 / agentic coding 成熟度 / 对照趋势报告评估项目 / 团队 AI 使用率 / 谁在用 AI 写代码 / harness 成熟度 / 出一份 AI 开发治理报告 / 重跑成熟度体检 / 给个 AI 协作优化方案"，或要把这类分析做成 PDF / HTML 发给团队时，使用本 skill——即使用户没说"成熟度"三个字，只要是"评估我们 AI 辅助开发做得怎么样并给建议"，都走这里。
---

# AI 协作开发成熟度评估

把「我们用 AI 做开发到底做到什么水平、下一步怎么优化」变成一次**可重复、可对比、跨项目通用**的体检：
同一套扫描脚本、同一张 9 维度量表、同一个报告模板；项目差异全部收进一份 `profile.json`，
每次结果存成项目基线，季度重跑就能看趋势。

## 什么时候用、什么时候不用

- **用**：季度 / 半年一次的成熟度复盘；新趋势报告出来要对照自查；要一份能发给团队或管理层的治理报告；有人问"谁在用 AI 写代码、用到什么程度"。
- **不用**：单个 PR 的代码评审；产品能力完成度体检（那评的是产品，不是协作方式）；只想看 git 统计而不需要判断和方案（直接跑 `scripts/scan.py` 就够了，不必走完整流程）。

## 全流程（五个阶段）

```
① 预检：识别项目、钉基线 → ② 扫描（scan.py） → ③ 对照范式打分（rubric） → ④ 写分析（模板） → ⑤ 出报告（HTML + PDF）+ 存基线
```

每个阶段的产物放 session scratchpad；最终交付物按用户要求复制到桌面或归档进项目文档目录；
**基线**固定存进项目的 `.claude/ai-collab-maturity/`（见阶段⑤），这是下次对比的锚。

### ① 预检：识别项目、钉基线

成熟度评估最容易犯的错是拿本地 stale checkout 当现状，或者把项目 A 的约定套到项目 B。所以第一步不是扫，是**认清项目**：

```bash
python3 ~/.claude/skills/ai-collab-maturity/scripts/scan.py --root . --detect-only
```

它会打印自动识别结果：单仓还是多仓、每个仓的默认分支（读 `origin/HEAD`，退而求其次 develop / main / master）、合并约定（GitHub `Merge pull request #`、Gitee `!N`、GitLab `See merge request`、squash `(#N)` 后缀）、规格层（`openspec/`、Spec Kit `specs/`、ADR 目录）、agent 配置文件（CLAUDE.md、AGENTS.md、`.cursor/rules`、copilot-instructions、`.claude/hooks|skills|rules`、`.codex`）、CI 文件。

看一眼是否对。常见要人工改的：**作者别名**（同一人多个 git 身份）、**要排除的仓**（退役 / fork / 调研克隆）、**分支**（有的仓主线不在 origin/HEAD）。改法：

```bash
python3 ~/.claude/skills/ai-collab-maturity/scripts/scan.py --root . --write-profile .claude/ai-collab-maturity/profile.json
# 编辑 profile.json（字段说明见 references/scan-playbook.md），以后每次扫描都读它
```

已有 profile 的项目直接跳到②。第二次以后的体检，先读 `.claude/ai-collab-maturity/baseline-*.md` 里最近一份，知道上次的数字，扫描时才会注意到异常变化。

### ② 扫描：跑脚本，不要手抄

```bash
python3 ~/.claude/skills/ai-collab-maturity/scripts/scan.py --root . --profile .claude/ai-collab-maturity/profile.json > "$SCRATCH/scan.json"
```

输出一个 JSON，覆盖 `references/scan-playbook.md` 里列出的全部指标：每仓吞吐（commit / 合并 PR / fix 与 feat / revert）、
按作者与按工具的 AI 署名率、PR 平均体量、测试文件比、CI 门禁文件、agent 配置文件与行数；根目录 hooks（按事件计数）、skills、rules；
规格层 active / stale / 未关联任务 / verification 覆盖。

跑完先做三件事：

- **核对异常值**。作者名分裂、merged_prs 为 0（合并约定没识别出来）、AI 署名率异常低（团队用的工具不留 trailer），都先查 playbook「数字对不上时」一节。
  三个**必看**的自检字段：`spec.time_source_warning`（出现就说明 stale 数字取自 mtime，不可信）、
  `spec.unlinked` / `with_verification` 若为 0 或等于 active 总数（太整齐 = 多半是没匹配上而不是真的全没有）、
  `ai_by_branch` 与 `ai_by_tool` 的落差（落差大 = 有不留 trailer 的工具在用，署名率只是下限）。
- **补人工项**。脚本拿不到的：服务端分支保护是否启用、各人实际用的 AI 工具与时长、上季度验收打回次数、非工程角色的使用量。scan.json 末尾 `manual_checks` 列了清单，逐条问用户或查文档。
- **对比基线**。哪些指标比上次好、哪些更差，这是报告里最有价值的一段。

窗口默认 90 天；季度复盘用 90 天，半年复盘 `--since "180 days ago"`。

### ③ 对照范式打分

读 `references/maturity-rubric.md`（9 维度、1–5 分锚点、每维度看什么证据），逐维度给分并写一句依据。纪律：

- **分数跟着证据走**。每一分都要能指到 scan.json 的一个字段、一个文件路径，或一条人工核对结果。
- **3 分是分水岭**：有机制但靠自觉 = 3；确定性执行（hook / CI 拦得住）= 4；确定性执行且有度量 = 5。
- **总分简单平均**，不加权。定级：< 2.5 = L2 AI 辅助；2.5–3.5 = L3 Harness 化；3.5–4.5 = L4 编排规模化；> 4.5 = L5。
- **不要用厂商数字当目标**。目标只对自己的上一次基线。

外部范式知识在 `references/paradigms-2026.md`。这份摘要写于 2026-09；**距今超过 6 个月就先按文末「刷新清单」做一轮 WebSearch 更新**再打分。

### ④ 写分析

按 `references/report-template.md` 写 markdown。六节固定：一句话结论 → 外部范式 → 现状证据 → 打分 → 优化方案（三波）→ 来源。要点：

- **一句话结论先说位置，再说瓶颈，再说下一阶段主题**。读者只看这段也能带走判断。
- **优化方案每条四件套**：做什么 / 为什么（指向哪条范式或哪个数据）/ 落点（哪个文件、哪个配置、哪个人）/ 验收指标。没有落点的建议不写。
- **一定要有「明确不做的事」**。Thoughtworks 警告规则堆砌不可规模化；方案里要有减法，否则每次体检都在加闸。
- **集中度类发现要拆开说**。"某人占 40% commit"至少拆成写 / 合 / 验三件事分别看谁，旁边放各人的 AI 署名率，否则会被读成"某人没用 AI"（第一次用这套方法时就被误读过）。
- **合并数要分清 PR 合并与同步合并**。`Merge branch 'develop'` 之类是把主线合进特性分支的同步动作，不是评审合并；只算脚本识别出的 PR 合并。

### ⑤ 出报告 + 存基线

报告的图表和排版由脚本生成，内容通过一个 JSON 数据文件喂进去，改数字不用改代码：

```bash
cp ~/.claude/skills/ai-collab-maturity/assets/report.template.json "$SCRATCH/report.json"   # 或参考 examples/ 里填好的
# 按本次分析填值（结构说明见模板内注释字段 _doc）
python3 ~/.claude/skills/ai-collab-maturity/scripts/build_report.py "$SCRATCH/report.json" --out "$SCRATCH"
```

生成时**自动跑分页自检**（同一个浏览器会话里量，几乎不额外花时间），输出形如：

```
分页自检
  打印区 673×979px（读自 @page）
  封面 999px / 979px ❌ 超出
  各页内容底边：95% 5% 53% 93% ...
  ⚠️  分页问题：
     - 封面超出 20px ≈ 1 行 —— 删 summary.conclusion_html 约 1 行
     - 第 2/10 页内容只填到 5% 页高，多半是孤儿页
```

两层判据：**封面高度**（DOM，打印布局下量，超出多少直接换算成砍几行）与**每页内容底边**
（渲染结果，抓 DOM 规则覆盖不到的孤儿页）。有问题时退出码为 1，可进 CI。

- 改完 `report.json` 想单独复查：`build_report.py <json> --out DIR --check-layout`（不重新生成）
- 赶时间跳过：`--no-layout-check`
- `meta.layout.score_on_new_page` 可强制打分节另起一页

自检报干净通常就不必逐页看图了；仍想肉眼确认时用 pdf2image 转 70dpi 预览。**别自己写测量脚本**——
用默认 viewport 宽度量出来的高度偏小（实测量到 888 以为没超，打印布局下其实是 1003），自检已经处理了这一点。

**字段转义**：表格行（`governance_rows` / `plan.waves[].rows` / `dims[].basis`）与所有 `*_html`
字段吃原始 HTML，但**图表的 `title` / `caption` / `segments[].label` 和 `kpis[].value` / `label` 会被转义**——
在 caption 里写 `<b>` 会原样印进 PDF。完整清单见 `assets/report.template.json` 的 `_doc_html_fields`。

存基线（每次必做，否则下次没得比）：

```bash
mkdir -p .claude/ai-collab-maturity
cp "$SCRATCH/scan.json"   .claude/ai-collab-maturity/scan-<YYYYMMDD>.json
cp "$SCRATCH/report.json" .claude/ai-collab-maturity/report-<YYYYMMDD>.json
# 再写一份 baseline-<YYYYMMDD>.md：总分、各维度分与依据、关键数字、方案摘要、下次要专门核对的 3–5 条（格式见 examples/）
```

PDF 不进 git。交付时复制到桌面（`open -R` 定位）或归档到项目文档目录。

## 改了脚本就跑自检

```bash
python3 ~/.claude/skills/ai-collab-maturity/scripts/selftest.py      # 加 -v 看每条
```

造 GitHub / GitLab / Gitee / CODING / Bitbucket 五种平台的假仓，断言合并约定、CI 识别、AI 取证
（trailer 与分支名两条路）、多种关联键（`github_issue` / `jira_ticket` / `coding_task` / `issue`）、
verification（文件 / 英文段 / 中文段）、以及**独立子仓下 stale 的时间来源必须是 git 而不是 mtime**。
28 条断言，全过才算没破坏通用性——这个 skill 给别人打「测试与门禁」的分，自己不能没有回归。

## 依赖

- Python 3 + `playwright`（装好 chromium：`python3 -m playwright install chromium`）；`pdf2image` 用于分页自检的孤儿页检测与预览（缺了自检会跳过这一层，封面检查不受影响）
- 中文报告需要一款 CJK 字体（脚本按 Source Han Sans CN → PingFang SC → Noto Sans CJK 回退）；纯英文项目不需要
- `git` 能访问各仓远端（`--no-fetch` 可离线跑旧数据）

## 文件索引

| 文件 | 何时读 |
|---|---|
| `references/scan-playbook.md` | 跑扫描前；profile 字段、每个指标怎么算、数字不对时查什么 |
| `references/maturity-rubric.md` | 打分时；9 维度锚点与证据来源 |
| `references/paradigms-2026.md` | 打分前；外部范式摘要 + 刷新清单 |
| `references/report-template.md` | 写分析时；六节结构与常见写作错误 |
| `references/measuring-roi.md` | 用户问「怎么算 ROI / 怎么自己衡量收益」时；本 skill 打的是成熟度分不是 ROI，边界与自测方法在这里 |
| `scripts/scan.py` | 阶段①②；`--detect-only` / `--write-profile` / 正式扫描 |
| `scripts/build_report.py` | 阶段⑤；report.json → HTML + PDF |
| `assets/report.template.json` | 阶段⑤；空模板，字段带 `_doc` 说明 |
| `examples/atlas-20260909/` | 一份填好的完整样例（多仓、Gitee、OpenSpec、中文报告）：report.json + baseline.md + profile.json |
