"""Render a 31-day contribution activity graph as an SVG.

Replaces the hosted github-readme-activity-graph card, whose public
deployment was disabled. Usage: activity_graph.py <output.svg>
Env: GITHUB_TOKEN, USERNAME
"""

import json
import math
import os
import sys
import urllib.request
from datetime import date

DAYS = 31
WIDTH, HEIGHT = 1200, 420
LEFT, RIGHT, TOP, BOTTOM = 80, 40, 80, 70

BG = "#000000"
TEXT = "#FFFFFF"
MUTED = "#AAAAAA"
GRID = "#1F1F1F"
LINE = "#36854C"
POINT = "#4CAF50"
TITLE = "Contribution Activity"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode())

    if payload.get("errors"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")

    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    return [(date.fromisoformat(d["date"]), d["contributionCount"]) for d in days[-DAYS:]]


def nice_step(max_value, target_ticks=5):
    raw = max(max_value, 1) / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        if m * magnitude >= raw:
            return max(1, int(m * magnitude))
    return max(1, int(10 * magnitude))


def render(days):
    counts = [c for _, c in days]
    step = nice_step(max(counts))
    y_max = max(step, math.ceil(max(counts) / step) * step)

    plot_w = WIDTH - LEFT - RIGHT
    plot_h = HEIGHT - TOP - BOTTOM
    x = lambda i: LEFT + plot_w * i / (len(days) - 1)
    y = lambda v: TOP + plot_h * (1 - v / y_max)

    points = [(x(i), y(c)) for i, c in enumerate(counts)]
    line_path = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(points))
    area_path = f"{line_path} L{points[-1][0]:.1f},{y(0):.1f} L{points[0][0]:.1f},{y(0):.1f} Z"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{TITLE}">',
        "<defs>",
        '<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">',
        f'<stop offset="0%" stop-color="{LINE}" stop-opacity="0.55"/>',
        f'<stop offset="100%" stop-color="{LINE}" stop-opacity="0.03"/>',
        "</linearGradient>",
        "</defs>",
        f'<rect width="100%" height="100%" fill="{BG}"/>',
        f'<text x="{WIDTH / 2}" y="44" fill="{LINE}" font-family="{FONT}" font-size="24" font-weight="600" text-anchor="middle">{TITLE}</text>',
    ]

    for v in range(0, y_max + 1, step):
        gy = y(v)
        parts.append(f'<line x1="{LEFT}" y1="{gy:.1f}" x2="{WIDTH - RIGHT}" y2="{gy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(f'<text x="{LEFT - 14}" y="{gy + 5:.1f}" fill="{MUTED}" font-family="{FONT}" font-size="14" text-anchor="end">{v}</text>')

    for i, (d, _) in enumerate(days):
        parts.append(f'<text x="{x(i):.1f}" y="{HEIGHT - BOTTOM + 26}" fill="{MUTED}" font-family="{FONT}" font-size="13" text-anchor="middle">{d.day}</text>')

    start, end = days[0][0], days[-1][0]
    parts += [
        f'<text x="{LEFT + plot_w / 2}" y="{HEIGHT - 16}" fill="{TEXT}" font-family="{FONT}" font-size="15" text-anchor="middle">{start:%b %d} – {end:%b %d, %Y}</text>',
        f'<text transform="translate(26 {TOP + plot_h / 2}) rotate(-90)" fill="{TEXT}" font-family="{FONT}" font-size="15" text-anchor="middle">Contributions</text>',
        f'<path d="{area_path}" fill="url(#area)"/>',
        f'<path d="{line_path}" fill="none" stroke="{LINE}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>',
    ]

    for (px, py), (d, c) in zip(points, days):
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{POINT}"><title>{d:%b %d}: {c}</title></circle>')

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: activity_graph.py <output.svg>")

    days = fetch_days(os.environ["USERNAME"], os.environ["GITHUB_TOKEN"])
    out = sys.argv[1]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(days))

    print(f"Wrote {out} ({days[0][0]} to {days[-1][0]}, {sum(c for _, c in days)} contributions)")


if __name__ == "__main__":
    main()
