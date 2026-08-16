# Aries 28 — Control-Plane Node Setup (k3s + partitioned NVMe)

**Runbook for bringing up a k3s server node on a Raspberry Pi 5 with an NVMe SSD split into etcd + data partitions.**
Version 1.0 — July 2026 · Validated on a practice node (`aries-28-test`, Pi 5, k3s v1.36.2+k3s1)

> Scope: this is the **first server** procedure, prepared for a redundant control plane (embedded etcd via `--cluster-init`, which allows additional server nodes to join for quorum).
> Adding more servers (cp-2, cp-3) or agents (workers) is a follow-on doc; the token location is noted at the end.

---

## 0. Prerequisites & conventions

- Raspberry Pi 5 with NVMe HAT (Geekworm X1001) + NVMe SSD, assembled and detected.
- Raspberry Pi OS Lite 64-bit (or Ubuntu Server), freshly flashed, SSH enabled.
- **Decide the node's role-name before you start** — k3s takes the node name from the hostname *at install time*, and renaming after it joins etcd is painful. Use the fleet convention: `aries-cp-1`, `aries-cp-2`, `aries-cp-3` (control plane), `aries-st-1` (storage), `aries-gw` (gateway, not in k3s).
- All steps assume `sudo`.

Set the hostname first:
```bash
sudo hostnamectl set-hostname aries-cp-1     # adjust per node
```

---

## 1. Kernel boot parameters (cmdline.txt)

Two fixes go on the **same single line**, space-separated, **no newline** (a line break here breaks boot parsing).

File: `/boot/firmware/cmdline.txt` (older images: `/boot/cmdline.txt`)

Append to the end of the existing line:
```
cgroup_memory=1 cgroup_enable=memory nvme_core.default_ps_max_latency_us=0 pcie_aspm=off pcie_port_pm=off
```

Why each is needed:
- `cgroup_memory=1 cgroup_enable=memory` — Raspberry Pi OS ships with the memory cgroup **disabled**; Kubernetes requires it to enforce pod memory limits. Without it, k3s dies at startup with `failed to find memory cgroup (v2)`. **Every node needs this.**
- `nvme_core.default_ps_max_latency_us=0` — forbids the NVMe drive from entering deep power-save (APST) states. Budget drives (Vansuny/Fanxiang-tier) mishandle the wake handshake on the Pi 5 controller, producing `CSTS=0xffffffff` "controller is down" errors. **Storage nodes especially.**
- `pcie_aspm=off pcie_port_pm=off` — disables PCIe-link-level power management (the bus-side companion to the above).

Edit, then **reboot** (cgroup changes only take effect at boot):
```bash
sudo nano /boot/firmware/cmdline.txt
sudo reboot
```

> ⚠️ This file is unforgiving — a typo can prevent boot. Double-check it's still ONE line with a single space before each new parameter.

Optional (SD longevity on SD-booted nodes): install `log2ram` to keep logs in RAM.

---

## 2. Partition the NVMe (GPT: etcd + data)

**Survey first — never wipe the wrong device:**
```bash
lsblk -f
```
Expect `mmcblk0` = SD card (OS), `nvme0n1` = the SSD. Confirm before proceeding.

