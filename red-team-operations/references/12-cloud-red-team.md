# 12 — Cloud Red Team (AWS / Azure-Entra / GCP)

**When to read:** Cloud tenant(s) in scope (check 00's scope-artifact caveat: cloud tenants must be NAMED); foothold on cloud workload (instance/pod/function) exposing creds; cloud credential material found (01 leaks, 08 files); Entra/Azure AD as the identity plane of an internal engagement (route from 05 when the domain is Entra-synced).
**Prerequisites:** RoE tenant scoping in writing (00 third-party/shared-infra caveat: provider-side attacks are out of scope by default); cloud creds with known role OR a workload foothold; non-destructive guardrails below.
**Primary ATT&CK mapping:** T1580 Cloud Infrastructure Discovery, T1526 Cloud Service Discovery, T1078.004 Cloud Accounts, T1098 Account Manipulation (T1098.001 Additional Cloud Credentials, T1098.003 Additional Cloud Roles), T1136.003 Cloud Account, T1552.005 Unsecured Credentials: Cloud Instance Metadata API, T1552.001 Credentials In Files (workload creds), T1530 Data from Cloud Storage, T1537 Transfer Data to Cloud Account, T1496 Resource Hijacking (detection-only — cryptomining-class activity is report material, not performed).

## Cloud-specific guardrails (read before ANY cloud action)

1. **Shared infrastructure:** the provider's control plane is NEVER in scope. Attack the client's tenant resources, not the provider.
2. **Blast radius asymmetry:** cloud actions scale instantly (a privesc chain that works on one region can exist across all). Every state-changing command (`create`, `attach`, `update`, `delete`) requires: RoE action class check + one-target first + record original state.
3. **Non-destructive absolute:** NO log tampering (never disable/delete CloudTrail/Entra diagnostic settings/audit logs — even when RoE allows "evasion": cloud log deletion = destruction of evidence + provider ToS breach; report the COULD, not the DID).
4. **Data-minimal:** enumerate + COUNT + one canary/masked sample, never bulk storage download (00 rule — cloud exfil "demo" uses planted canary objects only).
5. **Billing awareness:** resource creation (compute/keys) bills the client — every created resource goes to artifacts-left for close-out (15).

## AWS

### Phase 1 — Credential & environment reconnaissance

```bash
aws sts get-caller-identity                       # THE first command: account, principal, ARN
aws iam get-account-authorization-details --output json > iam.json   # full policy graph (huge; parse offline)
# environment from a workload foothold (metadata — T1552.005):
curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/   # IMDSv1
# IMDSv2: token-first flow (PUT /latest/api/token) — v2 with hop-limit blocks SSRF-via-proxy classes (03)
```

Pacu framework (module-driven, keeps action-class awareness): `pacu` → `ls` → `data` after each module (session state = evidence trail). AWS analysis offline: policy-graph reasoning (whoami → principal policies → trusted-principal chains).

### Phase 2 — Privilege escalation chains (T1098/T1098.003)

High-yield permission-class chains (test with a dedicated TEST role when possible — 00 lab-first):

| Present permission | Chain class |
|---|---|
| `iam:PassRole` + `ec2:RunInstances` / `lambda:CreateFunction`+`Invoke` / glue/dev-endpoint class | Pass service a privileged role → workload with role creds → role's privileges |
| `iam:CreateAccessKey` / `iam:UpdateLoginProfile` on privileged user | Direct credential creation (T1098.001) |
| `iam:AttachUserPolicy`/`PutUserPolicy` (self) | Self-grant admin (most direct) |
| `iam:AddUserToGroup` (admin group) | Membership escalation |
| `iam:UpdateAssumeRolePolicy` + `sts:AssumeRole` | Role-trust rewrite → assume privileged role |
| `iam:SetDefaultPolicyVersion` (older versions had broad grants) | Version rollback escalation |
| `sts:AssumeRole` cross-account (client's other accounts) | Cross-account lateral — scope check (00): other account in RoE scope? |

Every chain executed = state change → original state recorded + artifacts-left entry (15).

### Phase 3 — Data & persistence (T1530/T1537/T1098)

- S3 enumeration (list/count/masked sample; canary upload for exfil-proof only), RDS/SQS/Secrets Manager enumeration (read = vault, 00).
- Persistence classes (RoE-gated, each an artifact): new IAM user/access key (T1136.003/T1098.001), role trust-policy edit, SSM document abuse class (T1072-adjacent — Software Deployment Tools as lateral), `aws:CreatedBy` tagging avoidance for realism testing (purple value — flag to client that untagged actor resources are the gap).
- Cross-service abuse: SSM → command on managed instances (T1072), EC2 serial console (recovery-path class), snapshot sharing/AMIs (data-plane exfil paths — demonstrate with canary object only).

## Azure / Entra ID

### Phase 1 — Reconnaissance (T1526)

```bash
# Entra ID graph enumeration from a user token (ROADtools family: roadrecon)
roadrecon auth -u <user>@<tenant> && roadrecon gather && roadrecon gui/plot
az ad user list / az role assignment list --all        # or Graph API directly
```

- **Synced-domain synergy (route from 05):** Entra Connect sync / password-hash sync/PTA topologies change the AD attack-surface (AD→Entra and Entra→AD paths — cloud→on-prem pivot classes (PTA-agent abuse-era, AADConnect config abuse-era) — treat each as high-impact action class needing RoE sign-off).
- Key surfaces: users/groups/service principals/app registrations, role assignments (Entra roles: Global Admin/Privileged Auth/Exchange-class), Azure RBAC (Owner/Contributor on subscriptions/resources), Conditional Access policy state (bypass classes = report findings), MFA registration policy.

### Phase 2 — Authentication abuse classes

| Surface | Class | Notes |
|---|---|---|
| Password spray (T1110.003) | RoE rules (04/08 spray discipline; Entra lockout/smart-lockout behavior changes cadence) | Smart-lockout-aware timing; all attempts logged |
| Device code flow phishing | OAuth device-code prompt → user enters code → token (route: 04's phishing approval class — identity impersonation needs explicit RoE) | |
| OAuth consent phishing (illicit consent grant) | Attacker-registered app asking `User.Read.All`-class delegated perms → long-lived refresh token persistence (T1098-class) | Client-approved app registrations only; every grant = artifact (revoke at close-out, 15) |
| PRT/primary-refresh-token abuse (pass-the-PRT class) | With device access or token theft: session as the user on compliant-device-gated apps (T1550-class) | Token theft classes follow 08 evidence rules |
| Service principals/managed identities | Workload identity abuse: cert/key creds, role assignments → privilege | From any Azure-hosted foothold (VM/App Service/Functions) |

### Phase 3 — Azure resource plane

- Storage account key/`listKeys` classes (storage enumeration per data-minimal rule), Key Vault access policies (`get` secrets = vault), RunCommand/Custom Script Extensions (VM command-execution class — RoE action class), deployment-template abuse (ARM with embedded script — artifacted).

## GCP

- Service-account key files (`~/.config/gcloud`, workload metadata — T1552.005 for GCP metadata header rules), IAM policy escalation (`setIamPolicy` chains — the GCP equivalent of the PassRole class), org-policy enumeration, storage bucket enum (data-minimal), GKE workload abuse → route 13.

## Detection footprint (cloud telemetry is RICH — assume everything is logged)

- AWS: CloudTrail (management events — every API call with principal identity), VPC flow logs, GuardDuty-class findings (unusual-actor calls); Entra: sign-in logs (every auth attempt), audit logs (role changes), risky detections (spray/anomalous token use); GCP: audit logs.
- RoE posture: cloud actions are PERMANENTLY attributable (no "quiet mode") — every command in the engagement log (00) doubles as the deconfliction record. Where possible use a client-provided dedicated test role/user so their post-engagement log review is trivially scoped.

## Common failures / misreads

| Symptom | Misread | Reality check |
|---|---|---|
| `get-caller-identity` returns role with `AdministratorAccess` | "Game over, dump everything" | Even when authorized: data-minimal rule; record role evidence, enumerate, but no bulk pulls |
| PassRole chain "works" | "Escalated" | Verify the workload actually received the role's creds (metadata returns them) before claiming escalation |
| Entra spray: no lockouts | "No smart-lockout" | Smart-lockout is per-tenant silent — lockout-absence ≠ no-control; test policy via approved low-risk account |
| Consent-phish granted | "Persistence achieved" | Grant ≠ token: complete the flow + record refresh-token artifact (and the revoke step for 15) |
| `list` on buckets = 200 | "Data exposed, Critical" | Exposure finding ≠ exfiltration — classify honestly (listable vs readable vs downloadable) |

## Tool fallback order

- AWS recon/attack: Pacu (module+state discipline) > manual CLI + offline policy-graph analysis > ScoutSuite-class (audit posture, read-only).
- Entra: ROADtools (roadrecon) > Graph SDK scripts > az cli.
- Cross-cloud posture audit: ScoutSuite-class (read-only) > manual.
- Metadata: curl-native (full control over IMDSv2 flow) > cloud-metadata helper tools.

## Evidence handoff

Per cloud finding: the exact API call sequence + principal identity at each step + original-state record for every state change + artifacts-left (users/keys/roles/app-grants/policies created or modified — close-out removal list, 15). Tenant-level finding classes: privesc-chain paths (permission graph), over-privileged identities, log-coverage gaps (if you did X and CloudTrail-class shows no relevant event = the client's #1 finding — document via the technique→telemetry table like 10's).
