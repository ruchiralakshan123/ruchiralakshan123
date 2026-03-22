"""
Auto-update script for ruchiralakshan123's GitHub profile README.
Fetches ALL public repos (paginated), builds cards with orange/amber badges,
and rewrites the <!--PROJECTS_START--> ... <!--PROJECTS_END--> block.
"""

import os
import re
import requests
from datetime import datetime

USERNAME = os.environ.get("GITHUB_USERNAME", "ruchiralakshan123")
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# Amber/orange-themed language badges to match profile palette
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
    "user":       "🗃️", "manage":    "🗃️", "inventory": "🛒",
    "sustain":    "🌱", "insight":   "🌱", "news":      "📰",
    "yahtz":      "🎲", "game":      "🎲", "python":    "🐍",
    "api":        "🔌", "auth":      "🔐", "shop":      "🛒",
    "weather":    "☀️", "travel":    "🌍", "chat":      "💬",
    "todo":       "✅", "blog":      "✍️", "test":      "🧪",
    "demo":       "🎬", "lib":       "📚", "book":      "📖",
    "port":       "🌐", "web":       "🌐", "app":       "📱",
}

def get_icon(name: str) -> str:
    lower = name.lower()
    for kw, icon in ICON_MAP.items():
        if kw in lower:
            return icon
    return "🔹"

def fetch_all_repos():
    all_repos = []
    page = 1
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

    if language:
        lang_badge = LANG_BADGES.get(
            language,
            f"![{language}](https://img.shields.io/badge/-{language.replace(' ','_')}-555?style=flat-square)"
        )
    else:
        lang_badge = ""

    stars_badge = (
        f"![Stars](https://img.shields.io/github/stars/{USERNAME}/{name}"
        f"?style=flat-square&color=f97316&labelColor=1a0a00)"
    )

    return f"""<td width="50%">

**{icon} {name}**{fork_label}
> {desc}

{lang_badge} {stars_badge}
<sub>🕒 Updated: {updated}</sub>

[![View](https://img.shields.io/badge/View_Repo-1a0a00?style=for-the-badge&logo=github&logoColor=f97316)]({url})

</td>"""

def build_projects_section(repos) -> str:
    if not repos:
        return (
            "<!--PROJECTS_START-->\n"
            "### `> ls -la /projects`\n\n"
            "*No public repositories yet — check back soon!*\n\n"
            "<!--PROJECTS_END-->"
        )

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
        + '\n</table>\n</div>\n\n'
        + f'<sub align="center">🤖 Auto-updated on {last_updated} &nbsp;·&nbsp; {len(repos)} public repos</sub>'
    )

    return (
        "<!--PROJECTS_START-->\n"
        "<!-- Auto-updated by GitHub Actions — do not edit this block manually -->\n\n"
        + table
        + "\n\n<!--PROJECTS_END-->"
    )

def update_readme(new_section: str):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    updated, n = re.subn(
        r"<!--PROJECTS_START-->.*?<!--PROJECTS_END-->",
        new_section,
        content,
        flags=re.DOTALL,
    )

    if n == 0:
        print("⚠️  Markers not found — appending section.")
        updated = content.rstrip() + "\n\n" + new_section + "\n"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ README updated — {n} section(s) replaced.")

if __name__ == "__main__":
    print(f"🔍 Fetching ALL public repos for @{USERNAME}...")
    repos = fetch_all_repos()
    print(f"📦 Found {len(repos)} repos")
    update_readme(build_projects_section(repos))
    print("🚀 Done!")
