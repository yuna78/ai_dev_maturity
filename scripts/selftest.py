#!/usr/bin/env python3
"""ai-collab-maturity · 自检：造多平台假仓，跑 scan.py，断言识别结果。

    python3 scripts/selftest.py [-v]

改了 scan.py 的识别规则（MERGE_PATTERNS / CI_PATTERNS / 关联键 / verification / 时间来源）后必须跑一次。
这个 skill 要给别人打「测试与门禁」的分，自己不能没有回归。
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
GIT_ENV = {**os.environ, "GIT_AUTHOR_DATE": "", "GIT_COMMITTER_DATE": "",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}


def git(repo, *a, when=None):
    env = dict(GIT_ENV)
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when
    else:
        env.pop("GIT_AUTHOR_DATE", None); env.pop("GIT_COMMITTER_DATE", None)
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=T", "-c", "user.email=t@t",
                           "-c", "commit.gpgsign=false", *a],
                          capture_output=True, text=True, env=env).stdout


def mkrepo(path, branch="main"):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", branch, str(path)], capture_output=True, env=GIT_ENV)
    return path


def commit(repo, subject, body="", files=None, when=None, author=None):
    for f, c in (files or {"f.txt": subject}).items():
        p = repo / f; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(c, encoding="utf-8")
    git(repo, "add", "-A")
    msg = subject + (("\n\n" + body) if body else "")
    a = ["commit", "-q", "-m", msg]
    if author: a += [f"--author={author}"]
    git(repo, *a, when=when)


_side = [0]


def merge_commit(repo, subject, body="", when=None):
    """造一个真的 merge commit（两个父），因为 scan.py 用 --merges 筛。
    侧分支内容必须每次不同，否则第二次 git commit 无改动可提交、静默失败（自检第一版就栽在这）。"""
    _side[0] += 1
    base = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "checkout", "-q", "-b", f"_tmp{_side[0]}")
    commit(repo, "side work", files={f"side{_side[0]}.txt": f"side {_side[0]}"}, when=when)
    side = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "checkout", "-q", "-")
    git(repo, "merge", "--no-ff", "-q", side, "-m", subject + (("\n\n" + body) if body else ""), when=when)
    git(repo, "branch", "-q", "-D", f"_tmp{_side[0]}")
    return base


def fake_origin(repo, branch):
    """scan.py 只读 origin/<branch>；造一个本地 remote 让 ref 存在。"""
    bare = repo.parent / (repo.name + ".git")
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], capture_output=True, env=GIT_ENV)
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "origin", f"{branch}:{branch}")
    git(repo, "symbolic-ref", f"refs/remotes/origin/HEAD", f"refs/remotes/origin/{branch}")


CASES, FAILED = [], []


def check(name, got, want):
    ok = got == want
    CASES.append((name, ok, got, want))
    if not ok: FAILED.append(name)


def build(root):
    old = (time.time() - 90 * 86400)
    old_s = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(old))

    # ---- 平台 A：GitHub（merge commit + squash + AI 分支名 + trailer）----
    r = mkrepo(root / "gh", "main")
    commit(r, "chore: init", files={".github/workflows/ci.yml": "jobs:\n  t:\n    steps: [coverage, gitleaks]\n",
                                    "src/a.ts": "x", "src/a.test.ts": "t", "AGENTS.md": "map\n"})
    commit(r, "feat: signed", body="Co-Authored-By: Claude <noreply@anthropic.com>")
    merge_commit(r, "Merge pull request #12 from acme/codex/add-widget")
    commit(r, "fix: squashed thing (#34)")
    fake_origin(r, "main")

    # ---- 平台 B：GitLab（body 里 See merge request）----
    r = mkrepo(root / "gl", "master")
    commit(r, "chore: init", files={".gitlab-ci.yml": "test:\n  script: pytest --cov\n"})
    merge_commit(r, "Merge branch 'feat/x' into 'master'", body="See merge request grp/proj!56")
    fake_origin(r, "master")

    # ---- 平台 C：Gitee ----
    r = mkrepo(root / "gitee", "master")
    commit(r, "chore: init", files={".gitee/workflows/ci.yml": "on: pr\n"})
    merge_commit(r, "Merge pull request !78 from dev/feature-y")
    fake_origin(r, "master")

    # ---- 平台 D：CODING ----
    r = mkrepo(root / "coding", "main")
    commit(r, "chore: init", files={".coding-ci.yml": "main:\n  push:\n    - script: make ci  # coverage + gitleaks\n"})
    merge_commit(r, "Accept Merge Request #90: (mr/main/codex/thing -> main)")
    merge_commit(r, "Accept Merge Request #91: (mr/main/codex-fix-thing -> main)")
    fake_origin(r, "main")

    # ---- 平台 E：Bitbucket ----
    r = mkrepo(root / "bb", "main")
    commit(r, "chore: init", files={"bitbucket-pipelines.yml": "pipelines: {}\n"})
    merge_commit(r, "Merged in feature/z (pull request #11)")
    fake_origin(r, "main")

    # ---- 同步合并不能算 PR 合并 ----
    r = mkrepo(root / "sync", "main")
    commit(r, "chore: init")
    merge_commit(r, "Merge branch 'main' into feature/x")
    fake_origin(r, "main")

    # ---- 规格层：独立子仓（复现「多仓下 stale 静默回落 mtime」）----
    sp = mkrepo(root / "specrepo", "main")
    ch = sp / "openspec" / "changes"
    mk = lambda n, files: [ (ch / n / f).parent.mkdir(parents=True, exist_ok=True) or
                            (ch / n / f).write_text(c, encoding="utf-8") for f, c in files.items() ]
    mk("gh-linked",   {".openspec.yaml": 'schema: x\ngithub_issue: "#42"\n', "tasks.md": "- [x] a\n"})
    mk("jira-linked", {".openspec.yaml": "schema: x\njira_ticket: PROJ-7\n",  "tasks.md": "- [ ] a\n"})
    mk("coding-linked", {".openspec.yaml": 'schema: x\ncoding_task: "#31396"\n', "tasks.md": "- [ ] a\n"})
    mk("plain-linked", {".openspec.yaml": "schema: x\nissue: 99\n", "tasks.md": "- [ ] a\n"})
    mk("unlinked",    {".openspec.yaml": "schema: x\ncreated: 2026-01-01\n", "tasks.md": "- [ ] a\n"})
    mk("pending",     {".openspec.yaml": "schema: x\ncoding_task: PENDING\n", "tasks.md": "- [ ] a\n"})
    mk("verif-file",  {".openspec.yaml": "schema: x\nissue: 1\n", "tasks.md": "- [ ] a\n", "verification.md": "ok"})
    mk("verif-en",    {".openspec.yaml": "schema: x\nissue: 2\n", "tasks.md": "- [ ] a\n",
                       "proposal.md": "# p\n\n## Verification\nsteps\n"})
    mk("verif-zh",    {".openspec.yaml": "schema: x\nissue: 3\n", "tasks.md": "- [ ] a\n",
                       "specs/s.md": "# s\n\n## 验收\n标准\n"})
    (ch / "archive" / "done1").mkdir(parents=True, exist_ok=True)
    (ch / "archive" / "done1" / "tasks.md").write_text("- [x]\n", encoding="utf-8")
    git(sp, "add", "-A"); git(sp, "commit", "-q", "-m", "specs", when=old_s)   # 全部提交在 90 天前
    fake_origin(sp, "main")

    prof = {"name": "selftest", "since": "365 days ago",
            "repos": [{"path": p, "branch": b} for p, b in
                      [("gh", "main"), ("gl", "master"), ("gitee", "master"), ("coding", "main"),
                       ("bb", "main"), ("sync", "main"), ("specrepo", "main")]],
            "author_aliases": {}, "merge_patterns": ["auto"], "squash_patterns": ["auto"],
            "spec": {"openspec": "specrepo/openspec", "speckit": None, "adr_dirs": []}}
    (root / "profile.json").write_text(json.dumps(prof, ensure_ascii=False), encoding="utf-8")
    return prof


def main():
    verbose = "-v" in sys.argv
    root = pathlib.Path(tempfile.mkdtemp(prefix="acm-selftest-"))
    try:
        build(root)
        out = subprocess.run([sys.executable, str(HERE / "scan.py"), "--root", str(root),
                              "--profile", str(root / "profile.json"), "--no-fetch"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            print("scan.py 挂了：\n", out.stderr[-2000:]); return 1
        d = json.loads(out.stdout)
        R = {r["repo"]: r for r in d["repos"]}

        # --- 合并约定：五个平台都要认出 1 个 PR 合并（GitHub 还多一个 squash）---
        check("GitHub merge+squash",  R["gh"]["merged_prs"], 2)
        check("GitLab See MR",        R["gl"]["merged_prs"], 1)
        check("Gitee !N",             R["gitee"]["merged_prs"], 1)
        check("CODING Accept MR",     R["coding"]["merged_prs"], 2)
        check("Bitbucket Merged in",  R["bb"]["merged_prs"], 1)
        check("同步合并不算 PR",       R["sync"]["merged_prs"], 0)

        # --- CI 识别 ---
        check("GH Actions",  R["gh"]["ci_files"], [".github/workflows/ci.yml"])
        check("GitLab CI",   R["gl"]["ci_files"], [".gitlab-ci.yml"])
        check("Gitee CI",    R["gitee"]["ci_files"], [".gitee/workflows/ci.yml"])
        check("CODING CI",   R["coding"]["ci_files"], [".coding-ci.yml"])
        check("Bitbucket CI", R["bb"]["ci_files"], ["bitbucket-pipelines.yml"])
        check("覆盖率关键词", R["gh"]["ci_mentions_coverage"], True)
        check("密钥扫描关键词", R["gh"]["ci_mentions_secrets"], True)

        # --- AI 取证：trailer 与分支名两条路 ---
        check("trailer 署名",     R["gh"]["ai_signed"], 1)
        check("分支名 codex/x",   R["gh"]["ai_by_branch"].get("codex"), 1)
        check("分支名 codex-fix", R["coding"]["ai_by_branch"].get("codex"), 2)
        check("正文词不误判",      R["gl"].get("ai_branch_prs", 0), 0)

        # --- 规格层 ---
        s = d["spec"]
        check("active 计数",   s["active"], 9)
        check("archived 计数", s["archived"], 1)
        check("多键关联（github_issue/jira_ticket/coding_task/issue）", s["unlinked"], 1)
        check("PENDING 单列",  s["pending"], 1)
        check("verification：文件+英文段+中文段", s["with_verification"], 3)
        check("stale 全部命中", s["stale_30d"], 9)
        check("时间来源=git（子仓也要取得到）", s.get("time_source", {}).get("git"), 9)
        check("无 mtime 回落",  s.get("time_source", {}).get("mtime"), None)
        check("无 mtime 就不告警", "time_source_warning" in s, False)

        # --- 其它 ---
        check("测试文件识别", R["gh"]["test_files"], 1)
        check("agent 文件识别", R["gh"]["agent_files"], ["AGENTS.md"])

        # --- 扫描前自检 warnings ---
        # 健康仓（push 过、窗口内有提交）不许误报，否则警告会变成噪音、没人再看
        codes = lambda name: sorted(w["code"] for w in R[name].get("warnings", []))
        check("warnings 字段存在", isinstance(d.get("warnings"), list), True)
        check("健康仓零误报", codes("gh"), [])

        # 造一个「本地领先远端」的仓：这正是让报告静默全 0 的那种情况
        ahead = root / "ahead"
        mkrepo(ahead); commit(ahead, "feat: pushed")
        fake_origin(ahead, "main")
        commit(ahead, "feat: not pushed yet")
        out2 = subprocess.run([sys.executable, str(HERE / "scan.py"), "--root", str(ahead), "--no-fetch"],
                              capture_output=True, text=True)
        d2 = json.loads(out2.stdout)
        w2 = sorted(w["code"] for w in d2["warnings"])
        check("未推送提交被抓到", "unpushed" in w2, True)
        check("warnings 同时写进 repos[]", len(d2["repos"][0].get("warnings", [])) > 0, True)
        check("警告走 stderr（不污染 stdout）", "unpushed" in out2.stderr or "\u672a\u63a8\u9001" in out2.stderr or out2.stderr.strip() != "", True)
        check("默认不改退出码", out2.returncode, 0)

        out3 = subprocess.run([sys.executable, str(HERE / "scan.py"), "--root", str(ahead), "--no-fetch", "--strict"],
                              capture_output=True, text=True)
        check("--strict 有 error 就退 1", out3.returncode, 1)
        check("--strict 仍然输出完整 JSON", isinstance(json.loads(out3.stdout).get("repos"), list), True)

        for n, ok, got, want in CASES:
            if verbose or not ok:
                print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   got={got!r} want={want!r}"))
        print(f"\n{len(CASES) - len(FAILED)}/{len(CASES)} 通过" + ("" if not FAILED else f"，失败：{', '.join(FAILED)}"))
        return 1 if FAILED else 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
