"""Builds the SVG cards for the GitHub profile README.

Runs daily in GitHub Actions. Reads public profile data through the
GitHub GraphQL API and writes three cards to dist/:
  header.svg     name, role, stats and a small RAG pipeline diagram
  skyline.svg    this year's contributions as an isometric skyline
  stack.svg      languages across my repositories

Local preview without a token:  DEMO=1 python scripts/build.py
"""
import json, math, os, urllib.request
from datetime import date

LOGIN = os.environ.get("PROFILE_LOGIN", "mhatami12")
NAME = "Maryam Hatami"
ROLE = "Applied AI Engineer · RAG & Backend"
SUB = "MSc NLP · Universität Trier · Backend: PHP, Node.js, Python"
TAGS = [("RAG", "#c4a7ff"), ("LLM evaluation", "#7dd3fc"), ("PHP / Laravel", "#fbbf24"), ("Python", "#86efac")]

W = 1000
BG, PANEL, LINE = "#0f0c17", "#17131f", "#2a2338"
TXT, MUTED, ACC, ACC2 = "#ece8f5", "#9a93ab", "#c4a7ff", "#8b6fd6"
SANS = "Inter, Segoe UI, Helvetica, Arial, sans-serif"
MONO = "JetBrains Mono, SFMono-Regular, Menlo, Consolas, monospace"
OUT = os.path.join(os.path.dirname(__file__), "..", "dist")


