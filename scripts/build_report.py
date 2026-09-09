#!/usr/bin/env python3
"""ai-collab-maturity · 报告生成（通用）
所有可见文案可通过 report.json 的 "labels" 覆盖（默认中文），见 assets/report.template.json。
用法：python3 build_report.py report.json [--out DIR] [--no-pdf]
输入 report.json（结构见 ../assets/report.example.json），输出同名 .html 与 .pdf（A4，Playwright/Chromium）。
图表全部为内联 SVG：雷达、得分条、分组柱状 ×2、环图 ×2、路线图。
"""
import sys, json, math, re, asyncio, pathlib, argparse, html as H

NAVY = "#1F3A5F"; ORANGE = "#E8762B"; TEAL = "#2A9D8F"; RED = "#D1495B"; AMBER = "#E9A03B"
GREY = "#6B7280"; LIGHT = "#F4F6F9"; LINE = "#D9DEE5"; INK = "#1E293B"
FONT = "Source Han Sans CN, PingFang SC, Hiragino Sans GB, Noto Sans CJK SC, Noto Sans SC, Microsoft YaHei, sans-serif"
COLORS = {"navy": NAVY, "orange": ORANGE, "teal": TEAL, "red": RED, "amber": AMBER, "grey": LINE}

def col(c): return COLORS.get(c, c)
def score_color(s): return TEAL if s >= 4 else (AMBER if s >= 3 else RED)
def esc(s): return H.escape(str(s), quote=False)

# ---------- SVG ----------
def radar_svg(dims, now_label, tgt_label):
    cx, cy, R = 210, 200, 140; n = len(dims)
    def pt(i, r):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(a), cy + r * math.sin(a)
    P = [f'<svg viewBox="0 0 420 400" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']
    for lvl in range(1, 6):
        r = R * lvl / 5
        P.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, r) for i in range(n)))}" fill="none" stroke="{LINE}"/>')
        P.append(f'<text x="{cx+4}" y="{pt(0, r)[1]+4:.1f}" font-size="9" fill="{GREY}">{lvl}</text>')
    for i, d in enumerate(dims):
        x, y = pt(i, R); P.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{LINE}"/>')
        lx, ly = pt(i, R + 26); anchor = "middle" if abs(lx - cx) < 12 else ("start" if lx > cx else "end")
        P.append(f'<text x="{lx:.1f}" y="{ly+4:.1f}" font-size="11" text-anchor="{anchor}" fill="{INK}">{esc(d["name"])}</text>')
    tg = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * d["target"] / 5) for i, d in enumerate(dims)))
    nw = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, R * d["now"] / 5) for i, d in enumerate(dims)))
    P.append(f'<polygon points="{tg}" fill="{TEAL}" fill-opacity="0.12" stroke="{TEAL}" stroke-width="1.5" stroke-dasharray="5 3"/>')
    P.append(f'<polygon points="{nw}" fill="{ORANGE}" fill-opacity="0.25" stroke="{ORANGE}" stroke-width="2"/>')
    for i, d in enumerate(dims):
        x, y = pt(i, R * d["now"] / 5); P.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ORANGE}"/>')
    P.append(f'<rect x="20" y="372" width="14" height="10" fill="{ORANGE}" fill-opacity="0.5" stroke="{ORANGE}"/><text x="40" y="381" font-size="10" fill="{INK}">{esc(now_label)}</text>')
    P.append(f'<rect x="140" y="372" width="14" height="10" fill="{TEAL}" fill-opacity="0.2" stroke="{TEAL}" stroke-dasharray="3 2"/><text x="160" y="381" font-size="10" fill="{INK}">{esc(tgt_label)}</text>')
    P.append("</svg>"); return "\n".join(P)

