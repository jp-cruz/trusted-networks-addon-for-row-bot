"""Reference implementation: opt-in trusted-network allowlist for local-access detection.

Extends a strict "is this loopback" check to also accept an explicit, operator-configured
allowlist of trusted CIDR ranges -- letting devices on a trusted home/office network (or
a container runtime's internal NAT range) get full local-equivalent access without an
additional pairing/auth step.

This is a deliberate, OPT-IN trade-off: convenience vs. authorization-by-network-location.
Off by default -- if the environment variable isn't set, behavior is unchanged (loopback
only). Document this clearly to anyone who enables it; trusting a network range means any
device on that range gets local-equivalent access with no further check.
"""

from __future__ import annotations

import os
from functools import lru_cache
from ipaddress import ip_address, ip_network

ENV_VAR = "ROW_BOT_TRUSTED_NETWORKS"


@lru_cache(maxsize=1)
def _trusted_networks():
    raw = os.environ.get(ENV_VAR, "").strip()
    if not raw:
        return ()
    networks = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            networks.append(ip_network(entry, strict=False))
        except ValueError:
            continue  # skip malformed entries rather than crash at import/call time
    return tuple(networks)


def is_trusted_client_ip(host: str) -> bool:
    """Return True if `host` is loopback or within an operator-configured trusted network.

    Reads the allowlist from the `ROW_BOT_TRUSTED_NETWORKS` environment variable
    (comma-separated CIDR ranges), evaluated once and cached -- set it before the app
    starts, not at runtime, if using a process manager that doesn't restart on env change.
    """
    if host == "localhost":
        return True
    try:
        addr = ip_address(host)
    except ValueError:
        return False
    if addr.is_loopback:
        return True
    return any(addr in network for network in _trusted_networks())
