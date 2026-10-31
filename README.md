# LLM serving case studies

Write-ups of problems I found and fixed in open-source LLM serving systems: what was wrong, how I showed it, what changed upstream, and what is still unproven. Each one links the upstream issue and PR and includes whatever code is needed to check the numbers.

| Case study | System | Upstream status |
|---|---|---|
| [Routing on stale latency](aibrix-routing/) | AIBrix (vLLM project) least-latency router | merged: [#3327](https://github.com/vllm-project/aibrix/pull/3327), from issue [#3297](https://github.com/vllm-project/aibrix/issues/3297) |

Related: [llm-bench-wire-audit](https://github.com/dilipna/llm-bench-wire-audit) checks three LLM benchmark tools against the raw stream.

Every number in these write-ups is labelled as a unit test, a model, or a measurement, with its source. Statuses were checked on the date at the top of each case study.
