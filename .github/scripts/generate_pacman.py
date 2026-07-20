#!/usr/bin/env python3
"""Generate Pac-Man contribution grid animation SVG."""

import json
import math
import os
import sys
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = os.environ.get("GITHUB_REPOSITORY_OWNER", "")

if not TOKEN:
    print("::error::GITHUB_TOKEN environment variable is required")
    sys.exit(1)
if not USERNAME:
    print("::error::GITHUB_REPOSITORY_OWNER environment variable is required")
    sys.exit(1)

query = """
query($user: String!) {
  user(login: $user) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""
payload = json.dumps({"query": query, "variables": {"user": USERNAME}}).encode()
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    },
)
try:
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
except Exception as e:
    print(f"::error::Failed to fetch contribution data: {e}")
    sys.exit(1)

if "errors" in data:
    print(f"::error::GraphQL errors: {json.dumps(data['errors'])}")
    sys.exit(1)

weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

grid = []
for w in weeks:
    for d in w["contributionDays"]:
        c = d["contributionCount"]
        if c == 0:
            grid.append(0)
        elif c <= 3:
            grid.append(1)
        elif c <= 6:
            grid.append(2)
        elif c <= 9:
            grid.append(3)
        else:
            grid.append(4)

while len(grid) % 7 != 0:
    grid.insert(0, 0)

COLS = len(grid) // 7
ROWS = 7

CELL = 15
GAP = 4
PAD = 30
RADIUS = 3
PAC_R = CELL // 2 - 1

W = COLS * (CELL + GAP) - GAP + 2 * PAD
H = ROWS * (CELL + GAP) - GAP + 2 * PAD


def cell_pos(idx):
    row = idx % 7
    col = idx // 7
    x = PAD + col * (CELL + GAP)
    y = PAD + row * (CELL + GAP)
    return x, y


path_points = []
for row in range(ROWS):
    if row % 2 == 0:
        col_range = range(COLS)
    else:
        col_range = range(COLS - 1, -1, -1)
    for col in col_range:
        idx = row + col * 7
        x, y = cell_pos(idx)
        path_points.append((x + CELL / 2, y + CELL / 2))

DURATION = max(len(path_points) * 0.1, 8)
FRAME_TIME = DURATION / len(path_points)


def angle_between(p1, p2):
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))


def generate_svg(dark):
    if dark:
        bg = "#0d1117"
        empty = "#161b22"
        levels = ["#0e4429", "#006d32", "#26a641", "#39d353"]
    else:
        bg = "#ebedf0"
        empty = "#ffffff"
        levels = ["#9be9a8", "#40c463", "#30a14e", "#216e39"]

    pac_color = "#ff0000"
    eye_color = "#ffffff"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
        f' viewBox="0 0 {W} {H}" style="background:{bg}">',
        "<defs>",
        f'<clipPath id="mouthClip">',
        f'<path d="M0,0 L{PAC_R * 1.5},{PAC_R * 1.5} L{PAC_R * 1.5},{-PAC_R * 1.5} Z"/>',
        "</clipPath>",
        "</defs>",
    ]

    for i, level in enumerate(grid):
        x, y = cell_pos(i)
        fill = empty if level == 0 else levels[min(level - 1, 3)]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RADIUS}" fill="{fill}"/>'
        )

    pellet_color = "#ff4444" if dark else "#cc0000"
    for i, level in enumerate(grid):
        if level > 0:
            x, y = cell_pos(i)
            cx = x + CELL / 2
            cy = y + CELL / 2
            parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="{pellet_color}" opacity="0.5"/>'
            )

    mouth_angles = [
        f"M0,-{PAC_R} L{PAC_R * 0.6},{-PAC_R * 0.1} L{PAC_R * 0.6},{PAC_R * 0.1} L0,{PAC_R} Z",
        f"M0,-{PAC_R} L{PAC_R * 0.2},{-PAC_R * 0.02} L{PAC_R * 0.2},{PAC_R * 0.02} L0,{PAC_R} Z",
        f"M0,-{PAC_R} L{PAC_R * 0.6},{-PAC_R * 0.1} L{PAC_R * 0.6},{PAC_R * 0.1} L0,{PAC_R} Z",
    ]

    for idx, (cx, cy) in enumerate(path_points):
        if idx < len(path_points) - 1:
            angle = angle_between(path_points[idx], path_points[idx + 1])
        else:
            angle = 0

        start_time = idx * FRAME_TIME
        end_time = (idx + 1) * FRAME_TIME
        fade = 0.3
        v1 = start_time / DURATION
        v2 = (start_time + fade) / DURATION
        v3 = (end_time - fade) / DURATION
        v4 = end_time / DURATION

        parts.append(
            f'<g transform="translate({cx},{cy}) rotate({angle})">'
        )

        parts.append(
            f'<circle cx="0" cy="0" r="{PAC_R}" fill="{pac_color}">'
            f'<animate attributeName="opacity" values="0;0;1;1;0;0"'
            f' keyTimes="0;{v1};{v1 + 0.001};{v3};{v4};1"'
            f' dur="{DURATION}s" repeatCount="indefinite"/>'
            f'</circle>'
        )

        parts.append(
            f'<path fill="{bg}">'
            f'<animate attributeName="d"'
            f' values="{mouth_angles[0]};{mouth_angles[1]};{mouth_angles[2]};{mouth_angles[1]};{mouth_angles[0]}"'
            f' keyTimes="0;0.25;0.5;0.75;1"'
            f' dur="0.4s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0;1;1;0;0"'
            f' keyTimes="0;{v1};{v1 + 0.001};{v3};{v4};1"'
            f' dur="{DURATION}s" repeatCount="indefinite"/>'
            f'</path>'
        )

        parts.append(
            f'<circle cx="{PAC_R * 0.35}" cy="{-PAC_R * 0.35}" r="1.8" fill="{eye_color}">'
            f'<animate attributeName="opacity" values="0;0;1;1;0;0"'
            f' keyTimes="0;{v1};{v1 + 0.001};{v3};{v4};1"'
            f' dur="{DURATION}s" repeatCount="indefinite"/>'
            f'</circle>'
        )

        parts.append("</g>")

    parts.append("</svg>")
    return "\n".join(parts)


os.makedirs("dist", exist_ok=True)

for dark, suffix in [(True, "-dark"), (False, "")]:
    svg = generate_svg(dark)
    path = f"dist/pacman-contribution-graph{suffix}.svg"
    with open(path, "w") as f:
        f.write(svg)
    print(f"Generated {path}")
