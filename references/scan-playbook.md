# 扫描手册

`scripts/scan.py` 把指标一次采齐，输出 JSON。本文说明 **profile 怎么写、每个指标怎么算、哪里会算错**。

## 运行

```bash
S=~/.claude/skills/ai-collab-maturity/scripts/scan.py
python3 $S --root . --detect-only                       # 只打印识别结果，不扫
python3 $S --root . --write-profile .claude/ai-collab-maturity/profile.json   # 把识别结果写成 profile 供编辑
python3 $S --root . --profile .claude/ai-collab-maturity/profile.json > scan.json   # 正式扫描
python3 $S --root . --since "180 days ago" > scan.json  # 半年窗口（无 profile 时全自动识别）
python3 $S --root . --no-fetch > scan.json              # 离线
```

## profile.json 字段

```jsonc
{
  "name": "项目名",                       // 报告封面用
  "since": "90 days ago",                 // git --since 窗口；命令行 --since 优先
  "repos": [                              // 空数组 = 自动识别（根目录是 git 仓 → 单仓；否则一级子目录里的 git 仓）
    {"path": ".", "branch": "main"},      // path 相对 root；branch 留空 = 自动（origin/HEAD → develop → main → master → 当前）
    {"path": "backend", "branch": "develop", "skip": true}   // skip=true 排除（退役仓、fork、调研克隆）
  ],
  "author_aliases": {"Alice": ["alice", "Alice Wang", "alice@corp.com"]},   // 同一人多个 git 身份 → 规范名；
                                          // 姓名与邮箱都认，邮箱优先。有人把 user.name 配成了别人的名字时，只有邮箱能修
  "merge_patterns": ["auto"],             // 或自定义正则列表（匹配合并 commit subject/body）
  "squash_patterns": ["auto"],            // squash 合并的 subject 后缀，如 "\\(#\\d+\\)$"
  "ai_patterns": [],                      // 额外的 AI 署名正则（默认已覆盖 Claude/Codex/Copilot/Cursor/Gemini/Devin/aider 等）
  "spec": {"openspec": "openspec", "speckit": null, "adr_dirs": ["docs/adr"]},   // 留空自动探测
  "exclude_dirs": ["node_modules", "vendor", ".venv", "dist", "build"],          // 计文件时排除
  "src_extensions": [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".kt", ".rs", ".rb", ".cs", ".swift"]
}
```

## 自动识别规则

| 识别项 | 规则 | 认错时怎么办 |
|---|---|---|
| 单仓 / 多仓 | root 下有 `.git` → 单仓；否则扫一级子目录里的 `.git`（目录或 worktree 文件）| profile 里写死 `repos` |
| 默认分支 | `git symbolic-ref refs/remotes/origin/HEAD` → 否则 origin/develop → origin/main → origin/master → 当前分支 | `repos[].branch` |
| 合并约定 | 合并 commit：GitHub `Merge pull request #N`、Gitee `Merge pull request !N` 或 subject 以 `!N ` 开头、GitLab body `See merge request`、Bitbucket `Merged in … (pull request #N)`、**CODING `Accept Merge Request #N`**；squash：`--first-parent` 非合并 commit subject 以 `(#N)` / `(!N)` 结尾 | `merge_patterns` / `squash_patterns` |
| 规格层 | `openspec/changes/` → OpenSpec；`specs/*/spec.md` 或 `.specify/` → Spec Kit；`docs/adr`、`doc/adr`、`docs/decisions`、`adr/`、`architecture/decisions` → ADR | `spec` |
| agent 配置 | CLAUDE.md、AGENTS.md、GEMINI.md、`.cursorrules`、`.cursor/rules/`、`.github/copilot-instructions.md`、`.windsurfrules`、`.clinerules`、`.claude/{hooks,skills,rules,settings*.json}`、`.codex/` | 无需改 |
| CI | `.github/workflows/`、`.gitlab-ci.yml`、`.workflow/`（Gitee Go）、`Jenkinsfile`、`.circleci/`、`azure-pipelines.yml`、`bitbucket-pipelines.yml`、`.pre-commit-config.yaml`、`.githooks/`、`.husky/`、`lefthook.yml`、`Makefile`、`.coding-ci.yml`（CODING CI 2.0）| 无需改 |

