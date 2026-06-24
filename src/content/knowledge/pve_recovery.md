---
title: "PVE Upgrade Recovery Procedure"
pubDate: 2026-06-24
category: infrastructure
tags: [proxmox, pve, upgrade, recovery]
status: archived
host: jasperlake
last_verified: 2026-06-21
---

# PVE Upgrade Recovery Procedure — jasperlake

> Companion to `pve_upgrade_plan.md`. Read this BEFORE you start Phase 2.
> Last updated: 2026-06-21 19:10 +07 (revision: SRBDS section added; PVE 8.4.19 final state).

## TL;DR

| Scenario | Time to fix | Difficulty | Outcome |
|---|---|---|---|
| 1. apt breaks mid-upgrade, before reboot | 10 min | Easy | chroot from USB, `dpkg --configure -a` |
| 2. Reboot fails (kernel panic, no network) | 20-30 min | Medium | chroot from USB, fix grub or finish apt |
| 3. Reboot succeeds, but LXCs/network broken | 5-15 min | Easy-Medium | Boot old kernel from grub, or fix config in place |
| 4. Host is unrecoverable, fresh start needed | 60-90 min | Hard | Reinstall PVE 8.x from ISO, restore LXCs from `/var/lib/vz/dump/` |

**The good news**: LXCs live on `local-lvm` (an independent LV from `pve-root`). They will survive a host re-install as long as `/var/lib/vz/dump/` (on `pve-root`) and the LXC disks (on `local-lvm`) are both intact.

---

## What to have on hand

- **PVE 8.x ISO on a USB stick** (download from proxmox.com, ~1.2 GB)
  - 7.4 ISO for fixing 7.4 issues, 8.x ISO for fresh install
- **A monitor + keyboard** (or IPMI / iKVM if your box has it) — you need console access
- **The following files**, already captured in `preflight-20260616-150126/`:
  - `07_lvm.json` — LVM layout
  - `18_etc_network_interfaces.txt` — network config
  - `16_acl.json` — ACLs
  - `17_users.json` — users and tokens
  - `pve_upgrade_collect.py` and the cluster backup JSON
  - This file (`pve_recovery.md`)
- **A working host** (your laptop, another VM) to consult docs

---

## Scenario 1 — apt breaks mid-upgrade, before reboot

Symptoms: `apt full-upgrade` errors out partway; host still bootable in 7.4.

```bash
# 1. Check what's broken
tail -100 /var/log/apt/term.log

# 2. Try to fix in place
apt update
apt -f install
dpkg --configure -a
apt full-upgrade -y   # retry the upgrade

# 3. If that fails, identify the broken package
dpkg -l | grep -v '^ii' | head   # lists non-installed packages
```

If apt is unrecoverable, you need the USB:
1. Boot PVE 8.x ISO
2. At installer menu, choose **Debug mode** (or `Rescue boot`)
3. Mount the root: `mount /dev/mapper/pve-root /mnt`
4. Bind-mount system dirs: `mount --bind /dev /mnt/dev; mount --bind /proc /mnt/proc; mount --bind /sys /mnt/sys`
5. Chroot: `chroot /mnt`
6. From inside chroot: `dpkg --configure -a && apt -f install && apt full-upgrade -y`
7. Exit, reboot, remove USB

---

## Scenario 2 — Reboot fails, host is unreachable

Symptoms: host doesn't come back after `reboot`. Console shows:
- Black screen
- Kernel panic
- Grub rescue prompt (`grub>`)
- "Boot Device Not Found"
- Repeating reboot

### Sub-scenario 2a: Grub rescue prompt

The grub itself is there but can't find its config. Try:

```
grub> ls
grub> ls (hd0,gpt2)/   # /boot/efi
grub> ls (hd0,gpt3)/boot/   # /boot on pve-root
grub> set root=(hd0,gpt3)
grub> linux /boot/vmlinuz-5.15.158-2-pve root=/dev/mapper/pve-root ro
grub> initrd /boot/initrd.img-5.15.158-2-pve
grub> boot
```

