"""GitHub verilerinden terminal görünümlü profil kartı (SVG) üretir.

Kullanım:  GITHUB_TOKEN=... python .github/scripts/terminal_card.py [çıktı.svg]
Ortam değişkenleri:
  GITHUB_TOKEN      GraphQL için token (Actions'ta otomatik gelir)
  GH_USER           kullanıcı adı (varsayılan: serkankorkut17)
  INCLUDE_PRIVATE   "1" ise private repoların dilleri de sayılır (token izin veriyorsa)
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "serkankorkut17")
TOKEN = os.environ["GITHUB_TOKEN"]
INCLUDE_PRIVATE = os.environ.get("INCLUDE_PRIVATE") == "1"
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/terminal.svg"

NAME = "Serkan Korkut"
ROLE = "Software Engineer / Backend Engineer @ Mapa Global"
HOST = "serkan@mapaglobal"

BG, BAR, BORDER = "#0A0A0A", "#141414", "#262626"
ORANGE, ORANGE_LIGHT, TEXT, MUTED, DIM = "#EA580C", "#FB923C", "#E5E5E5", "#A3A3A3", "#525252"
LEVELS = {"NONE": "#171717", "FIRST_QUARTILE": "#7C2D12", "SECOND_QUARTILE": "#C2410C",
          "THIRD_QUARTILE": "#EA580C", "FOURTH_QUARTILE": "#FDBA74"}
FONT = "'JetBrains Mono','Fira Code','SF Mono',Consolas,'Liberation Mono',monospace"

QUERY = """
query($login: String!, $privacy: RepositoryPrivacy) {
  user(login: $login) {
    createdAt
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: $privacy, first: 100) {
      totalCount
      nodes { languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""


def fetch():
    variables = {"login": USER, "privacy": None if INCLUDE_PRIVATE else "PUBLIC"}
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["user"]


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def uptime(created_at):
    start = dt.date.fromisoformat(created_at[:10])
    today = dt.date.today()
    months = (today.year - start.year) * 12 + today.month - start.month - (today.day < start.day)
    return f"up {plural(months // 12, 'year')}, {plural(months % 12, 'month')} · joined {start:%b %Y}"


def most_active_weekday(days):
    totals = {}
    for d in days:
        wd = dt.date.fromisoformat(d["date"]).strftime("%A")
        totals[wd] = totals.get(wd, 0) + d["contributionCount"]
    return max(totals, key=totals.get)


def busiest_day(days):
    d = max(days, key=lambda d: d["contributionCount"])
    return f'{d["contributionCount"]} · {dt.date.fromisoformat(d["date"]):%d %b}'


def top_languages(repos, n=5):
    sizes, colors = {}, {}
    for repo in repos["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            sizes[name] = sizes.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or MUTED
    total = sum(sizes.values()) or 1
    return [(name, size / total, colors[name]) for name, size in sorted(sizes.items(), key=lambda x: -x[1])[:n]]


def text(x, y, s, fill=TEXT, weight=400, anchor="start", size=14):
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}">{escape(str(s))}</text>')


def prompt(x, y, cmd):
    return (f'<text x="{x}" y="{y}" font-size="14"><tspan fill="{ORANGE}" font-weight="700">➜</tspan>'
            f'<tspan fill="{ORANGE_LIGHT}"> ~ </tspan><tspan fill="{TEXT}">{escape(cmd)}</tspan></text>')


def render(user):
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    langs = top_languages(user["repositories"])

    W, PAD = 840, 28
    parts, y = [], 72

    parts.append(prompt(PAD, y, "whoami"))
    y += 26
    parts.append(f'<text x="{PAD}" y="{y}" font-size="14"><tspan fill="{TEXT}" font-weight="700">{escape(NAME)}</tspan>'
                 f'<tspan fill="{MUTED}">  ·  {escape(ROLE)}</tspan></text>')
    y += 22
    parts.append(text(PAD, y, uptime(user["createdAt"]), DIM))

    y += 44
    parts.append(prompt(PAD, y, "gh stats --last-year"))
    stats = [
        ("contributions", f'{cal["totalContributions"]:,}'),
        ("commits", f'{cc["totalCommitContributions"]:,}'),
        ("repositories", f'{user["repositories"]["totalCount"]:,}'),
        ("active days", f'{sum(d["contributionCount"] > 0 for d in days)}'),
        ("most active", most_active_weekday(days)),
        ("busiest day", busiest_day(days)),
    ]
    for i, (label, value) in enumerate(stats):
        col, row = i % 3, i // 3
        x = PAD + col * 268
        yy = y + 30 + row * 26
        parts.append(text(x, yy, label, MUTED))
        parts.append(text(x + 230, yy, value, ORANGE_LIGHT, 700, "end"))

    y += 30 + 26 * 2 + 22
    parts.append(prompt(PAD, y, "langs --top 5"))
    bar_x, bar_w = PAD + 130, 520
    for i, (name, share, color) in enumerate(langs):
        yy = y + 30 + i * 24
        parts.append(f'<circle cx="{PAD + 5}" cy="{yy - 5}" r="5" fill="{color}"/>')
        parts.append(text(PAD + 18, yy, name, TEXT))
        parts.append(f'<rect x="{bar_x}" y="{yy - 11}" width="{bar_w}" height="12" rx="2" fill="{BORDER}"/>')
        parts.append(f'<rect x="{bar_x}" y="{yy - 11}" width="{max(bar_w * share, 3):.1f}" height="12" rx="2" '
                     f'fill="{ORANGE}"/>')
        parts.append(text(bar_x + bar_w + 16, yy, f"{share * 100:.1f}%", MUTED))

    y += 30 + 24 * len(langs) + 18
    parts.append(prompt(PAD, y, "git log --graph --since='1 year ago'"))
    cell, gap = 11, 3
    gy = y + 16
    month_seen = None
    for wi, week in enumerate(cal["weeks"]):
        for d in week["contributionDays"]:
            wd = dt.date.fromisoformat(d["date"]).isoweekday() % 7
            today = ' stroke="#FFFFFF" stroke-width="1.5" class="today"' if d is days[-1] else ""
            parts.append(f'<rect x="{PAD + wi * (cell + gap)}" y="{gy + 16 + wd * (cell + gap)}" width="{cell}" '
                         f'height="{cell}" rx="2" fill="{LEVELS[d["contributionLevel"]]}"{today}/>')
        first = dt.date.fromisoformat(week["contributionDays"][0]["date"])
        if first.month != month_seen and first.day <= 7 and wi < len(cal["weeks"]) - 2:
            parts.append(text(PAD + wi * (cell + gap), gy + 8, first.strftime("%b"), DIM, size=11))
            month_seen = first.month
    gy += 16 + 7 * (cell + gap)
    legend_x = W - PAD - 5 * (cell + gap) - 40
    parts.append(text(legend_x - 8, gy + 16, "less", DIM, anchor="end", size=11))
    for i, color in enumerate(LEVELS.values()):
        parts.append(f'<rect x="{legend_x + i * (cell + gap)}" y="{gy + 6}" width="{cell}" height="{cell}" rx="2" fill="{color}"/>')
    parts.append(text(legend_x + 5 * (cell + gap) + 4, gy + 16, "more", DIM, size=11))

    y = gy + 50
    parts.append(prompt(PAD, y, ""))
    parts.append(f'<rect x="{PAD + 38}" y="{y - 13}" width="9" height="17" fill="{ORANGE}" class="cursor"/>')

    H = y + 26
    updated = dt.date.today().strftime("%d %b %Y")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(NAME)} GitHub terminal">
<style>
text {{ font-family: {FONT}; white-space: pre; }}
.cursor {{ animation: blink 1.1s steps(1) infinite; }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>
<path d="M0.5 12.5 a12 12 0 0 1 12 -12 h{W - 25} a12 12 0 0 1 12 12 v23.5 h-{W - 1} z" fill="{BAR}"/>
<line x1="0.5" y1="36" x2="{W - 0.5}" y2="36" stroke="{BORDER}"/>
<circle cx="22" cy="18" r="6" fill="{ORANGE}"/><circle cx="42" cy="18" r="6" fill="{ORANGE_LIGHT}"/><circle cx="62" cy="18" r="6" fill="#FDBA74"/>
{text(W / 2, 23, f"{HOST}: ~", MUTED, anchor="middle", size=13)}
{text(W - 16, 23, f"updated {updated}", DIM, anchor="end", size=11)}
{chr(10).join(parts)}
</svg>
'''


def main():
    svg = render(fetch())
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{OUT} yazıldı")


if __name__ == "__main__":
    main()
