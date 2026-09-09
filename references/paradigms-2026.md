# 外部范式摘要（AI 协作开发，截至 2026-09）

> 打分前要读的「参照系」。全部是自己的提炼，不是原文；要引用原话去看来源。
> **有效期约 6 个月**。超期先按文末刷新清单更新，再拿来评项目。

## 一、各来源一句话结论

| 来源 | 时间 | 类型 | 对评估最有用的结论 |
|---|---|---|---|
| Anthropic《2026 Agentic Coding Trends Report》 | 2026 | 厂商趋势 | 8 个趋势归成 4 个优先事项：多 Agent 协同、监督规模化、推广到工程之外、安全前置。核心悖论：开发者约 60% 工作用 AI，但能完全委托的只有 0–20%——协作而非替代。 |
| Anthropic《How AI is transforming work at Anthropic》 | 2025-12 | 内部实证（132 人问卷 + 53 访谈） | Claude 用于 59% 工作；人均合并 PR +67%；27% 的 AI 工作是「本来不会做的事」；Claude Code 自主链从 10 步涨到 21 步；担忧是技能退化和同事互动减半。 |
| DORA《ROI of AI-assisted Software Development》 | 2026-04 | 行业研究 | AI 是**放大器**：放大好组织的优点，也放大差组织的问题。采用走 **J 曲线**，先降后升，降的根因是**验证税**（核对 AI 产出的额外成本）。ROI 通过代码评审兑现。配套 7 项能力：明确 AI 立场、健康数据生态、AI 可访问内部数据、强版本控制、小批量、用户中心、优质内部平台。 |
| Thoughtworks Technology Radar Vol.34 | 2026-04 | 行业雷达 | 主题「认知债」：AI 产码快于人理解。控制手段分两类——**前馈**（Agent Skills、Spec-driven development，在生成前约束）与**反馈**（变异测试等，在人审前自纠）。OpenSpec 列 Assess，附带提醒：模型变强后要重估 SDD 工具是否还必要。对 SDD 的总体警告：手工堆规则不可规模化。 |
| OpenAI《Harness engineering》 | 2026-02 | 厂商实践 | 3 人 5 个月 1500 PR（3.5 PR/人/日）。做法：AGENTS.md 约 100 行只做「地图」；`docs/` 目录是 agent 的知识库；架构约束靠自定义 linter / CI 强制而不靠 prompt；agent 定期做文档「垃圾回收」对抗熵增；人只在高风险点介入。 |
| Microsoft CLI Agent 推广研究（arXiv 2607.01418） | 2026-07 | 大样本实证 | 数万工程师 4 个月：采用者合并 PR +24%，无新鲜感衰减；**采用靠同伴可见使用传播**，不靠自上而下推；留存与本人原有编码活跃度相关。 |
| METR 开发者生产力研究 2026 更新 | 2026-02 / 04 | 独立实证 | 早期 2026「AI 大概率提升生产力」；个体差异 2x–10x；需要 30–100 小时上手后才转正；资深工程师从 agentic 工作流（评估、指挥、系统判断）获益更大。方法论提醒仍有效：自报收益普遍高估。 |
| Stack Overflow 开发者调查 2025 / 2026 | 2025-07 / 2026-06 | 行业调查 | 采用率 84%，但「高度信任」仅 3%，资深者最不信任。信任缺口是行业性的，只能靠可核查验证弥合，不能靠更好的模型。 |
| Claude Code 官方最佳实践 | 持续更新 | 工具指南 | 精简 CLAUDE.md；规则要强制就用 hooks / permissions，上下文知识用 skills，委托边界用 subagents；改代码前先 plan；并行工作用 git worktree；能验证才能交付。 |

## 二、把它们揉成 9 个评估维度

