# Docker Compose notes

Two gotchas specific to using this pattern with Compose that are easy to miss.

## 1. Pin the bridge network's subnet — don't rely on Docker's auto-assigned one

By default, Compose creates a bridge network per project (e.g. `<project>_default`) with
a subnet Docker picks automatically. That subnet **can change** across rebuilds/recreates
if the auto-assigned range happens to differ next time (e.g. another project on the same
host claimed the one it used before). If you trust that subnet in
`ROW_BOT_TRUSTED_NETWORKS` without pinning it, a later rebuild can silently drift to a
different subnet — the trust match quietly breaks, with no error, and the symptom looks
identical to "the fix stopped working" rather than "the config is now stale."

Pin it explicitly instead:

```yaml
networks:
  default:
    ipam:
      config:
        - subnet: 192.0.2.0/24   # RFC 5737 placeholder -- pick your own private range
```

Now the bridge subnet is fixed and matches what you put in `ROW_BOT_TRUSTED_NETWORKS`
regardless of rebuild order or what else is running on the host.

## 2. Separate the two trust ranges you actually need

There are two conceptually different "Docker-side" ranges, don't conflate them:

- **The Compose project's own bridge network** (container-to-container traffic) — this is
  the one you just pinned above, and it's project-specific.
- **The container-runtime's host-forwarded-traffic gateway** (what a browser on the Docker
  host itself looks like from inside the container) — this is **not** Compose-controlled
  at all. On Docker Desktop for Mac, for example, it's the Desktop app's own internal VM
  gateway range, the same for every project on that installation. Verify it empirically
  (see `INTEGRATION.md`'s debugging tip) rather than assuming it matches the bridge subnet
  you just pinned — they are usually different ranges entirely.

## 3. Env var changes need a recreate, not just a restart

```sh
# This does NOT pick up a changed ROW_BOT_TRUSTED_NETWORKS value:
docker restart <container>

# This does:
docker compose up -d
```

A plain restart reuses the container's already-baked-in environment. Compose's `up -d`
detects the config change and recreates the container with the new value.

## Minimal example

```yaml
services:
  app:
    # ...
    environment:
      ROW_BOT_TRUSTED_NETWORKS: "192.0.2.0/24,198.51.100.0/24"  # placeholders -- see above

networks:
  default:
    ipam:
      config:
        - subnet: 192.0.2.0/24  # must match one of the ranges above if you want the
                                 # bridge network itself trusted, not just the host path
```

## 4. Persist the pairing database — a related but separate concern

Not part of this patch itself, but directly affects whether the goal holds for devices
*outside* your trusted range: Row-Bot's pairing store (`MobileAuthStore`, SQLite-backed)
lives at whatever path the app's data-directory setting points to. If that path isn't on
a persistent volume, **every container recreate wipes all device pairings** — any device
outside `ROW_BOT_TRUSTED_NETWORKS` (remote/tailnet access, for example) has to re-pair
from scratch each time you rebuild, even though nothing about its own configuration
changed.

```yaml
services:
  app:
    volumes:
      - app-data:/path/to/data/dir   # must include wherever the pairing DB lives

volumes:
  app-data:
    driver: local
```

Trusted-network devices never hit this — they skip pairing entirely — but it's worth
getting right for anyone who'll also access the instance from outside the trusted range.
