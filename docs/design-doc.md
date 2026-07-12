# Project Aries 28 — Design Document

**A tower-format Raspberry Pi cluster: a mini private data center and a k3s learning platform.**
Version 0.5 — July 2026

---

## 1. Mission & Non-Goals

**Mission:** Build a 7-node (expandable to 10) ARM Linux cluster in a desktop-tower-style enclosure that serves as (a) a private cloud (storage + hosting), (b) a hands-on Kubernetes/infrastructure learning platform, and (c) a display piece with live status visualization and a front-panel dashboard screen.

**Non-goals:** Production reliability guarantees, performance competitiveness with x86, minimizing cost at the expense of learnability. This is a toy with a curriculum.

**Cost:** full from-scratch replication is roughly **$800–$1,000**, and varies heavily with current market pricing — this specification was priced during a period of elevated RAM/storage prices (see the BOM in §7). Existing hardware reduces the total; the from-scratch figure is the reference for a complete build.

**Lessons embedded in the design (the real deliverables):**
1. k3s from single-server to a redundant control plane (embedded etcd, quorum) — node-level fault tolerance; the migration itself is a lesson
2. Distributed storage (Longhorn) and what happens when a node dies
3. Routing/NAT/DHCP/DNS (the gateway is a mini-course in networking)
4. Infrastructure as Code + GitOps (the cluster state lives in git)
5. Power distribution, fusing, and voltage-drop calibration (real electrical design)
6. Node lifecycle: provisioning, draining, replacing, recovering
7. Resource scheduling on heterogeneous nodes (1GB/2GB/4GB mix makes requests/limits real)
8. Backup discipline: one storage node = one replica = off-tower backup from day one (Restic)
9. Power sequencing: orderly fleet shutdown via self-holding soft-power circuit (Phase 6)

---

## 2. Architecture Overview

### 2.1 Logical topology

```
Internet / Home LAN
        │
   [WAN keystone on panel]
        │
   ┌────┴─────┐
   │ GATEWAY  │  aries-gw   (router, DHCP, DNS, WireGuard — NOT in k3s)
   └────┬─────┘
        │ 10.28.0.0/24 (private cluster subnet)
   ┌────┴───────────────────────────────────┐
   │      8-port managed GbE switch         │
   └─┬────┬────┬────┬────┬────┬─────────────┘
     │    │    │    │    │    │
   cp-1 cp-2 cp-3 wk-1 st-1 face
   └─ servers+workers ─┘      └ LED/kiosk, outside k3s
```

- **Subnet:** `10.28.0.0/24`. Gateway static `.1`; control-plane reservations `.11–.13`; `.100+` dynamic pool for all other nodes and maintenance devices (agents named via `*.aries.lan` DNS). See `network-design.md` §4.
- **Naming:** `aries-gw`, `aries-cp-1..3`, `aries-wk-*`, `aries-st-*`, `aries-face`.
- **Ingress:** all external traffic via gateway; port-forward or WireGuard only. Cluster invisible to home LAN by default.
- **DNS:** dnsmasq on the gateway resolves internal names on the cluster subnet — `*.aries.lan` (nodes by hostname; services via the ingress). Home-LAN and internet access use separate naming scopes (`*.athome.example.com` and the public domain) — see `dns-and-exposure.md` §1.1.
- **No WiFi anywhere inside the box.** The face node uses a USB-ethernet adapter.
- **VLAN plan (managed switch, TL-SG108E):** VLAN 10 cluster, VLAN 20 face/kiosk, VLAN 99 MAINT; gateway port trunked, router-on-a-stick between them. Port mirroring to MAINT = live Wireshark classroom. Switch management IP moved from factory default into `10.28.0.0/24` at first boot.

### 2.2 Fleet

