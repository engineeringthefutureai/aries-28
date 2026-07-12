# Aries 28 — Naming, DNS & Service Exposure

**How traffic finds a service — from a browser tab to a pod, inside the house and from the internet.**
Companion to the network design doc. Version 1.0 — July 2026

> Covers the path a request takes to reach a service, how service addressing changes with an ingress controller, and how names resolve differently for internal versus external clients. See the network design doc for the underlying physical topology.

---

## 1. The core model — two hops, one front door

Every request to a hosted service takes the same path:

```
name  →  gateway (reverse proxy)  →  cluster ingress  →  Service  →  pod
```

- **DNS resolves a service name to the GATEWAY's IP** — never to a node, never to the control plane, never to a pod. The gateway is the single front door.
- **The gateway proxy forwards** all web traffic to the cluster's **ingress controller** (one static rule — see §3).
- **The ingress controller routes by hostname** (`Host:` header) to the right Service.
- **The Service load-balances** across the pods backing that app (kube-proxy).

The control plane (API server, etcd) is **not** in this path — user traffic never touches it. It only serves the Kubernetes API (used by kubectl and the LED daemon).

### 1.1 Three naming scopes

A name resolves differently depending on where the client sits, and the three scopes use **three distinct domains** so they never overlap — a given name means exactly one thing:

| Scope | Domain | Resolver | Resolves to | TLS | Reachable from |
|---|---|---|---|---|---|
| **On-subnet** | `*.aries.lan` | dnsmasq on the gateway | internal addresses on `10.28.0.0/24` (nodes directly; services via the ingress) | none — internal only | inside the Aries subnet (a node, or a laptop on the MAINT port) |
| **Home LAN** | `*.athome.example.com` | public DNS, or a local resolver (§6) | the gateway's home-LAN IP → reverse proxy | real, via DNS-01 (§7) | any device on the home LAN |
| **Internet** | `*.example.com` | public DNS | Cloudflare tunnel → gateway (§8) | real, via Cloudflare | anywhere |

Access narrows as the client moves outward from the box:

- **On the internal subnet** — direct access to every node and service by its `*.aries.lan` name.
- **From the home LAN** — no direct route to nodes; a node is reached only by jumping through the gateway **bastion** (`ssh -J`, network-design §7.1), and a service only through the gateway **reverse proxy** at `*.athome.example.com`.
- **From the internet** — no node access at all; only the reverse proxy is exposed, at `*.example.com` through the Cloudflare tunnel.

The rest of this document details the outer two scopes — §5–7 the home-LAN (`athome`) scope, §8 the internet scope. The innermost `*.aries.lan` scope is served entirely by dnsmasq on the gateway (design-doc §2.1) and needs no public DNS.

---

## 2. Locating a service: by port, then by name

The ingress controller changes how a service is addressed — but naming and routing are two separate layers, and it is worth keeping them distinct.

**NodePort — address is `node-IP : port`, unnamed.** A `Service` of type `NodePort` exposes an application on a port on every node. Unless the port is explicitly pinned, it is auto-assigned from the 30000–32767 range, so a service is reached at, for example, `10.28.0.11:31847`. There is no name involved: a client must know a node's IP and the specific assigned port, and with several services the ports are opaque (`10.28.0.11:31847`, `10.28.0.11:30225` — with nothing indicating which is which). Ports are per-service and must be tracked individually.

**Ingress — routing by hostname on ports 80/443.** An ingress controller exposes all applications on the standard web ports and distinguishes them by the `Host:` header of the request. A request for `nextcloud.<domain>` and one for `grafana.<domain>`, both arriving on 443, are routed to their respective backends by name. Applications no longer carry individual ports.

**Ingress routes by name; it does not create names.** This is the key distinction. The ingress controller *matches* on a hostname, but something external must first *resolve* that hostname to the ingress's address. Ingress is routing, not naming. `nextcloud.<domain>` only reaches the ingress once DNS (or a hosts file, or the wildcard record in §5) points that name at the gateway/ingress. Registering the name is a separate step, described in §5–6; ingress supplies only the per-hostname routing once the request arrives.

