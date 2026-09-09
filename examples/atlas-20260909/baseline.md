# 基线：第一次体检（2026-09-09）· atlas-workspace

> 下次体检用这份对比。口径：近 90 天（2026-06-11 → 09-08），三个码仓 `origin/develop`（svc-search 为 `origin/master`），
> 由 `ai-collab-maturity/scripts/scan.py` + `profile.json` 产出（`scan-20260909.json`）。**以脚本数为准**；文末「更正记录」说明与首版报告的差异。

## 总分与定级

**3.3 / 5 · L3 Harness 化后段**。三个月目标 4.0。

| 维度 | 当前 | 目标 | 依据 |
|---|---|---|---|
| 1 意图与规格 | 4.0 | 4.5 | OpenSpec 205 archived；但 52 active 中 39 个 stale >30d，22 未关联 + 8 PENDING，仅 8 个有 verification.md |
| 2 上下文工程 | 3.5 | 4.0 | 根仓 CLAUDE.md 260 行、AGENTS.md 279 行（diff 20 行）；两码仓 develop 无任何 agent 指令文件；41 skill / 7,960 行；无 .claude/rules |
| 3 前馈约束 | 4.5 | 4.5 | 11 hook 挂 4 事件（PreToolUse 6 / PostToolUse 3 / Stop 1 / PreCompact 1）；review-policy.yaml 声明式；.codex/hooks 14 同源；局限：Bash 改码不拦、网页 PR 绕过、全部 fail-open、Gitee 未启用非作者审批 |
| 4 反馈验证 | 3.0 | 4.0 | CI：lint + typecheck + gitleaks + test-cov（后端全局 78%）+ diff-cov（后端 85% / 前端 80%）+ build；e2e pipeline；atlas-eval 每日；无变异测试；评审为自审 |
| 5 多 Agent 编排 | 2.5 | 3.5 | 前端 8 + 后端 16 worktree；Claude + Cursor 并用（Codex 只见分支名）；无 Workflow；CI 红无自修 |
| 6 人类监督 | 2.5 | 3.5 | Dev-A 写 40–42% 非合并 commit + 合 31–38% PR + 全部验收；Dev-B 合 43–51% PR；review-policy 有分级但无分流 |
| 7 度量经济账 | 2.0 | 3.5 | 只有 openspec tracker 合规巡检 |
| 8 安全前置 | 3.5 | 4.0 | gitleaks 双层（CI 命中 secrets 扫描）；LLM 出网 fail-loud；SQL select-only + 行级权限 fail-closed；agent 常 bypass；hook fail-open |
| 9 工程之外 | 3.5 | 4.0 | BA / PM / 解决方案 skill 齐；用量黑箱 |

## 吞吐（scan.py 口径）

| 指标 | 后端 | 前端 |
|---|---|---|
| commit（含合并） | 909 | 804 |
| 非合并 commit | 597 | 550 |
| 合并 PR（merge commit，subject 或 body 含 Merge pull request） | 213 | 184 |
| fix : feat（首词不分大小写） | 258 : 180 | 286 : 130 |
| revert / hotfix | 2 | 2 |
| AI 署名（非合并；对全部 commit） | 164（27%；18%） | 238（43%；30%） |
| 按工具 | claude 158 · cursor 6 · codex 0 | claude 233 · cursor 5 |
| 合并 PR 平均体量（~40 样本） | 12.2 文件 / +1,241 / −106 | 9.7 文件 / +691 / −100 |
| 测试文件 : 源码文件 | 482 : 748 | 341 : 533 |
| worktree | 16 | 8 |

## 按作者（非合并 commit，AI 署名率）

| 作者 | 后端 total / AI | 前端 total / AI |
|---|---|---|
| Dev-A | 239 / 136（57%） | 231 / 178（77%） |
| Dev-B | 101 / 7（7%） | 54 / 6（11%） |
| Dev-C | 65 / 8（12%） | 57 / 8（14%） |
| Dev-D | 50 / 3（6%） | 75 / 37（49%） |
| Dev-E | 43 / 0 | 57 / 0 |
| Dev-F | 34 / 0 | 19 / 0 |
| Dev-G | 30 / 0 | — |
| Dev-H | 22 / 0 | 16 / 0 |
| Dev-I | — | 35 / 3（8%） |