| Node | Board | Role | RAM need | Storage |
|---|---|---|---|---|
| aries-gw | Pi 4 1GB | Router, DHCP, DNS, WireGuard, netboot (Ph.4) | ~512MB | microSD |
| aries-cp-1..3 | Pi 5 2GB | k3s server **and** worker (servers schedule pods) | ~2GB | microSD |
| aries-st-1 | **Pi 5 4GB** | k3s agent, storage-labeled; Longhorn, Nextcloud/MinIO | 4GB | **NVMe 256GB** (1TB-class upgrade later) |
| aries-wk-1 | Pi 4 1GB *(pending autopsy)* | light worker | 1GB | microSD |
| aries-face | Pi 3A+ + USB-ethernet | LED daemon + 7" kiosk dashboard — outside k3s | 512MB | microSD |
| bays 8–10 | empty, engraved covers | expansion | — | — |

Why the face node is outside the cluster: the monitor must survive what it monitors. It polls the k3s API over wired ethernet (USB 2.0 adapter, ~300Mbps — irrelevant for API polls and pixels).

### 2.3 Control plane strategy

k3s servers run workloads by default — there are no dedicated "dead weight" masters. The HA tax is only ~600–900MB of RAM per server for k3s + etcd.

**Phase 1:** single server (cp-1) + agents. **Phase 3+:** migrate to 3-server embedded-etcd HA (k3s supports `--cluster-init` migration). etcd requires majority quorum: 1 server = SPOF, 2 = worse than 1, 3 = any single node can be pulled live. The "yank a control-plane carrier while Nextcloud keeps serving" demo is the graduation exam.

---

## 3. Physical Design

### 3.1 Frame — 2020 aluminum extrusion

Stock: **10× 600mm black anodized 2020** (VEVOR kit, ~$42).

Cut plan (minimizes cuts, keeps compactness):
- **4× verticals @ 450mm** (cut 4 pieces; 150mm offcuts become internal rail supports)
- **4× width horizontals @ 250mm** and **4× depth horizontals @ 350mm** (cut 4 pieces into 250+350 each — zero waste)
- **2 spare full-length pieces** for mid-height rack supports / shelf supports / mistakes

Resulting envelope ≈ **450 (H) × 290 (W) × 390 (D) mm external** (250/350 inner rails + 2020 profile) — a compact mid-tower, roughly half the volume of the 600mm no-cut option. Printed corner brackets or cast corner cubes; T-nuts throughout.

Cutting notes: miter saw with non-ferrous blade or fine-tooth hacksaw + miter box; deburr ends; square cuts matter for corner brackets.

Three zones, bottom to top:
1. **Power bay** (bottom): LRS-200-5, AC inlet, 12-circuit fuse block, ground bus. Heavy stuff low.
2. **Node bays** (middle): carrier bays in rod-and-bead rack cartridges (see `rack-design.md`) at **two pitches** — a **30 mm compute pitch** for bare/diskless nodes (most of the fleet) and a **42 mm extended pitch** for nodes with a vertical accessory. The storage carrier (Pi 5 + top-mounted X1001 NVMe adapter) lives in a 42 mm extended bay. See `architecture.md` §6 for the two-pitch rationale.
3. **Network shelf** (top): 8-port managed switch (second 8-port cascades here at expansion), patch cables dropping to carriers.

Front face reserves a cutout for the 7" display (portrait or landscape — decide in CAD before cutting acrylic). Panel/airflow/thermal/mounting details in §3.3.

### 3.2 Carrier specification (the standard interface)

**Standardize the carrier, not the board.** Fixed spec: outer geometry, rack-interface (rod/bead) engagement, XT30 pigtail position, handle. Per-board variants change only the mounting-hole pattern:
- `carrier-rpi-b.*` — Pi 3B / 4B / 5 (shared 85×56mm footprint, M2.5 holes on 58×49mm — one carrier fits all three B-series generations)
- `carrier-rpi-a.*` — Pi 3A+ (65×56mm, same hole spacing, shorter)
- extensible: `carrier-<board>.*` for any additional board type, added as needed

File naming and per-board detail are authoritative in [`hardware/carrier/`](../hardware/carrier/); see also `rack-design.md` for the mounting mechanism.

Details: PETG body, M3/M2.5 brass inserts, XT30 keyed power pigtail, labeled slim patch cable, node name laser-engraved on handle. Blank engraved covers for empty bays.