## 指标定义

### 每个仓（`repos[]`，一律以 `origin/<branch>` 为准）

| 字段 | 算法 | 为什么 / 坑 |
|---|---|---|
| `head` / `head_date` | `git log -1 origin/<branch>` | 写进报告封面作基线 |
| `commits` / `commits_nonmerge` | `rev-list --count [--no-merges] --since` | 作者统计用非合并 |
| `merged_prs` | 合并 commit 命中合并约定 + first-parent squash 命中 | 为 0 说明约定没识别出来 |
| `merge_authors[]` | 上述 PR 合并的作者分布 | **只算 PR 合并**。`Merge branch 'develop' into feat/x` 是同步合并，算进去会把「合 PR 前先合主线」的人误判成评审者（踩过） |
| `fix` / `feat` | 非合并 subject 首词（不分大小写，允许 `fix(scope)`）| 不规范 message 不计，是下限 |
| `reverts_hotfix` | subject 含 revert / hotfix / rollback / 回滚 / 紧急 | 变更失败率代理 |
| `ai_signed` / `ai_signed_pct` | body 命中 AI 署名正则 | **按 commit 分割 body**（`%x1e` 分隔），按行 grep 会把多行 body 拆成多条「作者」 |
| `ai_by_tool` | 署名里识别出的工具（claude / codex / copilot / cursor / gemini / other）计数 | 多工具并用是编排维度的证据 |
| `ai_by_branch` / `ai_branch_prs` | 合并进来的**分支名**里出现工具名的 PR 数（工具名须是完整一段 `codex/x`，或一段的起始词 `codex-fix-x`）| **不留 trailer 的工具（Codex / Cursor）唯一的痕迹**，必须与 `ai_by_tool` 并排看：`ai_by_tool` 只有 claude、`ai_by_branch` 一堆 codex，就证明署名率是严重低估的下限。误报方向：`fix/cursor-position-bug` 会算成 cursor，量少，核对时扫一眼分支名 |
| `authors[]` | 别名合并后按人 total / ai_signed / ai_pct | 新人加入补 `author_aliases` |
| `top_author` / `top_author_pct` | 非合并 commit 最多的人及占比 | 集中度；要与 `merge_authors` 分开解读 |
| `pr_avg_files` / `pr_avg_add` / `pr_avg_del` / `pr_sample` | 最近 40 个 PR 合并与第一父的 `diff --shortstat` 均值 | squash 仓用该 commit 自身 diff |
| `test_files` / `src_files` | 树内按模式计数：`test_*.py`、`*_test.py`、`*.test.*`、`*.spec.*`、`tests?/`、`__tests__/`、`spec/` vs `src_extensions` 且不在排除目录 | 只做趋势，不同语言不横比 |
| `agent_files` | 仓内 agent 指令文件与行数 | 多仓项目每仓都要有自己的 |
| `ci_files` / `ci_mentions_coverage` / `ci_mentions_secrets` | CI 文件清单；文件内是否出现 cov / coverage、gitleaks / trufflehog / detect-secrets | 只证明「配置里有」，门槛数值要人读 |
| `worktrees` | `git worktree list` 行数 − 1 | 并行度代理；含废弃的 |

### 根目录（`root`）

| 字段 | 算法 |
|---|---|
| `agent_files[]` | 根目录 agent 指令文件与行数 |
| `instruction_files_diff_lines` | CLAUDE.md 与 AGENTS.md 同时存在时的 diff 行数（大 = 漂移） |
| `hooks_by_event` / `hooks_total` | 解析 `.claude/settings.json` + `settings.local.json` 的 `hooks`，按事件数命令条数 |
| `codex_hooks` | `.codex/hooks.json` 里的条数或 `.codex/hooks/` 文件数 |
| `has_rules_dir` | `.claude/rules/` 或 `.cursor/rules/` 是否存在 |
| `skills_count` / `skills_total_lines` | `.claude/skills/*/SKILL.md` |
| `workflows_count` | `.claude/workflows/` 文件数 |