Because the resolution mechanism is separable, the ingress layer can be tested in isolation before the gateway, reverse proxy, and DNS exist: a single hosts-file entry (§6.6) pointing a name directly at the ingress confirms that hostname routing works on a minimal single-node cluster. The gateway forward and wildcard DNS are then added on top of a component already known to work — the incremental approach applied to the network stack.

So the progression is: NodePort gives an unnamed `node-IP:port`; ingress consolidates everything onto 80/443 and routes by hostname; and DNS (§5–6) supplies the hostnames that make routing usable.

---

## 3. The gateway proxy holds a single static rule

The gateway's reverse proxy is configured once, with one rule:

> Forward all inbound HTTP/HTTPS to the cluster ingress.

It is not modified when services are added or removed. Per-service routing is handled **inside the cluster** by the ingress controller, whose configuration is supplied by each application's own manifest (§4).

This reflects a division of responsibility: the network edge (the gateway forward) is set up once at the infrastructure level and remains constant, while per-service routing is declared in the application manifest alongside the service itself. Adding a service therefore does not touch the gateway configuration.

---

## 4. Deploying a service — a single declarative step

With an ingress controller and wildcard DNS (§5), exposing a new service requires deploying one manifest and nothing else.

A service manifest declares three objects together:
1. **Deployment** — the pods that run the application.
2. **Service** — load-balances across those pods.
3. **Ingress** — declares the hostname-to-Service mapping (e.g. `foo.<domain>` → this Service).

Applying the manifest (`kubectl apply -f foo.yaml`, or a `git push` under GitOps) triggers three actions:
- The ingress controller reads the Ingress object and begins routing the hostname — no gateway change.
- The hostname resolves through the wildcard DNS record — no per-service DNS change, provided the wildcard record has been configured once as a prerequisite (§5).
- A TLS certificate is issued automatically (§7) — no certificate step.

The routing configuration lives in the application's manifest, which is version-controlled. Adding a service touches only that manifest; the gateway, DNS, and certificate infrastructure are untouched. This is the GitOps model: a committed manifest results in a live, routable, TLS-secured service — once the one-time prerequisites (gateway forward, wildcard DNS, cert-manager) are in place.

---

## 5. Wildcard DNS — configured once

A wildcard DNS record directed at the gateway removes the need for a per-service DNS entry. A wildcard record uses `*` as the leftmost label of an **A record** (IPv4) or **AAAA record** (IPv6), so that any subdomain matching the pattern resolves to the same address:

- `*.athome.example.com → <gateway home-LAN IP>` (internal, §6.2 shows the concrete record)
- `*.example.com → <tunnel>` (external, §8)

Every subdomain then resolves automatically. New services (`grafana.athome…`, `nextcloud.athome…`, and so on) resolve immediately because the wildcard matches any label, so no per-service DNS record is required. This record is configured once, as a prerequisite to the single-step deploy in §4. (mDNS/`.local` is the one resolution method that cannot express a wildcard — see §6.3.)

---

## 6. Internal resolution (home LAN, no internet dependency)

Resolving service names from devices on the home LAN, independent of any cloud service. Several methods are available; the practical constraint is the home router's capabilities. (This is the **home-LAN** scope, `*.athome.example.com` — distinct from the on-subnet `*.aries.lan` scope of §1.1, which serves clients already inside the Aries network.)

### 6.1 Home-router constraint
Many consumer routers — particularly mesh systems oriented toward simplicity — expose no local DNS controls: no custom local records, no custom-zone resolution, and no conditional forwarding. Such routers typically do allow the *upstream* DNS server to be changed. That single setting is the integration point for every server-based method below: the router is pointed at a resolver that does support local records. Where a router does support local DNS records or conditional forwarding directly, the wildcard entry (§6.2) can be placed on the router itself and the separate resolver is unnecessary.

### 6.2 Recommended — public wildcard to a private gateway IP
A public DNS record for a controlled subdomain resolves to the gateway's address on the home LAN:

```
*.athome.example.com   A   <gateway home-LAN IP>
```

The gateway has two network interfaces: one on the home LAN (an address assigned by the home network, typically in `192.168.x.x`) and one on the Aries internal subnet (`10.28.0.1`). Home devices route to the **home-LAN-side** address, so that is the address the record must point to — not the Aries-internal `10.28.0.1`, which home devices cannot reach directly.

