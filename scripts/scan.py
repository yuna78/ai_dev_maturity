#!/usr/bin/env python3
"""ai-collab-maturity · 通用扫描脚本
用法：
  scan.py --root DIR --detect-only                 只打印自动识别结果
  scan.py --root DIR --write-profile profile.json  把识别结果写成 profile（供编辑）
  scan.py --root DIR [--profile profile.json] [--since "90 days ago"] [--no-fetch] > scan.json
指标定义、profile 字段与坑：../references/scan-playbook.md
"""
import argparse, collections, glob, json, os, pathlib, re, subprocess, sys, time

# ---------- 默认规则 ----------
DEFAULT_EXCLUDE = ["node_modules", "vendor", ".venv", "venv", "dist", "build", ".next", "target", "__pycache__", ".git", ".tmp", "coverage"]
DEFAULT_SRC_EXT = [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".kt", ".rs", ".rb", ".cs", ".swift", ".php", ".scala", ".vue"]
MERGE_PATTERNS = [r"Merge pull request #\d+", r"Merge pull request !\d+", r"^!\d+\s", r"See merge request", r"Merged in .* \(pull request #\d+\)",
                  r"Accept Merge Request #\d+"]   # CODING (e.coding.net)
SQUASH_PATTERNS = [r"\(#\d+\)\s*$", r"\(!\d+\)\s*$"]
AI_TOOLS = [("claude", r"claude"), ("codex", r"codex"), ("copilot", r"copilot"), ("cursor", r"cursor"), ("gemini", r"gemini"),
            ("devin", r"devin"), ("aider", r"aider"), ("windsurf", r"windsurf"), ("cline", r"cline"), ("other-ai", r"anthropic|openai|chatgpt|\bamp\b|\bbot\b")]
AI_LINE = re.compile(r"(co-authored-by:[^\n]*|generated with[^\n]*|🤖[^\n]*)", re.I)
# 分支名取证：Codex / Cursor 等不写 trailer，分支名是唯一痕迹。只认「斜杠路径里的完整一段」，
# 避免把正文里的 "cursor management" 这类词误判成工具（踩过）。
BRANCH_PATH = re.compile(r"(?:^|[\s(\'\"])((?:[\w.\-]+/)+[\w.\-]+)")
AGENT_FILES = ["CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".windsurfrules", ".clinerules", ".github/copilot-instructions.md"]
AGENT_DIRS = [".cursor/rules", ".claude/rules", ".claude/hooks", ".claude/skills", ".claude/workflows", ".codex", ".agents/skills"]
CI_PATTERNS = [r"^\.github/workflows/.*\.ya?ml$", r"^\.gitlab-ci\.ya?ml$", r"^\.workflow/.*\.ya?ml$", r"^Jenkinsfile$", r"^\.circleci/", r"^azure-pipelines\.ya?ml$",
               r"^bitbucket-pipelines\.ya?ml$", r"^\.pre-commit-config\.ya?ml$", r"^\.githooks/", r"^\.husky/", r"^lefthook\.ya?ml$", r"^Makefile$", r"^\.gitee/",
               r"^\.coding-ci\.ya?ml$"]   # CODING CI 2.0
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*\.py$|_test\.(py|go|rs)$|\.(test|spec)\.(ts|tsx|js|jsx|mjs)$|Tests?\.(java|kt|cs|swift)$", re.I)
ADR_DIRS = ["docs/adr", "doc/adr", "docs/decisions", "doc/decisions", "adr", "architecture/decisions", "docs/architecture/decisions"]

def sh(args, cwd=None, default=""):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180).stdout
    except Exception:
        return default

def git(repo, *args): return sh(["git", "-C", str(repo), *args])

def count_lines(p):
    try: return sum(1 for _ in open(p, encoding="utf-8", errors="ignore"))
    except Exception: return 0