### 规格层（`spec`）

| 字段 | 算法 |
|---|---|
| `kind` | openspec / speckit / adr / none（可多种并存，`kinds` 列表） |
| `active` / `archived` | OpenSpec：`changes/` 非 archive 目录 / `changes/archive/`；Spec Kit：`specs/` 目录数 |
| `stale_30d` / `stale_list` | active 中主文件（tasks.md / spec.md）最后 git 提交时间 > 30 天（取不到用 mtime） |
| `unlinked` | `.openspec.yaml` 或 spec.md 里找不到任何 `*issue*:` / `ticket:` / `jira:` / `#\d+` 关联；frozen 不计 |
| `pending` | 关联值为 PENDING / TBD |
| `with_verification` | 有 `verification.md`，**或**任一 `*.md` / `specs/**/*.md` 里有 `## Verification / 验证 / 验收 / 测试结果` 段 |
| `time_source` / `time_source_warning` | stale 判定的时间来源分布 `{"git": n, "mtime": m}`；只要 `m > 0` 就带 warning | **先看这个再看 stale**。mtime 等于本机 checkout 日期，会把一批 change 算成同一个天数。脚本已改为向上找最近的 `.git`（多仓里 spec 目录常是独立子仓）；仍出现 mtime 说明该 change 尚未提交，或仓库是 shallow clone |
| `no_tasks` | 没有 tasks.md 的骨架 |
| `adr_count` / `adr_newest_days` | ADR 目录 md 数与最新一篇距今天数 |

## 人工核对清单（脚本拿不到，报告里必须有）

1. 服务端分支保护：主线是否要求非作者审批、CI 必过。
2. 各人实际在用的 AI 工具与时长（署名率只反映会加 trailer 的工具）。
3. 上季度验收打回 / 返工次数。
4. 非工程角色的 AI 使用量。
5. 逃生口 / 免审模式的使用情况。

## 数字对不上时先查这几处

- `merged_prs` = 0 → 合并约定没识别；看 `git log --merges -5 --format=%s` 和 `git log --first-parent --no-merges -5 --format=%s`，补 `merge_patterns` / `squash_patterns`。
- `merged_prs` 比手数多 → 多半是手数只看了 subject。Gitee 一个仓里就有两种合并 commit：`Merge pull request !N …` 在 subject，或 subject 是 `!N <标题>`、`Merge pull request !N from …` 在 body。脚本对 subject + body 一起匹配，同时把 `Merge branch 'develop' into …` 这类同步合并排除在外。第一次用时手数 145，脚本 213，脚本是对的。
- 「codex 署名 8 条」之类 → 先看命中的是 trailer 还是分支名（`Merge … from user/codex/…`）。脚本只在 `Co-Authored-By` / `Generated with` 行里识别工具名。
- 作者突然分裂成两个 → 补 `author_aliases`（姓名或邮箱都行）。
- **`merge_authors` 和 `authors` 里像是两拨人** → 合并 commit 带的是**平台显示名**（如「贾明浩」），git author 是 `user.name`（如 `jiaminghao`），同一个人在两张表里是两个名字。rubric 维度⑥要求「写 / 合 / 验拆开看」，这里读错会直接把结论搞反——把两种写法都放进同一个 `author_aliases` 条目。
- `ai_signed_pct` 远低于预期 → 团队用的工具不留 trailer；这本身是发现，写进报告。
- `stale_30d` 全是新的，**或一批 change 的天数一模一样** → 时间取自 mtime 而非 git。先看 `spec.time_source`；`mtime > 0` 时 `time_source_warning` 会明说。多仓 workspace 里 spec 目录是独立子仓，2026-09 以前的版本会用根仓取时间、永远取不到、静默回落 mtime，把 36 个 change 全算成「35 天」（就是本机 clone 的日子）。
- 本地主线落后远端 → 脚本只读 `origin/<branch>`，但 `worktrees` 读本地。
