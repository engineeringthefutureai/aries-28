# Ansible

Infrastructure-as-code for provisioning Aries 28 nodes. This directory is a
placeholder for the node-provisioning automation described in
[`../docs/node-setup.md`](../docs/node-setup.md) §7.

## Intended scope (base role)

The base role captures the manual node bring-up sequence so that nodes are
reproducible rather than hand-configured:

- Kernel boot parameters (`cmdline.txt`): the memory-cgroup enable and the
  NVMe power-save workaround (universal to all nodes).
- Storage: partition, label, and mount (etcd + data split on storage nodes;
  minimal on compute nodes).
- k3s install: `server --cluster-init` for the first server, `server --server`
  for additional control-plane nodes, `agent` for workers.
- Hostname per inventory.
- kubeconfig fetch.

## Addressing

Node addressing is hybrid (see
[`../docs/dns-and-exposure.md`](../docs/dns-and-exposure.md) §9): the gateway is
static, the control-plane servers use DHCP reservations, and all other nodes are
dynamic. The reservation MAC→IP map lives in the gateway configuration and is
mirrored in the Ansible inventory.

## Security

Do not commit inventories containing real hostnames/IPs, tokens, or vault
files. See `.gitignore`. Use `ansible-vault` for any secret material.

*Status: not yet implemented. The node-setup runbook is the manual procedure
this role will automate.*
