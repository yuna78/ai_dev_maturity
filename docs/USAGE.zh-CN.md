# 使用手册

## 这东西解决什么问题

团队用上 AI 编码工具之后，早晚会问一句：**「我们到底是真的变强了，还是只是变忙了？」**

常见的答案都不太可信——厂商报告量的是别人的团队；「AI 写了多少行代码」量的是活动量不是产出；
个人感觉则普遍高估（METR 的研究反复验证过这一点）。

本工具回答一个更窄、也更有用的问题：**你们这套跟 AI 协作的方式，撑不撑得住规模化，
以及最先会从哪里裂开。** 它打的是**协作机制（harness）**的分——规格、上下文、门禁、
评审、度量——不是打人的分。

**它不算 ROI。** 成熟度高说明「你把事情做对的概率高」，不等于「这季度赚回来了」。
想自己量回报，看 [`references/measuring-roi.md`](../references/measuring-roi.md)。

## 五个阶段

```
① 预检：认清项目 → ② 扫描 → ③ 对照范式打分 → ④ 写分析 → ⑤ 出报告 + 存基线
```

完整流程在 [`SKILL.md`](../SKILL.md)，Claude Code 会自己按它走。下面是人要知道的部分。

### ① 预检

```bash
S=~/.claude/skills/ai-collab-maturity/scripts
python3 $S/scan.py --root . --detect-only
```

先看识别对不对：单仓还是多仓、每个仓的默认分支、规格层（OpenSpec / Spec Kit / ADR）、
agent 配置文件、CI 文件。**单仓项目通常零配置就对了**，不需要 profile。

需要人工修的常见三种：作者别名（同一人多个 git 身份）、要排除的仓（退役 / fork / 调研克隆）、
分支（主线不在 `origin/HEAD`）。改法：

```bash
python3 $S/scan.py --root . --write-profile .claude/ai-collab-maturity/profile.json
# 编辑后，以后每次扫描都带 --profile
```

字段说明见 [`references/scan-playbook.md`](../references/scan-playbook.md)。

### ② 扫描

```bash
python3 $S/scan.py --root . --profile .claude/ai-collab-maturity/profile.json \
        --trend 12 --manual .claude/ai-collab-maturity/manual.json > scan.json
```

- `--trend 12`：额外按月分桶，产出吞吐与返工的月度序列。**强烈建议加上**——
  只看 90 天窗口会得出和 14 个月窗口相反的结论，本工具自己就栽过一次。
  **读法**：吞吐与返工两条线一起看；返工率没有及格线，只能跟自己的历史比，
  且要先确认「有多少提交带 fix/feat 前缀」这个比例本身没变，否则趋势是规范变化造成的假象。
  **别把「我们在 J 曲线上升沿」当结论汇报**——J 曲线是比喻，没有公认测量方法。
- `--manual`：人工核对项。文件不存在时写一份待填模板，填过的下次自动带进结果，
  这样跨季度还能对比「上次答的是什么」。
- 窗口默认 90 天；半年复盘用 `--since "180 days ago"`。

**跑完必看三个自检字段**（数字太整齐往往不是真的整齐，是没匹配上）：

| 字段 | 异常信号 |
|---|---|
| `spec.time_source_warning` | 出现 = stale 天数取自文件 mtime 而非 git，**不可信** |
| `spec.unlinked` / `with_verification` | 等于 0 或等于 active 总数 = 多半是规则没匹配上 |
| `ai_by_branch` vs `ai_by_tool` | 落差大 = 有不留 trailer 的工具在用，署名率只是下限 |

数字对不上时查 playbook 的「数字对不上时先查这几处」。

### ③ 打分

读 [`references/maturity-rubric.md`](../references/maturity-rubric.md)，9 个维度逐个给分。纪律：

- **每一分都要能指到证据**：scan.json 的某个字段、某个文件路径、或某条人工核对结果。
- **3 分是分水岭**：有机制但靠自觉 = 3；hook / CI 拦得住 = 4；拦得住且有度量 = 5。
- **总分简单平均**，不加权。< 2.5 = L2；2.5–3.5 = L3；3.5–4.5 = L4；> 4.5 = L5。
- **不要拿厂商数字当目标**，目标只对自己的上一次基线。

### ④ 写分析

按 [`references/report-template.md`](../references/report-template.md) 的六节结构写。
最容易写错的四处：

1. 把「某人 commit 占比高」写成「这人没用 AI」。**拆成写 / 合 / 验三件事分别看**，
   旁边放各人的 AI 署名率。
2. 把同步合并（`Merge branch 'main' into feat/x`）当评审合并。用脚本的 `merge_authors`，
   别用 `git log --merges` 裸数。
3. 方案只有加法。**必须有「明确不做的事」**——规则堆砌不可规模化。
4. 建议没有落点。「加强评审」不算建议，「评审策略文件加 reviewer 字段，门禁 hook 校验」才算。

### ⑤ 出报告 + 存基线

```bash
cp assets/report.template.json report.json     # 或抄 examples/atlas-20260909/report.json
# 填数字后：
python3 $S/build_report.py report.json --out .
```

生成时**自动跑分页自检**，两层判据：封面高度（超出多少直接换算成砍几行）、
每页内容底边（抓孤儿页）。有问题退出码为 1。单独复查用 `--check-layout`。

**字段转义**：表格行和 `*_html` 字段吃原始 HTML；图表的 `title` / `caption` /
`segments[].label` 和 `kpis[].value` / `label` 会被转义，写 `<b>` 会原样印出来。
清单见 `assets/report.template.json` 的 `_doc_html_fields`。

存基线（每次必做，否则下次没得比）：

```bash
mkdir -p .claude/ai-collab-maturity
cp scan.json   .claude/ai-collab-maturity/scan-$(date +%Y%m%d).json
cp report.json .claude/ai-collab-maturity/report-$(date +%Y%m%d).json
# 再写一份 baseline-YYYYMMDD.md：总分、各维度分与依据、关键数字、方案摘要、
# 以及「下次要专门核对的 3–5 条」。格式见 examples/atlas-20260909/baseline.md
```

## 第二次以后：对比

```bash
python3 $S/scan.py --compare .claude/ai-collab-maturity/scan-2026Q1.json scan.json
```

输出吞吐 / 台账 / 按仓三张差异表，并对「越低越好」的指标（stale、未关联、回滚）
自动标 ✅ / ⚠️。**报告里最有价值的一段就是这个差异**，不是绝对分数。

## 常见问题

**我们只有一个仓，也没有 OpenSpec，能用吗？**
能，零配置。单仓会自动识别，规格层认 `docs/adr` 之类的 ADR 目录；一个都没有就记 `none`，
维度①按锚点扣分即可。

**我们用 GitLab / Gitee / CODING，不是 GitHub？**
都支持，合并约定和 CI 文件都在自动识别里。`scripts/selftest.py` 对五种平台各有断言。

**AI 署名率很低，是不是说明团队没在用？**
先看 `ai_by_branch`。Codex、Cursor、网页版都不留 trailer，只有分支名能看出来。
两个数落差大，说明署名率只是下限——**这本身就是报告里该写的一条发现**。

**报告点名了具体的人，合适吗？**
这是有意的：合并权集中在一个人是真实的风险信号，匿了就看不见。但 commit 占比是活动量，
读成生产力就是误读。**运行之前先想清楚这份报告给谁看。**

**多久跑一次？**
季度。跑太勤没有信号，只有噪声；一年一次又太晚，方案落不了地。