# ---------- 识别 ----------
def detect_repos(root):
    """根目录是 git 仓 → 先当单仓；但若一级子目录里还有 git 仓（多仓 workspace），把它们都列出来，根仓标 role=root（常是治理层，可 skip）。"""
    nested = [{"path": d.name, "branch": None} for d in sorted(root.iterdir())
              if d.is_dir() and not d.name.startswith(".") and d.name not in DEFAULT_EXCLUDE and (d / ".git").exists()]
    if (root / ".git").exists():
        return ([{"path": ".", "branch": None, "role": "root"}] + nested) if nested else [{"path": ".", "branch": None}]
    return nested

def detect_branch(repo, since="90 days ago"):
    """候选：origin/HEAD 指向的分支 + develop / main / master / trunk；选窗口内 commit 最多的那个。
    只信 origin/HEAD 会踩坑：不少仓 HEAD 指向长期不动的 master，真正的主线是 develop。"""
    head = git(repo, "symbolic-ref", "-q", "refs/remotes/origin/HEAD").strip().rsplit("/", 1)[-1] or None
    cands = [b for b in dict.fromkeys([head, "develop", "main", "master", "trunk"]) if b and git(repo, "rev-parse", "--verify", "-q", f"origin/{b}").strip()]
    if not cands:
        cur = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        return cur or "HEAD", "local HEAD (no remote)"
    counts = {b: int(git(repo, "rev-list", "--count", f"--since={since}", f"origin/{b}").strip() or 0) for b in cands}
    best = max(cands, key=lambda b: (counts[b], b == head))
    src = "origin/HEAD" if best == head else f"most active in window ({counts[best]} commits; origin/HEAD→{head} has {counts.get(head, 0)})"
    return best, src

def ref_for(repo, branch):
    if git(repo, "rev-parse", "--verify", "-q", f"origin/{branch}").strip(): return f"origin/{branch}"
    return branch

def detect_spec(root):
    spec = {"openspec": None, "speckit": None, "adr_dirs": []}
    for c in ("openspec", "doc/openspec", "docs/openspec"):
        if (root / c / "changes").is_dir(): spec["openspec"] = c; break
    if (root / ".specify").is_dir() or glob.glob(str(root / "specs" / "*" / "spec.md")): spec["speckit"] = "specs"
    spec["adr_dirs"] = [d for d in ADR_DIRS if (root / d).is_dir()]
    return spec

def detect_profile(root, since):
    return {"name": root.name, "since": since, "repos": detect_repos(root), "author_aliases": {}, "merge_patterns": ["auto"],
            "squash_patterns": ["auto"], "ai_patterns": [], "spec": detect_spec(root), "exclude_dirs": DEFAULT_EXCLUDE, "src_extensions": DEFAULT_SRC_EXT}

# ---------- 扫描 ----------
def agent_files_in_tree(tree):
    out = []
    s = set(tree)
    for f in AGENT_FILES:
        if f in s: out.append(f)
    for d in AGENT_DIRS:
        n = sum(1 for p in tree if p.startswith(d + "/"))
        if n: out.append(f"{d}/ ({n})")
    return out