**Why two partitions:** the split provides **space and filesystem isolation, not I/O-performance isolation** — this distinction matters. etcd is latency-sensitive and performs constant small fsync writes; Longhorn/data performs bulk sequential writes. A separate partition guarantees etcd cannot be starved of capacity (bulk data growth or logs cannot fill etcd's space) and keeps the two filesystems independent, which makes it straightforward to relocate the data volume to a separate physical device in a later revision. It does **not** isolate I/O contention: both partitions share one NVMe controller, one command queue, one NAND, and the single PCIe lane, so if bulk I/O saturates the controller's queue depth, etcd's fsync latency can still spike regardless of the partition boundary. True performance isolation requires a separate physical device or cgroup-level (blkio) IOPS limits. The partition split is chosen here as the low-cost step that makes that later separation easy, not as a performance guarantee. etcd is small in practice (hundreds of MB); 8 GB is generous, so the split is deliberately lopsided: small etcd, large data.

```bash
# clear any remnants from earlier attempts
sudo wipefs -a /dev/nvme0n1

# GPT label + two partitions
sudo parted /dev/nvme0n1 --script mklabel gpt
sudo parted /dev/nvme0n1 --script mkpart etcd ext4 0% 8GB
sudo parted /dev/nvme0n1 --script mkpart data ext4 8GB 100%

# filesystems + labels (mount by label -> survives device renaming)
sudo mkfs.ext4 -L aries-etcd /dev/nvme0n1p1
sudo mkfs.ext4 -L aries-data /dev/nvme0n1p2
```

> **Storage node vs cp node:** on a pure control-plane 2 GB node you barely need the data partition — etcd is the point. On the 4 GB storage node the data partition is the large Longhorn/Nextcloud volume. Adjust the 8 GB split only if you have a reason; it's fine as-is for both.

> **Note for Longhorn:** Longhorn can take a mounted directory (what we do here) or a raw block device. If you later decide to give Longhorn the raw device, don't format the data partition. For this runbook we use a mounted directory at `/mnt/data`.

---

## 3. Mount points + fstab

etcd's default k3s location is `/var/lib/rancher/k3s/server/db` — we mount the etcd partition there so etcd lives on the SSD from the very first start.

```bash
sudo mkdir -p /var/lib/rancher/k3s/server/db /mnt/data

echo 'LABEL=aries-etcd /var/lib/rancher/k3s/server/db ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
echo 'LABEL=aries-data /mnt/data ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab

sudo systemctl daemon-reload     # systemd regenerates mount units from edited fstab
sudo mount -a
```
`noatime` cuts needless metadata writes — good habit on any node.

**Verify BEFORE installing k3s (critical ordering requirement):**
```bash
findmnt /var/lib/rancher/k3s/server/db     # must show nvme0n1p1
findmnt /mnt/data                          # must show nvme0n1p2
lsblk -f
```
If the etcd partition is **not** mounted here, k3s will write etcd onto the SD card and the mount will later hide it. Do not proceed until `findmnt` confirms the mount.

Troubleshooting:
- `special device LABEL=... does not exist` → label didn't set. Check `sudo blkid`; fix with `sudo e2label /dev/nvme0n1p1 aries-etcd`.
- fstab edited but "systemd still uses the old version" → run `sudo systemctl daemon-reload`, then `sudo mount -a`.
- Test `mount -a` immediately after editing fstab — a bad entry caught now is a typo; caught at next boot it can hang the boot.

---

## 4. Install k3s (first server, quorum-capable, embedded etcd)

```bash
curl -sfL https://get.k3s.io | sh -s - server --cluster-init --secrets-encryption
```

`--cluster-init` initializes **embedded etcd** (not the default SQLite). This is what makes the dedicated etcd partition meaningful and lets you add cp-2/cp-3 later without rebuilding — the single-server-now → HA-later path.

`--secrets-encryption` encrypts Secrets at rest in etcd. It belongs **at install time**; enabling it later is supported but costs a two-restart enable-and-rekey cycle across every server (§8). Without it, every Secret in the cluster is stored in etcd as base64 — encoding, not encryption — and is directly readable from the NVMe or from any etcd snapshot.

`--disable traefik` is optional if you plan to bring your own ingress via GitOps later. For a first node, leave defaults.

---

## 5. Verify

```bash
sudo systemctl status k3s
sudo k3s kubectl get nodes
sudo k3s kubectl get pods -A
```
Healthy target:
```
NAME         STATUS   ROLES                AGE   VERSION
aries-cp-1   Ready    control-plane,etcd   ...   v1.36.2+k3s1
```
- `Ready` isn't instant — the node registers immediately, then flips `NotReady → Ready` (~20–30 s) once flannel (CNI) and coredns are up.
- `ROLES` showing `control-plane,etcd` confirms embedded etcd is running.

**kubectl without sudo** (convenience):
```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config        # add to ~/.bashrc to persist
kubectl get nodes
```

---

## 6. Expanding the cluster later (reference)

Node-join token (needed for cp-2/cp-3 and workers):
```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```
- **Add another server (control-plane quorum):** on cp-2/cp-3, install with `server --server https://<cp-1-ip>:6443 --token <token> --secrets-encryption` (still on their own etcd partitions). The flag goes on every server (§8); a server started without it cannot read what the others wrote.
- **Add a worker (agent):** install with `agent --server https://<cp-1-ip>:6443 --token <token>`.
- HA needs **3 servers** for etcd quorum: 1 = SPOF, 2 = worse than 1, 3 = any single node can be pulled live.

---

## 7. Automate this (do it after the first hand-run)

Everything above is deterministic → it belongs in an Ansible **base role** so cp-2/cp-3/storage are a one-command apply, not a repeat:
- cmdline params (cgroup + NVMe) — universal, every node
- partition + label + fstab (role-conditional: storage gets large data, cp gets minimal)
- k3s install (server `--cluster-init` for first, `server --server` for HA joins, `agent` for workers)
- `--secrets-encryption` on every server (§8) — trivial as an install flag, awkward to retrofit, and therefore role-managed rather than per-node manual
- hostname per inventory
- kubeconfig fetch

Fleet mapping (from the main design doc): `aries-cp-1..3` = Pi 5 2 GB servers; `aries-st-1` = Pi 5 4 GB storage; `aries-gw` = Pi 4 gateway (not in k3s); `aries-face` = Pi 3A+ (LED/kiosk, not in k3s).

---

## 8. Secrets encryption at rest

Kubernetes Secrets are **base64-encoded, not encrypted**. On a k3s server with embedded etcd they live on the etcd partition (§2) in a form anyone with the disk can read. `--secrets-encryption` makes the API server encrypt them (AES-CBC) before they reach etcd, using a key in `/var/lib/rancher/k3s/server/cred/encryption-config.json`.

### Scope of protection

The flag name overstates its reach. What it covers:

- **Offline access to the data** — a stolen NVMe, an etcd snapshot copied elsewhere, a decommissioned disk leaving the premises. This is the case the flag genuinely addresses.

What it does not cover:

- **Callers holding `get secrets` RBAC.** The API server decrypts transparently; `kubectl get secret -o yaml` returns plaintext exactly as before.
- **Root on the server node.** The key resides on the same disk as the data it protects, so a whole-node compromise yields both halves.

The flag therefore hardens backups and retired disks. It is not a substitute for RBAC discipline, nor for keeping secret material out of the cluster in the first place.

### Enabling on an existing cluster

New builds set the flag at install (§4). Retrofitting takes **two restarts**, not one — `enable` only stages the change:

```bash
sudo k3s secrets-encrypt status        # Encryption Status: Disabled, no configuration file found
sudo k3s secrets-encrypt enable        # generates the key, stages the change
```

Add `--secrets-encryption` to the server's own arguments (`/etc/systemd/system/k3s.service` or `/etc/rancher/k3s/config.yaml`) so the flag survives the restart and every restart after it, then restart:

```bash
sudo systemctl restart k3s
sudo k3s secrets-encrypt status        # Encryption Status: Disabled / Current Rotation Stage: start
```

`Disabled` here is expected, not a failure. Nothing is encrypted yet, and existing Secrets are untouched. The rewrite is a second step, followed by a second restart:

```bash
sudo k3s secrets-encrypt rotate-keys   # rotates and reencrypts; ~5 secrets/second
sudo systemctl restart k3s             # same arguments as before
sudo k3s secrets-encrypt status        # Encryption Status: Enabled / Stage: reencrypt_finished
```

Stopping after `enable` is the common failure: the flag is set and the config file exists, so the change looks complete, while status still reads `Disabled` and every pre-existing Secret is still plaintext on disk. Encryption is only real once status reports `Enabled` and `reencrypt_finished`.

### Key rotation

Current k3s performs the prepare → rotate → reencrypt sequence in a single command, and a restart afterwards is part of the sequence:

```bash
sudo k3s secrets-encrypt rotate-keys
sudo systemctl restart k3s
sudo k3s secrets-encrypt status        # Stage: reencrypt_finished, one active key
```

Rotation is warranted on suspected key or node exposure, and after any recovery from a lost or restored disk. Note that this is the same command that completes the retrofit above — an unencrypted cluster is just the case where the old key does not exist yet.

### Key backup

Once Secrets are encrypted, `encryption-config.json` is the **only** means of reading an etcd snapshot. If it is lost, every encrypted Secret becomes unrecoverable and an etcd backup alone is worthless.

Storing the key alongside the etcd snapshots negates the protection, as a single compromised backup set then yields both halves. The key belongs somewhere the snapshots are not — a password manager or an offline copy. Whether a snapshot from the previous month is still decryptable is a reasonable check to include in any restore drill.

### HA considerations (Phase 3+)

With a single server, `enable` and `rotate-keys` are one command on one host. Once cp-2/cp-3 join (§6) the shape changes: pick **one** server to run the `secrets-encrypt` commands from, and after each phase — `enable`, then `rotate-keys` — restart **every** server before starting the next phase. A partial rollout leaves servers disagreeing on how to read etcd.

Restarts should be sequenced one host at a time to preserve etcd quorum. `secrets-encrypt status` reports `Server Encryption Hashes: All hashes match` once the fleet has converged; that line, not the restart finishing, is the signal that the phase is done.

### Related

This section covers Secrets at rest within the cluster. It does not address how secret material reaches the cluster: credentials created by hand via `kubectl create secret` exist only in etcd and are not reproducible from this repository. That is a separate, currently open concern.

---

## Appendix — full cmdline.txt parameter block

Append to the single existing line in `/boot/firmware/cmdline.txt`:
```
cgroup_memory=1 cgroup_enable=memory nvme_core.default_ps_max_latency_us=0 pcie_aspm=off pcie_port_pm=off
```
