"""Draw stall_gaps.svg: one request's inter-token gaps under the injected 300 ms stall.

    python make_chart.py <llm-bench-wire-audit>/results/stall/gl_1.jsonl

Reads the wire proxy's log, picks the request whose average gap is the median of the
run (a typical request, not the worst), and draws its 63 gaps with the request's
average gap as a reference line. Stdlib only.
"""

import json
import statistics
import sys

GENERATION_PATHS = ("/v1/completions", "/v1/chat/completions")
TEXT_EVENT = 1  # wire_proxy.py event kind for a token event with visible text

records = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
requests = []
for r in records:
    if r["path"].split("?")[0] not in GENERATION_PATHS or r["status"] != 200:
        continue
    times = [e[0] for e in r["events"] if e[2] == TEXT_EVENT]
    gaps = [(b - a) * 1000 for a, b in zip(times, times[1:])]
    requests.append({"req": r["req"], "gaps": gaps, "mean": statistics.fmean(gaps)})

requests.sort(key=lambda r: r["mean"])
pick = requests[len(requests) // 2]
gaps, mean = pick["gaps"], pick["mean"]
stall_i = max(range(len(gaps)), key=gaps.__getitem__)
before = statistics.median(gaps[:stall_i])
json.dump({"source": sys.argv[1].replace("\\", "/").split("results/")[-1], "req": pick["req"],
           "gaps_ms": [round(g, 3) for g in gaps], "mean_ms": round(mean, 3),
           "median_gap_before_stall_ms": round(before, 3), "stall_gap_index": stall_i},
          open("stall_gaps.json", "w"), indent=1)

W, H = 760, 400
L, R, T, B = 64, 24, 96, 52
Y1 = 350.0
n = len(gaps)
step = (W - L - R) / n
bar = step - 2  # 2px surface gap between adjacent bars


def x(i):
    return L + i * step + 1


def y(v):
    return H - B - v / Y1 * (H - T - B)


style = """
  .surface{fill:#fcfcfb} .ink{fill:#0b0b0b} .ink2{fill:#52514e} .muted{fill:#898781}
  .grid{stroke:#e1e0d9} .axis{stroke:#898781} .ref{stroke:#52514e} .f1{fill:#2a78d6}
  @media (prefers-color-scheme: dark){
    .surface{fill:#1a1a19} .ink{fill:#f0efec} .ink2{fill:#c3c2b7}
    .grid{stroke:#2c2c2a} .ref{stroke:#c3c2b7} .f1{fill:#3987e5}
  }
  text{font-family:system-ui,-apple-system,'Segoe UI',sans-serif}
"""

out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
       'aria-labelledby="t d">',
       '<title id="t">Inter-token gaps of one streamed request under a 300 ms stall</title>',
       f'<desc id="d">63 gaps between streamed tokens. Before the stall they are about {before:.0f} ms; '
       f'gap {stall_i + 1} is {gaps[stall_i]:.0f} ms; the tokens held during the stall then arrive '
       f'almost at once. The request\'s average gap is {mean:.1f} ms.</desc>',
       f"<style>{style}</style>",
       f'<rect class="surface" width="{W}" height="{H}"/>',
       f'<text class="ink" x="{L}" y="24" font-size="16" font-weight="600">'
       'A 300 ms freeze, seen gap by gap and as one average</text>',
       f'<text class="ink2" x="{L}" y="43" font-size="12">Gaps between streamed tokens for one typical '
       'request, measured at the proxy. The proxy froze every stream</text>',
       f'<text class="ink2" x="{L}" y="59" font-size="12">for 300 ms before token 20. Qwen3-0.6B on vLLM, '
       'GuideLLM run 1, 8 requests in flight.</text>']

for v in (0, 100, 200, 300):
    out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke-width="1"/>')
    out.append(f'<text class="muted" x="{L - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end">{v} ms</text>')
for i in (0, 9, 19, 29, 39, 49, 59):
    out.append(f'<text class="muted" x="{x(i) + bar / 2:.1f}" y="{H - B + 18}" font-size="11" '
               f'text-anchor="middle">{i + 1}</text>')
out.append(f'<text class="ink2" x="{(L + W - R) / 2:.0f}" y="{H - 12}" font-size="12" '
           'text-anchor="middle">gap number (gap 1 is between tokens 1 and 2)</text>')

for i, g in enumerate(gaps):
    h = max(y(0) - y(g), 1.0)
    r = min(4.0, bar / 2, h / 2)  # rounded data end, flat at the baseline
    x0, x1, top, base = x(i), x(i) + bar, y(0) - h, y(0)
    d = (f"M{x0:.1f},{base:.1f} L{x0:.1f},{top + r:.1f} Q{x0:.1f},{top:.1f} {x0 + r:.1f},{top:.1f} "
         f"L{x1 - r:.1f},{top:.1f} Q{x1:.1f},{top:.1f} {x1:.1f},{top + r:.1f} L{x1:.1f},{base:.1f} Z")
    out.append(f'<path class="f1" d="{d}"><title>gap {i + 1}: {g:.1f} ms</title></path>')
out.append(f'<line class="axis" x1="{L}" x2="{W - R}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke-width="1"/>')

# the request's average gap: what a per-request ITL percentile is computed from
out.append(f'<line class="ref" x1="{L}" x2="{W - R}" y1="{y(mean):.1f}" y2="{y(mean):.1f}" '
           'stroke-width="1.5" stroke-dasharray="5 4"/>')
lx = x(stall_i) + bar + 14
out.append(f'<text class="ink" x="{lx:.1f}" y="{y(mean) - 30:.1f}" font-size="12">'
           f'average gap for this request: {mean:.1f} ms</text>')
out.append(f'<text class="ink2" x="{lx:.1f}" y="{y(mean) - 14:.1f}" font-size="12">'
           'what a per-request ITL percentile is built from</text>')

sx = x(stall_i) + bar + 8
out.append(f'<text class="ink" x="{sx:.1f}" y="{y(gaps[stall_i]) + 12:.1f}" font-size="12">'
           f'gap {stall_i + 1}: {gaps[stall_i]:.0f} ms, the freeze the user sees</text>')
out.append(f'<text class="ink2" x="{sx:.1f}" y="{y(gaps[stall_i]) + 28:.1f}" font-size="12">'
           'a raw-gap ITL percentile keeps this</text>')

out.append("</svg>")
open("../stall_gaps.svg", "w", encoding="utf-8").write("\n".join(out))
print(f"wrote ../stall_gaps.svg: req {pick['req']}, {n} gaps, stall gap {stall_i + 1} = {gaps[stall_i]:.1f} ms, "
      f"median before = {before:.1f} ms, request mean = {mean:.2f} ms")
