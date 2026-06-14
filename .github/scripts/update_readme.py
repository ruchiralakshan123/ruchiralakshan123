"""
Auto-update script for ruchiralakshan123's GitHub profile README.

Manages two independent auto-updated sections:

  1. <!--ANALYTICS_START--> ... <!--ANALYTICS_END-->
     Refreshes the GitHub Analytics section by cache-busting the four
     original dynamic card image URLs (GitHub Stats, Most Used Languages,
     Streak Stats, Activity Graph). No custom language table is generated —
     the original github-readme-stats "Most Used Languages" card is used.

  2. <!--PROJECTS_START--> ... <!--PROJECTS_END-->
     Controlled by SHOW_PROJECTS flag (currently disabled).

Run:  python update_readme.py
Env:  GITHUB_TOKEN    — recommended for higher API rate limits
      GITHUB_USERNAME — defaults to ruchiralakshan123
"""

import os
import re
from datetime import datetime, timezone

import requests

# ─── Master switches ──────────────────────────────────────────────────────────
SHOW_PROJECTS    = False  # Set True to re-enable the projects grid
UPDATE_ANALYTICS = True   # Set False to freeze the analytics section
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
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

def build_analytics_section():
    """
    Rebuilds the <!--ANALYTICS_START--> block with the four original dynamic
    card images. URLs are cache-busted hourly so GitHub always fetches fresh
    data from the upstream badge services.

    The 'Most Used Languages' card is the original github-readme-stats card —
    no custom language table is generated.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H")  # hourly token

    return (
        "<!--ANALYTICS_START-->\n"
        "<!-- Auto-updated by GitHub Actions — do not edit this block manually -->\n\n"
        "## 📊 GitHub Analytics\n\n"
        '<div align="center">\n'
        f'  <img src="https://github-readme-stats.vercel.app/api?username={USERNAME}'
        f"&show_icons=true&theme=dark&hide_border=true&bg_color=0d0500"
        f"&title_color=f97316&icon_color=fb923c&text_color=fde68a"
        f'&border_radius=10&count_private=true&v={timestamp}" width="48%" alt="GitHub Stats" />\n'
        f'  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}'
        f"&layout=compact&theme=dark&hide_border=true&bg_color=0d0500"
        f'&title_color=f97316&text_color=fde68a&border_radius=10&langs_count=8&v={timestamp}" width="40%" alt="Top Languages" />\n'
        "  <br/><br/>\n"
        f'  <img src="https://streak-stats.demolab.com?user={USERNAME}'
        f"&theme=dark&hide_border=true&background=0d0500&ring=f97316&fire=fb923c"
        f'&currStreakLabel=f97316&sideLabels=d97706&sideNums=fde68a&dates=92400d&v={timestamp}" width="56%" alt="GitHub Streak" />\n'
        "  <br/><br/>\n"
        f'  <img src="https://github-readme-activity-graph.vercel.app/graph?username={USERNAME}'
        f"&bg_color=0d0500&color=f97316&line=ea580c&point=fbbf24&area=true"
        f'&hide_border=true&area_color=2d1500&radius=8&v={timestamp}" width="98%" alt="GitHub Activity Graph" />\n'
        "</div>\n\n"
        "<!--ANALYTICS_END-->"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  PROJECTS HELPERS
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


def fetch_all_repos():
    """Return public repos with EXCLUDED_REPOS filtered out."""
    all_repos = fetch_all_repos_raw()
    filtered  = [r for r in all_repos if r["name"] not in EXCLUDED_REPOS]
    skipped   = [r["name"] for r in all_repos if r["name"] in EXCLUDED_REPOS]
    if skipped:
        print(f"🚫 Excluded from grid: {', '.join(skipped)}")
    return filtered


def get_icon(name: str) -> str:
    lower = name.lower()
    for kw, icon in ICON_MAP.items():
        if kw in lower:
            return icon
    return "🔹"


def format_date(iso: str) -> str:
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return iso[:10]


def build_card(repo) -> str:
    name       = repo.get("name", "")
    desc       = repo.get("description") or "No description provided."
    url        = repo.get("html_url", "")
    language   = repo.get("language") or ""
    updated    = format_date(repo.get("updated_at", ""))
    is_fork    = repo.get("fork", False)
    icon       = get_icon(name)
    fork_label = " *(fork)*" if is_fork else ""
    lang_badge = (
        LANG_BADGES.get(
            language,
            f"![{language}](https://img.shields.io/badge/-{language.replace(' ', '_')}-555?style=flat-square)",
        )
        if language else ""
    )
    stars_badge = (
        f"![Stars](https://img.shields.io/github/stars/{USERNAME}/{name}"
        f"?style=flat-square&color=f97316&labelColor=1a0a00)"
    )
    return (
        f'<td width="50%">\n\n'
        f"**{icon} {name}**{fork_label}\n"
        f"> {desc}\n\n"
        f"{lang_badge} {stars_badge}\n"
        f"<sub>🕒 Updated: {updated}</sub>\n\n"
        f"[![View](https://img.shields.io/badge/View_Repo-1a0a00?style=for-the-badge"
        f"&logo=github&logoColor=f97316)]({url})\n\n"
        f"</td>"
    )


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
        + f'\n</table>\n</div>\n\n'
        f'<sub align="center">🤖 Auto-updated on {last_updated}'
        f" &nbsp;·&nbsp; {len(repos)} public repos</sub>"
    )
    return (
        "<!--PROJECTS_START-->\n"
        "<!-- Auto-updated by GitHub Actions — do not edit this block manually -->\n\n"
        + table
        + "\n\n<!--PROJECTS_END-->"
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
        print("🔄 Refreshing analytics card URLs…")
        replace_block(README, "<!--ANALYTICS_START-->", "<!--ANALYTICS_END-->", build_analytics_section())
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
