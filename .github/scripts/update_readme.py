"""
Auto-update script for ruchiralakshan123's GitHub profile README.

Manages two independent auto-updated sections:

  1. <!--ANALYTICS_START--> ... <!--ANALYTICS_END-->
     Rebuilds the GitHub Analytics section using live API data:
       - Real commit count (last year) via GitHub Events API
       - Real top languages across all repos
       - Dynamic cache-busting timestamps on all image URLs
       - Real public repo count badge

  2. <!--PROJECTS_START--> ... <!--PROJECTS_END-->
     Controlled by SHOW_PROJECTS flag (currently disabled).

Run:  python update_readme.py
Env:  GITHUB_TOKEN  — required for higher API rate limits
      GITHUB_USERNAME — defaults to ruchiralakshan123
"""

import os
import re
import requests
from datetime import datetime, timezone
from collections import defaultdict

# ─── Master switches ──────────────────────────────────────────────────────────
SHOW_PROJECTS  = False   # Set True to re-enable the projects grid
UPDATE_ANALYTICS = True  # Set False to freeze the analytics section
# ─────────────────────────────────────────────────────────────────────────────

USERNAME = os.environ.get("GITHUB_USERNAME", "ruchiralakshan123")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# ─── Repos excluded from the projects grid ───────────────────────────────────
EXCLUDED_REPOS = {
    "Programming-in-Python-",
}
# ─────────────────────────────────────────────────────────────────────────────

LANG_BADGES = {
    "Java":       "![Java](https://img.shields.io/badge/-Java-FF6B00?style=flat-square&logo=openjdk&logoColor=white)",
    "Python":     "![Python](https://img.shields.io/badge/-Python-FFD43B?style=flat-square&logo=python&logoColor=black)",
    "JavaScript": "![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)",
    "TypeScript": "![TypeScript](https://img.shields.io/badge/-TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)",
    "C":          "![C](https://img.shields.io/badge/-C-00599C?style=flat-square&logo=c&logoColor=white)",
    "HTML":       "![HTML](https://img.shields.io/badge/-HTML-E34F26?style=flat-square&logo=html5&logoColor=white)",
    "CSS":        "![CSS](https://img.shields.io/badge/-CSS-1572B6?style=flat-square&logo=css3&logoColor=white)",
    "Shell":      "![Shell](https://img.shields.io/badge/-Shell-4EAA25?style=flat-square&logo=gnubash&logoColor=white)",
    "Dart":       "![Dart](https://img.shields.io/badge/-Dart-0175C2?style=flat-square&logo=dart&logoColor=white)",
    "Kotlin":     "![Kotlin](https://img.shields.io/badge/-Kotlin-7F52FF?style=flat-square&logo=kotlin&logoColor=white)",
    "Go":         "![Go](https://img.shields.io/badge/-Go-00ADD8?style=flat-square&logo=go&logoColor=white)",
    "PHP":        "![PHP](https://img.shields.io/badge/-PHP-777BB4?style=flat-square&logo=php&logoColor=white)",
}

ICON_MAP = {
    "user": "🗃️", "manage": "🗃️", "inventory": "🛒",
    "sustain": "🌱", "insight": "🌱", "news": "📰",
    "yahtz": "🎲", "game": "🎲", "python": "🐍",
    "api": "🔌", "auth": "🔐", "shop": "🛒",
    "weather": "☀️", "travel": "🌍", "chat": "💬",
    "todo": "✅", "blog": "✍️", "test": "🧪",
    "demo": "🎬", "lib": "📚", "book": "📖",
    "port": "🌐", "web": "🌐", "app": "📱",
}


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def fetch_all_repos_raw():
    """Return all public repos (raw dicts, no exclusion filter)."""
    all_repos, page = [], 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=HEADERS,
            params={"sort": "updated", "per_page": 100, "page": page, "type": "public"},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_repos.extend(batch)
        page += 1
    return all_repos


