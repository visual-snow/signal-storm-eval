"""Agent-facing tools: read the live storm and the core config (P3).

Four named actions wrapping signal_storm_bench.sandbox_ops: query the live
registration counters off Prometheus, read the AMF config, read an NF log file,
and replay the registration storm. Tools return live state and surface command
failures as text (never raised); ground truth stays hidden in sample metadata.
"""

import json

from inspect_ai.tool import Tool, tool
from inspect_ai.util import ExecResult

from signal_storm_bench import sandbox_ops

# NF log files under /open5gs/install/var/log/open5gs/ (amf.log path is pinned in
# config/amf.yaml; the other daemons log to the same directory by NF name).
_NF_NAMES = ("amf", "smf", "ausf", "udm", "udr", "pcf", "nssf", "nrf", "scp", "upf")


def _format(result: ExecResult, cmd_name: str) -> str:
    if result.success:
        return result.stdout
    stderr_part = f"\n[stderr]: {result.stderr}" if result.stderr else ""
    return f"[{cmd_name} failed with code {result.returncode}]\n{result.stdout}{stderr_part}"


@tool
def query_prometheus_metrics() -> Tool:
    """Run an instant PromQL query against the AMF metrics."""

    async def execute(promql: str) -> str:
        """Run an instant PromQL query against the live AMF metrics in Prometheus.

        Use this to read the registration-storm counters the AMF exposes (each
        counter name starts with fivegs_amffunction_). Plain PromQL: an instant
        query, no range or step. Examples:

            fivegs_amffunction_rm_reginitreq
            increase(fivegs_amffunction_rm_reginitreq[3m])
            rate(fivegs_amffunction_rm_reginitsucc[30s])

        Args:
            promql: An instant PromQL expression

        Returns:
            The JSON result rows from Prometheus; query failures are returned, not raised
        """
        try:
            rows = await sandbox_ops.query_prometheus(promql)
        except RuntimeError as e:
            return f"[prometheus query failed]\n{e}"
        return json.dumps(rows, indent=2)

    return execute


@tool
def read_amf_config() -> Tool:
    """Read the live AMF configuration file (amf.yaml)."""

    async def execute() -> str:
        """Read the running AMF configuration (amf.yaml) from the core.

        Use this to inspect the AMF's current settings: NGAP server, metrics,
        GUAMI/TAI/PLMN, security, timers. There is no flow-control section unless
        one has been added.

        Returns:
            The contents of amf.yaml; a read failure is returned, not raised
        """
        result = await sandbox_ops.safe_exec(
            sandbox_ops.CORE, ["cat", sandbox_ops.AMF_CONFIG_PATH]
        )
        return _format(result, "read_amf_config")

    return execute


@tool
def read_nf_log_file() -> Tool:
    """Read a network-function log file from the core (e.g. amf.log)."""

    async def execute(nf_name: str) -> str:
        """Read an NF daemon log file from the core container.

        Use this to inspect what a network function logged during the storm; the
        AMF (amf) carries the registration traffic. This reads the on-disk log
        file under /open5gs/install/var/log/open5gs/, not docker logs.

        Args:
            nf_name: NF name, one of amf, smf, ausf, udm, udr, pcf, nssf, nrf, scp, upf (amf carries the storm)

        Returns:
            The log file contents; an unknown NF name or read failure is returned, not raised
        """
        nf = nf_name.strip().lower()
        if nf not in _NF_NAMES:
            return f"[unknown NF '{nf_name}'] valid NFs: {', '.join(_NF_NAMES)}"
        path = f"/open5gs/install/var/log/open5gs/{nf}.log"
        result = await sandbox_ops.safe_exec(sandbox_ops.CORE, ["cat", path])
        return _format(result, "read_nf_log_file")

    return execute


@tool
def run_ue_storm_simulator() -> Tool:
    """Replay or extend the UE registration storm against the AMF."""

    async def execute(rate: int, ue_count: int, duration_s: int) -> str:
        """Drive a UE registration storm via the PacketRusher injector.

        Use this to replay or extend the storm: it registers ue_count UEs at
        rate registrations/second for up to duration_s seconds, over real
        NGAP-over-SCTP. This call blocks until the storm finishes. The counters
        in Prometheus stand afterward; re-query them to read the new state. The
        storm already fired before you started; to reproduce it faithfully use
        rate=120, ue_count=6000, duration_s=90.

        Args:
            rate: Registration attempts per second (0 means no storm)
            ue_count: Number of UEs to register
            duration_s: Maximum storm duration in seconds

        Returns:
            The injector output; an injection failure is returned, not raised
        """
        try:
            result = await sandbox_ops.run_storm(
                rate=rate,
                ue_count=ue_count,
                duration_s=duration_s,
                timeout=duration_s + 60,
            )
        except RuntimeError as e:
            return f"[storm injection failed]\n{e}"
        return result.stdout

    return execute


def agent_tools() -> list[Tool]:
    return [
        query_prometheus_metrics(),
        read_amf_config(),
        read_nf_log_file(),
        run_ue_storm_simulator(),
    ]
