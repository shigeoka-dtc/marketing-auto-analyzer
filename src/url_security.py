import ipaddress
import os
import socket
from urllib.parse import urlsplit

ALLOWED_TARGET_HOSTS = [
    host.strip().lower()
    for host in os.getenv("ALLOWED_TARGET_HOSTS", "").split(",")
    if host.strip()
]
DISALLOWED_HOSTNAMES = {
    "localhost",
    "host.docker.internal",
    "metadata",
    "metadata.google.internal",
    "ip6-localhost",
}


def _matches_allowed_hosts(hostname: str) -> bool:
    if not ALLOWED_TARGET_HOSTS:
        return True
    return any(
        hostname == allowed or hostname.endswith(f".{allowed}")
        for allowed in ALLOWED_TARGET_HOSTS
    )


def _is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def _resolved_ips(hostname: str) -> set[str]:
    infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    return {info[4][0] for info in infos}


def assert_safe_target_url(url: str):
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("分析対象URLは http:// または https:// のみ許可します")
    if parsed.username or parsed.password:
        raise ValueError("認証情報付きURLは許可していません")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError("ホスト名が不正です")
    if hostname in DISALLOWED_HOSTNAMES or hostname.endswith(".local"):
        raise ValueError("localhost / private host / local network host は許可していません")
    if not _matches_allowed_hosts(hostname):
        raise ValueError("ALLOWED_TARGET_HOSTS に含まれないホストです")

    try:
        if not _is_public_ip(hostname):
            raise ValueError("private / loopback / link-local IP は許可していません")
        return
    except ValueError as exc:
        if "private / loopback" in str(exc):
            raise
    except Exception:
        pass

    try:
        resolved_ips = _resolved_ips(hostname)
    except socket.gaierror as exc:
        raise ValueError(f"ホスト名を解決できません: {exc}") from exc

    if not resolved_ips:
        raise ValueError("ホスト名を解決できません")

    unsafe_ips = [ip for ip in resolved_ips if not _is_public_ip(ip)]
    if unsafe_ips:
        raise ValueError(f"private / loopback / link-local 宛てのホストは許可していません: {', '.join(sorted(unsafe_ips))}")