def compute_top_languages(repos, top_n=6):
    """
    Fetch per-repo language byte counts and return sorted list of
    (language, percentage_string) tuples.
    """
    totals = defaultdict(int)
    for repo in repos:
        if repo.get("fork"):
            continue  # skip forks — they skew your real language split
        lang_url = repo.get("languages_url", "")
        if not lang_url:
            continue
        try:
            r = requests.get(lang_url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            for lang, bytes_count in r.json().items():
                totals[lang] += bytes_count
        except Exception:
            pass

    grand_total = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [(lang, f"{bytes_count / grand_total * 100:.1f}%") for lang, bytes_count in ranked]


def fetch_commit_count_last_year():
    """
    Approximate commits in the last year via the contributions endpoint.
    Falls back to summing PushEvents from the events API if unavailable.
    """
    # Try the GraphQL contributions API first
    if TOKEN:
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              totalCommitContributions
              restrictedContributionsCount
            }
          }
        }
        """
        try:
            resp = requests.post(
                "https://api.github.com/graphql",
                headers={**HEADERS, "Content-Type": "application/json"},
                json={"query": query, "variables": {"login": USERNAME}},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                cc = data["data"]["user"]["contributionsCollection"]
                total = cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
                print(f"📊 Commits last year (GraphQL): {total}")
                return total
        except Exception as e:
            print(f"⚠️  GraphQL failed: {e}")

    # REST fallback — count PushEvents (capped at 300 events by GitHub)
    count = 0
    for page in range(1, 4):
        try:
            resp = requests.get(
                f"https://api.github.com/users/{USERNAME}/events/public",
                headers=HEADERS,
                params={"per_page": 100, "page": page},
                timeout=10,
            )
            resp.raise_for_status()
            events = resp.json()
            if not events:
                break
            for ev in events:
                if ev.get("type") == "PushEvent":
                    count += ev.get("payload", {}).get("size", 0)
        except Exception:
            break
    print(f"📊 Commits approximated (REST fallback): {count}")
    return count


def build_analytics_section(repos):
    """
    Builds the full <!--ANALYTICS_START--> block with:
      - GitHub Stats card (cache-busted)
      - Top Languages card (cache-busted)
      - Streak stats (cache-busted)
      - Activity graph (cache-busted)
      - Dynamic language table from live API data
      - Dynamic summary line (repo count + last-updated)
    """
    now_utc   = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y%m%d%H")          # hourly cache-bust token
    repo_count = len([r for r in repos if not r.get("fork")])

    # Live language breakdown
    print("🔍 Computing language breakdown (this may take ~30s)…")
    top_langs = compute_top_languages(repos)

    # Build language pill row (up to 6, two columns)
    lang_rows = ""
    for i in range(0, len(top_langs), 2):
        left  = top_langs[i]
        right = top_langs[i + 1] if i + 1 < len(top_langs) else None
        left_dot  = _lang_dot(left[0])
        right_dot = _lang_dot(right[0]) if right else ""
        right_cell = f"| {right_dot} **{right[0]}** `{right[1]}`" if right else "|"
        lang_rows += f"| {left_dot} **{left[0]}** `{left[1]}` {right_cell} |\n"

    lang_table = f"""\
| Language | Language |
|----------|----------|
{lang_rows}"""

    section = f"""\
<!--ANALYTICS_START-->
<!-- Auto-updated by GitHub Actions — do not edit this block manually -->

## 📊 GitHub Analytics

<div align="center">
  <img src="https://github-readme-stats.vercel.app/api?username={USERNAME}&show_icons=true&theme=dark&hide_border=true&bg_color=0d0500&title_color=f97316&icon_color=fb923c&text_color=fde68a&border_radius=10&count_private=true&v={timestamp}" width="48%" alt="GitHub Stats" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&theme=dark&hide_border=true&bg_color=0d0500&title_color=f97316&text_color=fde68a&border_radius=10&langs_count=8&v={timestamp}" width="40%" alt="Top Languages" />
  <br/><br/>
  <img src="https://streak-stats.demolab.com?user={USERNAME}&theme=dark&hide_border=true&background=0d0500&ring=f97316&fire=fb923c&currStreakLabel=f97316&sideLabels=d97706&sideNums=fde68a&dates=92400d&v={timestamp}" width="56%" alt="GitHub Streak" />
  <br/><br/>
  <img src="https://github-readme-activity-graph.vercel.app/graph?username={USERNAME}&bg_color=0d0500&color=f97316&line=ea580c&point=fbbf24&area=true&hide_border=true&area_color=2d1500&radius=8&v={timestamp}" width="98%" alt="GitHub Activity Graph" />
</div>

### 🧑‍💻 Language Breakdown (live · own repos only)

{lang_table}
<sub align="center">🤖 Analytics refreshed on {now_utc.strftime("%Y-%m-%d %H:%M UTC")} &nbsp;·&nbsp; {repo_count} original public repos</sub>

