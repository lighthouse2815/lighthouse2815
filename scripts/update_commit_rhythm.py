#!/usr/bin/env python3
"""Build a public-commit activity card using GitHub's GraphQL API."""

import calendar
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      commitContributionsByRepository(maxRepositories: 100) {
        repository { isPrivate }
        contributions(first: 100) {
          pageInfo { hasNextPage }
          nodes { occurredAt commitCount }
        }
      }
    }
  }
}
"""


def month_ranges(start, end):
    current = start
    while current <= end:
        last_day = calendar.monthrange(current.year, current.month)[1]
        last = min(end, current.replace(day=last_day))
        yield current, last
        current = last + dt.timedelta(days=1)


def fetch_commits(login, token, start, end):
    counts = {}
    for first, last in month_ranges(start, end):
        variables = {
            "login": login,
            "from": first.isoformat() + "T00:00:00Z",
            "to": last.isoformat() + "T23:59:59Z",
        }
        request = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": variables}).encode(),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "commit-rhythm"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        if result.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")
        user = result["data"]["user"]
        if user is None:
            raise RuntimeError(f"GitHub user {login!r} was not found")
        repositories = user["contributionsCollection"]["commitContributionsByRepository"]
        if len(repositories) == 100:
            raise RuntimeError("The 100-repository monthly limit was reached; the chart could be incomplete")
        for repository in repositories:
            if repository["repository"]["isPrivate"]:
                continue
            contributions = repository["contributions"]
            if contributions["pageInfo"]["hasNextPage"]:
                raise RuntimeError("The contribution page limit was reached; the chart could be incomplete")
            for contribution in contributions["nodes"]:
                day = dt.date.fromisoformat(contribution["occurredAt"][:10])
                if start <= day <= end:
                    counts[day] = counts.get(day, 0) + contribution["commitCount"]
    return counts


def streaks(counts, start, end):
    longest = run = 0
    day = start
    while day <= end:
        run = run + 1 if counts.get(day, 0) else 0
        longest = max(longest, run)
        day += dt.timedelta(days=1)
    day = end if counts.get(end, 0) else end - dt.timedelta(days=1)
    current = 0
    while day >= start and counts.get(day, 0):
        current += 1
        day -= dt.timedelta(days=1)
    return current, longest


def render(counts, start, end):
    current, longest = streaks(counts, start, end)
    # Columns begin on Sunday, like GitHub's contribution calendar.
    offset = (start.weekday() + 1) % 7
    colors = ("#42283d", "#ffdab6", "#ffb36b", "#ff8b38", "#f45c20")
    cells = []
    day = start
    while day <= end:
        index = (day - start).days + offset
        count = counts.get(day, 0)
        level = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 9 else 4
        x, y = 26 + (index // 7) * 15, 139 + (index % 7) * 15
        cells.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="3" fill="{colors[level]}"><title>{day}: {count} commits</title></rect>')
        day += dt.timedelta(days=1)
    squares = "\n    ".join(cells)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="850" height="295" viewBox="0 0 850 295" role="img" aria-labelledby="title desc">
  <title id="title">Commit rhythm</title>
  <desc id="desc">Public commits from {start} to {end}. Current streak {current} days; longest streak {longest} days.</desc>
  <defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#261a2b"/><stop offset="1" stop-color="#46253d"/></linearGradient></defs>
  <rect width="850" height="295" rx="20" fill="url(#bg)"/>
  <text x="26" y="39" fill="#ffd3e5" font-family="Verdana, sans-serif" font-size="13" font-weight="bold" letter-spacing="3">YOUR COMMIT RHYTHM</text>
  <text x="26" y="80" fill="#fff4f8" font-family="Verdana, sans-serif" font-size="30" font-weight="bold">{current} <tspan font-size="13" fill="#f5bed4">DAY CURRENT STREAK</tspan></text>
  <text x="355" y="80" fill="#fff4f8" font-family="Verdana, sans-serif" font-size="30" font-weight="bold">{longest} <tspan font-size="13" fill="#f5bed4">DAY BEST STREAK</tspan></text>
  <text x="26" y="117" fill="#cba9bb" font-family="Verdana, sans-serif" font-size="11">{start} — {end} · {sum(counts.values())} PUBLIC COMMITS</text>
  <g>
    {squares}
  </g>
  <text x="26" y="270" fill="#cba9bb" font-family="Verdana, sans-serif" font-size="10">LESS</text>
  <g>{''.join(f'<rect x="{65 + i * 16}" y="259" width="11" height="11" rx="3" fill="{color}"/>' for i, color in enumerate(colors))}</g>
  <text x="153" y="270" fill="#cba9bb" font-family="Verdana, sans-serif" font-size="10">MORE</text>
  <text x="824" y="270" text-anchor="end" fill="#f7b5ce" font-family="Verdana, sans-serif" font-size="10">KEEP THE BEAT ♡</text>
</svg>
'''


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    login = os.environ.get("PROFILE_LOGIN", "lighthouse2815")
    end = dt.datetime.now(dt.timezone.utc).date()
    start = end - dt.timedelta(days=364)
    counts = fetch_commits(login, token, start, end)
    output = Path(__file__).resolve().parent.parent / "assets" / "commit-rhythm.svg"
    output.write_text(render(counts, start, end), encoding="utf-8")


if __name__ == "__main__":
    main()
