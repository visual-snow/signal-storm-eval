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

# The ten tasks, in operator-loop order: characterise (t1-t4), recommend
# (t5-t8), verify (t9-t10).
KINDS = ("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10")

# t5 candidate mechanisms shown to the model. Safe in the prompt: the candidate
# list is published neutrally; which one is the distractor is the hidden part.
T5_CANDIDATES = (
    "NGAP Overload Start",
    "Traffic Load Reduction Indication",
    "AMF load-balancing Weight Factor",
)


# ===========================================================================
#  ANSWER KEY  -  the correct answers; scorers.py only, NEVER a prompt
# ===========================================================================

# t5: the two genuine flow-control mechanisms, plus the distractor that must be
# excluded. Wording matches T5_CANDIDATES so a verbatim copy normalizes equal.
T5_EXPECTED = (
    "NGAP Overload Start",
    "Traffic Load Reduction Indication",
)
T5_DISTRACTOR = "AMF load-balancing Weight Factor"

# t6: the TS 38.413 sec 9.3.1.105 Overload Action enumeration value.
T6_ACTION = "Permit Emergency Sessions and mobile terminated services only"

# t9 verdict synonyms: phrases that mean "the planted TLR does NOT hold the
# load". Only judgment-bearing phrases, never bare state words ("overloaded")
# that appear in both a right and a wrong answer.
T9_FAILS = frozenset(
    {
        "ineffective",
        "not effective",
        "insufficient",
        "not sufficient",
        "inadequate",
        "not adequate",
        "not enough",
        "too low",
        "does not hold",
        "doesn t hold",
        "will not hold",
        "won t hold",
        "cannot hold",
        "can t hold",
        "fails to hold",
        "not capped",
        "does not cap",
        "will not cap",
        "won t cap",
        "ceiling exceeded",
        "still overloaded",
        "remains overloaded",
    }
)

# t10 verdict synonyms: phrases that mean "no flow control is needed" on the
# idle baseline.
T10_NO_CONTROL = frozenset(
    {
        "no control needed",
        "no flow control needed",
        "no flow control is needed",
        "no control required",
        "no flow control required",
        "no flow control is required",
        "flow control is not needed",
        "flow control not needed",
        "flow control is not required",
        "flow control not required",
        "control is not needed",
        "control not needed",
        "not needed",
        "not required",
        "not necessary",
        "none needed",
        "none required",
        "no action needed",
        "no action required",
        "unnecessary",
        "unwarranted",
        "below ceiling",
        "below threshold",
        "below the idle",
    }
)


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
