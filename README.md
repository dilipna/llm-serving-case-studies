# LLM serving case studies

Write-ups of problems I found in open-source LLM serving systems and the tools used to measure them: what was wrong, how I showed it, what changed upstream, and what is still unproven. Each one links the upstream issue and PR and includes whatever code is needed to check the numbers.

| Case study | System | Upstream status |
|---|---|---|
| [Routing on stale latency](aibrix-routing/) | AIBrix (vLLM project) least-latency router | merged: [#3327](https://github.com/vllm-project/aibrix/pull/3327), from issue [#3297](https://github.com/vllm-project/aibrix/issues/3297) |
| [Same name, different number](benchmark-audit/) | `vllm bench serve`, GuideLLM and AIPerf checked against the raw stream | measurement study; code and raw logs in [llm-bench-wire-audit](https://github.com/dilipna/llm-bench-wire-audit) |

Every number in these write-ups is labelled as a unit test, a model, or a measurement, with its source. Statuses were checked on the date at the top of each case study.
