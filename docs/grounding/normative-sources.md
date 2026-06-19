# Normative sources

Local copies of the spec bounds the scorers depend on, so a hermetic reviewer
can verify grounding offline. Each entry has the citation, the exact bound, and
a slot for the verbatim excerpt, which is pasted from the 3GPP corpus before the
scorers ship. All four citations below were confirmed in the judge citation
spot-checks.

## TS 38.413 sec 9.3.1.105: Overload Action (t6)

Bound: the Overload Action IE is an enumeration; the value the suite grades
against is "Permit Emergency Sessions and mobile terminated services only". t6 is
an exact, format-tolerant match against this enumeration.

> [paste verbatim enumeration here]

## TS 38.413 sec 9.3.1.106: Traffic Load Reduction Indication (t7, t9)

Bound: INTEGER, range 1..99 (percent). t7 accepts any integer in 1..99 that
satisfies the live-peak inequality; t9 judges an undersized value against the
live peak.

> [paste verbatim here]

## TS 23.501 sec 5.19.7: NAS-level congestion control (t8)

Bound: the 5GC should select each back-off time value so that the deferred
requests are not synchronized. t8 enforces a non-zero range (range > 0) to
codify this de-synchronisation requirement.

> [paste verbatim here]

## TS 23.501 sec 5.19.5.2: AMF overload control, action d (t5, t6)

Bound: action d permits only 5G-AN signalling connection requests for emergency
sessions and mobile terminated services. Grounds the flow-control mechanism set
and the overload action.

> [paste verbatim here]

## Measurement counters (t1..t4): environment-grounded, not normative

t1..t4 are graded against live counters, not a normative measurement definition.
TS 28.552 sec 5.2 is only weakly related and is NOT vendored. The measurement
basis is the environment metric names:

- `fivegs_amffunction_rm_reginitreq`: cumulative count of UE initial-registration
  requests. The storm signal.
- `fivegs_amffunction_rm_reginitsucc`: successful initial registrations. Lags
  reginitreq under load; the emergent overload signal.

Correct arithmetic uses PromQL `increase(...)` over the storm interval and
`rate(...)` for the peak rate.