def score_bars_svg(dims):
    h = 21; top = 8; w = 420
    P = [f'<svg viewBox="0 0 {w} {top + h*len(dims) + 8}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']
    for i, d in enumerate(sorted(dims, key=lambda d: -d["now"])):
        y = top + i * h; now, tgt = d["now"], d["target"]
        P.append(f'<text x="98" y="{y+17}" font-size="11" text-anchor="end" fill="{INK}">{esc(d["name"])}</text>')
        P.append(f'<rect x="106" y="{y+5}" width="260" height="14" rx="3" fill="{LIGHT}"/>')
        P.append(f'<rect x="106" y="{y+5}" width="{260*tgt/5:.1f}" height="14" rx="3" fill="{TEAL}" fill-opacity="0.18"/>')
        P.append(f'<rect x="106" y="{y+5}" width="{260*now/5:.1f}" height="14" rx="3" fill="{score_color(now)}"/>')
        P.append(f'<text x="374" y="{y+17}" font-size="11" font-weight="600" fill="{score_color(now)}">{now:.1f}</text>')
        P.append(f'<text x="398" y="{y+17}" font-size="10" fill="{GREY}">→{tgt:.1f}</text>')
    P.append("</svg>"); return "\n".join(P)

def grouped_bars_svg(c):
    groups, series, colors = c["groups"], c["series"], [col(x) for x in c["colors"]]
    W, Hh = 420, 200; left, bottom, top = 44, 36, 26
    maxv = max(max(s["values"]) for s in series) * 1.15
    gw = (W - left - 10) / len(groups); bw = gw / (len(series) + 1)
    P = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']
    P.append(f'<text x="{left}" y="14" font-size="11" font-weight="600" fill="{NAVY}">{esc(c["title"])}</text>')
    for k in range(5):
        v = maxv * k / 4; y = Hh - bottom - (Hh - bottom - top) * k / 4
        P.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W-10}" y2="{y:.1f}" stroke="{LINE}"/>')
        P.append(f'<text x="{left-4}" y="{y+4:.1f}" font-size="9" text-anchor="end" fill="{GREY}">{int(v)}</text>')
    for gi, g in enumerate(groups):
        for si, s in enumerate(series):
            v = s["values"][gi]; bh = (Hh - bottom - top) * v / maxv
            x = left + gi * gw + bw * (si + 0.5); y = Hh - bottom - bh
            P.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.9:.1f}" height="{bh:.1f}" rx="2" fill="{colors[si]}"/>')
            P.append(f'<text x="{x+bw*0.45:.1f}" y="{y-3:.1f}" font-size="9" text-anchor="middle" fill="{INK}">{v}</text>')
        P.append(f'<text x="{left+gi*gw+gw/2:.1f}" y="{Hh-bottom+14}" font-size="10" text-anchor="middle" fill="{INK}">{esc(g)}</text>')
    lx = left
    for si, s in enumerate(series):
        P.append(f'<rect x="{lx}" y="{Hh-12}" width="10" height="10" fill="{colors[si]}"/><text x="{lx+14}" y="{Hh-3}" font-size="9" fill="{INK}">{esc(s["name"])}</text>')
        lx += 14 + len(s["name"]) * 10 + 14
    P.append("</svg>"); return "\n".join(P)