def scan_repo(root, rp, prof, since, no_fetch, trend_months=0):
    repo = root / rp["path"]
    name = rp["path"] if rp["path"] != "." else root.name
    if not (repo / ".git").exists(): return {"repo": name, "error": "not a git repo"}
    if not no_fetch: git(repo, "fetch", "--prune", "-q")
    branch = rp.get("branch") or detect_branch(repo, since)[0]
    ref = ref_for(repo, branch)
    if not git(repo, "rev-parse", "--verify", "-q", ref).strip(): return {"repo": name, "error": f"{ref} missing"}
    # 别名支持姓名与邮箱两种写法：邮箱能修「同事把 git user.name 配成了别人的名字」这类污染（踩过）
    alias = {a.strip().lower(): k for k, v in prof.get("author_aliases", {}).items() for a in v}
    def who(name, email):
        return alias.get((email or "").strip().lower()) or alias.get((name or "").strip().lower()) or (name or "").strip()
    mp = MERGE_PATTERNS if prof.get("merge_patterns", ["auto"]) == ["auto"] else prof["merge_patterns"]
    sp = SQUASH_PATTERNS if prof.get("squash_patterns", ["auto"]) == ["auto"] else prof["squash_patterns"]
    ai_extra = [re.compile(p, re.I) for p in prof.get("ai_patterns", [])]
    head = git(repo, "log", "-1", "--format=%h|%ci", ref).strip().split("|")
    out = {"repo": name, "path": rp["path"], "branch": branch, "ref": ref, "head": head[0], "head_date": head[1][:10] if len(head) > 1 else ""}
    out["commits"] = int(git(repo, "rev-list", "--count", f"--since={since}", ref).strip() or 0)
    out["commits_nonmerge"] = int(git(repo, "rev-list", "--count", "--no-merges", f"--since={since}", ref).strip() or 0)
    # 合并 PR：merge commit 命中约定 + first-parent squash
    # 记录用 %x1e 分隔、字段用 %x1f 分隔：body 多行，按行 split 会炸
    def recs(*fmt_args):
        raw = git(repo, "log", *fmt_args, ref)
        return [r.split("\x1f") for r in raw.split("\x1e") if r.strip()]
    merges = recs("--merges", f"--since={since}", "--format=%x1e%H%x1f%an%x1f%ae%x1f%s%x1f%b")      # [H, an, ae, subject, body]
    pr_merges = [m for m in merges if any(re.search(p, m[3] + "\n" + (m[4] if len(m) > 4 else ""), re.I) for p in mp)]
    fp = recs("--first-parent", "--no-merges", f"--since={since}", "--format=%x1e%H%x1f%an%x1f%ae%x1f%s")   # [H, an, ae, subject]
    squash = [m for m in fp if any(re.search(p, m[3]) for p in sp)]
    out["merged_prs"] = len(pr_merges) + len(squash); out["merged_via"] = {"merge_commit": len(pr_merges), "squash": len(squash)}
    ma = collections.Counter(who(m[1], m[2]) for m in pr_merges + squash)
    # 分支名取证：不留 trailer 的工具（Codex / Cursor）只能从合并进来的分支名看出来
    tool_names = {t for t, _ in AI_TOOLS if t != "other-ai"}
    by_branch = collections.Counter()
    for m in pr_merges + squash:
        segs = [seg.lower() for path in BRANCH_PATH.findall(m[3] + "\n" + (m[4] if len(m) > 4 else ""))
                for seg in path.split("/")]
        # 命中条件：工具名是完整一段（codex/foo），或一段的起始词（codex-fix-foo）。
        # 不做任意子串匹配——正文里的 "cursor management" 之类会误判（踩过）。
        # 反过来 fix/cursor-position-bug 这种会误报，量少，靠「核对异常值」环节兜。
        for t in {t for t in tool_names for seg in segs
                  if seg == t or seg.startswith(t + "-") or seg.startswith(t + "_")}:
            by_branch[t] += 1
    out["ai_by_branch"] = dict(by_branch.most_common())
    out["ai_branch_prs"] = sum(by_branch.values())
    out["merge_authors"] = [{"author": a, "merges": n} for a, n in ma.most_common(6)]
    # 非合并 commit：类型 + AI 署名（按 commit 分割）
    raw = git(repo, "log", "--no-merges", f"--since={since}", "--format=%x1e%an%x1f%ae%x1f%s%x1f%b", ref)
    recs = [r for r in raw.split("\x1e") if r.strip()]
    tot, ai, kinds, tools = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    rev = 0
    for r in recs:
        parts = r.split("\x1f"); an = who(parts[0], parts[1] if len(parts) > 1 else "")
        subj = parts[2] if len(parts) > 2 else ""; body = parts[3] if len(parts) > 3 else ""
        tot[an] += 1
        hit = None
        for line in AI_LINE.findall(body):
            for tname, pat in AI_TOOLS:
                if re.search(pat, line, re.I): hit = tname; break
            if hit: break
        if not hit and any(p.search(body) for p in ai_extra): hit = "custom"
        if hit: ai[an] += 1; tools[hit] += 1
        m = re.match(r"^\s*([a-z]+)", subj.lower())
        if m: kinds[m.group(1)] += 1
        if re.search(r"revert|hotfix|rollback|回滚|紧急", subj, re.I): rev += 1
    # ---- 按月分桶（J 曲线）：一次 git log 拿全，别按月循环调 N 次 ----
    if trend_months:
        tb = {}
        traw = git(repo, "log", "--no-merges", f"--since={trend_months} months ago",
                   "--format=%x1e%at%x1f%an%x1f%ae%x1f%s%x1f%b", ref)
        for r in (x for x in traw.split("\x1e") if x.strip()):
            q = r.split("\x1f")
            try: mon = time.strftime("%Y-%m", time.localtime(int(q[0].strip())))
            except Exception: continue
            b = tb.setdefault(mon, {"commits": 0, "ai_signed": 0, "fix": 0, "feat": 0, "reverts": 0, "merged_prs": 0})
            b["commits"] += 1
            sj = q[3] if len(q) > 3 else ""; bd = q[4] if len(q) > 4 else ""
            if any(re.search(pat, line, re.I) for line in AI_LINE.findall(bd) for _, pat in AI_TOOLS) \
               or any(pp.search(bd) for pp in ai_extra):
                b["ai_signed"] += 1
            mm = re.match(r"^\s*([a-z]+)", sj.lower())
            if mm and mm.group(1) in ("fix", "feat"): b[mm.group(1)] += 1
            if re.search(r"revert|hotfix|rollback|回滚|紧急", sj, re.I): b["reverts"] += 1
        mraw = git(repo, "log", "--merges", f"--since={trend_months} months ago",
                   "--format=%x1e%at%x1f%s%x1f%b", ref)
        for r in (x for x in mraw.split("\x1e") if x.strip()):
            q = r.split("\x1f")
            txt = (q[1] if len(q) > 1 else "") + "\n" + (q[2] if len(q) > 2 else "")
            if not any(re.search(pat, txt, re.I) for pat in mp): continue
            try: mon = time.strftime("%Y-%m", time.localtime(int(q[0].strip())))
            except Exception: continue
            tb.setdefault(mon, {"commits": 0, "ai_signed": 0, "fix": 0, "feat": 0, "reverts": 0, "merged_prs": 0})["merged_prs"] += 1
        out["trend"] = {k: tb[k] for k in sorted(tb)}

    n = max(1, len(recs))
    out.update({"fix": kinds.get("fix", 0), "feat": kinds.get("feat", 0), "reverts_hotfix": rev, "ai_signed": sum(ai.values()),
                "ai_signed_pct": round(100 * sum(ai.values()) / n), "ai_by_tool": dict(tools.most_common())})
    out["authors"] = [{"author": a, "total": c, "ai_signed": ai[a], "ai_pct": round(100 * ai[a] / c)} for a, c in tot.most_common(10)]
    top = tot.most_common(1)[0] if tot else ("", 0)
    out["top_author"], out["top_author_pct"] = top[0], round(100 * top[1] / n)
    # PR 体量
    files = adds = dels = cnt = 0
    for m in (pr_merges[:40] if pr_merges else squash[:40]):
        h = m[0].strip()
        st = git(repo, "diff", "--shortstat", f"{h}^1", h).strip()   # 与第一父比对：merge commit 得整个 PR，squash commit 得自身
        if not st: continue
        cnt += 1
        f = re.search(r"(\d+) files? changed", st); a = re.search(r"(\d+) insertions?", st); d = re.search(r"(\d+) deletions?", st)
        files += int(f.group(1)) if f else 0; adds += int(a.group(1)) if a else 0; dels += int(d.group(1)) if d else 0
    out["pr_sample"] = cnt
    out["pr_avg_files"] = round(files / cnt, 1) if cnt else None; out["pr_avg_add"] = round(adds / cnt) if cnt else None; out["pr_avg_del"] = round(dels / cnt) if cnt else None
    # 树盘点
    tree = git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()
    excl = prof.get("exclude_dirs", DEFAULT_EXCLUDE); exts = tuple(prof.get("src_extensions", DEFAULT_SRC_EXT))
    def excluded(p): return any(seg in excl for seg in p.split("/")[:-1])
    out["test_files"] = sum(1 for p in tree if TEST_RE.search(p) and not excluded(p))
    out["src_files"] = sum(1 for p in tree if p.endswith(exts) and not TEST_RE.search(p) and not excluded(p))
    out["agent_files"] = agent_files_in_tree(tree)
    ci = [p for p in tree if any(re.search(pat, p) for pat in CI_PATTERNS)]
    out["ci_files"] = ci[:15]
    blob = " ".join(git(repo, "show", f"{ref}:{p}") for p in ci[:15] if not p.endswith("/"))
    out["ci_mentions_coverage"] = bool(re.search(r"cov(erage)?\b", blob, re.I))
    out["ci_mentions_secrets"] = bool(re.search(r"gitleaks|trufflehog|detect-secrets|secret[- ]scan", blob, re.I))
    out["worktrees"] = max(0, len(git(repo, "worktree", "list").splitlines()) - 1)
    return out