If that gets you in, fix grub permanently:
```bash
update-grub
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=proxmox
efibootmgr -v   # verify 'proxmox' is the boot entry
```

### Sub-scenario 2b: UEFI doesn't see the disk

The UEFI NVRAM boot entry was lost. Fix from PVE 8.x ISO in debug mode:

```bash
mount /dev/mapper/pve-root /mnt
mount /dev/sda2 /mnt/boot/efi
mount --bind /dev /mnt/dev
mount --bind /proc /mnt/proc
mount --bind /sys /mnt/sys
chroot /mnt
grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=proxmox
update-grub
efibootmgr -v
exit
reboot
```

### Sub-scenario 2c: Kernel panic after grub

Try booting the OLD kernel from grub menu (if 5.15.74-1-pve is still installed):
- At grub menu, press `Advanced options for Proxmox VE GNU/Linux`
- Pick `5.15.74-1-pve` instead of `5.15.158-2-pve`
- If that boots: re-install grub-efi-amd64 properly, then apt full-upgrade again

If old kernel also panics: USB recovery per Scenario 2b.

---

## Scenario 3 — Reboot succeeds, but LXCs/network broken

Symptoms: host is up, `pveproxy` works, but:
- LXCs 110/120 don't start
- `vmbr0` is down
- No DNS / network

### Sub-scenario 3a: vmbr0 missing or down

```bash
# Check current state
ip link show
cat /etc/network/interfaces

# If vmbr0 is missing, edit /etc/network/interfaces to recreate it
# (Original is in preflight-20260616-150126/18_etc_network_interfaces.txt)
ifreload -a
systemctl restart networking
```

### Sub-scenario 3b: LXCs don't start

```bash
# Try to start one
pct start 110
journalctl -u pve-container@110 -n 50

# Common fix: LXC config got out of sync with host kernel
pct config 110 | grep -E 'features|cgroups'
# If the LXC has features that the new kernel doesn't support, edit the config:
nano /etc/pve/lxc/110.conf
# Remove or adjust unsupported features
pct start 110
```

---

## Scenario 4 — Fresh start (worst case)

If everything is bricked, this is the cleanest path. Assumes the disk and LVM are still intact.

### 4.1 Boot PVE 8.x ISO on USB

1. Download `proxmox-ve_8.*.iso` from proxmox.com
2. Use `dd` or `etcher` to write to USB stick
3. Plug into jasperlake, power on, press F12/Del to choose boot device
4. At installer menu, choose **Install Proxmox VE**

### 4.2 Install to the same disk

- Target disk: `/dev/sda` (the existing 119 GB)
- The installer will **WIPE** the partition table. **This is destructive** for the existing `/dev/pve` data. The installer creates a fresh layout.
- **CRITICAL**: if you want to preserve the LXC data on `local-lvm`, you must NOT let the installer wipe the disk. Use **Debug mode** instead and re-create the LVM manually, OR use a separate disk for the fresh PVE install and keep `sda` for the LXCs.

### 4.3 Simpler approach: keep one disk for LXCs, use a different disk for fresh PVE

If you have a second disk or can spare an external USB SSD for the new PVE install:
1. Disconnect the existing disk
2. Install PVE 8.x fresh to the new disk
3. Reconnect the old disk as `/dev/sdb`
4. `vgscan` and `vgimport` to make the old `pve` VG available
5. Mount `local-lvm` and `pve-root` (which has the backup archives)
6. `pct restore` LXCs from the backup files

### 4.4 Full reinstall with the same disk (destructive but simple)

Only do this if you don't care about the LXC data and have backups elsewhere:

1. Install PVE 8.x to `/dev/sda` (wipes everything)
2. Recreate network: copy from `preflight-20260616-150126/18_etc_network_interfaces.txt`
3. Re-add storage: `pvesm add local-lvm lvmthin ...` (or use the UI)
4. Restore LXCs from `/var/lib/vz/dump/vzdump-lxc-{110,120}-*.tar.zst`:
   - But wait, the backups are on the wiped disk — you need them off-host first
   - **This is why you should always have off-host backups before destructive ops**