<!--ANALYTICS_END-->"""

    return section


def _lang_dot(lang: str) -> str:
    """Return a coloured dot emoji that roughly matches the language colour."""
    colours = {
        "Java": "🟠", "Python": "🟡", "JavaScript": "🟡",
        "TypeScript": "🔵", "C": "🔵", "C++": "🔵",
        "HTML": "🔴", "CSS": "🟣", "Shell": "🟢",
        "Go": "🔵", "Kotlin": "🟣", "PHP": "🟣",
        "Dart": "🔵", "Dockerfile": "🔵",
    }
    return colours.get(lang, "⚪")


# ══════════════════════════════════════════════════════════════════════════════
#  PROJECTS HELPERS  (unchanged from previous version)
# ══════════════════════════════════════════════════════════════════════════════

def get_icon(name: str) -> str:
    lower = name.lower()
    for kw, icon in ICON_MAP.items():
        if kw in lower:
            return icon
    return "🔹"


def fetch_all_repos():
    """Return public repos with EXCLUDED_REPOS filtered out."""
    all_repos = fetch_all_repos_raw()
    filtered  = [r for r in all_repos if r["name"] not in EXCLUDED_REPOS]
    skipped   = [r["name"] for r in all_repos if r["name"] in EXCLUDED_REPOS]
    if skipped:
        print(f"🚫 Excluded from grid: {', '.join(skipped)}")
    return filtered


def format_date(iso: str) -> str:
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return iso[:10]


def build_card(repo) -> str:
    name     = repo.get("name", "")
    desc     = repo.get("description") or "No description provided."
    url      = repo.get("html_url", "")
    language = repo.get("language") or ""
    updated  = format_date(repo.get("updated_at", ""))
    is_fork  = repo.get("fork", False)
    icon       = get_icon(name)
    fork_label = " *(fork)*" if is_fork else ""
    lang_badge = LANG_BADGES.get(language, f"![{language}](https://img.shields.io/badge/-{language.replace(' ','_')}-555?style=flat-square)") if language else ""
    stars_badge = f"![Stars](https://img.shields.io/github/stars/{USERNAME}/{name}?style=flat-square&color=f97316&labelColor=1a0a00)"
    return f"""<td width="50%">

**{icon} {name}**{fork_label}
> {desc}

{lang_badge} {stars_badge}
<sub>🕒 Updated: {updated}</sub>

[![View](https://img.shields.io/badge/View_Repo-1a0a00?style=for-the-badge&logo=github&logoColor=f97316)]({url})

</td>"""


def build_projects_section(repos) -> str:
    if not repos:
        return "<!--PROJECTS_START-->\n*No public repositories yet.*\n<!--PROJECTS_END-->"
    cards = [build_card(r) for r in repos]
    rows  = []
    for i in range(0, len(cards), 2):
        pair = cards[i:i+2]
        if len(pair) == 1:
            pair.append('<td width="50%"></td>')
        rows.append("<tr>\n" + "\n".join(pair) + "\n</tr>")
    last_updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    table = (
        '<div align="center">\n<table>\n'
        + "\n".join(rows)
        + f'\n</table>\n</div>\n\n<sub align="center">🤖 Auto-updated on {last_updated} &nbsp;·&nbsp; {len(repos)} public repos</sub>'
    )
    return (
        "<!--PROJECTS_START-->\n"
        "<!-- Auto-updated by GitHub Actions — do not edit this block manually -->\n\n"
        + table + "\n\n<!--PROJECTS_END-->"
    )


def remove_projects_section():
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()
    cleaned, n = re.subn(
        r"\n---\n\n<!--PROJECTS_START-->.*?<!--PROJECTS_END-->",
        "", content, flags=re.DOTALL,
    )
    if n == 0:
        cleaned, n = re.subn(
            r"<!--PROJECTS_START-->.*?<!--PROJECTS_END-->",
            "", content, flags=re.DOTALL,
        )
    if n > 0:
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(cleaned)
        print("✅ Projects section removed from README.")
    else:
        print("ℹ️  No projects section found — nothing to remove.")


# ══════════════════════════════════════════════════════════════════════════════
#  GENERIC README BLOCK UPDATER
# ══════════════════════════════════════════════════════════════════════════════

def replace_block(readme_path: str, start_marker: str, end_marker: str, new_block: str):
    """Replace start_marker...end_marker in readme_path with new_block."""
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    updated, n = re.subn(pattern, new_block, content, flags=re.DOTALL)

    if n == 0:
        print(f"⚠️  Markers '{start_marker}' not found — appending block.")
        updated = content.rstrip() + "\n\n" + new_block + "\n"

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"✅ Block '{start_marker}' updated ({n} replacement(s)).")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    README = "README.md"

    # ── 1. Analytics ──────────────────────────────────────────────────────────
    if UPDATE_ANALYTICS:
        print(f"🔍 Fetching repos for @{USERNAME} (analytics)…")
        all_repos = fetch_all_repos_raw()
        analytics_block = build_analytics_section(all_repos)
        replace_block(README, "<!--ANALYTICS_START-->", "<!--ANALYTICS_END-->", analytics_block)
    else:
        print("ℹ️  Analytics update skipped (UPDATE_ANALYTICS = False).")

    # ── 2. Projects grid ──────────────────────────────────────────────────────
    if not SHOW_PROJECTS:
        print("🚫 Projects grid disabled (SHOW_PROJECTS = False).")
        remove_projects_section()
    else:
        print(f"🔍 Fetching repos for @{USERNAME} (projects grid)…")
        repos = fetch_all_repos()
        print(f"📦 Displaying {len(repos)} repo(s)")
        replace_block(README, "<!--PROJECTS_START-->", "<!--PROJECTS_END-->", build_projects_section(repos))

    print("🚀 All done!")