def scan_root(root):
    r = {"agent_files": []}
    for f in AGENT_FILES:
        p = root / f
        if p.exists(): r["agent_files"].append({"file": f, "lines": count_lines(p)})
    if (root / "CLAUDE.md").exists() and (root / "AGENTS.md").exists():
        r["instruction_files_diff_lines"] = len(sh(["diff", str(root / "AGENTS.md"), str(root / "CLAUDE.md")]).splitlines())
    hooks = collections.Counter()
    for sf in (".claude/settings.json", ".claude/settings.local.json"):
        p = root / sf
        if p.exists():
            try:
                for ev, lst in json.loads(p.read_text(encoding="utf-8")).get("hooks", {}).items():
                    hooks[ev] += sum(len(x.get("hooks", [])) for x in lst)
            except Exception: pass
    r["hooks_by_event"] = dict(hooks); r["hooks_total"] = sum(hooks.values())
    cj = root / ".codex/hooks.json"
    r["codex_hooks"] = len(glob.glob(str(root / ".codex/hooks/*"))) or (len(json.loads(cj.read_text()).get("hooks", [])) if cj.exists() else 0)
    r["has_rules_dir"] = (root / ".claude/rules").is_dir() or (root / ".cursor/rules").is_dir()
    sk = glob.glob(str(root / ".claude/skills/*/SKILL.md"))
    r["skills_count"] = len(sk); r["skills_total_lines"] = sum(count_lines(p) for p in sk)
    r["workflows_count"] = len(glob.glob(str(root / ".claude/workflows/*")))
    return r

