from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ.get("PROFILE_USERNAME", "ArgenisPadill")
TOKEN = os.environ["GITHUB_TOKEN"]

now = dt.datetime.now(dt.timezone.utc)
year = now.year
date_from = f"{year}-01-01T00:00:00Z"
date_to = now.strftime("%Y-%m-%dT%H:%M:%SZ")

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
  }
}
"""

payload = json.dumps({
    "query": query,
    "variables": {"login": USERNAME, "from": date_from, "to": date_to},
}).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "profile-metrics-action",
    },
    method="POST",
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read().decode("utf-8"))

if result.get("errors"):
    raise RuntimeError(json.dumps(result["errors"], ensure_ascii=False))

user = result.get("data", {}).get("user")
if not user:
    raise RuntimeError(f"GitHub user not found: {USERNAME}")

collection = user["contributionsCollection"]
calendar = collection["contributionCalendar"]
weeks = calendar["weeks"]

metrics = {
    "total": int(calendar["totalContributions"]),
    "commits": int(collection["totalCommitContributions"]),
    "prs": int(collection["totalPullRequestContributions"]),
    "issues": int(collection["totalIssueContributions"]),
    "reviews": int(collection["totalPullRequestReviewContributions"]),
}

TEXT = {
    "es": {
        "readme": Path("README.md"),
        "marker": "METRICS_ES",
        "title": f"Calendario de contribuciones · {year}",
        "subtitle": "Actividad pública registrada por GitHub",
        "updated": "Actualizado",
        "generated": "Generado automáticamente con GitHub Actions",
        "contribution_singular": "contribución",
        "contribution_plural": "contribuciones",
        "metrics_heading": lambda m: f"### {m['total']:,} contribuciones en {year}",
        "metrics_line": lambda m: (
            f"**{m['commits']:,} commits** · **{m['prs']:,} pull requests** · "
            f"**{m['issues']:,} issues** · **{m['reviews']:,} revisiones**"
        ),
    },
    "en": {
        "readme": Path("README.en.md"),
        "marker": "METRICS_EN",
        "title": f"Contribution calendar · {year}",
        "subtitle": "Public activity recorded by GitHub",
        "updated": "Updated",
        "generated": "Generated automatically by GitHub Actions",
        "contribution_singular": "contribution",
        "contribution_plural": "contributions",
        "metrics_heading": lambda m: f"### {m['total']:,} contributions in {year}",
        "metrics_line": lambda m: (
            f"**{m['commits']:,} commits** · **{m['prs']:,} pull requests** · "
            f"**{m['issues']:,} issues** · **{m['reviews']:,} reviews**"
        ),
    },
}

THEMES = {
    "dark": {
        "bg1": "#0B1220", "bg2": "#111827", "panel": "#0E1727",
        "border": "#94A3B8", "border_opacity": ".10",
        "title": "#F8FAFC", "subtitle": "#94A3B8", "footer": "#64748B",
        "zero": "#1E293B", "one": "#164E63", "low": "#0369A1",
        "mid": "#2563EB", "high": "#7C3AED",
    },
    "light": {
        "bg1": "#F8FAFC", "bg2": "#EEF2FF", "panel": "#FFFFFF",
        "border": "#94A3B8", "border_opacity": ".32",
        "title": "#0F172A", "subtitle": "#475569", "footer": "#64748B",
        "zero": "#E2E8F0", "one": "#BAE6FD", "low": "#38BDF8",
        "mid": "#3B82F6", "high": "#7C3AED",
    },
}

W, H = 900, 225
CELL = 12
GAP = 3
STEP = CELL + GAP
HEAT_Y = 78

def color_for(count: int, theme: dict[str, str]) -> str:
    if count <= 0:
        return theme["zero"]
    if count == 1:
        return theme["one"]
    if count <= 3:
        return theme["low"]
    if count <= 6:
        return theme["mid"]
    return theme["high"]

def build_svg(lang: str, theme_name: str) -> str:
    t = TEXT[lang]
    theme = THEMES[theme_name]
    heat_width = max(STEP, len(weeks) * STEP - GAP)
    heat_x = max(32, (W - heat_width) / 2)

    parts = [f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
    <stop stop-color="{theme['bg1']}"/><stop offset="1" stop-color="{theme['bg2']}"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="22" fill="url(#bg)"/>
<rect x="18" y="18" width="{W-36}" height="{H-36}" rx="18" fill="{theme['panel']}" stroke="{theme['border']}" stroke-opacity="{theme['border_opacity']}"/>
<text x="42" y="54" fill="{theme['title']}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="22" font-weight="700">{escape(t["title"])}</text>
<text x="42" y="74" fill="{theme['subtitle']}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13.5">{escape(t["subtitle"])}</text>
"""]

    for wx, week in enumerate(weeks):
        for dy, day in enumerate(week["contributionDays"]):
            count = int(day["contributionCount"])
            x = heat_x + wx * STEP
            y = HEAT_Y + dy * STEP
            label = t["contribution_singular"] if count == 1 else t["contribution_plural"]
            parts.append(
                f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.4" fill="{color_for(count, theme)}">'
                f'<title>{escape(day["date"])} · {count} {escape(label)}</title></rect>'
            )

    parts.append(
        f'<text x="42" y="207" fill="{theme["footer"]}" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11.5">'
        f'{escape(t["updated"])} {now.strftime("%Y-%m-%d %H:%M UTC")} · {escape(t["generated"])}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)

def update_readme(lang: str) -> None:
    t = TEXT[lang]
    path = t["readme"]
    content = path.read_text(encoding="utf-8")
    marker = t["marker"]
    replacement = (
        f"<!-- {marker}:START -->\n"
        f"{t['metrics_heading'](metrics)}\n"
        f"{t['metrics_line'](metrics)}\n"
        f"<!-- {marker}:END -->"
    )
    pattern = re.compile(
        rf"<!-- {re.escape(marker)}:START -->.*?<!-- {re.escape(marker)}:END -->",
        re.DOTALL,
    )
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise RuntimeError(f"Metrics marker not found in {path}: {marker}")
    path.write_text(updated, encoding="utf-8")

for lang in ("es", "en"):
    for theme_name in ("dark", "light"):
        suffix = "-light" if theme_name == "light" else ""
        output = Path(f"assets/activity-{lang}{suffix}.svg")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(build_svg(lang, theme_name), encoding="utf-8")
        print(f"Wrote {output}")
    update_readme(lang)
    print(f"Updated {lang}: {metrics['total']} contributions in {year}")