**Hot-surgery procedure:** `kubectl drain <node> --ignore-daemonsets` → LED trace amber → unplug XT30 + ethernet → pull carrier. Reverse; `kubectl uncordon`.

### 3.3 Panels & enclosure styling (optional aesthetic layer)

The panel and lighting choices below are one implementation's aesthetic; they are **optional** and not required for a functioning cluster. A build may use plain panels, omit the smoked/clear treatment, or skip lighting entirely without affecting the compute, power, or network design. The functional requirements are only that panels provide the specified openings and that the enclosure allows airflow; everything else in this section is presentation.

**Show faces vs. hide faces.** The enclosure has three display faces and two solid faces — the aesthetic showcases *both* the compute and the power wiring, hiding only the truly-boring cable back and the never-seen bottom.

| Face | Panel | Rationale |
|---|---|---|
| Front | smoked acrylic | Hero face: boards, LEDs, swing carriers, engraved Aries glyph + radiating traces, edge-lit |
| Left (access) | smoked acrylic | Removable/openable — service side; shows the rack |
| Right (power bay) | smoked acrylic | **Power wiring is a feature, not a thing to hide** — exposed Meanwell, dressed red/black leads, fuse block, IEC inlet run, underlit warm amber |
| Back | solid black 3mm | Cable back-of-house; dark backdrop for LEDs |
| Bottom | solid black 3mm | Never seen; structural |
| Top | clear or black | Judgment call — clear to see down into the rack, or black with the exhaust-fan cutout |

**Smoked over clear** on the show faces: reads as deliberate dark-tech, hides minor cable imperfection, and makes LEDs pop against a near-black background (unlit acrylic ≈ black, lit elements glow). Translucent *colored* panels are avoided — they muddy the status-LED colors (a blue wall makes green "healthy" LEDs read wrong); color comes from the LEDs, not the walls.