def find_repo(path):
    """向上找最近的 .git。多仓 workspace 里 openspec/ 常是独立子仓，用根仓取 git 时间永远取不到。"""
    p = pathlib.Path(path).resolve()
    for c in [p, *p.parents]:
        if (c / ".git").exists(): return c
    return None

def last_commit_days(repo, abs_path):
    """返回 (天数, 来源)。来源为 'git' 或 'mtime'——mtime 在刚 clone 的机器上等于 checkout 日期，
    会把全部条目算成同一个天数，必须让调用方看得见，不能静默回落（踩过：36 个 change 全是 35 天）。"""
    ap = pathlib.Path(abs_path).resolve()
    if repo:
        try: rel = str(ap.relative_to(pathlib.Path(repo).resolve()))
        except ValueError: rel = None
        if rel:
            ts = git(repo, "log", "-1", "--format=%ct", "--", rel).strip()
            if ts: return (time.time() - int(ts)) / 86400, "git"
    try: return (time.time() - ap.stat().st_mtime) / 86400, "mtime"
    except Exception: return None, None

VERIFY_SECTION = re.compile(r"^#{1,4}\s*(verification|validation|验证|验收|测试结果)", re.M | re.I)

def has_verification_section(d):
    """验证留痕不一定是 verification.md；很多团队写在 proposal / design / spec 的「## 验证」段里。
    playbook 一直是这么写的，代码此前只查文件，漏了一半（踩过：报 0，实为 44/93）。"""
    for f in list(d.glob("*.md")) + list(d.glob("specs/**/*.md")):
        try:
            if VERIFY_SECTION.search(f.read_text(encoding="utf-8", errors="ignore")): return True
        except Exception: pass
    return False

