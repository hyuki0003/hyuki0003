#!/usr/bin/env python3
"""Generate assets/stats.svg from the GitHub API — no third-party service."""
import json, os, sys, urllib.request, urllib.error
from collections import defaultdict

USER  = os.environ.get("GH_USER", "hyuki0003")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API   = "https://api.github.com"

def get(path):
    req = urllib.request.Request(API + path,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "stats-card",
                 **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def collect():
    user = get(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = get(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos += batch
        if len(batch) < 100: break
        page += 1
    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    langs = defaultdict(int)
    for r in own:
        if r.get("language"):
            langs[r["language"]] += max(r.get("size", 0), 1)
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    return {
        "name": user.get("name") or USER,
        "repos": len(own),
        "stars": stars,
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "langs": [(n, v * 100.0 / total) for n, v in top],
    }

PALETTE = ["#00ff88", "#00c7b7", "#7ddfc3", "#ffd166", "#ee4c2c"]

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def render(d):
    W, H = 820, 300
    rows = "".join(
        f'<text x="52" y="{112 + i*30}" font-family="\'Courier New\', monospace" font-size="15" fill="#7ddfc3">{esc(l)}</text>'
        f'<text x="250" y="{112 + i*30}" text-anchor="end" font-family="\'Courier New\', monospace" font-size="15" fill="#ffffff">{esc(v)}</text>'
        for i, (l, v) in enumerate([("PUBLIC REPOS", d["repos"]), ("TOTAL STARS", d["stars"]),
                                    ("FOLLOWERS", d["followers"]), ("FOLLOWING", d["following"])]))
    bar, x = "", 0.0
    legend = ""
    BAR_X, BAR_END, GAP = 330.0, 770.0, 2.0
    n = max(len(d["langs"]), 1)
    shown = sum(p for _, p in d["langs"]) or 100.0
    scale = (BAR_END - BAR_X - GAP * (n - 1)) / shown      # never overflows the panel
    for i, (name, pct) in enumerate(d["langs"]):
        w = pct * scale
        bar += f'<rect x="{330 + x:.1f}" y="98" width="{max(w,1):.1f}" height="14" fill="{PALETTE[i%5]}" rx="2"/>'
        legend += (f'<circle cx="340" cy="{144 + i*26}" r="4.5" fill="{PALETTE[i%5]}"/>'
                   f'<text x="356" y="{149 + i*26}" font-family="\'Courier New\', monospace" font-size="14" fill="#7ddfc3">{esc(name)}</text>'
                   f'<text x="770" y="{149 + i*26}" text-anchor="end" font-family="\'Courier New\', monospace" font-size="14" fill="#ffffff">{pct:.1f}%</text>')
        x += w + GAP
    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="sm" width="10" height="10" patternUnits="userSpaceOnUse">
      <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#0c1a14" stroke-width="0.5"/>
    </pattern>
    <pattern id="lg" width="50" height="50" patternUnits="userSpaceOnUse">
      <rect width="50" height="50" fill="url(#sm)"/>
      <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#123020" stroke-width="0.9"/>
    </pattern>
  </defs>
  <rect width="{W}" height="{H}" rx="10" fill="#04070a"/>
  <rect width="{W}" height="{H}" rx="10" fill="url(#lg)"/>
  <rect x="0.7" y="0.7" width="{W-1.4}" height="{H-1.4}" rx="9.3" fill="none" stroke="#123020" stroke-width="1.4"/>

  <text x="52" y="52" font-family="'Courier New', monospace" font-size="16" letter-spacing="4" fill="#00ff88">GITHUB READOUT</text>
  <text x="770" y="52" text-anchor="end" font-family="'Courier New', monospace" font-size="14" letter-spacing="2" fill="#2f6b4d">{esc(d["name"])}</text>
  <line x1="52" y1="68" x2="770" y2="68" stroke="#123020" stroke-width="1.2"/>

  <text x="52" y="90" font-family="'Courier New', monospace" font-size="12" letter-spacing="3" fill="#2f6b4d">SUMMARY</text>
  {rows}

  <text x="330" y="90" font-family="'Courier New', monospace" font-size="12" letter-spacing="3" fill="#2f6b4d">LANGUAGE DISTRIBUTION</text>
  {bar}
  {legend}
</svg>
'''

if __name__ == "__main__":
    try:
        d = collect()
    except urllib.error.HTTPError as e:
        print(f"GitHub API error {e.code}: {e.reason}", file=sys.stderr); sys.exit(1)
    os.makedirs("assets", exist_ok=True)
    open("assets/stats.svg", "w").write(render(d))
    print("wrote assets/stats.svg ->", d)