合并 PR 作者：后端 Dev-B 92（43%）/ Dev-A 81（38%）/ Dev-D 22 / Dev-J 18；前端 Dev-B 94（51%）/ Dev-A 57（31%）/ Dev-J 21 / Dev-D 12。

解读：单点不是「没用 AI」——Dev-A 是团队 AI 署名率最高的人。写（40–42%）与验（全部验收）集中在 Dev-A，合集中在 Dev-B + Dev-A 两人；其他人 AI 署名 0–14%（Dev-D 前端 49% 例外），AI 使用没扩散。署名率是 trailer 下限。

## 治理层

- 根仓：CLAUDE.md 260 · AGENTS.md 279（diff 20）· hooks 11 / 4 事件 · .codex/hooks 14 · skills 41 / 7,960 行 · 无 rules / workflows
- 码仓：backend / frontend 主线上无 CLAUDE.md / AGENTS.md；svc-search 有（上游带）；CI 文件 8 / 7 / 3，覆盖率与密钥扫描均命中（search-svc 无密钥扫描）
- openspec（09-09 晨快照）：52 active / 205 archived / 39 stale / 22 unlinked / 8 PENDING / 1 frozen / 8 with verification / 1 无 tasks
  - 同日稍后 pull 后另一会话已归档一批：42 active / 234 archived / 29 stale / 7 unlinked。下次体检以新状态为起点
- doc：ADR 11 条；claudereview 14 份；harness panorama（2026-07-13）已指出台账脱节、重影、本地落后
- 人工核对：Gitee 服务端非作者审批**未启用**；非工程 skill 用量未知；验收打回次数未统计

## 17 项方案摘要（验收指标见报告）

第一波（2 周）：#1 码仓 CLAUDE.md ≤100 行 · #2 根仓瘦身 ≤130 行 · #3 台账清扫 active ≤20 · #4 Gitee 分支保护 · #5 PR 体量硬门
第二波（1–2 月）：#6 第二模型评审 · #7 verification 归档硬门 · #8 变异测试试点 · #9 CI 红自修 · #10 前端红线制度化 · #11 关键闸 fail-closed
第三波（季度）：#12 度量看板 · #13 监督分层（单人合并 ≤40%、Dev-A 验收 ≤30%） · #14 Workflow 编排 · #15 文档 GC agent · #16 agent 安全纪律 · #17 工程之外推广

## 下次体检要专门核对的

1. #3 台账清扫做了没：active 数、stale 数（起点 42 / 29）。
2. #4 Gitee 分支保护开了没。
3. 合并集中度（Dev-B + Dev-A 合计 ≥80% 是否下降）、Dev-A 验收占比、AI 署名扩散（其他人是否 > 30%）。
4. 后端 PR 中位体量是否 ≤400 行。
5. 是否出现独立第二模型评审记录。

## 更正记录（同日）

首版报告（手工统计）与脚本口径的差异，均已在报告与本基线改正：

| 项 | 首版 | 更正 | 原因 |
|---|---|---|---|
| 合并 PR | 145 / 135 | 213 / 184 | 只看 subject 漏掉 Gitee「Merge pull request 在 body」的格式 |
| Dev-A 合并 | 先写 112 / 78（50%），后改 17 / 8 | 81 / 57（38% / 31%） | 第一次把同步合并算进去，第二次又只看 subject |
| 未关联 change | 13 | 22 | 手数漏了 |
| PR 体量 | 15.4 文件 / +1,547 | 12.2 / +1,241 | 样本只含 subject 格式的合并 |
| 前端源码文件 | 852 | 533 | 852 含 330 个同目录测试文件 |
| Codex 署名 | 8 | 0 | 8 是分支名 `codex/…` 出现在合并 body，不是 trailer |