def scan_spec(root, spec_cfg):
    out = {"kinds": []}
    now = time.time()
    if spec_cfg.get("openspec"):
        base = root / spec_cfg["openspec"] / "changes"; out["kinds"].append("openspec"); out["openspec_path"] = spec_cfg["openspec"]
        o = {"active": 0, "archived": 0, "stale_30d": 0, "unlinked": 0, "pending": 0, "frozen": 0, "with_verification": 0, "no_tasks": 0, "stale_list": []}
        repo = find_repo(base) or (root if (root / ".git").exists() else None)
        o["_time_source"] = collections.Counter()
        for d in sorted(base.iterdir()):
            if not d.is_dir(): continue
            if d.name == "archive": o["archived"] = sum(1 for x in d.iterdir() if x.is_dir()); continue
            o["active"] += 1
            y = d / ".openspec.yaml"; ytxt = y.read_text(encoding="utf-8", errors="ignore") if y.exists() else ""
            frozen = (d / "FROZEN.md").exists() or re.search(r"^status:\s*frozen", ytxt, re.M)
            if frozen: o["frozen"] += 1
            # 前缀式命名（coding_task / gitee_issue / linear_ticket）必须能匹配：
            # 旧写法 ([a-z_]*issue|ticket|jira|task) 的分支只有第一项带前缀，coding_task 漏检（踩过：93 个全报未关联，实为 46）
            link = re.search(r"^\s*[a-z_]*(issue|ticket|jira|task)[a-z_]*:\s*[\"\']?(\S+?)[\"\']?\s*$", ytxt, re.M | re.I)
            if not link and not frozen: o["unlinked"] += 1
            elif link and link.group(2).upper() in ("PENDING", "TBD", "TODO"): o["pending"] += 1
            if (d / "verification.md").exists() or has_verification_section(d): o["with_verification"] += 1
            t = d / "tasks.md"
            if not t.exists(): o["no_tasks"] += 1; continue
            # frozen 是「有意停」，不是「没人管」——不计入 stale，否则补 FROZEN.md 这个动作就没意义了
            if frozen: continue
            age, src = last_commit_days(repo, t)
            if src: o["_time_source"][src] += 1
            if age and age > 30: o["stale_30d"] += 1; o["stale_list"].append({"change": d.name, "days": int(age)})
        o["stale_list"].sort(key=lambda x: -x["days"])
        ts = o.pop("_time_source"); o["time_source"] = dict(ts)
        if ts.get("mtime"):   # mtime 不可信：stale 数字很可能是 checkout 日期，必须让读报告的人看见
            o["time_source_warning"] = (f"{ts['mtime']} 个 change 的时间取自文件 mtime 而非 git 提交时间"
                                        "（多仓时 spec 目录可能是独立子仓，或仓库是 shallow clone）——stale 数字不可信，请人工复核")
        out.update(o)
    if spec_cfg.get("speckit"):
        out["kinds"].append("speckit"); specs = glob.glob(str(root / spec_cfg["speckit"] / "*" / "spec.md"))
        out["speckit_specs"] = len(specs)
        out["speckit_with_tasks"] = sum(1 for s in specs if (pathlib.Path(s).parent / "tasks.md").exists())
    if spec_cfg.get("adr_dirs"):
        out["kinds"].append("adr"); files = [f for d in spec_cfg["adr_dirs"] for f in glob.glob(str(root / d / "*.md"))]
        out["adr_count"] = len(files)
        out["adr_newest_days"] = int(min((now - os.path.getmtime(f)) / 86400 for f in files)) if files else None
    if not out["kinds"]: out["kinds"] = ["none"]
    out["kind"] = "+".join(out["kinds"])
    return out

MANUAL_CHECKS = [
    ("branch_protection", "服务端分支保护：主线是否要求非作者审批 + CI 必过"),
    ("tools_in_use", "各人实际使用的 AI 工具与时长（署名率只反映会加 trailer 的工具）"),
    ("rework_count", "上季度验收打回 / 返工次数"),
    ("non_eng_usage", "非工程角色的 AI 使用量"),
    ("escape_hatch", "逃生口 / 免审模式使用情况（--no-verify、网页直合）"),
]


