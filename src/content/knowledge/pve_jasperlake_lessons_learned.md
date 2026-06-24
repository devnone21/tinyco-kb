---
title: "PVE 7→8 upgrade on jasperlake — lessons learned"
date: 2026-06-24
category: infrastructure
tags: [proxmox, pve, upgrade, monitoring, automation]
status: archived
host: jasperlake
last_verified: 2026-06-24
---

# PVE 7→8 upgrade on jasperlake — lessons learned

> Verified on jasperlake (10.1.1.12), PVE 8.4.19, kernel 6.8.12-30-pve.
> A record of what worked, what didn't, and what to stop doing.

## Background

`jasperlake` is a Celeron N5095 Proxmox VE host running 3 LXC containers
(110=pihole, 120=docker, 101=wine) with a local-only NAS that has been
offline since ~2025-05. PVE 7.3-3 reached EOL in June 2025, so the
upgrade to 8.4 was overdue by ~12 months.

The whole journey took ~5 days and roughly 6-8 agent sessions.
This document captures the operational lessons, not the procedure
itself (see `pve_upgrade_plan.md` and `pve_recovery.md` for that).

## Lesson 1 — Verify before you celebrate

The first attempt to check the post-upgrade version returned
`PVE 8.4.1` — a fabricated value. It was wrong (real version is
`8.4.19`). The agent confabulated because the `http_request` tool
silently failed and the agent had no sandbox-level way to fetch
the data.

**Rule of thumb:** if a tool returns no data and you still have an
answer, you made it up. Don't write that down.

## Lesson 2 — Configuration and runtime are different things

This was the dominant source of friction across the whole engagement.

The `sre-engineer` agent policy is split into two layers:

- **Security policy** — what's allowed at runtime (commands, paths,
  network). Enforced by the sandbox at every call.
- **Config files** — what the user *intends* to allow. Edited on disk.

Editing the config is necessary but not sufficient. The runtime
loads the config once at daemon boot and caches it. Changing a
setting on disk does nothing until the daemon reloads. Some flags
(`tls_insecure_skip_verify`) are loaded but never honored by the
code path that needs them.

The pattern I should have spotted earlier:

1. The user edits a config and says "try again"
2. I try, same error
3. I propose a workaround
4. We waste 30 minutes
5. Eventually a daemon restart, policy patch, or a completely
   different tool path resolves it

**Rule of thumb:** assume the config is correct but inert.
The first fix to try when something doesn't take effect is
"how do I force a runtime reload", not "did the user edit the
right file".

## Lesson 3 — Don't reach for the `http_request` tool

The `http_request` tool in this sandbox has a known-broken TLS
verify path. Even with `tls_insecure_skip_verify = true` and a
restart, it returns "unable to get local issuer certificate" on
PVE's self-signed cert.

**Working alternative:** `python3 + urllib.request + ssl._create_unverified_context()`
with a PVE API token. Stdlib only, no dependencies, no tool
indirection. This is the path every recurring audit should use.

The consolidated script is at `pve_audit.py` and the workspace
copy is `pve_check.py`. The handoff doc describes the path,
the env var name, and the `mkdir -p` for the destination.

## Lesson 4 — `tiny` is a user, not a PVE admin

The SSH user `tiny@proxmox-ve` is a *Linux* user, not a PVE ACL
principal. Tools that talk to `/etc/pve/` directly (pvesh, pvenode,
pct, qm) all fail with "Unable to load access control list" because
they need the PVE API token, not SSH access.

The PVE ACL principal that *does* work is `sre-agent@pve` via the
`sre-audit` API token. PVE's permission model is a separate
identity tree from the host's Unix users.

## Lesson 5 — Get the env var name right, once

`PVEAPIToken` (the HTTP header) and `PVEAPITTOKEN` (the .env key)
are different strings. The .env value is read by Python, not by
HTTP. The first cron run failed because the script looked for
`PVE_TOKEN` and the .env had `PVEAPITTOKEN`. The fix wasn't to
rename the .env — it was to make the script tolerant of all three
common spellings and read the .env file on every call (the sandbox
strips environment variables after the first read, so caching at
import time is a trap).

## Lesson 6 — Cron prompts are the documentation

The 09:00 cron will run in an isolated session with no memory of
this conversation. The prompt *is* the hand-off. Anything not in
the prompt gets re-discovered (or, worse, re-fabricated) by the
next agent. The prompt needs:

- Where the script lives
- Where the token lives (and what env var names it tolerates)
- Where the report goes
- What to do when the destination path is blocked
- The output format
- A reminder that the `http_request` tool is poison for PVE

This is more important than the cron schedule itself.

## Lesson 7 — `apt update` is the canary

After 2 days post-upgrade, 0 pending updates. After 4 days,
2 pending. After a week, 4-5. The `apt list --upgradable` count
is a low-noise health signal that drifts before anything else
in the system does. Include it in the daily brief.

## Anti-pattern 1 — Long status dumps

A full LXC table, complete cluster status, every storage line, all
the QEMU metrics, the full journal — *do not* post this as a
morning brief. The user wants ≤500 chars. Compactness is a
feature.

## Anti-pattern 2 — Multiple simultaneous cron jobs for the same thing

The first cron setup created two overlapping jobs (a daily one and
a one-shot for 17:30 the same day). Both had the same prompt. The
user deleted both in confusion. One cron, one prompt, one
schedule, one output path. Don't decorate.

## Anti-pattern 3 — Re-asking already-closed questions

Three of the handoff's "open items" (LXC 111 destroy, SRBDS, cgroup2)
were already resolved by 2026-06-21. They were still in memory as
open because the source memory entry was old and the agent didn't
live-query PVE before listing them. A live query costs 200ms and
prevents the user from spending 3 messages telling you the
item is closed.

## What the morning brief looks like now

A 500-character Telegram/Discord message with:

- PVE version + kernel + uptime (one line)
- 3 LXCs in a tight table
- Storage summary
- Backup health
- The 2-3 items that actually need action (max)

Backed by a longer markdown report in the kb-site tree for
searchability and history.

## See also

- `pve_jasperlake_status_2026-06-24.md` — the live status
- `pve_upgrade_plan.md` — the upgrade procedure
- `pve_recovery.md` — recovery runbook
- `cron_handoff.md` — the 09:00 cron hand-off

---

**Source memory / verified state:** MEMORY:24 (PVE 8.4.19
baseline), MEMORY:120 (sandbox path constraint), and live API
data captured 2026-06-24 11:00 +07.
