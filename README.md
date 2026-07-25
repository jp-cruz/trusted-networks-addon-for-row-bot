# row-bot trusted-networks patch (reference implementation)

A small, generalized reference implementation of the trusted-network allowlist proposed in
[siddsachar/row-bot#297](https://github.com/siddsachar/row-bot/issues/297) and
[discussion #298](https://github.com/siddsachar/row-bot/discussions/298).

**Status: private staging repo, not yet published.** Content is deliberately generalized
(no environment-specific paths, IPs, or identifiers) and ready to go public once reviewed.

## Problem

Row-Bot's Mobile Access gate treats "local" as strictly loopback (`127.0.0.1`/`localhost`).
That check silently never succeeds for browser traffic to a Dockerized instance, because
container runtimes NAT the connection — the app sees a Docker-internal gateway address,
never true loopback. Practical effect: any Dockerized deployment is permanently stuck
behind the mobile-companion pairing flow, with no way to reach the full desktop UI, even
from the same machine Docker is running on.

This also compounds into a full lockout for a browser session with no paired-device
cookie yet: the only documented way to get a pairing code is a settings page that's
itself behind the same local-only gate.

## Proposed fix

Extend the loopback check to an explicit, **opt-in, operator-configured** allowlist of
trusted CIDR ranges, read from an environment variable. Off by default — existing
behavior is unchanged unless the operator explicitly sets it.

See `trust.py` for the reference implementation and `INTEGRATION.md` for how it would
slot into Row-Bot's existing local-check call sites.

## Precedent

Home Assistant's `trusted_networks` auth provider solves the same problem the same way,
for a very similar risk profile (home-automation/agent software with real device and
execution control). This isn't a novel idea — it's a well-established, well-understood
pattern being proposed for a project that could benefit from it.

## Configuration

```sh
export ROW_BOT_TRUSTED_NETWORKS="192.0.2.0/24,198.51.100.0/24"
```

(Using RFC 5737 documentation ranges here as placeholders — substitute your own
container-runtime gateway range and/or trusted local network CIDR.)

## License

Apache License 2.0 (see `LICENSE`/`NOTICE`) — the same license as the upstream Row-Bot
project, chosen deliberately so this can be contributed back with no license
reconciliation needed.

## Status

Reference implementation only — not a drop-in patch for any specific Row-Bot version.
Adapt integration points to whatever version you're running.
