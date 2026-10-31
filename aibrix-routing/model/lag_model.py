"""Model of AIBrix least-latency scoring after a pod slows down.

This is NOT a cluster measurement. It replays the rules of the merged code
(vllm-project/aibrix 48cf8309ad, pkg/cache/recent_mean.go and utils.go) on a
synthetic arrival stream, to check the lag table in PR #3327 and to produce a
score timeline for the case study.

Rules modelled, from the merged code:
- the gateway scrapes every 5 s; a snapshot is kept when >= 5 s after the last
  one, at most 36 snapshots / 3 minutes (appendSnapshot1m, cleanupOldSnapshots)
- base = snapshot closest to now - 60 s, excluding the newest (baseSnapshot1m)
- no recent mean if < 10 s since base or < 5 observations in the window
  (calculateMean1m); readers then use the lifetime mean (RecentHistogramMean)
- the lifetime mean is Sum / Count of the cumulative histogram (GetMean)

Scenario, matching the PR table: 50 req/s; p1's queue time is 0.05 s for its
first N requests, then 2 s; p2 queues 0.5 s. Prefill and decode are equal on
both pods, so the router picks the pod with the lower queue-time score.
Assumption: the gateway has scraped p1 for at least 3 minutes before the
slowdown (full snapshot history). See young_pod() for when it has not.

Usage: python lag_model.py   (stdlib only)
"""

import json
import sys

RATE = 50.0  # requests per second
FAST, SLOW, OTHER = 0.05, 2.0, 0.5
SCRAPE = 5.0  # scrape cadence assumed by the PR table
SNAPSHOT = 5.0  # window1mSnapshotInterval: snapshot throttle, independent of the scrape cadence
TARGET, MAX_AGE, MAX_COUNT, MIN_ELAPSED, MIN_SAMPLES = 60.0, 180.0, 36, 10.0, 5


def cumulative(t, n_before, young):
    """(sum, count) of p1's queue-time histogram at time t (slowdown at t=0).

    Full-history mode keeps 50 req/s of fast traffic before t=0 and only fixes
    the lifetime count at t=0 to n_before; counts before t=0 are used only as
    differences. Young mode starts the pod at its first request (count 0).
    """
    if t <= 0:
        count = n_before + RATE * t
        if young:
            count = max(count, 0.0)
        return FAST * count, count
    slow = RATE * t
    return FAST * n_before + SLOW * slow, n_before + slow


def run(n_before, horizon, history_start=-MAX_AGE - SNAPSHOT, young=False, scrape=SCRAPE):
    """Yield (t, lifetime_mean, recent_mean_or_None, score_used) at each scrape."""
    history = []
    i = 0
    while True:
        t = round(history_start + i * scrape, 6)
        i += 1
        if t > horizon:
            break
        s, c = cumulative(t, n_before, young)
        if not history or t - history[-1][0] >= SNAPSHOT - 1e-9:
            history.append((t, s, c))
        history = [h for h in history if h[0] > t - MAX_AGE][-MAX_COUNT:]
        recent = None
        if len(history) >= 2:
            candidates = history[:-1]
            base = min(candidates, key=lambda h: abs(h[0] - (t - TARGET)))
            ds, dc = s - base[1], c - base[2]
            if t - base[0] >= MIN_ELAPSED and dc >= MIN_SAMPLES:
                recent = ds / dc
        lifetime = s / c if c > 0 else None
        if t > 0 or (lifetime is not None and t > -TARGET):
            yield t, lifetime, recent, (recent if recent is not None else lifetime)


def lag(n_before, use_recent, scrape=SCRAPE):
    """Seconds after the slowdown until p1 scores worse than p2 (0.5 s)."""
    start = round(-MAX_AGE - SNAPSHOT, 6)
    for t, lifetime, recent, used in run(n_before, horizon=0.01 * n_before + 120,
                                         history_start=start, scrape=scrape):
        if t <= 0:
            continue
        score = used if use_recent else lifetime
        if score > OTHER:
            return t
    return None


def young_pod(n_before):
    """Recent-mean lag when the gateway has only seen p1 since its first request."""
    start = -n_before / RATE
    for t, lifetime, recent, used in run(n_before, horizon=600, history_start=start, young=True):
        if t > 0 and used > OTHER:
            return t
    return None


def main():
    pr_table = {1_000: (10, 15), 10_000: (65, 15), 100_000: (605, 15), 1_000_000: (6005, 15)}
    rows, ok = [], True
    for n, (pr_main, pr_fix) in pr_table.items():
        main_lag, fix_lag = lag(n, use_recent=False), lag(n, use_recent=True)
        match = (main_lag, fix_lag) == (pr_main, pr_fix)
        ok &= match
        rows.append({"n_before": n, "lifetime_lag_s": main_lag, "recent_lag_s": fix_lag,
                     "pr_table": [pr_main, pr_fix], "matches_pr": match,
                     "recent_lag_if_young_pod_s": young_pod(n)})
    # The scrape loop defaults to 1 s (AIBRIX_POD_METRIC_REFRESH_INTERVAL_MS=1000) and the
    # shipped manifests set 50 ms; snapshots stay throttled to 5 s either way.
    cadences = {}
    for scrape in (1.0, 0.05):
        cadences[str(scrape)] = [{"n_before": n, "lifetime_lag_s": lag(n, False, scrape),
                                  "recent_lag_s": lag(n, True, scrape)} for n in pr_table]
    timeline = [{"t": t, "lifetime": round(lt, 4), "recent": None if r is None else round(r, 4)}
                for t, lt, r, _ in run(100_000, horizon=700) if t >= -60]
    json.dump({"lag_table": rows, "lag_by_scrape_interval_s": cadences, "timeline_n_100000": timeline}, open("lag_model.json", "w"), indent=1)
    for r in rows:
        print(r)
    for k, v in cadences.items():
        print(f"scrape every {k} s:", [(r["n_before"], r["lifetime_lag_s"], r["recent_lag_s"]) for r in v])
    print("ALL MATCH PR #3327 TABLE" if ok else "MISMATCH WITH PR #3327 TABLE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
