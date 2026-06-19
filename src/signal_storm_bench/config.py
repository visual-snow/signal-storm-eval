"""The single source of truth for the signal_storm eval.

Read this file top to bottom and you know the whole eval: the storm we inject,
how we measure it, what counts as a storm, the normative bounds, and the hidden
answer key the scorer grades against. Every other module imports its constants
from here; nothing is duplicated.

Two halves, split by a loud banner:

  1. PROMPT-SAFE  - the world's shape and the things the model is allowed to see.
                    dataset.py (the prompts) and scorers.py both import these.
  2. ANSWER KEY   - the correct answers. scorers.py imports these to grade.
                    A prompt must NEVER import them (tests/test_dataset.py guards
                    this); leaking an answer into a prompt breaks the eval.

Nothing here imports anything; it is plain data, on purpose.
"""

# ===========================================================================
#  PROMPT-SAFE  -  the world's shape; safe for both prompts and the scorer
# ===========================================================================

# The storm we inject. These mirror topology/compose.yaml (the packetrusher
# service reads them from its env at runtime, so compose.yaml is the real
# authority); this is the Python view the solver and the agent-facing tool use.
# The offered rate sits well above the cpu-capped AMF's throughput, so the storm
# leaves a permanent reginitreq > reginitsucc deficit.
STORM_RATE = 120  # registration attempts per second
STORM_UE_COUNT = 6000  # number of UEs the injector registers
STORM_DURATION_S = 90  # how long the storm runs

# How the scorer reads the storm back off Prometheus. The outer window spans the
# whole storm for increase(...)/peak reads; the inner window is the rate()
# sub-window for the peak/capacity reads; the step matches the scrape interval so
# the short throughput peak is not missed.
STORM_INTERVAL = "5m"
PEAK_WINDOW = "30s"
SCRAPE_INTERVAL_S = 5

# The two AMF counters the entire eval is measured against (exposed by the AMF
# metrics server; see topology/config/amf.yaml).
REGINITREQ = "fivegs_amffunction_rm_reginitreq"  # registration attempts
REGINITSUCC = "fivegs_amffunction_rm_reginitsucc"  # registration successes

# Load bands, in registrations per second. Below the idle threshold is normal
# load (t10's baseline must read here); at or above the storm floor is a real
# overload (t4 must read here, and the world-setup gate replays the storm until
# it does, so t7/t8/t9 always have valid ground truth). A healthy storm drives
# ~106-115 reg/s; the gap between 1 and 50 cleanly separates the two states.
IDLE_PEAK_THRESHOLD = 1.0
MIN_STORM_PEAK_RATE = 50.0

# Normative bound: a TS 38.413 Traffic Load Reduction is an integer percent in
# 1..99. Used to range-check the model's proposed and the planted TLR.
TLR_MIN = 1
TLR_MAX = 99

# The undersized Traffic Load Reduction we plant in t9. Small enough that the
# residual rate (peak after the cut) still exceeds capacity, so the only correct
# verdict is that it fails to hold the load.
GIVEN_TLR = 10

# The four investigation tasks, in operator-loop order: measure the storm (i1),
# diagnose the load state (i2, run in both the storm and baseline worlds), select
# the flow-control mechanism + overload action (i3), size the NAS back-off (i4).
# The culminating apply-and-verify TLR task (P1) is built in a separate plan.
KINDS = ("i1", "i2", "i3", "i4")

# i2 runs as two samples from one identity: a storm world (correct verdict:
# overloaded) and a baseline world (correct verdict: normal). The agent does not
# know which world it is in; it must read the live state.
I2_WORLDS = ("storm", "baseline")

# i3 candidate mechanisms shown to the model, published neutrally. Which are the
# genuine overload-control mechanisms and which are distractors is the hidden part
# (the ANSWER KEY below). Expanded past a 2-of-3 list so the pick is not guessable.
# Grounding to verify against TS 38.413 / TS 23.501 / TS 24.501 before calibration
# (see docs/grounding/normative-sources.md); these are the working set.
I3_CANDIDATES = (
    "NGAP Overload Start",
    "Traffic Load Reduction Indication",
    "NAS congestion control back-off",
    "AMF load-balancing Weight Factor",
    "RACH back-off (RAN admission)",
    "SMF Session-AMBR throttling",
)


# ===========================================================================
#  ANSWER KEY  -  the correct answers; scorers.py only, NEVER a prompt
# ===========================================================================

# i3 ANSWER KEY: the genuine NGAP/NAS overload-control mechanisms vs the
# distractors. Wording matches I3_CANDIDATES so a verbatim copy normalizes equal.
I3_CORRECT = (
    "NGAP Overload Start",
    "Traffic Load Reduction Indication",
    "NAS congestion control back-off",
)
I3_DISTRACTORS = (
    "AMF load-balancing Weight Factor",
    "RACH back-off (RAN admission)",
    "SMF Session-AMBR throttling",
)

# i3 overload-action traffic classes (TS 38.413 sec 9.3.1.105 Overload Action:
# permit emergency + mobile-terminated only). Scored as controlled sets, not an
# exact enum string.
I3_PROTECTED = ("emergency", "mobile terminated")
# Rejected classes must not contain the protected tokens: the rejected-traffic
# component treats I3_PROTECTED as unsafe extras (rejecting emergency/MT voids it),
# and "non-emergency" would normalize to contain the "emergency" token, so use
# wording that cannot collide.
I3_REJECTED = ("mobile originated", "other registrations")

# i2 judge anchors: the live-forced correct load state per world. The grader
# derives the expected state from the live peak (deterministic) and the judge only
# decides whether the agent's verdict text agrees with that state.
I2_EXPECTED_STATE = {"storm": "overloaded", "baseline": "normal"}


# ===========================================================================
#  OFFLINE GATES  -  used by the scripts in scripts/, not by the live eval
# ===========================================================================

# A product score at or above this is a pass (used by pass^k and the gate
# export).
PASS_THRESHOLD = 0.8

# A task suite "differentiates" models when the per-model means spread by at
# least DIFF_SPREAD_MIN and fall into at least DIFF_BANDS_REQUIRED groups
# separated by gaps larger than DIFF_BAND_GAP.
DIFF_SPREAD_MIN = 0.25
DIFF_BAND_GAP = 0.05
DIFF_BANDS_REQUIRED = 3