- The record is publicly resolvable but points to a private, non-routable address — see the safety analysis in §7.1.
- It functions from any home device; traffic remains on the LAN (the name is resolved via public DNS, the connection is made locally).
- It enables **real TLS certificates** (§7), because the domain is publicly owned and controlled.
- It requires the gateway's home-LAN address to be fixed (static or reserved by the home router's DHCP).
- It is wildcard-compatible — one record covers all services.

**Dependency on internet access.** A record held only in public DNS requires reaching the public resolver to resolve — so a home internet outage breaks internal name resolution even for a service physically on the same LAN. A local resolver holding the same record (§6.4) resolves it locally and continues to function during an internet outage. Where offline internal access matters, a local resolver is preferable to a public-DNS-only record.

### 6.3 Alternative — mDNS / Avahi (`.local`)
Multicast DNS is the mechanism by which a freshly imaged Pi is reachable as `raspberrypi.local` with no configuration. Avahi on the gateway advertises `.local` names; clients (macOS/Bonjour, Linux/Avahi, Windows 10+) resolve them peer-to-peer, requiring no DNS server and no router configuration — so the router constraint in §6.1 does not apply.

- The gateway publishes per-service Avahi aliases (`nextcloud.local`, `grafana.local`, …), all resolving to the gateway.
- Limitations: no wildcard support (each service is listed explicitly); no public TLS certificates (certificates cannot be issued for `.local`); resolution is confined to the local network segment (it does not cross into the Aries `10.28.*` subnet, which is acceptable since traffic enters at the gateway regardless).
- A zero-infrastructure option that forgoes real TLS.

### 6.4 Alternative — a local forwarding resolver (e.g. Pi-hole)
A local resolver (Pi-hole or dnsmasq) runs on a small always-on device separate from the Aries box — a low-power SBC, a NAS, or a lightweight container. The home router's upstream DNS is pointed at it. The resolver holds the `*.athome…` wildcard (or any local zone) and forwards all other queries upstream.

- Provides whole-network resolution and wildcard support.
- Resolves internal names **locally**, so internal name resolution continues to function during a home internet outage — unlike a public-DNS-only record (§6.2).
- Includes a DNS-rebinding allow setting (§6.5) in the case of Pi-hole, which addresses the one caveat of the public-wildcard-to-private-IP method.
- Hosting it on a device separate from the Aries cluster means cluster downtime does not affect network DNS.
- A local resolver plus the `*.athome.example.com` wildcard plus real TLS is the recommended combination — it balances convenience, offline resilience, and certificate support.

### 6.5 Caveat — DNS rebinding protection
Some resolvers and routers block public names that resolve to private IP addresses, as a defense against the DNS-rebinding attack class. Where this is active, `*.athome…→<private IP>` fails to resolve. The resolution is to allowlist the domain on the resolver — Pi-hole provides an explicit setting for this, as do some routers. This should be verified early in setup; it is typically a single configuration change.

### 6.6 Debugging only — `/etc/hosts`
The hosts file is not a resolution method for running the system, but a bootstrap and debugging tool: it allows a single client to test ingress routing before any DNS — or even the gateway and reverse proxy — is configured, by mapping a hostname directly to the ingress. A static entry (`<ingress or gateway IP> nextcloud.athome.example.com`) lets one machine reach a service and confirm that hostname routing works, on a minimal single-node cluster, ahead of building the rest of the stack. This supports incremental bring-up: the ingress layer is validated in isolation first, and the gateway forward and wildcard DNS (§3, §5) are added on top of a component already confirmed to work.

Its limits make it unsuitable as a general solution: it supports no wildcards, must be maintained per device, and is unavailable on mobile platforms.

- **Linux / macOS:** `/etc/hosts` (root required).
- **Windows:** `%SystemRoot%\System32\drivers\etc\hosts` (administrator required).
- **iOS:** not available without jailbreaking.
- **Android:** not available without root.

Because mobile devices cannot use it, and because it does not scale, the hosts file is appropriate only for early testing on a single desktop client. A resolver-based method (§6.2, §6.4) is required for normal use and for mobile clients.

---

## 7. TLS certificates for internal services