| # | 维度 | 来自哪条范式 | 看什么 |
|---|---|---|---|
| 1 | 意图与规格 | Radar 前馈控制、SDD | 需求 → 规格 → 任务是否结构化可追溯；规格台账是否腐化 |
| 2 | 上下文工程 | OpenAI 地图式 AGENTS.md、Claude Code 最佳实践 | CLAUDE.md / AGENTS.md / cursor rules / skills 的质量与体积；每个仓有没有自己的 |
| 3 | 前馈约束 | Radar 前馈控制、OpenAI「靠 linter 不靠 prompt」 | hooks、权限、worktree、门禁是否确定性执行；能否被绕过 |
| 4 | 反馈验证 | DORA「ROI 通过评审兑现」、Radar 变异测试 | 测试、CI、增量覆盖、变异测试、独立评审、评测是否闭环 |
| 5 | 多 Agent 编排 | Anthropic 趋势 2、OpenAI 吞吐 | 并行、专业化分工、propose→PR 是否串成可复用流程 |
| 6 | 人类监督规模化 | Anthropic 趋势 4「只审要紧的」 | 按风险分层；写 / 合 / 验是否有单点 |
| 7 | 度量与经济账 | DORA 四指标 + J 曲线 | 有没有 DORA 指标、AI 归属率、返工率、认知债代理 |
| 8 | 安全前置 | Anthropic 趋势 8、Radar「权限饥渴的 agent」 | 密钥、数据边界、agent 权限、fail-closed |
| 9 | 工程之外的扩散 | Anthropic 趋势 7、Microsoft「同伴可见」 | 非工程角色是否被赋能且有使用度量 |

## 三、几条容易误用的范式

- **「合并 PR +67% / +24%」不是目标值**。那是别人的数字，你的基线是自己的上一次体检。
- **AI 署名率 ≠ AI 使用率**。只有部分工具（Claude Code、部分 Copilot / Codex 流程）会自动加 `Co-Authored-By` trailer；Cursor、网页版、手动改的不留痕。署名率是**下限**，要问人才知道真实用量。
- **「完全委托 0–20%」描述现状，不是上限**。它说明人的审查角色仍在中心，不是说不该扩大委托——扩大要靠验证能力跟上，不是靠信任。
- **Radar 对 OpenSpec / SDD 的 Assess 不是否定**。它说的是「持续观察是否还需要」；对已重度投入的团队，正确动作是治好台账而不是换工具。

## 四、来源

- Anthropic 2026 Agentic Coding Trends Report — resources.anthropic.com/2026-agentic-coding-trends-report
- Anthropic, How AI is transforming work at Anthropic — anthropic.com/research/how-ai-is-transforming-work-at-anthropic
- DORA, ROI of AI-assisted Software Development — dora.dev/ai/roi/report/ ；DORA AI Capabilities Model — dora.dev/ai/
- Thoughtworks Technology Radar Vol.34 — thoughtworks.com/about-us/news/2026/combat-ai-cognitive-debt-radar-v34；OpenSpec blip — thoughtworks.com/en-us/radar/tools/openspec；SDD blip — thoughtworks.com/radar/techniques/spec-driven-development
- OpenAI, Harness engineering — openai.com/index/harness-engineering/
- Microsoft rollout study — arxiv.org/abs/2607.01418
- METR 2026 update — metr.org/blog/2026-02-24-uplift-update/
- Stack Overflow, Closing the developer AI trust gap — stackoverflow.blog/2026/02/18/closing-the-developer-ai-trust-gap/
- Claude Code best practices — code.claude.com/docs/en/best-practices

## 五、刷新清单（超过 6 个月时执行）

按下面的查询各搜一次，只收**厂商一手报告、行业研究机构、同行评审 / arXiv、大厂工程博客**，不收自媒体转述：

1. `Anthropic agentic coding trends report <年份>` / `Anthropic how AI is transforming work engineers`
2. `DORA state of AI-assisted software development <年份>` / `DORA AI capabilities model`
3. `Thoughtworks Technology Radar vol <最新卷号> AI coding agents`
4. `OpenAI harness engineering` / `OpenAI Codex engineering practices`
5. `METR developer productivity AI <年份>`
6. `Stack Overflow developer survey <年份> AI trust`
7. `arXiv coding agent adoption enterprise study <年份>`
8. `Claude Code best practices`（看官方文档是否改了 hooks / subagents / skills 的推荐）

每条更新完把「一句话结论」表和「9 维度」表同步改掉，并在文件顶部改日期。
