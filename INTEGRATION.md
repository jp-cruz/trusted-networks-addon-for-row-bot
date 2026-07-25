# Integration notes

Row-Bot (as of the version this was built against) has three separate places doing a
near-identical loopback-only check:

- `row_bot/mobile/access_gate.py` — `is_true_local_scope(scope)`, used by the
  `MobileAccessGate` ASGI middleware (the main gate deciding local vs. requires-pairing)
- `row_bot/mobile/routes.py` — `is_true_local_request(request)`, used for
  settings-management permission checks
- `row_bot/ui/mobile.py` — `_is_direct_local_request(request)`, used to pick the mobile
  companion vs. full desktop UI shell

Each currently does roughly:

```python
def _is_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False
```

## Suggested integration

Replace each of the three with a call to `is_trusted_client_ip(host)` from `trust.py` —
or better, consolidate all three into one shared import, since they already commonly
import from the same module (`row_bot.mobile.store` in the version this was built
against) and are otherwise identical logic maintained in three places.

Example (`access_gate.py`):

```python
from trust import is_trusted_client_ip  # or wherever this ends up living

def is_true_local_scope(scope: dict) -> bool:
    client = scope.get("client") or ("", 0)
    client_host = str(client[0] or "")
    return is_trusted_client_ip(client_host) and not has_forwarded_headers(scope)
```

Repeat the same substitution for the other two call sites, keeping each file's own
forwarded-header check unchanged — only the loopback-membership test itself changes.

## Debugging tip

Don't assume which internal address range host-forwarded traffic will present as under a
given container runtime — verify empirically. On Docker Desktop for Mac, for example,
host-originated port-forwarded traffic arrives via the Desktop app's internal VM gateway
range, not the container's own bridge network gateway — two different, non-obvious
subnets. A temporary debug print in the trust-check function (removed once you've
confirmed the real observed address) is the fastest way to get this right rather than
guessing from `docker inspect` alone.
