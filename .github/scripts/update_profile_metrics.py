from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ.get("PROFILE_USERNAME", "ArgenisPadill")
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT = Path("assets/activity.svg")
# Generated asset: keep this script as the single source of truth for profile metrics.

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
      restrictedContributionsCount
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

total = int(calendar["totalContributions"])
commits = int(collection["totalCommitContributions"])
prs = int(collection["totalPullRequestContributions"])
issues = int(collection["totalIssueContributions"])
reviews = int(collection["totalPullRequestReviewContributions"])
restricted = int(collection["restrictedContributionsCount"])

W, H = 1180, 330
CARD_Y = 112
HEAT_Y = 226
CELL = 10
GAP = 3
STEP = CELL + GAP
HEAT_X = 58

def color_for(count: int) -> str:
    if count <= 0:
        return "#1E293B"
    if count == 1:
        return "#164E63"
    if count <= 3:
        return "#0369A1"
    if count <= 6:
        return "#2563EB"
    return "#7C3AED"

def stat_card(x: int, label: str, value: int, width: int = 246) -> str:
    return f"""
    <g>
      <rect x="{x}" y="{CARD_Y}" width="{width}" height="78" rx="16" fill="#101A2D" stroke="#94A3B8" stroke-opacity=".08"/>
      <text x="{x + 22}" y="{CARD_Y + 28}" fill="#94A3B8" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11.5" font-weight="600" letter-spacing=".7">{escape(label.upper())}</text>
      <text x="{x + 22}" y="{CARD_Y + 59}" fill="#F8FAFC" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="27" font-weight="700">{value:,}</text>
    </g>"""

parts = [f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
    <stop stop-color="#0B1220"/><stop offset="1" stop-color="#111827"/>
  </linearGradient>
  <linearGradient id="accent" x1="48" y1="0" x2="1132" y2="0" gradientUnits="userSpaceOnUse">
    <stop stop-color="#38BDF8"/><stop offset=".55" stop-color="#60A5FA"/><stop offset="1" stop-color="#A78BFA"/>
  </linearGradient>
</defs>
<rect width="{W}" height="{H}" rx="24" fill="url(#bg)"/>
<rect x="28" y="28" width="{W-56}" height="{H-56}" rx="20" fill="#0E1727" stroke="#94A3B8" stroke-opacity=".10"/>
<text x="56" y="70" fill="#F8FAFC" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="20" font-weight="700">GitHub Activity · {year}</text>
<text x="56" y="94" fill="#94A3B8" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12.5">Public contribution metrics generated from GitHub and stored in this profile repository.</text>
"""]

parts.append(stat_card(56, "Contributions", total))
parts.append(stat_card(316, "Commits", commits))
parts.append(stat_card(576, "Pull requests", prs))
parts.append(stat_card(836, "Issues", issues))

parts.append(f'<text x="56" y="216" fill="#CBD5E1" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12.5" font-weight="600">Contribution calendar</text>')

for wx, week in enumerate(weeks):
    for dy, day in enumerate(week["contributionDays"]):
        count = int(day["contributionCount"])
        x = HEAT_X + wx * STEP
        y = HEAT_Y + dy * STEP
        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color_for(count)}">'
            f'<title>{escape(day["date"])} · {count} contribution{"s" if count != 1 else ""}</title></rect>'
        )

summary = f"{reviews:,} reviews"
if restricted:
    summary += f" · {restricted:,} private contributions included by GitHub"

parts.append(f'<text x="1124" y="216" text-anchor="end" fill="#64748B" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="11">{escape(summary)}</text>')
parts.append(f'<text x="56" y="312" fill="#64748B" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="10.5">Updated {now.strftime("%Y-%m-%d %H:%M UTC")} · Generated automatically by GitHub Actions</text>')
parts.append("</svg>")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(parts), encoding="utf-8")
print(f"Wrote {OUTPUT} — {total} contributions in {year}")