def load_manual(path):
    """人工核对项要能跨季度对比，就不能只存在于当次对话里。
    没有文件时输出一份待填模板，填过的下次直接带进 scan.json。"""
    tpl = {k: {"question": q, "answer": None, "asked_on": None} for k, q in MANUAL_CHECKS}
    if not path: return {"status": "not_provided", "items": tpl}
    f = pathlib.Path(path)
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(tpl, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"status": "template_written", "path": str(f), "items": tpl}
    got = json.loads(f.read_text(encoding="utf-8"))
    for k, q in MANUAL_CHECKS:
        got.setdefault(k, {"question": q, "answer": None, "asked_on": None})
        got[k]["question"] = q
    unanswered = [k for k in got if not got[k].get("answer")]
    return {"status": "loaded", "path": str(f), "unanswered": unanswered, "items": got}


def _num(x):
    return x if isinstance(x, (int, float)) else None


def compare(old, new):
    """两次 scan.json 的差异。整个 skill 的复购价值都在第二次体检，靠人肉比两个 JSON 太贵。"""
    def tot(d, k):
        return sum((r.get(k) or 0) for r in d.get("repos", []))
    out = {"old_at": old.get("generated_at"), "new_at": new.get("generated_at"), "totals": [], "spec": [], "repos": [], "notes": []}
    for k, label, good in [("commits_nonmerge", "非合并 commit", None), ("merged_prs", "合并 PR", None),
                           ("ai_signed", "AI 署名 commit", "up"), ("ai_branch_prs", "AI 分支 PR", None),
                           ("fix", "fix", None), ("feat", "feat", None), ("reverts_hotfix", "revert/hotfix", "down"),
                           ("test_files", "测试文件", "up")]:
        o, n = tot(old, k), tot(new, k)
        out["totals"].append({"metric": label, "old": o, "new": n, "delta": n - o, "better": good})
    for k, label, good in [("active", "active change", None), ("stale_30d", "stale >30d", "down"),
                           ("unlinked", "未关联任务", "down"), ("with_verification", "有验证记录", "up"),
                           ("archived", "已归档", "up")]:
        o, n = _num(old.get("spec", {}).get(k)), _num(new.get("spec", {}).get(k))
        if o is None and n is None: continue
        out["spec"].append({"metric": label, "old": o, "new": n,
                            "delta": (n or 0) - (o or 0), "better": good})
    om = {r.get("repo"): r for r in old.get("repos", [])}
    for r in new.get("repos", []):
        o = om.get(r.get("repo"))
        if not o: out["notes"].append(f"新增仓：{r.get('repo')}"); continue
        out["repos"].append({"repo": r["repo"],
                             "commits_nonmerge": [o.get("commits_nonmerge"), r.get("commits_nonmerge")],
                             "merged_prs": [o.get("merged_prs"), r.get("merged_prs")],
                             "ai_signed_pct": [o.get("ai_signed_pct"), r.get("ai_signed_pct")],
                             "test_files": [o.get("test_files"), r.get("test_files")]})
    for name in set(om) - {r.get("repo") for r in new.get("repos", [])}:
        out["notes"].append(f"消失的仓：{name}")
    ots, nts = old.get("spec", {}).get("time_source", {}), new.get("spec", {}).get("time_source", {})
    if ots.get("mtime") or nts.get("mtime"):
        out["notes"].append("有一侧的 stale 取自 mtime，stale 差异不可信（见 spec.time_source）")
    return out


