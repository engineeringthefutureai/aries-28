# Monitoring — VictoriaMetrics + Grafana

Historical metrics and dashboards for the cluster, sized for single-board
computers.

## Why not Prometheus

[`../../docs/design-doc.md`](../../docs/design-doc.md) §5 caps the monitoring
layer deliberately: *"metrics-server + Netdata; VictoriaMetrics later if
historical graphs are wanted; full Prometheus only if an 8GB node appears."*

That constraint is real. On a 2GB Pi 5 already running the k3s server and
etcd, Prometheus alone wants 0.5–1.5GB at default settings — a monitoring
stack that reliably OOM-kills the node it is meant to be watching.

VictoriaMetrics is a single Go binary exposing the same PromQL query API, in
roughly a fifth of the memory. Dashboards written for Prometheus work
unchanged, Grafana talks to it with the stock Prometheus datasource, and
nothing you learn here has to be unlearned if an 8GB node ever appears.

## Why the database lives on NVMe

A time-series database writes continuously in small increments — the workload
that wears SD cards out. k3s's default `local-path` StorageClass writes to
`/var/lib/rancher/k3s/storage`, which is on the SD card, so using it here would
put a permanent write load on the fleet's most fragile component.

`00-namespace-and-storage.yaml` therefore declares a `local` PersistentVolume
on the NVMe data partition, matching the reasoning
[`../../docs/node-setup.md`](../../docs/node-setup.md) §2 applies to etcd. The
volume binds by node **label** rather than hostname, so it stays correct as
more nodes get NVMe (`design-doc.md` §4.3).

## Placement

The two stateful concerns pull in opposite directions, so they are split:

| Component | Runs on | Because |
|---|---|---|
| VictoriaMetrics | the NVMe node (`aries28/storage=nvme`) | needs write endurance; RAM footprint is small |
| Grafana | prefers a non-control-plane node | needs RAM, holds no state; keeps etcd's node uncontended |
| node-exporter | every node (DaemonSet, tolerates all taints) | the node you most want to watch is often the tainted one |
| kube-state-metrics | anywhere | cluster object state only |

Total footprint is roughly 570Mi across the fleet.

## Prerequisites

On the node holding the NVMe:

```bash
sudo mkdir -p /mnt/data/victoria-metrics
```

Then label it (from anywhere with cluster access):

```bash
kubectl label node <nvme-node> aries28/storage=nvme
```

Without the label, the VictoriaMetrics pod stays `Pending` — that is the
volume binding working correctly, not a failure.

## Apply

Files are numbered in dependency order. Grafana's admin credentials are
deliberately not stored in this repository, so the Secret is created out of
band between steps:

```bash
kubectl apply -f 00-namespace-and-storage.yaml
kubectl apply -f 01-victoria-metrics.yaml
kubectl apply -f 02-exporters.yaml

kubectl -n monitoring create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password='<choose-a-password>'

kubectl apply -f 03-grafana.yaml
```

Without that Secret the Grafana pod stays `CreateContainerConfigError`.

## Verify

```bash
kubectl -n monitoring get pods -o wide       # placement matches the table above
kubectl -n monitoring get pvc                # storage Bound, not Pending
```

Check that every node is actually being scraped — VictoriaMetrics serves its
own target list:

```bash
kubectl -n monitoring port-forward svc/victoria-metrics 8428:8428
# then open http://localhost:8428/targets
```

Every node should appear under `kubernetes-nodes`, `kubernetes-cadvisor`, and
once via `kubernetes-pods` for node-exporter. A node missing from that list is
not in your graphs, however healthy the dashboard looks.

## Reaching Grafana

Three ways, in increasing order of how much infrastructure they assume:

**NodePort — works today, no DNS needed.** Every node answers on port 30300
regardless of which one runs the pod:

```
http://<any-node-ip>:30300
```

**Ingress by hostname** at `http://grafana.aries.lan`, the pattern
[`../../docs/dns-and-exposure.md`](../../docs/dns-and-exposure.md) describes.
Before gateway DNS exists, one hosts entry on your workstation enables it —
and unlike the NodePort, it then works for every future service without
further per-service setup:

```
10.28.0.11   grafana.aries.lan
```

**Port-forward**, for when the ingress and NodePort are both unavailable:

```bash
kubectl -n monitoring port-forward svc/grafana 3000:80
```

Credentials come from the `grafana-admin` Secret created in the prerequisites
above. Rotate the password with `kubectl create secret ... --dry-run=client -o
yaml | kubectl apply -f -`, then restart the deployment — Grafana reads the
admin password only when initializing its database.

## Dashboards

The datasource is provisioned as code; dashboards are not, to avoid running a
sidecar for them on a small fleet. Import these by ID under
*Dashboards → New → Import*:

| ID | Dashboard | Notes |
|---|---|---|
| 1860 | Node Exporter Full | per-node CPU, RAM, disk, network, temperature |
| 15757 | Kubernetes / Views / Global | cluster-wide pod and workload state |
| 15759 | Kubernetes / Views / Pods | per-pod resource use |

Importing by ID requires Grafana to reach grafana.com. Offline, download the
JSON on another machine and paste it into the same import dialog.

Imported dashboards persist across restarts via the Grafana PVC. Dashboards
authored here should still be exported to JSON and committed alongside these
manifests, so the cluster can be rebuilt from the repository alone
(`design-doc.md` §5.1).

## Known gaps

- **Image tags are `latest`** (except kube-state-metrics). Pin them to released
  versions before relying on this.
- **No alerting.** VictoriaMetrics stores the data; firing alerts requires
  `vmalert` plus a receiver. A fan-failure alarm is called for in
  `design-doc.md` §3.3.1 and is the obvious first rule.
- **Per-node temperature** is collected (`node_hwmon_temp_celsius`) but has no
  dedicated dashboard. §3.3.1's airflow model is stated rather than measured,
  and this data is what would validate it.