---

## Post-recovery: verification checklist

After any recovery action, verify these are good:

```bash
# Host
pveversion -v | head -3
uname -r
uptime
df -h /
free -h
pvecm status

# LXCs
pct list
pct status 110
pct status 120
pct enter 110 echo OK   # if you can enter, LXC is working
pct enter 120 echo OK

# Network
ip -br addr show
ip route
ping 10.1.1.8   # gateway
nslookup google.com 8.8.8.8   # DNS

# Services
systemctl is-active pveproxy pvedaemon pve-cluster pve-firewall pvescheduler
```

If all check out, you're back in business.

---

## Lessons-learned checklist (apply BEFORE any future PVE upgrade)

- [ ] Off-host backup of LXC archives (rsync to NAS, S3, etc.) — at least one copy somewhere other than `/var/lib/vz/dump/` on the same disk
- [ ] `grub-efi-amd64` installed and `update-grub` tested
- [ ] Old kernel kept in `/boot` for fallback
- [ ] Network config exported to a file on a separate machine
- [ ] Recovery USB (PVE 8.x ISO) created and tested (boot from it, mount /dev/pve/root, exit — verify you can do this)
- [ ] Maintenance window scheduled with the LAN (pihole will be down)
- [ ] Tested the path: ssh as `tiny` should work after each step

---

## SRBDS residual risk — accepted (2026-06-21)

jasperlake hosts an **Intel Celeron N5095** (Jasper Lake, Atom-derived microarchitecture). This CPU is **vulnerable to SRBDS** (Special Register Buffer Data Sampling, CVE-2020-0543).

**Status verified 2026-06-21 19:07**: `cat /sys/devices/system/cpu/vulnerabilities/srbds` returns:
```
Vulnerable: No microcode
```

### Why this is unmitigatable

- Intel has **not shipped** microcode that mitigates SRBDS for the Jasper Lake / Atom family. The microcode loaded on the host (`intel-microcode 3.20251111.1~deb12u1`, revision `0x24000026`) addresses other microarchitectural issues (e.g., some MDS/RDRAND bugs) but not SRBDS.
- No kernel workaround is available for Atom-class parts (the `srso=` kernel param and similar are for AMD or for Intel cores with the vulnerable structure; not applicable here).
- PVE-side or hypervisor-side mitigations are not applicable — SRBDS is a CPU-internal side channel between logical processors on the same physical core.

### Risk assessment

- **Likelihood**: Low. Atom-derived parts are typically not targeted in published cross-thread attacks. The relevant research (e.g., the original academic paper from 2020) focuses on Skylake/Kaby Lake/Coffee Lake server cores with the Special Register Buffer used for write-combining store buffers.
- **Impact if exploited**: Cross-thread leakage of stale store buffer data between sibling threads. On a single-tenant host (jasperlake runs only the operator's LXCs), the attack surface is the operator's own processes.
- **Compensating controls already in place**:
  - Single-tenant physical host (no other users' code runs).
  - LXCs are not shared with untrusted parties; 110/120/101 all run operator workloads.
  - No cross-thread-sensitive workloads in LXCs (pihole is single-threaded; docker runs trusted containers).
  - Network is on a private LAN (10.1.1.0/24), with separate physical/management interfaces.

### Decision

**Accepted as residual risk.** Will revisit only if:
1. Intel ships a microcode update covering Jasper Lake for SRBDS (check `apt changelog intel-microcode` periodically), OR
2. A practical PoC targeting Atom parts is published, OR
3. The host begins running untrusted/multi-tenant workloads.

### How to re-check

```bash
ssh tiny@proxmox-ve 'cat /sys/devices/system/cpu/vulnerabilities/srbds'
```

Expected output: `Vulnerable: No microcode` (unchanged — this is the permanent state until/unless Intel ships a fix).

**Do not** report this as a security regression in future audits — it is the known, accepted state of the hardware.
