"""Sandbox-side operations: exec, boot wait, storm injection, live probes (P3).

The only module that touches the sandbox. Runs commands against the Open5GS
core and the PacketRusher injector, waits for the core to settle, fires the
seeded storm, and reads the live registration counters off Prometheus. Raising
RuntimeError here errors the sample (infrastructure fault), which is the correct
outcome per the guide: an infra failure must never score as a model failure.
"""

import asyncio
import json
from urllib.parse import urlencode

from inspect_ai.util import ExecResult, sandbox

# Compose service names (topology/compose.yaml). The AMF config + log live in the
# all-in-one core; Prometheus scrapes its metrics; PacketRusher drives the storm.
CORE = "open5gs-aio"
PROM = "prometheus"
INJECTOR = "packetrusher"

SERVICE_HINT = """
Valid service names:
- Core (AMF config + log): open5gs-aio
- Metrics: prometheus
- Storm injector: packetrusher
"""

# Paths inside the core container (config/amf.yaml, run.sh logger config).
AMF_CONFIG_PATH = "/open5gs/config/amf.yaml"
AMF_LOG_PATH = "/open5gs/install/var/log/open5gs/amf.log"

# Live registration counters exposed by the AMF (config/amf.yaml metrics server).
REGINITREQ = "fivegs_amffunction_rm_reginitreq"
REGINITSUCC = "fivegs_amffunction_rm_reginitsucc"

BOOT_TIMEOUT_S = 180
# The storm has already run by the time the gate polls, so its counters are
# present within a scrape or two; a short timeout bounds the cost of replaying an
# under-fired storm.
MANIFEST_TIMEOUT_S = 60
# Minimum live peak rate (reg/s) that counts as a real overload. A healthy storm
# drives ~106-115 reg/s; the injector occasionally under-fires and leaves only a
# few reg/s, which would flip the ground truth of t7/t8/t9. 50 cleanly separates
# the two without being sensitive to per-run capacity jitter.
MIN_STORM_PEAK_RATE = 50.0
_POLL_INTERVAL_S = 3


async def safe_exec(host: str, cmd: list[str], timeout: int = 15) -> ExecResult:
    """Execute on a sandbox service; helpful error for invalid service names."""
    try:
        return await sandbox(host).exec(cmd, timeout=timeout)
    except ValueError:
        return ExecResult(
            success=False,
            returncode=1,
            stdout="",
            stderr=f"'{host}' is not a valid service name.{SERVICE_HINT}",
        )


# --- Prometheus ------------------------------------------------------------


async def query_prometheus(promql: str, timeout: int = 20) -> list[dict]:
    """Run an instant PromQL query; return the parsed `data.result` list.

    Queried from inside the Prometheus container via busybox wget against the
    local API (prom/prometheus ships wget but no curl). Any transport, HTTP, or
    parse failure is an infrastructure fault and raises RuntimeError.
    """
    body = urlencode({"query": promql})
    cmd = [
        "wget",
        "-q",
        "-O-",
        "--post-data",
        body,
        "http://127.0.0.1:9090/api/v1/query",
    ]
    result = await safe_exec(PROM, cmd, timeout=timeout)
    if not result.success:
        raise RuntimeError(
            f"Prometheus query failed (code {result.returncode}): {promql}\n"
            f"{result.stderr or result.stdout}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Prometheus returned non-JSON for {promql}: {e}") from e
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query errored for {promql}: {payload}")
    return payload["data"]["result"]


def _scalar(result: list[dict], promql: str) -> float:
    """Pull the single numeric value out of an instant-vector result."""
    if not result:
        raise RuntimeError(f"Prometheus returned empty result for {promql}")
    try:
        return float(result[0]["value"][1])
    except (KeyError, IndexError, ValueError, TypeError) as e:
        raise RuntimeError(f"malformed Prometheus value for {promql}: {e}") from e


async def _query_scalar(promql: str) -> float:
    return _scalar(await query_prometheus(promql), promql)


async def _query_rate(promql: str) -> float:
    """Scalar read for a max-sustained-rate subquery; empty result is 0 reg/s.

    A `max_over_time(rate(...)[w:])` subquery returns an empty vector when no
    rate activity sits in the window (the idle baseline, or a world with less
    history than the window). That is a real zero rate, not an infra fault, so it
    must not raise. A storm world always has in-window data, so this only zeroes
    the genuinely-idle case.
    """
    result = await query_prometheus(promql)
    return _scalar(result, promql) if result else 0.0


# --- Live-state probes (the scorer's ground truth) -------------------------


async def live_count(window: str) -> float:
    """Initial-registration requests over the storm window (registrations)."""
    return await _query_scalar(f"increase({REGINITREQ}[{window}])")


