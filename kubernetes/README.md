# Kubernetes

Cluster manifests for Aries 28.

## `example-static-site.yaml`

A generic, self-contained example demonstrating the service-exposure pattern
from [`../docs/dns-and-exposure.md`](../docs/dns-and-exposure.md): a
**Deployment + Service + Ingress** in a single manifest, exposed by hostname
through the ingress controller on ports 80/443 (no per-service NodePort).

Key points it illustrates:

- **Two replicas with topology spread** — placed across nodes so a single node
  loss does not take the service down.
- **Ingress by hostname** — the service is reached at a hostname, not a port;
  change `host:` to your domain.
- **Optional automatic TLS** — commented cert-manager annotations show how real
  certificates are issued via DNS-01 (see the DNS/exposure doc §7).
- **Resource requests/limits** — modest, sized for single-board computers.

Apply:

```
kubectl apply -f example-static-site.yaml
```

The example uses a stock `nginx:alpine` image serving its default page.
Replace the image or mount your own content to serve something real; the
manifest requires no external repository.

## Deploying your own services

Adding a service is a single declarative step (see the DNS/exposure doc §4):
copy this manifest, change the name, image, and host, and apply. With wildcard
DNS and the gateway forward already in place, the new hostname routes
automatically — no gateway edit, no per-service DNS record.