def print_compare(c):
    ar = lambda d, good: ("→" if d == 0 else ("↑" if d > 0 else "↓")) + (
        "" if not good or d == 0 else ("  ✅" if (d > 0) == (good == "up") else "  ⚠️"))
    print(f"基线对比：{c['old_at']}  →  {c['new_at']}\n")
    for title, rows in (("吞吐 / 质量", c["totals"]), ("规格台账", c["spec"])):
        if not rows: continue
        print(f"【{title}】")
        print(f"  {'指标':<16}{'上次':>8}{'本次':>8}{'变化':>9}")
        for r in rows:
            print(f"  {r['metric']:<16}{str(r['old']):>8}{str(r['new']):>8}{str(r['delta']):>7} {ar(r['delta'], r['better'])}")
        print()
    if c["repos"]:
        print("【按仓】上次 → 本次")
        print(f"  {'仓':<22}{'非合并commit':>16}{'合并PR':>12}{'AI署名%':>11}{'测试文件':>10}")
        for r in c["repos"]:
            f = lambda k: f"{r[k][0]}→{r[k][1]}"
            print(f"  {r['repo']:<22}{f('commits_nonmerge'):>16}{f('merged_prs'):>12}{f('ai_signed_pct'):>11}{f('test_files'):>10}")
        print()
    for n in c["notes"]: print("  ⚠️ " + n)


def aggregate_trend(repos):
    """把各仓的月度桶并成一条全局曲线。指标含义见 references/measuring-roi.md。"""
    agg = {}
    for r in repos:
        for mon, b in (r.get("trend") or {}).items():
            a = agg.setdefault(mon, {"commits": 0, "ai_signed": 0, "fix": 0, "feat": 0, "reverts": 0, "merged_prs": 0})
            for k, v in b.items(): a[k] = a.get(k, 0) + v
    out = []
    for mon in sorted(agg):
        b = agg[mon]; c = max(1, b["commits"])
        out.append({"month": mon, **b,
                    "ai_pct": round(b["ai_signed"] / c * 100),
                    # 返工代理：fix 占 fix+feat 的比例。越低越好，但只在同一团队内纵向比
                    "rework_pct": round(b["fix"] / max(1, b["fix"] + b["feat"]) * 100)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="."); ap.add_argument("--profile"); ap.add_argument("--since"); ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--detect-only", action="store_true"); ap.add_argument("--write-profile")
    ap.add_argument("--trend", type=int, default=0, metavar="N",
                    help="额外按月分桶最近 N 个月，产出 J 曲线数据（建议 12）")
    ap.add_argument("--compare", nargs=2, metavar=("OLD.json", "NEW.json"), help="对比两次 scan.json 并打印差异表")
    ap.add_argument("--manual", metavar="manual.json", help="人工核对项答案；文件不存在时写一份待填模板")
    a = ap.parse_args()
    if a.compare:
        o, n = (json.loads(pathlib.Path(x).read_text(encoding="utf-8")) for x in a.compare)
        print_compare(compare(o, n)); return 0
    root = pathlib.Path(a.root).resolve()
    prof = None
    if a.profile and pathlib.Path(a.profile).exists():
        prof = json.loads(pathlib.Path(a.profile).read_text(encoding="utf-8"))
    since = a.since or (prof or {}).get("since") or "90 days ago"
    if not prof: prof = detect_profile(root, since)
    if not prof.get("repos"): prof["repos"] = detect_repos(root)
    if not prof.get("spec"): prof["spec"] = detect_spec(root)
    for rp in prof["repos"]:
        if not rp.get("branch") and (root / rp["path"] / ".git").exists():
            rp["branch"], rp["_branch_source"] = detect_branch(root / rp["path"], since)
    if a.write_profile:
        p = pathlib.Path(a.write_profile); p.parent.mkdir(parents=True, exist_ok=True)
        clean = dict(prof); clean["repos"] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in prof["repos"]]
        p.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"); print("profile written:", p, file=sys.stderr)
    if a.detect_only or a.write_profile:
        print(json.dumps({"root": str(root), "repos": prof["repos"], "spec": prof["spec"], "root_agent_files": scan_root(root)["agent_files"]}, ensure_ascii=False, indent=1))
        return
    result = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M"), "root": str(root), "name": prof.get("name", root.name), "since": since,
        "repos": [scan_repo(root, rp, prof, since, a.no_fetch, a.trend) for rp in prof["repos"] if not rp.get("skip")],
        "root": scan_root(root), "spec": scan_spec(root, prof["spec"]),
        "manual_checks": load_manual(a.manual),
    }
    if a.trend: result["trend"] = aggregate_trend(result["repos"])
    result["root_path"] = str(root)
    print(json.dumps(result, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    sys.exit(main() or 0)
