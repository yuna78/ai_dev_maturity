# 9 维度成熟度量表

打分口径：**1 = 无 / 靠人记 · 2 = 有零散做法 · 3 = 有机制但靠自觉 · 4 = 确定性执行（hook / CI / 服务端规则拦得住）· 5 = 确定性执行且有度量**。
允许 .5。总分 = 9 维简单平均。定级：< 2.5 L2 AI 辅助；2.5–3.5 L3 Harness 化；3.5–4.5 L4 编排规模化；> 4.5 L5 自主。

每个维度给分时写一句「依据」，依据必须指向 scan.json 的字段、一个文件路径，或一次人工核对的结果。
下面每个维度的「证据」一栏列的是 scan.json 字段名（见 scan-playbook.md）。

## 1 意图与规格

| 分 | 锚点 |
|---|---|
| 1 | 需求在聊天记录里，没有结构化规格 |
| 2 | 有需求文档 / issue，但与实现没有链接 |
| 3 | 有规格层（OpenSpec / Spec Kit / ADR / 设计文档）且与任务系统关联，但关联靠人记 |
| 4 | 规格 ↔ 任务关联由 hook 或 CI 强制；完成有闭环（归档 / 关任务）；stale 规格有巡检 |
| 5 | 4 + 台账健康度有指标（stale 率、关联率、验证覆盖率）且持续收敛 |

证据：`spec.kind`、`spec.active / stale_30d / unlinked / with_verification / no_tasks`、`spec.adr_count / adr_newest_days`。
**扣分信号**：stale 占 active 超一半；规格描述的能力与主线代码脱节。

## 2 上下文工程

| 分 | 锚点 |
|---|---|
| 1 | 没有任何 agent 指令文件（CLAUDE.md / AGENTS.md / .cursor/rules / copilot-instructions） |
| 2 | 只有一份长文件，子仓 / 子目录没有 |
| 3 | 指令文件 + skills + memory 体系完整，但体积失控（主文件 > 200 行或 skills 持续膨胀） |
| 4 | 各仓各有 ≤100 行地图式指令文件；规则按路径分层（`.claude/rules/`、`.cursor/rules/*.mdc`）；多份指令文件单一来源（软链或 include） |
| 5 | 4 + 有 agent 定期做文档垃圾回收，过时点不超过一个周期 |

证据：`root.agent_files[]`（文件与行数）、`root.instruction_files_diff_lines`、`repos[].agent_files`、`root.skills_count / skills_total_lines`、`root.has_rules_dir`。

## 3 前馈约束

| 分 | 锚点 |
|---|---|
| 1 | 没有 hook，靠 prompt 里写「请不要」 |
| 2 | 有 1–3 个 hook 或 pre-commit，多数非阻塞 |
| 3 | 关键流程（改代码、建 PR、合并）有阻塞 hook，但可被网页操作或 Bash 绕过 |
| 4 | hook + 服务端分支保护双层；关键闸 fail-closed；多种 agent 工具（Claude / Codex / Cursor）同一套规则 |
| 5 | 4 + 绕过率有度量（逃生口使用次数、网页直合次数） |

证据：`root.hooks_by_event`（来自 `.claude/settings*.json`）、`root.codex_hooks`、`repos[].ci_files` 里的 pre-commit / husky / lefthook；人工核对服务端分支保护。

## 4 反馈验证

| 分 | 锚点 |
|---|---|
| 1 | 无 CI |
| 2 | CI 只跑 lint / build |
| 3 | CI 有测试 + 覆盖率门（全局或增量），评审是同一 agent 自审 |
| 4 | 增量覆盖门 + 独立第二模型评审 + 完成要有验证记录 |
| 5 | 4 + 变异测试 / 评测集进门禁，且 CI 红有 agent 自修闭环 |

证据：`repos[].ci_files`、`repos[].ci_mentions_coverage`、`repos[].test_files / src_files`、`spec.with_verification`；变异测试工具（mutmut / Stryker / PIT）是否在构建脚本里；评审策略文件是否区分 reviewer。

## 5 多 Agent 编排

| 分 | 锚点 |
|---|---|
| 1 | 单会话串行 |
| 2 | 会用 subagent 做调研 |
| 3 | 多 worktree 并行 + 多模型并用，但串联靠人 |
| 4 | propose → 实现 → 测试 → 评审 → PR 有可复用 Workflow；跨仓变更并行 |
| 5 | 4 + CI / 巡检失败自动派 agent，人只看升级 |

证据：`repos[].worktrees`、`root.workflows_count`、`repos[].ai_by_tool`（多工具并用）。

## 6 人类监督规模化

| 分 | 锚点 |
|---|---|
| 1 | 谁写谁合 |
| 2 | 有人审，但审什么靠心情 |
| 3 | 有风险分级策略，但所有 PR 走同一条人审路径 |
| 4 | PR 按风险分档分流；高危必指定人；低危 AI 评审 + 任一人 approve |
| 5 | 4 + 单人审阅占比、验收打回率有度量并持续下降 |

证据：`repos[].merge_authors`（谁在合）、`repos[].authors[]`（谁在写）、`repos[].top_author_pct`；验收打回记录（人工）。
**特别提醒**：集中度要拆成写 / 合 / 验三件事分别看，并把各人 AI 署名率放旁边；`merge_authors` 只算 PR 合并，不算同步合并。

## 7 度量与经济账

| 分 | 锚点 |
|---|---|
| 1 | 什么都不量 |
| 2 | 有流程合规巡检 |
| 3 | 有手工统计（本 skill 的 scan 就算） |
| 4 | DORA 四指标 + AI 归属率 + 返工率自动进周报 |
| 5 | 4 + 认知债代理指标（无测试 AI commit 比例、文件作者集中度）+ 能算 J 曲线位置 |

证据：项目里有没有度量脚本 / 看板；本 skill 的基线文件是否连续。

## 8 安全前置

| 分 | 锚点 |
|---|---|
| 1 | 密钥曾入库 |
| 2 | 有 .gitignore 纪律 |
| 3 | 密钥扫描本地 + CI；数据侧 fail-closed；但 agent 常跑免审模式、hook fail-open |
| 4 | agent 权限分级成文（何时可免审）；关键 hook fail-closed；高危路径 PR 自动安全评审 |
| 5 | 4 + token 轮换有记录；agent 运行有沙箱 |

证据：`repos[].ci_mentions_secrets`（gitleaks / trufflehog / detect-secrets）、pre-commit；agent 安全规则文件是否存在。

## 9 工程之外的扩散

| 分 | 锚点 |
|---|---|
| 1 | 只有工程师用 |
| 2 | 非工程角色偶尔用聊天 |
| 3 | 有面向非工程角色的 skill / 自动化，但用量是黑箱 |
| 4 | 角色 skill 有调用埋点进周报；有同伴演示机制 |
| 5 | 4 + 非工程角色能自己写 skill / 定时任务并有评审 |

证据：`root.skills_count` 里非工程 skill 数；周报有没有用量；人工问。

## 打分表模板

| 维度 | 分 | 依据（指向数据或文件） | 参照范式 |
|---|---|---|---|
| 1 意图与规格 | | | |
| 2 上下文工程 | | | |
| 3 前馈约束 | | | |
| 4 反馈验证 | | | |
| 5 多 Agent 编排 | | | |
| 6 人类监督 | | | |
| 7 度量经济账 | | | |
| 8 安全前置 | | | |
| 9 工程之外 | | | |
| **总分（简单平均）** | | | |
