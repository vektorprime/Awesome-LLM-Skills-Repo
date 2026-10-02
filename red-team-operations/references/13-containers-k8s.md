# 13 — Containers & Kubernetes

**When to read:** Container/pod foothold (from 04/08 or 07's docker-group path); Docker/K8s services in scan results (02 route table: 6443/10250/2379/10255/5000); whenever `~/.docker/config.json`, image-pull secrets, or service-account tokens are in reach; any "am I in a container" moment on a Linux host.
**Prerequisites:** Authorization gate with the cluster/host in scope; container escape class = RoE action-class check (escape affects the NODE — blast radius beyond the pod); non-destructive (no cluster-state changes without RoE).
**Primary ATT&CK mapping:** T1611 Escape to Host, T1610 Deploy Container, T1613 Location and Object Discovery, T1526 Cloud Service Discovery (cluster-service discovery class), T1552 Unsecured Credentials (image/service-account tokens class), T1078.004 Cloud Accounts (cloud-integrated service accounts), T1496 Resource Hijacking (detection-only class for crypto-mining presence).

## Phase 0 — Where am I? (30-second container check)

```bash
cat /proc/1/cgroup | head -5; ls /.dockerenv 2>/dev/null; hostname; cat /proc/self/mountinfo | head -20
cat /var/run/secrets/kubernetes.io/serviceaccount/namespace 2>/dev/null     # in-pod K8s marker
sudo -n docker ps 2>/dev/null; docker context ls 2>/dev/null               # docker-group/host access
```

Context classes → route: pod-in-cluster (→ K8s phases) | docker-host (→ Docker phases) | plain host (→ 07) | cloud-managed cluster (→ 12 cloud synergy).

## Docker (single-host + registry classes)

### From docker-group membership (= host root path, T1611)

```bash
# canonical path: mount host root via privileged container run
docker run -v /:/host -it ubuntu chroot /host /bin/sh       # host FS mounted → host-equivalent control
```

- The mount class = host compromise (artifact: the container itself — record + remove at close-out, 15).
- Alternative classes: socket mount (`-v /var/run/docker.sock:/...`) → docker API → same; `--privileged` run with full caps.
- **Privileged-container breakout decision table (T1611):**

| Condition present | Escape class |
|---|---|
| `--privileged` (full caps + devices) | `capsh --print` check → `mkdir /tmp/cgrp && mount` cgroup-v1 `release_agent` write path (cgroup v1 kernels) or full-device host-mount class |
| `CAP_SYS_ADMIN` in container | mount host FS directly / cgroup `release_agent` |
| `CAP_SYS_PTRACE` + hostPID | process injection into host-root process |
| `hostPath`-mounted sensitive dirs | file-based cred/key escape (read directly) |
| `CAP_DAC_READ_SEARCH` | full host-FS read bypass class |
| seccomp disabled + kernel vuln class | kernel-exploit path (11's crash rules apply × — node = multi-tenant blast radius) |
| Docker socket mounted | API escape (container-create with host mounts) |

Tooling: `amicontained` (cap/seccomp/ns inventory — run FIRST to select the row), kdigger (full in-container recon).

### Image/registry abuse classes

- `~/.docker/config.json` + registry creds (08 file-class) → private-registry pull → image mining (secrets baked in layers: env vars, tokens, keys — data-minimal rule; report counts + masked samples).
- Registry exposure (02 scan → registry port) → catalog `v2/_catalog` anonymous → same image-mining class (finding: unauthenticated registry).
- Image build-pipeline abuse (CI/CD class): privileged build contexts (Dockerfile `RUN --security=insecure`-era features), `ADD` remote URL + shell chain (build-time RCE class — client-approved build-abuse scope only).

## Kubernetes

### Architecture 30 seconds

API server (6443) = control plane; kubelet (10250) = node agent (exec API); etcd (2379) = the cluster's brain (ALL cluster state incl. secrets); service-account tokens = pod identity; RBAC = verb×resource permission graph. **K8s compromise classes: control-plane (API/etcd) > node (kubelet/escape) > workload (pod exec / SA token abuse).**

### Phase 1 — Reconnaissance (T1613/T1526)

```bash
# in-pod: SA token inventory (default location)
env | grep -i kube; ls /var/run/secrets/kubernetes.io/serviceaccount/
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
APISERVER=https://kubernetes.default.svc
curl -sk $APISERVER/api --header "Authorization: Bearer $TOKEN"          # auth + version check
kubectl auth can-i --list                                                # THE self-RBAC inventory
kubectl get pods,secrets,configmaps -A 2>&1 | head -40                   # cluster-view attempts
# network-based (02 route table entry):
nmap -p 6443,10250,2379,10255,5000 <node-ips> -sV
curl -sk https://<node>:10250/pods                                       # anonymous kubelet check
```

Record: anonymous API/kubelet exposure (each = finding), SA namespace/permissions (RBAC reality), network policy behavior (can the pod reach others? — policy-gap findings).

### Phase 2 — RBAC abuse (the permission-graph attack)

| RBAC grant visible in `auth can-i --list` | Abuse class |
|---|---|
| `secrets` get/list | Cluster-wide secret harvest (T1552 — vault discipline, 00; data-minimal: count+sample) |
| pods `exec`/`create` | Exec into privileged/host-network/other-workload pods (lateral + escape-as-service class) |
| pods `create` + `create` on `pods/exec`-era | Create privileged pod (hostPath / privileged) → node escape via workload creation (T1610-adjacent) |
| roles/clusterroles `escalate`+`bind` (or `update`) | Self-grant → `cluster-admin` equivalence (the direct class) |
| `nodes/proxy`, kubelet API write | Node-level exec class |
| `serviceaccounts` `impersonate` | Act as other SAs (T1078-class) |
| token `create` (T1550-adjacent) | Mint tokens for any SA — direct class |

Every RBAC escalation = `kubectl apply`/`create` state change → original state recorded + artifact-left (15).

### Phase 3 — Node breakout (T1611)

- Privileged/hostPath pod (created or exec'd into) → the Docker privileged-breakout table above (shared classes).
- `hostPID` + CAP_SYS_PTRACE → process injection into node-root; `hostNetwork` + node-services reachable (kubelet anonymous exec class).
- Kernel-exploit path: 11's crash rules × multi-tenant blast radius — RoE approval class higher still (node crash = many workloads).
- Cloud-node synergy (→ 12): node's cloud identity (node instance role/gMSA-equivalent) = cloud-plane lateral from the escaped node.

### Phase 4 — Cluster dominance (RoE-gated per action)

- etcd access (2379 unauth'd, or etcd-client certs found) → cluster state incl. all secrets — read-class evidence (data-minimal); write-class etcd tampering = almost always out (RoE highest class).
- Admission-controller/webhook abuse classes (deployed-malicious-admission — client-approved only); CRDs/operator abuse (privileged operators installed); persistent K8s resources as persistence (CronJob/ScheduledJob — 09's artifact rules apply verbatim: record + close-out).

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| SA token present | "Cluster compromised" | Default SAs are near-noop (can-i shows ~nothing); RBAC reality from `auth can-i --list`, not token presence |
| `/var/run/secrets/.../token` mounted | "Finding: token exposure" | Default pod behavior (not a finding alone) — finding = EXCESSIVE RBAC on the SA |
| Anonymous kubelet 200 | "Node RCE" | `/pods` readable ≠ exec; test exec endpoint specifically |
| Docker group on host | "Root via socket" | The class is right but record the EXACT artifact (which container/mount) for close-out |
| Escape "worked" | "Full node control" | Check node role: worker vs control-plane; cloud-node identity reachability (12) |

## Detection footprint

- K8s audit log (if configured): every API call with SA identity (immutable attribution — same as cloud, 12); kubelet exec events; anomalous SA activity classes.
- EDR-less nodes often blind to breakout — note the telemetry GAP per technique in the technique→telemetry table (15) — container-escape coverage gaps are the client's core K8s finding usually.

## Tool fallback order

- Container context inventory: amicontained + kdigger > manual /proc checks.
- K8s interaction: kubectl (token env) > curl API direct (audit-friendly minimal) > specialized attack tooling.
- RBAC analysis: `kubectl auth can-i --list` + offline policy review > Rakkess-class; kubectl-who-can for grant discovery.
- Image mining: skopeo/docker-save + layer diff (offline) > registry raw API.

## Evidence handoff

Per class exercised: in-cluster position evidence (RBAC inventory output), escape artifact (container name/mount/namespace/node), every cluster-state change (kubectl command + before-state + artifact-left entry, 15), secret-exposure findings (counts + masked samples + vault pointers). Cloud-node synergy handoffs → 12 (with node identity notes). K8s technique→telemetry rows → 15's detection appendix.