def line_svg(c):
    """双轴折线：左轴计数（吞吐），右轴百分比（返工率），可标一条竖线（如 AI 采用起点）。
    吞吐与返工必须放同一张图，分开看就看不出「速度是用什么换来的」。
    ⚠️ 不要把 AI 署名率也画上去：署名率只覆盖会写 trailer 的工具，真实使用上升时它可能反而下降，
    与返工同轴会给出反向暗示（踩过）。采用时点用 marker 竖线标注即可。"""
    W, Hh, left, right, top, bot = 700, 260, 44, 44, 18, 42
    xs = c["x"]; n = len(xs)
    P = [f'<svg viewBox="0 0 {W} {Hh}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto">']
    P.append(f'<text x="{left}" y="12" font-size="11" font-weight="600" fill="{NAVY}">{esc(c["title"])}</text>')
    plot_w, plot_h = W - left - right, Hh - top - bot
    xat = lambda i: left + (plot_w * i / max(1, n - 1))
    lmax = max([v for s_ in c["series"] if s_.get("axis", "left") == "left" for v in s_["values"]] + [1])
    rmax = max([v for s_ in c["series"] if s_.get("axis") == "right" for v in s_["values"]] + [1])
    rmax = max(rmax, 100) if any(s_.get("axis") == "right" for s_ in c["series"]) else rmax
    for f in (0, .5, 1):
        y = top + plot_h * (1 - f)
        P.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W-right}" y2="{y:.1f}" stroke="{LINE}" stroke-width="1"/>')
        P.append(f'<text x="{left-6}" y="{y+4:.1f}" font-size="9" text-anchor="end" fill="{GREY}">{round(lmax*f)}</text>')
        if any(s_.get("axis") == "right" for s_ in c["series"]):
            P.append(f'<text x="{W-right+6}" y="{y+4:.1f}" font-size="9" fill="{GREY}">{round(rmax*f)}%</text>')
    step = max(1, n // 12)
    for i, lab in enumerate(xs):
        if i % step == 0 or i == n - 1:
            P.append(f'<text x="{xat(i):.1f}" y="{Hh-bot+14}" font-size="9" text-anchor="middle" fill="{GREY}">{esc(lab)}</text>')
    if c.get("marker") is not None:
        mi = c["marker"]["at"]; mx = xat(mi)
        P.append(f'<line x1="{mx:.1f}" y1="{top}" x2="{mx:.1f}" y2="{top+plot_h}" stroke="{AMBER}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        anch = "start" if mi < n * .7 else "end"
        P.append(f'<text x="{mx + (4 if anch=="start" else -4):.1f}" y="{top+11}" font-size="9" fill="{AMBER}" text-anchor="{anch}">{esc(c["marker"]["label"])}</text>')
    for si, s_ in enumerate(c["series"]):
        mx_ = rmax if s_.get("axis") == "right" else lmax
        c_ = col(s_.get("color", ["navy", "red", "teal"][si % 3]))
        pts = " ".join(f'{xat(i):.1f},{top + plot_h * (1 - v / max(1, mx_)):.1f}' for i, v in enumerate(s_["values"]))
        dash = ' stroke-dasharray="5 3"' if s_.get("axis") == "right" else ""
        P.append(f'<polyline points="{pts}" fill="none" stroke="{c_}" stroke-width="2"{dash}/>')
        for i, v in enumerate(s_["values"]):
            P.append(f'<circle cx="{xat(i):.1f}" cy="{top + plot_h * (1 - v / max(1, mx_)):.1f}" r="2.4" fill="{c_}"/>')
        lx = left + si * 190
        P.append(f'<line x1="{lx}" y1="{Hh-10}" x2="{lx+16}" y2="{Hh-10}" stroke="{c_}" stroke-width="2"{dash}/>'
                 f'<text x="{lx+21}" y="{Hh-6}" font-size="9" fill="{INK}">{esc(s_["name"])}'
                 f'{"（右轴 %）" if s_.get("axis")=="right" else "（左轴）"}</text>')
    P.append("</svg>")
    return "".join(P)


def donut_svg(c):
    segs = c["segments"]; cx, cy, r, sw = 80, 80, 58, 22
    total = sum(s["value"] for s in segs); C = 2 * math.pi * r
    P = [f'<svg viewBox="0 0 300 160" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']
    P.append(f'<text x="8" y="14" font-size="11" font-weight="600" fill="{NAVY}">{esc(c["title"])}</text>')
    off = 0
    for s in segs:
        d = C * s["value"] / total
        P.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col(s["color"])}" stroke-width="{sw}" stroke-dasharray="{d:.2f} {C-d:.2f}" stroke-dashoffset="{-off:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        off += d
    P.append(f'<text x="{cx}" y="{cy+5}" font-size="14" font-weight="700" text-anchor="middle" fill="{INK}">{esc(c["center"])}</text>')
    ly = 44
    for s in segs:
        lab = s["label"] + (f' · {s["value"]}' if c.get("show_values", True) else "")
        P.append(f'<rect x="165" y="{ly-9}" width="11" height="11" rx="2" fill="{col(s["color"])}"/><text x="182" y="{ly}" font-size="10" fill="{INK}">{esc(lab)}</text>'); ly += 22
    P.append("</svg>"); return "\n".join(P)

def roadmap_svg(rm, week_fmt="第{n}周"):
    items, waves, weeks = rm["items"], rm["waves"], rm.get("weeks", 13)
    W = 720; rowh = 22; left = 150; top = 34
    Hh = top + rowh * len(items) + 30; scale = (W - left - 16) / weeks
    P = [f'<svg viewBox="0 0 {W} {Hh}" width="100%" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">']
    for wk in range(0, weeks + 1, 2):
        x = left + wk * scale
        P.append(f'<line x1="{x:.1f}" y1="{top-6}" x2="{x:.1f}" y2="{Hh-24}" stroke="{LINE}"/>')
        P.append(f'<text x="{x:.1f}" y="{top-12}" font-size="9" text-anchor="middle" fill="{GREY}">{esc(week_fmt.format(n=wk))}</text>')
    for w in waves:
        a, b, c = w["start"], w["end"], col(w["color"])
        P.append(f'<rect x="{left+a*scale:.1f}" y="{top-4}" width="{(b-a)*scale:.1f}" height="{Hh-top-20}" fill="{c}" fill-opacity="0.05"/>')
        P.append(f'<text x="{left+a*scale+4:.1f}" y="{Hh-6}" font-size="10" fill="{c}" font-weight="700">{esc(w["label"])}</text>')
    for i, it in enumerate(items):
        y = top + i * rowh; c = col(it["color"])
        P.append(f'<text x="{left-8}" y="{y+13}" font-size="10" text-anchor="end" fill="{INK}">{esc(it["label"])}</text>')
        P.append(f'<rect x="{left+it["start"]*scale:.1f}" y="{y+3}" width="{(it["end"]-it["start"])*scale:.1f}" height="14" rx="4" fill="{c}" fill-opacity="0.85"/>')
    P.append("</svg>"); return "\n".join(P)

# ---------- HTML ----------
def table(headers, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'

def badge(s): return f'<span class="badge" style="background:{score_color(s)}">{s:.1f}</span>'

DEFAULT_LABELS = {
    "conclusion": "一句话结论", "score_axis": "综合成熟度 / 5", "baseline": "评估基线", "author": "编制", "date": "日期", "doc_id": "编号",
    "radar_caption": "九维度成熟度雷达：当前 vs 目标", "paradigms_title": "一、外部范式：近 6 个月权威结论的提炼",
    "paradigms_cols": ["来源", "时间", "对本项目最相关的结论"], "evidence_title": "二、现状证据", "governance_title": "2.1 治理层盘点",
    "governance_cols": ["层", "已有", "缺口"], "scoring_title": "三、成熟度打分", "score_caption": "九维度得分（实心 = 当前，浅底 = 目标）",
    "score_cols": ["维度", "分", "依据 / 参照"], "plan_title": "四、优化方案", "plan_cols": ["#", "做什么", "为什么", "落点", "验收指标"],
    "not_doing": "明确不做的事", "targets": "下次重打分目标", "targets_cols": ["维度", "当前", "目标"], "sources_title": "附录 · 资料来源",
    "fig": "图", "week": "第{n}周",
}

def build_html(R):
    m, s, dims = R["meta"], R["summary"], R["dims"]
    L = {**DEFAULT_LABELS, **R.get("labels", {})}
    css = f"""
@page {{ size: A4; margin: 18mm 16mm 20mm 16mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: {FONT}; color: {INK}; font-size: 10.5pt; line-height: 1.6; margin: 0; }}
h1 {{ font-size: 24pt; color: {NAVY}; margin: 0 0 6px; line-height: 1.3; }}
h2 {{ font-size: 15pt; color: {NAVY}; border-left: 5px solid {ORANGE}; padding-left: 10px; margin: 18px 0 8px; break-after: avoid; }}
h3 {{ font-size: 12pt; color: {NAVY}; margin: 16px 0 6px; break-after: avoid; }}
p {{ margin: 6px 0; }}
.cover {{ break-after: page; padding-top: 16px; }}
.cover .kicker {{ color: {ORANGE}; font-weight: 600; letter-spacing: 2px; font-size: 11pt; }}
.cover .sub {{ color: {GREY}; font-size: 12pt; margin-top: 10px; }}
.cover .meta {{ margin-top: 10px; border-top: 1px solid {LINE}; padding-top: 14px; color: {GREY}; font-size: 10pt; }}
.cover .meta b {{ color: {INK}; }}
.hero {{ display: flex; gap: 18px; margin-top: 22px; }}
.hero .big {{ flex: 0 0 200px; background: {NAVY}; color: #fff; border-radius: 10px; padding: 18px; }}
.hero .big .num {{ font-size: 38pt; font-weight: 700; line-height: 1; }}
.hero .big .lab {{ font-size: 10pt; opacity: .85; margin-top: 6px; }}
.hero .txt {{ flex: 1; background: {LIGHT}; border-radius: 10px; padding: 16px 18px; font-size: 10.5pt; }}
.callout {{ background: #FFF4EC; border-left: 4px solid {ORANGE}; padding: 10px 14px; border-radius: 4px; margin: 10px 0; break-inside: avoid; }}
.callout.blue {{ background: #EEF3FA; border-color: {NAVY}; }}
.callout.green {{ background: #EAF6F4; border-color: {TEAL}; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 9.2pt; }}
th {{ background: {NAVY}; color: #fff; text-align: left; padding: 6px 8px; font-weight: 600; }}
td {{ padding: 5px 8px; border-bottom: 1px solid {LINE}; vertical-align: top; }}
tr {{ break-inside: avoid; }}
tbody tr:nth-child(even) td {{ background: #FAFBFD; }}
table.plan td:first-child {{ font-weight: 700; color: {ORANGE}; white-space: nowrap; }}
table.keep {{ break-inside: avoid; font-size: 8.6pt; }}
table.keep td {{ padding: 4px 7px; }}
.keepblock {{ break-inside: avoid; }}
.badge {{ display: inline-block; color: #fff; font-weight: 700; padding: 1px 8px; border-radius: 10px; font-size: 9pt; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }}
.card {{ border: 1px solid {LINE}; border-radius: 8px; padding: 10px 12px; break-inside: avoid; }}
.card h4 {{ margin: 0 0 6px; font-size: 10.5pt; color: {NAVY}; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0; }}
.kpi {{ background: {LIGHT}; border-radius: 8px; padding: 10px 12px; }}
.kpi .v {{ font-size: 18pt; font-weight: 700; color: {NAVY}; line-height: 1.1; }}
.kpi .l {{ font-size: 8.5pt; color: {GREY}; margin-top: 2px; }}
.kpi.warn .v {{ color: {RED}; }} .kpi.good .v {{ color: {TEAL}; }}
ul {{ margin: 4px 0 8px; padding-left: 20px; }} li {{ margin: 3px 0; }}
.small {{ font-size: 9pt; color: {GREY}; }}
.fig {{ break-inside: avoid; margin: 8px 0 14px; }} .fig .cap {{ font-size: 9pt; color: {GREY}; text-align: center; margin-top: 4px; }}
.src li {{ font-size: 9pt; }} .src span {{ color: {GREY}; }}
.pb {{ break-before: page; }}
"""
    kpis = "".join(f'<div class="kpi {k.get("tone","")}"><div class="v">{esc(k["value"])}</div><div class="l">{esc(k["label"])}</div></div>' for k in R["kpis"])
    charts = R["charts"]
    fig_n = [1]
    def fig(svg, cap, style=""):
        fig_n[0] += 1
        return f'<div class="fig" style="{style}">{svg}<div class="cap">{esc(L["fig"])} {fig_n[0]} · {esc(cap)}</div></div>'
    lines = "".join(fig(line_svg(c), c["caption"]) for c in charts.get("lines", []))
    bars = "".join(fig(grouped_bars_svg(c), c["caption"]) for c in charts.get("grouped_bars", []))
    donuts = "".join(fig(donut_svg(c), c["caption"]) for c in charts.get("donuts", []))
    score_rows = [[esc(d["name"]), badge(d["now"]), d["basis"]] for d in sorted(dims, key=lambda d: -d["now"])]
    waves_html = ""
    for w in R["plan"]["waves"]:
        waves_html += f'<h3>{esc(w["title"])}</h3>' + table(L["plan_cols"], w["rows"], "plan")
    targets = table(L["targets_cols"], [[t[0], badge(t[1]), badge(t[2])] for t in R["plan"]["targets"]])
    not_doing = "".join(f"<li>{x}</li>" for x in R["plan"]["not_doing"])
    sources = "".join(f"<li>{esc(t)}<br><span>{esc(u)}</span></li>" for t, u in R["sources"])
    rm = R["plan"]["roadmap"]
    pb3 = "pb" if m.get("layout", {}).get("score_on_new_page") else ""
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{esc(m["title"])}</title><style>{css}</style></head><body>
<section class="cover">
  <div class="kicker">{esc(m["kicker"])}</div>
  <h1>{m["title_html"]}</h1>
  <div class="sub">{esc(m["subtitle"])}</div>
  <div class="hero">
    <div class="big"><div class="num">{s["score"]:.1f}</div><div class="lab">{esc(L["score_axis"])}<br>{esc(s["level"])}</div></div>
    <div class="txt"><b>{esc(L["conclusion"])}</b><br>{s["conclusion_html"]}</div>
  </div>
  <div class="fig" style="margin-top:14px;max-width:400px;margin-left:auto;margin-right:auto">{radar_svg(dims, s["radar_now_label"], s["radar_target_label"])}<div class="cap">{esc(L["fig"])} 1 · {esc(L["radar_caption"])}</div></div>
  <div class="meta"><b>{esc(L["baseline"])}</b>：{esc(m["baseline"])}<br><b>{esc(L["author"])}</b>：{esc(m["author"])} · <b>{esc(L["date"])}</b>：{esc(m["date"])}{(" · <b>" + esc(L["doc_id"]) + "</b>：" + esc(m["doc_id"])) if m.get("doc_id") else ""}</div>
</section>

<h2>{esc(L["paradigms_title"])}</h2>
{table(L["paradigms_cols"], R["paradigms"]["rows"])}
<div class="callout blue">{R["paradigms"]["framework_html"]}</div>

<h2 class="pb">{esc(L["evidence_title"])}（{esc(R["evidence"]["window_label"])}）</h2>
<div class="kpis">{kpis}</div>
{lines}
<div class="grid2">{bars}</div>
<div class="grid2">{donuts}</div>
<h3>{esc(L["governance_title"])}</h3>
{table(L["governance_cols"], R["evidence"]["governance_rows"])}
<div class="callout">{R["evidence"]["self_awareness_html"]}</div>

<h2 class="{pb3}">{esc(L["scoring_title"])}</h2>
<div class="grid2" style="grid-template-columns:0.85fr 1.45fr;gap:12px">
  {fig(score_bars_svg(dims), L["score_caption"])}
  <div>{table(L["score_cols"], score_rows, "keep")}</div>
</div>
<div class="callout green">{R["scoring"]["position_html"]}</div>

<div class="keepblock"><h2>{esc(L["plan_title"])}：{esc(R["plan"]["headline"])}</h2>
<p>{R["plan"]["principles_html"]}</p>
{fig(roadmap_svg(rm, L["week"]), rm["caption"])}</div>
{waves_html}
<div class="grid2" style="margin-top:14px">
  <div class="card"><h4>{esc(L["not_doing"])}</h4><ul>{not_doing}</ul></div>
  <div class="card"><h4>{esc(L["targets"])}</h4>{targets}</div>
</div>

<h2 class="pb">{esc(L["sources_title"])}</h2>
<ol class="src">{sources}</ol>
<p class="small" style="margin-top:20px">{esc(R["footnote"])}</p>
</body></html>"""

# ---------- 分页自检 ----------
MM2PX = 96 / 25.4
LINE_PX = 22          # 正文 10.5pt × line-height 1.6 ≈ 22px，用于把「超 N px」换算成「砍几行」
# 孤儿页判据用「内容底边落在页面多高处」，不用「墨量占比」——实测墨量分不开：
# 真孤儿页 5.8%，而合法的稀疏附录页 6.5% / 7.0%，只差 0.7pp。
# 内容底边则清楚得多：孤儿页 ~15%，正常收尾页 ~60%。
ORPHAN_EXTENT = 0.25        # 内容在页面前 1/4 就结束 → 判为孤儿页
ORPHAN_EXTENT_LAST = 0.12   # 末页天然可以短，标准放宽

def page_box(html_text):
    """从生成的 CSS 里读 @page，别在两处各写一份 A4 尺寸。
    返回 (可打印宽 px, 可打印高 px, 上边距占页高比, 下边距占页高比)——后两个用于裁掉页眉页脚带。"""
    m = re.search(r"@page\s*{[^}]*margin:\s*([\d.]+)mm\s+([\d.]+)mm\s+([\d.]+)mm\s+([\d.]+)mm", html_text)
    t, rgt, btm, lft = (float(x) for x in m.groups()) if m else (18, 16, 20, 16)
    sz = re.search(r"@page\s*{[^}]*size:\s*(A4|Letter)", html_text)
    pw, ph = (216, 279) if (sz and sz.group(1) == "Letter") else (210, 297)
    return round((pw - lft - rgt) * MM2PX), round((ph - t - btm) * MM2PX), t / ph, btm / ph

async def measure_layout(pg, html_text):
    """在打印布局下量。注意必须 emulate_media('print') 且 viewport 宽 = 打印宽——
    用默认 1280px 宽量出来的高度偏小，会骗过你（踩过：量到 888 以为没超，实际打印是 1003）。"""
    w, h, _, _ = page_box(html_text)
    await pg.set_viewport_size({"width": w, "height": h})
    await pg.emulate_media(media="print"); await pg.wait_for_timeout(200)
    got = await pg.evaluate("""() => {
      const g = e => { const b = e.getBoundingClientRect(); return {h: Math.round(b.height)}; };
      const out = {blocks: []};
      const cover = document.querySelector('.cover');
      if (cover) out.cover = g(cover).h;
      document.querySelectorAll('.fig').forEach((f, i) => {
        const t = f.previousElementSibling, cap = f.querySelector('.cap');
        out.blocks.push({kind: 'fig', label: (cap ? cap.textContent : '') .slice(0, 34) || ('fig#' + i), h: g(f).h});
      });
      document.querySelectorAll('table').forEach((t, i) => out.blocks.push(
        {kind: 'table', label: 'table#' + (i + 1) + '（' + t.rows.length + ' 行）', h: g(t).h}));
      return out;
    }""")
    return w, h, got

def page_extents(pdf_path, mt=0.0, mb=0.0):
    """每页「正文内容底边 / 正文区高」。捕孤儿页的 DOM 规则写不完，直接看渲染结果最省事。
    必须先按页边距裁掉页眉页脚带——页码是每页都有的，不裁的话每页都量成 98%（踩过）。"""
    try:
        from pdf2image import convert_from_path
    except Exception:
        return None
    try:
        out = []
        for im in convert_from_path(str(pdf_path), dpi=50):
            g = im.convert("L"); H = g.height
            top, bot = int(H * mt), int(H * (1 - mb))
            body = g.crop((0, top, g.width, max(top + 1, bot)))
            bb = body.point(lambda v: 255 if v < 245 else 0).getbbox()   # 二值化后取包围盒
            out.append((bb[3] / body.height) if bb else 0.0)
        return out
    except Exception:
        return None

def report_layout(w, h, got, extents):
    warn = []
    print(f"  打印区 {w}×{h}px（读自 @page）")
    if got.get("cover") is not None:
        over = got["cover"] - h
        if over > 0:
            warn.append(f"封面超出 {over}px ≈ {max(1, round(over / LINE_PX))} 行 —— 雷达图或 meta 行会被挤到第 2 页。"
                        f"删 summary.conclusion_html 约 {max(1, round(over / LINE_PX))} 行（模板本来只要三句：位置 → 瓶颈 → 主题）")
        print(f"  封面 {got['cover']}px / {h}px {'❌ 超出' if over > 0 else '✅'}")
    for b in got["blocks"]:
        if b["h"] > h:
            warn.append(f"{b['kind']} 「{b['label']}」高 {b['h']}px > 整页 {h}px，必被截断或强制跨页")
    if extents:
        n = len(extents)
        for i, r in enumerate(extents, 1):
            lim = ORPHAN_EXTENT_LAST if i == n else ORPHAN_EXTENT
            if r < lim:
                warn.append(f"第 {i}/{n} 页内容只填到 {r*100:.0f}% 页高，多半是孤儿页（上一节末尾被挤过来）")
        print(f"  各页内容底边：{' '.join(f'{r*100:.0f}%' for r in extents)}")
    else:
        print("  各页内容底边：跳过（未装 pdf2image）")
    if warn:
        print("  ⚠️  分页问题：")
        for x in warn: print("     - " + x)
    else:
        print("  ✅ 分页无问题")
    return warn

async def check_layout_only(html_path):
    from playwright.async_api import async_playwright
    txt = html_path.read_text(encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto(html_path.as_uri()); await pg.wait_for_timeout(300)
        w, h, got = await measure_layout(pg, txt)
        await b.close()
    pdf = html_path.with_suffix(".pdf")
    _, _, mt, mb = page_box(txt)
    return report_layout(w, h, got, page_extents(pdf, mt, mb) if pdf.exists() else None)

async def render_pdf(html_path, pdf_path, footer, check=True):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto(html_path.as_uri()); await pg.wait_for_timeout(500)
        await pg.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True,
                     display_header_footer=True, header_template="<div></div>",
                     footer_template=f'<div style="width:100%;font-size:8px;color:{GREY};padding:0 16mm;display:flex;justify-content:space-between;font-family:Source Han Sans CN,sans-serif"><span>{esc(footer)}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
        # 同一个浏览器会话里顺手量一遍，几乎不花时间；靠人记得跑就等于不跑
        meas = await measure_layout(pg, html_path.read_text(encoding="utf-8")) if check else None
        await b.close()
    return meas

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("report_json"); ap.add_argument("--out", default=None); ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--check-layout", action="store_true", help="只对已生成的 HTML/PDF 复查分页，不重新生成")
    ap.add_argument("--no-layout-check", action="store_true", help="生成时跳过分页自检")
    a = ap.parse_args()
    src = pathlib.Path(a.report_json); R = json.loads(src.read_text(encoding="utf-8"))
    # resolve() 必须有：render_pdf 用 Path.as_uri()，相对路径会抛 ValueError，而此时 HTML 已经写出去了，
    # 报错像是整体失败，其实只差 PDF 一步（踩过）
    out = (pathlib.Path(a.out) if a.out else src.parent).resolve(); out.mkdir(parents=True, exist_ok=True)
    stem = R["meta"].get("file_stem", src.stem)
    html_path = out / f"{stem}.html"
    if a.check_layout:
        if not html_path.exists(): print("没找到", html_path, "——先跑一次生成"); return 1
        print("分页自检", html_path.name)
        return 1 if asyncio.run(check_layout_only(html_path)) else 0
    html_path.write_text(build_html(R), encoding="utf-8"); print("HTML", html_path)
    if not a.no_pdf:
        pdf_path = out / f"{stem}.pdf"
        meas = asyncio.run(render_pdf(html_path, pdf_path, f'{R["meta"]["title"]} · {R["meta"]["date"]}',
                                      check=not a.no_layout_check)); print("PDF ", pdf_path)
        if meas:
            print("分页自检")
            _, _, mt, mb = page_box(html_path.read_text(encoding="utf-8"))
            report_layout(*meas, page_extents(pdf_path, mt, mb))

if __name__ == "__main__":
    sys.exit(main() or 0)