def x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ data
QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": "bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json"},
    )
    u = json.load(urllib.request.urlopen(req))["data"]["user"]
    repos = u["repositories"]
    langs = {}
    for r in repos["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            size, col = langs.get(n, (0, e["node"]["color"] or "#888888"))
            langs[n] = (size + e["size"], col)
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    return {
        "repos": repos["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos["nodes"]),
        "followers": u["followers"]["totalCount"],
        "total": cal["totalContributions"],
        "weeks": weeks,
        "langs": langs,
    }


def demo():
    import random
    random.seed(7)
    weeks = [[(random.random() < 0.35) * random.randint(1, 14) for _ in range(7)] for _ in range(53)]
    return {"repos": 12, "stars": 9, "followers": 20, "total": sum(map(sum, weeks)), "weeks": weeks,
            "langs": {"Python": (60, "#3572A5"), "PHP": (25, "#4F5D95"), "JavaScript": (10, "#f1e05a"), "Dockerfile": (5, "#384d54")}}


# ------------------------------------------------------------------ shared
def shell(h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
            f'<defs><linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{ACC2}" stop-opacity=".9"/><stop offset="1" stop-color="{LINE}"/></linearGradient>'
            f'<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6"/></filter></defs>'
            f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="22" fill="{BG}" stroke="url(#edge)" stroke-width="1.5"/>'
            + body + "</svg>")


def save(name, svg):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(svg)


def t(xp, yp, s, size=16, fill=TXT, font=SANS, weight=400, anchor="start", extra=""):
    return (f'<text x="{xp}" y="{yp}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{x(s)}</text>')


# ------------------------------------------------------------------ header
def pipeline(x0, y0):
    """Small vertical diagram of the RAG pipeline I build."""
    steps = [("query", "multi-part questions split first"),
             ("hybrid retrieve", "bge-m3 dense + keyword"),
             ("rerank", "CrossEncoder + threshold"),
             ("generate", "Qwen2.5-7B on vLLM"),
             ("verify", "every sentence vs. source")]
    s = [f'<rect x="{x0}" y="{y0}" width="330" height="292" rx="14" fill="{PANEL}" stroke="{LINE}"/>',
         t(x0 + 20, y0 + 30, "rag.pipeline()", 13, MUTED, MONO),
         t(x0 + 310, y0 + 30, "● live", 13, "#86efac", MONO, anchor="end")]
    for i, (a, b) in enumerate(steps):
        cy = y0 + 64 + i * 48
        last = i == len(steps) - 1
        col = "#86efac" if last else ACC
        if i:
            s.append(f'<line x1="{x0+33}" y1="{cy-36}" x2="{x0+33}" y2="{cy-12}" stroke="{ACC2}" stroke-width="2" stroke-dasharray="3 4"/>')
        s.append(f'<circle cx="{x0+33}" cy="{cy}" r="11" fill="{BG}" stroke="{col}" stroke-width="2"/>')
        s.append(t(x0 + 33, cy + 4, "✓" if last else str(i + 1), 11, col, MONO, 700, "middle"))
        s.append(t(x0 + 56, cy - 2, a, 15, TXT, MONO, 600))
        s.append(t(x0 + 56, cy + 16, b, 12, MUTED, MONO))
    return "".join(s)


def header(d):
    h = 400
    s = []
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        s.append(f'<circle cx="{32+i*20}" cy="30" r="6" fill="{c}"/>')
    s.append(t(110, 35, f"~/{LOGIN}/README.md", 13, MUTED, MONO))
    s.append(f'<line x1="1" y1="56" x2="{W-1}" y2="56" stroke="{LINE}"/>')
    s.append(t(44, 104, "@" + LOGIN, 15, ACC, MONO))
    s.append(f'<g filter="url(#soft)" opacity=".55">{t(42, 158, NAME, 46, ACC2, SANS, 800)}</g>')
    s.append(t(42, 158, NAME, 46, TXT, SANS, 800, extra='letter-spacing="-.5"'))
    s.append(t(44, 192, ROLE, 20, TXT, SANS, 600))
    s.append(t(44, 220, SUB, 13, MUTED, MONO))
    stats = [("repositories", d["repos"]), ("stars", d["stars"]),
             ("contributions", d["total"]), ("followers", d["followers"])]
    for i, (lab, v) in enumerate(stats):
        cx, cy = 44 + (i % 2) * 260, 266 + (i // 2) * 34
        s.append(t(cx, cy, f"{v:,}", 18, ACC, MONO, 700))
        s.append(t(cx + 14 + 11 * len(f"{v:,}"), cy, lab, 15, MUTED, MONO))
    cx = 44
    for lab, col in TAGS:
        w = 34 + 8.2 * len(lab)
        s.append(f'<rect x="{cx}" y="338" width="{w}" height="30" rx="15" fill="{PANEL}" stroke="{LINE}"/>')
        s.append(f'<circle cx="{cx+16}" cy="353" r="4" fill="{col}"/>')
        s.append(t(cx + 26, 358, lab, 13, TXT, MONO))
        cx += w + 10
    s.append(pipeline(632, 84))
    return shell(h, "".join(s))


# ------------------------------------------------------------------ skyline
def skyline(d):
    h = 430
    weeks = d["weeks"]
    days = [c for w in weeks for c in w]
    active = sum(1 for c in days if c)
    peak = max(days) if days else 0
    s = [t(40, 62, "Commit skyline · " + str(date.today().year), 26, TXT, SANS, 700),
         t(40, 104, "CONTRIBUTIONS", 13, ACC, MONO, extra='letter-spacing="3"'),
         f'<g filter="url(#soft)" opacity=".5">{t(38, 166, f"{d["total"]:,}", 60, ACC2, SANS, 800)}</g>',
         t(38, 166, f'{d["total"]:,}', 60, TXT, SANS, 800),
         t(40, 206, f"{active} active days", 15, MUTED, MONO),
         t(40, 232, f"busiest day: {peak}", 15, MUTED, MONO),
         t(40, 396, "one building per day · taller = more commits, PRs and issues", 13, MUTED, MONO)]
    cs, sn = math.cos(math.radians(30)), math.sin(math.radians(30))
    u = 8.2
    ox, oy = 560, 150

    def p(wk, dy, z=0):
        return ox + (wk - dy) * cs * u, oy + (wk + dy) * sn * u - z

    cells = [(wk, dy, c) for wk, w in enumerate(weeks) for dy, c in enumerate(w)]
    cells.sort(key=lambda c: c[0] + c[1])
    for wk, dy, c in cells:
        ht = 0 if not c else 4 + 72 * (c / peak) ** 0.75
        a, b, cc, dd = p(wk, dy, ht), p(wk + 1, dy, ht), p(wk + 1, dy + 1, ht), p(wk, dy + 1, ht)
        pts = lambda *q: " ".join(f"{px:.1f},{py:.1f}" for px, py in q)
        if not ht:
            s.append(f'<polygon points="{pts(a,b,cc,dd)}" fill="#1b1626" stroke="#251f33" stroke-width=".6"/>')
            continue
        hot = c >= peak * 0.7
        top = "#e3d6ff" if hot else ACC
        b0, cc0, dd0 = p(wk + 1, dy, 0), p(wk + 1, dy + 1, 0), p(wk, dy + 1, 0)
        s.append(f'<polygon points="{pts(dd,cc,cc0,dd0)}" fill="#5b45a0"/>')
        s.append(f'<polygon points="{pts(b,cc,cc0,b0)}" fill="#3d2e70"/>')
        s.append(f'<polygon points="{pts(a,b,cc,dd)}" fill="{top}"/>')
    return shell(h, "".join(s))


# ------------------------------------------------------------------ stack
def stack(d):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1][0])[:6]
    total = sum(v[0] for _, v in items) or 1
    h = 120 + 44 * len(items)
    s = [t(40, 60, "Language stack", 26, TXT, SANS, 700),
         t(W - 40, 60, "$ stack --by-bytes", 13, MUTED, MONO, anchor="end"),
         t(40, 88, "share of code across my public repositories", 13, ACC, MONO)]
    for i, (n, (size, col)) in enumerate(items):
        y = 132 + i * 44
        pct = 100 * size / total
        s.append(f'<circle cx="46" cy="{y-5}" r="6" fill="{col}"/>')
        s.append(t(64, y, n, 16, TXT, MONO))
        s.append(f'<rect x="330" y="{y-12}" width="540" height="12" rx="6" fill="{PANEL}"/>')
        s.append(f'<rect x="330" y="{y-12}" width="{max(6, 540*pct/100):.1f}" height="12" rx="6" fill="{col}"/>')
        s.append(t(W - 40, y, f"{pct:.0f}%", 14, MUTED, MONO, anchor="end"))
    return shell(h, "".join(s))


if __name__ == "__main__":
    data = demo() if os.environ.get("DEMO") else fetch()
    save("header.svg", header(data))
    save("skyline.svg", skyline(data))
    save("stack.svg", stack(data))
    print("cards written to dist/")
