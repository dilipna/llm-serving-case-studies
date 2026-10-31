"""Draw timeline.svg from lag_model.json (run lag_model.py first). Stdlib only."""

import json

data = json.load(open("lag_model.json"))["timeline_n_100000"]

W, H = 760, 380
L, R, T, B = 64, 150, 92, 52  # plot margins
X0, X1, Y0, Y1 = -60, 700, 0.0, 2.1


def x(v):
    return L + (v - X0) / (X1 - X0) * (W - L - R)


def y(v):
    return H - B - (v - Y0) / (Y1 - Y0) * (H - T - B)


def path(key):
    pts = [(p["t"], p[key]) for p in data if p[key] is not None]
    return "M" + " L".join(f"{x(t):.1f},{y(v):.1f}" for t, v in pts)


style = """
  .surface{fill:#fcfcfb} .ink{fill:#0b0b0b} .ink2{fill:#52514e} .muted{fill:#898781}
  .grid{stroke:#e1e0d9} .axis{stroke:#898781} .ref{stroke:#898781}
  .s1{stroke:#2a78d6} .s2{stroke:#eb6834} .f1{fill:#2a78d6} .f2{fill:#eb6834} .ring{stroke:#fcfcfb}
  @media (prefers-color-scheme: dark){
    .surface{fill:#1a1a19} .ink{fill:#f0efec} .ink2{fill:#c3c2b7}
    .grid{stroke:#2c2c2a} .s1{stroke:#3987e5} .s2{stroke:#d95926}
    .f1{fill:#3987e5} .f2{fill:#d95926} .ring{stroke:#1a1a19}
  }
  text{font-family:system-ui,-apple-system,'Segoe UI',sans-serif}
"""

out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
       'aria-labelledby="t d">',
       '<title id="t">Queue-time score of a pod after it slows down</title>',
       '<desc id="d">Model of AIBrix scoring, 100,000 prior requests. The lifetime mean '
       'crosses the other pod\'s 0.5 s at 605 s; the 1-minute mean crosses it at 15 s.</desc>',
       f"<style>{style}</style>",
       f'<rect class="surface" width="{W}" height="{H}"/>',
       f'<text class="ink" x="{L}" y="24" font-size="16" font-weight="600">'
       'How long a slowed pod keeps winning the route</text>',
       f'<text class="ink2" x="{L}" y="43" font-size="12">Queue-time score after the pod slows '
       'from 0.05 s to 2 s at t = 0, after serving 100,000 requests.</text>',
       f'<text class="ink2" x="{L}" y="59" font-size="12">Model of the merged scoring rules with 5 s scrapes, '
       'not a cluster measurement.</text>']

for v in (0, 0.5, 1.0, 1.5, 2.0):
    out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke-width="1"/>')
    out.append(f'<text class="muted" x="{L - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end">{v:g} s</text>')
for v in (0, 100, 200, 300, 400, 500, 600, 700):
    out.append(f'<text class="muted" x="{x(v):.1f}" y="{H - B + 18}" font-size="11" text-anchor="middle">{v}</text>')
out.append(f'<line class="axis" x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke-width="1"/>')
out.append(f'<text class="ink2" x="{(L + W - R) / 2:.0f}" y="{H - 12}" font-size="12" '
           'text-anchor="middle">seconds since the slowdown</text>')

# the other pod's score: the threshold the slowed pod must cross to stop winning
out.append(f'<line class="ref" x1="{L}" x2="{W - R}" y1="{y(0.5):.1f}" y2="{y(0.5):.1f}" '
           'stroke-width="1.5" stroke-dasharray="5 4"/>')
out.append(f'<text class="ink2" x="{W - R + 8}" y="{y(0.5) + 18:.1f}" font-size="12">other pod, 0.5 s</text>')

out.append(f'<path class="s1" d="{path("lifetime")}" fill="none" stroke-width="2" stroke-linejoin="round"/>')
out.append(f'<path class="s2" d="{path("recent")}" fill="none" stroke-width="2" stroke-linejoin="round"/>')

# crossing markers, read from the data (first scrape above 0.5 s)
for key, cls in (("lifetime", "f1"), ("recent", "f2")):
    hit = next(p for p in data if p["t"] > 0 and p[key] is not None and p[key] > 0.5)
    cx, cy = x(hit["t"]), y(hit[key])
    out.append(f'<circle class="{cls} ring" cx="{cx:.1f}" cy="{cy:.1f}" r="5" stroke-width="2"/>')
    dy = -12 if key == "lifetime" else -10
    anchor = "end" if key == "lifetime" else "start"
    dx = -8 if key == "lifetime" else 8
    out.append(f'<text class="ink" x="{cx + dx:.1f}" y="{cy + dy:.1f}" font-size="12" '
               f'text-anchor="{anchor}">switches at {hit["t"]:g} s</text>')

# direct labels at the line ends
last = data[-1]
out.append(f'<text class="ink" x="{W - R + 8}" y="{y(last["recent"]) + 4:.1f}" font-size="12">1-minute mean (merged)</text>')
out.append(f'<text class="ink" x="{W - R + 8}" y="{y(last["lifetime"]) - 8:.1f}" font-size="12">lifetime mean (before)</text>')

# legend (identity never by color alone)
lx = L
for label, cls in (("lifetime mean (before)", "s1"), ("1-minute mean (merged)", "s2")):
    out.append(f'<line class="{cls}" x1="{lx}" x2="{lx + 18}" y1="{T - 18}" y2="{T - 18}" stroke-width="2"/>')
    out.append(f'<text class="ink2" x="{lx + 24}" y="{T - 14}" font-size="12">{label}</text>')
    lx += 190

out.append("</svg>")
open("../timeline.svg", "w", encoding="utf-8").write("\n".join(out))
print("wrote ../timeline.svg")
