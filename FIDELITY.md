# Fidelity record: signal_storm_bench vs the china-unicom signalling-storm submission

Source: GSMA Foundry library task
`china-unicom-henan-and-zte-simulating-signal-storms-and-setting-flow-controls`.
A verbatim per-task `submission.json` is absent for this slug; the grader
contracts below are taken from the judge report and the README, not from a
canonical submission file (see Deviations).

## Sample mapping

| Sample id | What it tests | Grader type | Implementation status |
|---|---|---|---|
| t1 | Characterise the storm: peak NAS registration request rate off live Prometheus counters | Numeric / tolerance | PENDING |
| t2 | Characterise the storm: identify the dominant procedure (registration vs service request) | Exact match | PENDING |
| t3 | Characterise the storm: AMF overload onset (when the core starts shedding) | Numeric / tolerance | PENDING |
| t4 | Characterise the storm: classify the cause (mass re-registration vs DoS vs cell outage recovery) | Exact match | PENDING |
| t5 | Recommend NGAP overload-control parameters against the live peak | Composite | PENDING |
| t6 | Recommend NAS back-off / congestion timers within the normative bounds | Composite | PENDING |
| t7 | Recommend a flow-control setting; negative case where no change is warranted | Exact match | PENDING |
| t8 | Recommend completeness: name the missing control for the seeded omission | Composite | PENDING |
| t9 | Verify: confirm a seeded already-applied flow-control setting holds against the peak | Outcome check | PENDING |
| t10 | Verify: detect a seeded failed/insufficient setting | Outcome check | PENDING |

## Deviations

| Deviation | Reason |
|---|---|
| k8s kustomize (declared stack) -> local docker-compose substrate | single-machine reproducibility, owner directive |
| Open5GS split NFs -> all-in-one container | local compose |
| AMF metrics bind 127.0.0.5 -> 0.0.0.0 | cross-container scrape |
| verbatim per-task submission.json absent for this slug | contracts taken from the judge report + README (provenance) |