Because `athome.example.com` is a publicly owned and controlled domain, Let's Encrypt certificates can be issued for it via the **DNS-01 challenge**, which proves domain ownership through the DNS provider's API and does not require the service to be reachable from the internet.

- `https://nextcloud.athome.example.com` presents a real, browser-trusted certificate even though the service is internal-only and its IP is private.
- No self-signed-certificate warnings, and no need to distribute a private certificate authority to client devices.
- Within the cluster, **cert-manager** automates issuance: it watches Ingress objects, requests certificates via DNS-01, and renews them. The single-manifest deployment (§4) therefore includes TLS with no additional steps.
- This capability is the principal advantage of a real domain (`*.athome…`) over mDNS `.local`, for which public certificates cannot be issued.

### 7.1 Safety of a public record pointing to a private IP
Publishing `*.athome.example.com → <private IP>` exposes only the fact that a name maps to a private address. This carries no practical risk:
- A private RFC-1918 address (whether `192.168.x.x` or `10.x.x.x`) is present on countless networks; it reveals nothing actionable about this specific network.
- Private addresses are non-routable on the internet — packets addressed to a private IP from outside are dropped and never reach the network. An external party cannot connect to it.
- The only disclosure is the low-value fact that an internal service exists at a common private address.

The one operational caveat is DNS-rebinding protection on the resolving side (§6.5), not a security exposure of the network itself.

---

## 8. External resolution (internet-facing — later phase)

Internet exposure is the final phase by design: it is added once the build is complete and a service is ready to expose, rather than during initial bring-up (there is no value in maintaining a live internet endpoint to an unfinished system). It is a logical extension of the internal setup, not a prerequisite for it. See the network design doc's external-exposure notes.

- `*.example.com → Cloudflare tunnel`: an outbound `cloudflared` connection on the gateway. This requires no port forwarding, is unaffected by a dynamic public IP, and operates behind the ISP's gateway.
- Cloudflare terminates TLS and can gate access via Cloudflare Access (authentication before the service is reached).
- The external scope uses the bare domain while the internal scope uses the `athome.` subdomain. The two names are distinct, so the scopes never overlap and no name resolves differently depending on origin.

---

## 9. Addressing — DHCP reservations

Name resolution depends on stable addresses. The chosen approach is **DHCP with reservations** served by the gateway (dnsmasq), rather than per-node static configuration:

- Nodes run standard DHCP with no per-node network configuration; a reimaged node boots with its correct address automatically.
- The gateway assigns each node's MAC address a designated fixed IP (`aries-cp-1` → `10.28.0.11`, and so on) — a single central MAC-to-IP map, held in the gateway configuration and in Ansible.
- Addresses are stable, which satisfies k3s's requirement for consistent node IPs; the TLS-SAN behavior is unaffected, as reserved addresses are equivalent to static ones.
- A dynamic pool (`10.28.0.100+`) serves transient devices (such as a laptop on the MAINT port) without configuration.
- dnsmasq provides both DHCP and DNS from one lightweight daemon, so internal name resolution — where used — is served by the same component.

The gateway's Aries-internal IP (`10.28.0.1`) is its address on the cluster subnet. The `*.athome…` wildcard record instead targets the gateway's **home-LAN-side** address (§6.2), which is the interface home devices route to.

---

## 10. The complete picture

```
HOME (no internet required with a local resolver):
  client → *.athome.example.com (public DNS or local resolver, real cert)
         → gateway home-LAN IP (on the LAN, e.g. 192.168.x.x)
         → ingress → Service → pod
  [local resolver optional: whole-network resolution + offline resolution + rebinding fix]

INTERNET (later phase):
  client → *.example.com (Cloudflare)
         → cloudflared tunnel → gateway
         → ingress → Service → pod
  [Cloudflare Access gates authentication]

SHARED CORE: gateway → ingress → Service → pod
DEPLOY A SERVICE: one manifest (Deployment + Service + Ingress + automatic TLS),
                  once the one-time prerequisites are in place.
```

---

## Related documentation

- `docs/network-design.md` — physical topology, gateway roles, VLANs, connection panel, load-balancing layers.
- `docs/architecture.md` — the containment hierarchy the network plugs into.
- `docs/node-setup.md` — k3s install; the IP-not-hostname / TLS-SAN behavior in practice.