**The power bay is a featured display.** Because the right panel is transparent: dress the DC wiring as display wiring (sleeved red +5V / black ground in clean parallel runs, held by a printed comb), keep the AC side heatshrinked and tidy (it's now *visible*, so sloppy mains wiring would be on show), and underlight the bay (amber static, or PSU-state-driven). The frame-bond ground lead (§4) becomes a visible tidy green wire to a labeled star point — reads as "the builder knows what they're doing." The inlet→fuse→PSU run is a deliberate visual line the eye follows — the opposite of a generic sealed-brick PC PSU.

**Panel material & mounting — 3mm throughout, clip-mounted (not slotted).**
- Use **3mm acrylic everywhere** (widely available, laser-cuttable). Don't fight the 3mm-in-6mm-slot gap: **surface-mount panels onto the frame face with printed PETG retainer clips** that T-nut into the extrusion slot, rather than sliding acrylic into the slot. 3mm is ideal for this, panels sit proud/floating (intentional look), and clips make panels **removable one-handed** — essential on a machine under constant iteration.
- Alternative for an inset look: printed PETG adapter frames (6mm outer to fill the slot, lip + foam tape holding the 3mm pane).
- Gasket/weatherstrip tape (≈1.5mm each side) is the quick legitimate fallback to snug 3mm in a slot and damp fan vibration.
- **At least the front (or left) panel must be removable or hinged** (magnets or printed hinge), so a board can be reached without disassembling the enclosure.
- Black 3mm → back and bottom; smoked 3mm → front, left, and right show faces (cut to size).

**Front panel engraving (brand mark).** Large Aries ram glyph (♈, the validated SVG from the carrier work) engraved on the **back face** of the smoked front panel, centered, with cyan circuit-traces radiating outward; LED strip along the panel edge edge-lights the engraving so it glows while the rest stays dark. Motif repeats at three scales: big glyph on the front (logo) · astrometric Aries constellation as a secondary detail (signature) · tiny ram per carrier (texture). 7" display integrated into the trace artwork.

- **Connection panel (rear, laser-cut):** IEC C14 inlet w/ switch+fuse (only power entry), RJ45 keystone **WAN**, RJ45 keystone **MAINT** (direct switch port, bypasses gateway), panel USB-C (gateway serial console).

### 3.3.1 Airflow & thermal

- **Intake:** back-left wall CNC/laser-cut with an air-inlet pattern (low, cool-air entry).
- **Exhaust:** 140mm A-RGB fan on **top or right side**, with matching vent holes, blowing hot air out. Vertical boards + rising heat = natural chimney the fan assists.
- **Fan:** ARCTIC P14 Pro A-RGB (140mm, 12V PWM motor + 5V ARGB signal). PWM lets the face node throttle by temperature; ARGB ties into the LED daemon (fan color = cluster state). 12V from a small 5V→12V boost converter (XL6019) off the main rail; ARGB data is the native 5V digital signal.
- **Acrylic thermal limits:** cast acrylic softens ~100–110°C and deforms under load well below that (~80°C practical ceiling). With the fan running, internal air sits ~35–45°C, so under normal operation the boards are the limiting factor: if they are cool enough to run, the acrylic is well within its margin (the Pi 5 throttles ~80–85°C at the chip, long before circulating air threatens the panels). **This holds only while airflow is maintained.** A fan failure removes that assumption — a stagnant hot pocket can form near a carrier, and localized air near a powered board with a heatsink can reach the point where 3mm acrylic sags under the heatsink's weight even though the silicon is still within limits. A fan-failure alert (via the LED/monitoring system) and conservative bay spacing mitigate this; the "boards as thermal canary" rule is a normal-operation guideline, not a fan-failure guarantee.
- **Power-bay thermal rules** (the one hotspot — the PSU is the only real heat source, ~45–55°C case surface at ~80W): keep a **15–20mm air gap** between the Meanwell and any acrylic; **vent the power bay** (slots low + high, or the diagonal-grid vent motif scaled up) so heat rises past the PSU rather than pooling against a panel; don't mount the PSU flush against an acrylic panel.
- **Shed caveat (LA-area, un-A/C):** summer ambient can hit 40°C+, raising every component's baseline. The cluster throttles before the acrylic is threatened, so the boards remain the limiting factor — but plan the vent/fan generously for hot days.

### 3.3.2 Board & PSU mounting

- **Boards sit on 3mm spacers** cut from black 3mm acrylic, on top of the carriers (lifts the board off the carrier for airflow and connector clearance). Spacers cut on the laser from the same black stock as the solid panels.
- **PSU on spacers** (standoffs) rather than flush — a small air gap under the Meanwell for convection and to keep conducted heat out of the bottom panel. (Mounting the PSU directly to the aluminum frame as a heatsink is thermally ideal but mechanically fiddly; spacers are the pragmatic choice — overengineering the frame mount isn't worth it.)

### 3.3.3 Fabrication: buy vs. print, and materials

- **Buy (must be strong + square):** 8× metal corner brackets or cast corner connectors (~$15) + a bag of 50+ M5 T-nuts and button-head screws (~$10). Printed corners flex and let the frame rack out of square; metal holds 90°. Frame squareness also depends on accurate cuts (miter saw, non-ferrous blade).
- **Print in PETG (custom-shaped, load-bearing, or near heat):** carriers, panel retainer clips, cable combs, LED/fan mounts, connection-panel bezel, feet, PSU spacers, vent bezels.
- **Why PETG not PLA:** PLA softens ~50–60°C (creeps near the PSU / on a hot shed day) and is brittle (latch fingers crack). PETG handles ~80°C and flexes before failing — required for the latch-flex features and anything near the power bay. Print PETG on the K1 (handles it easily); PLA is fine only for cheap test-fit mockups before committing the real PETG part.
- **PETG first-time settings (starting point):** nozzle 230–250°C, bed 70–85°C, slower (~40–50mm/s), higher retraction than PLA to fight stringing; use a release barrier on the bed (PETG sticks aggressively). Expect some stringing — tune retraction, heat-gun residual wisps.

### 3.4 Display & LED status subsystem

Driven by **aries-face** (Pi 3A+): DSI → 7" display; USB serial → Arduino Nano → WS2812B status LEDs (the Nano is 5V-native, so no 74AHCT125 level shifter — see `lighting-design.md` §3.2); USB → ethernet.

- **7" kiosk:** Netdata (or custom dashboard) full-screen — the tower's face.
- **LED daemon** (Python, in repo): polls k3s API every ~5s.
  - Cyan: node Ready · Amber: cordoned/draining · Red pulse: NotReady · Orange sweep: control plane degraded
- **Software power cap (mandatory):** `MAX_BRIGHTNESS = 0.5` constant in the daemon. This is a fuse implemented in software — see §4.
- **Phase 5 bonus:** 8×32 LED matrix as per-node CPU columns fed by metrics-server. Front panel gets mounting bosses now, populate later.

---

## 4. Power Design

### 4.1 Supply & budget

**PSU: Meanwell LRS-200-5 (5V / 40A / 200W), ~$33.**

Worst-case simultaneous-peak budget — a hypothetical fully-populated 10-bay endgame (mostly Pi 5s, two storage nodes), used to size the 200W PSU with headroom. This is a ceiling, **not** the current fleet (§2.2):

| Load | Peak | Watts |
|---|---|---|
| 7× Pi 5 headless under stress | ~2.4A ea | 84 |
| 2× storage nodes (Pi 5 + NVMe write spike ~8W) | | 40 |
| Pi 3A+ face node | ~1A | 5 |
| 7" display | ~0.8A | 4 |
| LEDs uncapped (~200× WS2812B full white) | 60mA/LED | 60 |
| 1× 140mm fan (ARCTIC P14 Pro A-RGB) | ~0.2A @12V | 3 |
| **Theoretical max** | | **~196** |

With the 50% LED brightness cap the realistic ceiling is ~170W. The current fleet (§2.2) peaks around ~100W. Switch runs on its own supply.

### 4.2 Distribution

At 5V, worst-case full-build current approaches ~40A (≈197W ÷ 5V), so voltage drop across the distribution is the central design concern — the wiring, calibration, and per-circuit fusing below all address it.

- **PSU → fuse block feed:** 10AWG (or doubled 12AWG). This run is short (roughly 6 inches), which keeps its drop small; 8AWG can be used for additional margin if desired, though over such a short run the benefit is marginal. Same gauge for the ground return to the bus bar.
- **Fuse block:** a 12-circuit automotive blade panel with integrated negative bus. Automotive blade fuses are rated to 32V, which is the maximum voltage they can safely *interrupt*; the trip behavior is current-based and unaffected by operating at 5V. These fuses protect against **sustained overcurrent and fire** — their role here — and are not intended to interrupt sub-millisecond board-level faults; on-board protection and short wire runs cover that domain.
  - Worker/cp/gateway circuits: **4A blade fuses**
  - Storage-node circuits: **5A** (Pi 5 + NVMe peaks ~4A)
  - Face node + LED circuit: 5A
- **Carrier leads:** 18AWG silicone, short as practical, XT30 terminated.
- **Voltage calibration:** with the fleet under `stress-ng` and LEDs at capped maximum, measure voltage at a carrier XT30 and trim the PSU V-ADJ pot to compensate distribution drop (Pi boards warn below ~4.8V). **Verify at both load extremes:** trimming the loaded voltage up reduces the drop margin at idle, so the idle carrier voltage rises — confirm it stays within the Pi's 5V ±5% window (4.75–5.25V) at both idle and full load rather than over-trimming for the loaded case alone. Perform this once at commissioning and after any wiring change. Correct calibration is the difference between stable operation and intermittent SD/undervoltage faults.
- **Pi 5 note:** on 5V fused rails (no PD negotiation) the Pi 5 caps USB port output — irrelevant headless. Add `usb_max_current_enable=1` only if a USB device is attached.
- **AC side:** inlet → fuse → PSU only; heatshrink, strain relief, physical separation from the DC bay. If unsure, use a pre-wired fused IEC module.
- **Bench station:** a low-power multi-port USB supply (inadequate for the assembled tower) is sufficient for flashing and first-boot on the bench.

---

### 4.3 Storage hardware (st-1)

- **Adapter:** Geekworm X1001 (PCIe FPC → M.2 Key-M, supports 2280), top-mount.
- **Drive:** Vansuny 256GB NVMe Gen3 (~$0.19/GB — best per-GB available mid-shortage). Right-sized deliberately: 1TB-class upgrade deferred to post-NAND-recovery; Longhorn replica rebuild onto the new disk *is* the migration path (and a lesson).
- **Config:** `dtparam=pciex1_gen=3` (Pi 5 defaults to Gen2; Gen3 is unofficial but stable). The single PCIe lane caps ~800MB/s — never pay for drive speed on this platform.
- **M.2 SATA drives (B+M key) are incompatible** — the Pi 5 FPC speaks PCIe only. NVMe or nothing.
- **Backup rule (lesson #8):** until st-2 exists, st-1 is a single point of truth. Restic from day one — external USB drive on the gateway or a B2/S3 bucket. A toy cluster is allowed to lose uptime, never family data.

### 4.4 Soft power — self-holding circuit (Phase 6, lesson #9)

Single front-panel control for orderly fleet shutdown. No battery, no always-on supervisor.

**Topology:** mains-rated **DPST toggle** and an **SSR** wired *in parallel* on the AC path between the fused IEC inlet and the PSU. Either closed = PSU energized.

- **Pole 1 (AC):** the toggle carries the load during normal operation — SSR state is irrelevant while running, so SSR/controller failure can never cut a live cluster.
- **Pole 2 (sense):** isolated low-voltage line to a face-node GPIO — how the node learns the human flipped the switch. Flipping back on mid-sequence aborts the shutdown.
- **SSR control:** face-node GPIO drives the SSR input directly (3–5V, no driver circuit), pull-down on the line, energized early in face-node boot and held all session. When the face node halts, the GPIO falls, the SSR opens — **the node's death is the off signal.** Choose a GPIO that stays low during boot (no relay chatter).

**Shutdown sequence:** toggle off → sense GPIO drops → display: SHUTDOWN SEQUENCE INITIATED, LED panel winks nodes out one by one → drain + `shutdown -h` in reverse dependency order (workers → storage → cp → gateway) → face node watches ethernet links go dark → halts itself → GPIO falls → SSR opens → silence.

**Power hierarchy:** toggle = soft off · IEC rocker = hard kill (upstream of everything).
**Known edge case:** face carrier pulled or face node down → soft-off silently degrades to hard-off (SSR already open; toggle-off cuts instantly). LED panel must show a warning state whenever the face node is absent.
**Day-one accommodations:** DPST toggle + SSR footprint in the power bay; one fuse-block circuit reserved; note that a halted Pi still draws power — `shutdown -h` makes filesystems safe but only the SSR actually de-energizes the tower.

---

## 5. Software Stack

The software layer, top to bottom. Everything non-physical is captured as code (§5.1).

| Layer | Choice | Notes |
|---|---|---|
| OS | Raspberry Pi OS Lite 64-bit (or Ubuntu Server) | One image, preconfigured via Pi Imager / cloud-init |
| Provisioning | **Ansible** | Roles: base, gateway, k3s_server, k3s_agent, face |
| Kubernetes | **k3s** — Phase 1 single server → Phase 3 HA (3 servers, embedded etcd) | servers also run workloads |
| GitOps | **Flux** | `git push` = deploy |
| Storage | **Longhorn** | storage nodes labeled; replicas ≥2 once st-2 exists |
| Private cloud | Nextcloud or Immich, MinIO (S3) | heavy pods pinned to st-1 |
| Monitoring | **metrics-server** (~50MB) + **Netdata** on kiosk | VictoriaMetrics later *if* historical graphs are wanted; full Prometheus only if an 8GB node appears |
| Access | WireGuard on gateway | private cloud from anywhere, zero exposed ports |

Heterogeneous RAM (1/2/4GB) is a feature: every workload gets explicit resource requests/limits, and the scheduler's choices become observable on the LED panel.

### 5.1 Configuration as Code

Everything non-physical is a file in git: Ansible playbooks/inventory, k3s bootstrap, Flux-managed manifests, LED daemon + systemd unit, dnsmasq/WireGuard templates.

**Acceptance test:** reflash any node's SD, boot, run one playbook → node rejoins with zero manual steps. If not, something escaped the repo.

---

## 6. Repository Layout (`aries-28`)

```
aries-28/
├── README.md               # overview, philosophy, repo map
├── docs/
│   ├── architecture.md         # containment hierarchy (start here)
│   ├── design-doc.md           # this file — physical, power, BOM (§7), phases, SPOFs
│   ├── network-design.md       # topology, gateway, VLANs, switching
│   ├── dns-and-exposure.md     # naming scopes, DNS, ingress, TLS
│   ├── rack-design.md          # rack & carrier mounting mechanism
│   ├── lighting-design.md      # optional two-tier lighting
│   ├── node-setup.md           # k3s + partitioned-NVMe runbook
│   ├── diagrams/               # Graphviz source + render
│   └── images/                 # renders (build-log photos later)
├── hardware/                   # fabrication files, organized BY PART, not by format
│   ├── README.md                   # parts index + fabrication legend
│   └── <part>/                     # carrier, rack, frame, panels, spacer, power-bay,
│                                   #   switch-mount, cable-brace, connection-panel —
│                                   #   each: its own README + all format options
├── kubernetes/                 # cluster manifests (generic example included)
├── ansible/                    # node provisioning (IaC) — placeholder
├── LICENSE                     # MIT (code) + CC-BY-SA 4.0 (hardware/docs)
└── .gitignore
```

(BOM and power live in this document — §7 and §4 — not in separate files. The
LED daemon and Ansible roles are described in the docs but not yet committed.)

---

## 7. Bill of Materials — full cost (assuming nothing owned)

Prices as of July 2026, during the DRAM shortage. A replication should expect these figures rather than pre-shortage ones.

| Item | Qty | Est. |
|---|---|---|
| Raspberry Pi 5 2GB (cp-1..3) | 3 | $180 |
| Raspberry Pi 5 4GB (st-1) | 1 | $110 |
| Raspberry Pi 4 1GB (gateway, wk-1) | 2 | $70 |
| Raspberry Pi 3A+ (face node) | 1 | $25 |
| Official 7" Touch Display 2 | 1 | $60 |
| USB3-to-GbE adapter (RTL8152/AX88179) | 1 | $10 |
| Geekworm X1001 M.2 adapter + Vansuny 256GB NVMe Gen3 | 1 | $63* |
| 8-port GbE **managed** switch (TP-Link TL-SG108E) | 1 | $28 |
| DPST mains toggle + SSR (Phase 6 soft power) | — | $15 |
| Meanwell LRS-200-5 | 1 | $33 |
| 12-circuit automotive blade fuse block w/ neg. bus | 1 | $15 |
| 2020 extrusion kit 10× 600mm black (VEVOR) | 1 | $42 |
| Blade fuses, XT30 pairs, 18AWG + 10AWG wire | — | $22 |
| microSD A2 32GB | 6 | $36 |
| Acrylic (black + smoked) | — | $25 |
| WS2812B addressable strip + Arduino Nano LED driver (no level shifter) | — | $14 |
| 140mm ARCTIC P14 Pro A-RGB fan + filter | 1 | $14 |
| Keystones, fused IEC inlet, patch cables | — | $18 |
| **Total (full replication, approximate)** | | **≈ $800** |

*Line items above are representative prices during the 2026 shortage and sum to roughly $800; realistic all-in cost including fabrication consumables, fasteners, and market variance ranges to about $1,000. Treat the total as a ballpark, not a fixed figure — component prices (boards, storage especially) move significantly.

*Right-sized into the NAND shortage (NAND ~8.5× mid-2025 spot prices; Q1 2026 street prices roughly doubled). 256GB covers phase-one Longhorn + Nextcloud; the 1TB-class upgrade waits for post-2027 recovery and rides the X1001 unchanged.

**Expansion (not in total):** second 8-port switch ~$21 cascaded when bays 8–10 populate (one uplink port lost per switch, 14 usable). 16-port switches carry an SMB-segment premium (~$60–80) that two 8-ports avoid.

**Reducing cost:** existing hardware can substantially lower the from-scratch total — any boards, storage, display, or supplies already on hand come off the top. The table prices a complete build from nothing.

Context for readers: this BOM is priced during the 2026 DRAM shortage, when 4GB+ boards roughly doubled. The architecture deliberately concentrates RAM in one storage node and right-sizes everything else to the price-protected 1–2GB tier; empty bays are a bet on post-2027 normalization.

---

## 8. Build Phases

1. **Bench cluster (now — boards in transit):** repo skeleton, Ansible base role, k3s single-server on any spare board via the bench USB supply. *Prove software before cutting metal.*
2. **Frame & power:** cut extrusion per §3.1, power bay, fused distribution. Load-test: full fleet `stress-ng`, calibrate V-ADJ to 5.1V at the carriers.
3. **Full integration:** all carriers racked, gateway routing live, switch in, panels cut. **Control-plane quorum:** cp-2/cp-3 join, single-node kill-test.
4. **Cloud layer:** Longhorn, Nextcloud/MinIO, WireGuard, Flux takeover. Stretch: Pi-native netboot from gateway (kills SD dependence for workers).
5. **Light show:** LED daemon v1 (status), 7" kiosk, then the CPU-matrix bonus.
6. **Soft power:** DPST toggle + SSR self-holding circuit, shutdown choreography on display + LEDs, abort-on-retoggle. (§4.4)

Each phase ends with a commit and a build-log entry. Ship the log entries.

---

## 9. Failure & Recovery Plan

### 9.1 Single points of failure and scope of availability

This is a single-tower system. It provides **control-plane redundancy as a learning exercise**, not end-to-end high availability. Several components are acknowledged single points of failure; the design does not attempt to eliminate them, because doing so is out of scope for a one-box build and the tradeoff is accepted:

- **The switch.** All nodes connect through one switch. A switch failure takes the entire cluster offline at once, regardless of control-plane redundancy. HA compute behind a non-redundant switch is not end-to-end HA.
- **The gateway.** The gateway provides routing, DHCP, and DNS for the internal network. Its failure breaks external access and internal name resolution (DHCP reservations keep existing node IPs stable through a gateway outage, but new leases and DNS stop). The cluster continues to run internally, but the system as a whole is degraded.
- **The PSU.** A single supply feeds everything; its failure stops the whole tower.

The control-plane quorum (three server nodes with embedded etcd) protects against the loss of a single *node*, which is a genuine and useful property to build and test. It does not make the tower as a whole highly available. This is the correct scope for a mini private data center: a single site that can go down, built to learn the mechanisms that larger multi-site systems use — not a distributed, multi-location production system.

### 9.2 Component failure behavior

- **Any single node dies (post-Phase 3):** the cluster continues; workloads reschedule. Pull carrier, reflash, Ansible, rejoin.
- **Gateway dies:** the cluster runs internally; external access and DNS stop (SPOF, §9.1). Reflash + `gateway.yml`; a spare flashed SD kept inside the case shortens recovery.
- **Switch dies:** entire cluster offline until replaced (SPOF, §9.1). Identical spare switch shortens recovery.
- **Face node dies:** cluster unaffected; the status display and LEDs stop, and soft-off degrades to hard-off (toggle-off cuts power directly). A LED warning state covers this.
- **PSU dies:** everything stops; data is safe if storage replicas ≥ 2. Replacement is four screws.
- **LED daemon bug sets full brightness:** the brightness cap holds draw to ~30W; the fuse is the hardware backstop behind the software cap.
- **Pi 4 boards found to be 2/4 GB on inspection:** promote to workers/storage; BOM adjusts accordingly.