def _max_sustained_rate(metric: str, storm_window: str, peak_window: str, step_s: int) -> str:
    """PromQL for the max sustained rate of a counter over the storm window.

    The storm window is the outer max_over_time range, peak_window the inner
    rate() sub-window. The explicit `:step` resolution is required: without it the
    subquery samples at Prometheus' coarse global eval interval and misses the
    short reginitsucc throughput peak, so step matches the scrape interval.
    """
    return f"max_over_time(rate({metric}[{peak_window}])[{storm_window}:{step_s}s])"


async def live_peak_rate(storm_window: str, peak_window: str, step_s: int) -> float:
    """Max sustained reginitreq rate over the storm window (reg/second)."""
    return await _query_rate(
        _max_sustained_rate(REGINITREQ, storm_window, peak_window, step_s)
    )


async def capacity_rate(storm_window: str, peak_window: str, step_s: int) -> float:
    """Max sustained reginitsucc rate; the AMF's emergent throughput (reg/s)."""
    return await _query_rate(
        _max_sustained_rate(REGINITSUCC, storm_window, peak_window, step_s)
    )


async def rejected_volume(window: str) -> float:
    """Deficit = reginitreq increase minus reginitsucc increase (registrations)."""
    promql = (
        f"increase({REGINITREQ}[{window}]) - increase({REGINITSUCC}[{window}])"
    )
    return await _query_scalar(promql)


# --- Core config + log -----------------------------------------------------


async def read_amf_config() -> str:
    """Read the live AMF config (config/amf.yaml) from the core container."""
    result = await safe_exec(CORE, ["cat", AMF_CONFIG_PATH])
    if not result.success:
        raise RuntimeError(f"reading {AMF_CONFIG_PATH} failed: {result.stderr}")
    return result.stdout


async def read_amf_log() -> str:
    """Read the AMF log file (not docker logs) from the core container."""
    result = await safe_exec(CORE, ["cat", AMF_LOG_PATH])
    if not result.success:
        raise RuntimeError(f"reading {AMF_LOG_PATH} failed: {result.stderr}")
    return result.stdout


# --- Storm injection + gates -----------------------------------------------


async def run_storm(
    rate: int | None = None,
    ue_count: int | None = None,
    duration_s: int | None = None,
    timeout: int = 300,
) -> ExecResult:
    """Run one storm via the injector (`/storm.sh run`).

    Overrides are passed as env to the exec; the storm world uses the compose
    defaults, the baseline world passes rate=0, ue_count=0. Storm.sh blocks for
    DURATION_S, so the exec timeout must exceed it. Infra failure raises.
    """
    env = {}
    if rate is not None:
        env["STORM_RATE"] = str(rate)
    if ue_count is not None:
        env["UE_COUNT"] = str(ue_count)
    if duration_s is not None:
        env["DURATION_S"] = str(duration_s)
    result = await sandbox(INJECTOR).exec(
        ["/storm.sh", "run"], env=env, timeout=timeout
    )
    if not result.success:
        raise RuntimeError(
            f"storm injection failed (code {result.returncode}): "
            f"{result.stderr or result.stdout}"
        )
    return result


async def _metric_queryable() -> bool:
    """True once the AMF target is up and the reginitreq counter is scrapeable."""
    try:
        return bool(await query_prometheus(REGINITREQ))
    except RuntimeError:
        return False


async def wait_for_boot(timeout_s: int = BOOT_TIMEOUT_S) -> None:
    """Poll until Prometheus has scraped the AMF registration counter."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        if await _metric_queryable():
            return
        await asyncio.sleep(_POLL_INTERVAL_S)
    raise RuntimeError(f"AMF metrics never scrapeable within {timeout_s}s")


async def wait_storm_manifest(
    storm_window: str,
    peak_window: str,
    step_s: int,
    timeout_s: int = MANIFEST_TIMEOUT_S,
) -> bool:
    """Gate: the storm must stand as a severe, sustained overload.

    Per the spec the storm has to overload the AMF enough that the offered peak
    rate dwarfs its throughput; otherwise the sized/verify tasks (t7/t8/t9) have
    no ground truth. A faint dribble (the injector occasionally under-fires) is
    not enough: it would make a 10% reduction "hold" and flip t9's expected
    verdict. Returns True once the live peak rate clears MIN_STORM_PEAK_RATE with
    a real deficit, or False on timeout so the caller can replay the storm.
    """
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        peak = await live_peak_rate(storm_window, peak_window, step_s)
        deficit = await rejected_volume(storm_window)
        if peak >= MIN_STORM_PEAK_RATE and deficit > 0:
            return True
        await asyncio.sleep(_POLL_INTERVAL_S)
    return False
