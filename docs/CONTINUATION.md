# CONTINUATION

A complete project-state snapshot, written to be readable cold — by a human collaborator, an interviewer looking at the repo before a call, or future-you returning after a long gap, with no other context needed.

---

## 1. What this project is

`swift-devsecops-lab` — a personal, production-equivalent DevSecOps lab built to demonstrate hands-on skill for a Principal/Senior DevSecOps Engineer role, in a SWIFT-adjacent (payment messaging) domain. Real GCP infrastructure, real Keycloak identity provider, real Docker deployments — deliberately not mocked, so every bug hit and fixed along the way is a genuine, defensible talking point.

**8-phase plan:**
1. Core messaging API — **done**
2. Identity & Authorization (OIDC, RBAC, ABAC, SAML, SCIM) — **done**
3. PKI, certificates & machine identity — not started
4. Secrets management (Vault/GSM) — not started
5. CI/CD security gates — not started
6. IaC + cloud governance — not started
7. Kubernetes hardening (optional) — not started
8. AI-driven DevSecOps layer — not started

---

## 2. Environment reference

**GCP project:** `swift-devsecops-lab-01` (display name in console: "swift-devsecops-lab" — note the `-01` suffix is required for CLI commands; the display name alone will fail `gcloud config set project`)
**Active `gcloud` account for this project:** `kuldeepjainphotos@gmail.com`
**Git remote:** `https://github.com/kuldeepjain1920/swift-devsecops-lab.git` (public repo)
**Git identity:** `Kuldeep Jain <kuldeepjain1920@gmail.com>`

| VM | Zone | Internal IP | External IP | Purpose |
|---|---|---|---|---|
| `swift-idp-01` | us-west1-b | 10.20.0.2 | none (IAP-only access) | Keycloak identity provider |
| `swift-lab-vm` | us-central1-a | 10.128.0.2 | ephemeral, reassigned on restart | The application itself |

**Both VMs are kept stopped between sessions** to avoid compute billing. All state (Docker images/containers, Keycloak config, Postgres data) persists across stop/start. See `docs/operations-runbook.md` for the exact start/stop sequence.

**Credentials:** none live in this repo or in any committed file. See `secure-notes/credentials-index.md` (gitignored, local-only) for what exists and how to regenerate each one — that file has no actual secret values either, only metadata and regeneration steps. Real values live in a personal password manager and in `.env` files on the VMs themselves.

---

## 3. Repo structure

```
swift-devsecops-lab/
├── app/                          # Phase 1: FastAPI service
│   ├── src/
│   │   ├── api/                  # routes.py, validation.py, routing.py, audit.py
│   │   ├── auth/                 # oidc.py — OIDC validation, RBAC, ABAC/OPA client, SCIM is Keycloak-side only
│   │   ├── crypto/               # signing.py, encryption.py
│   │   └── models/               # message.py
│   └── requirements.txt
├── terraform/
│   └── phase2-identity/          # VPC, VM, NAT, firewall rules for swift-idp-01
├── identity/
│   ├── keycloak/                 # docker-compose.yml (Keycloak + Postgres)
│   └── opa/
│       ├── policies/             # payment_authz.rego — the ABAC policy
│       └── tests/                # payment_authz_test.rego
├── docs/
│   ├── phase1-runbook.md
│   ├── phase2-runbook-part1-identity-oidc.md
│   ├── phase2-runbook-part2-rbac-abac-saml-scim.md
│   ├── operations-runbook.md
│   ├── architecture.md
│   ├── decisions.md
│   ├── demo-script.md
│   ├── threat-model.md
│   └── CONTINUATION.md           # this file
└── secure-notes/                 # gitignored entirely — credentials metadata only, no values
```

**Branches:**
- `phase-1-core-api` — Phase 1 work
- `phase-2-identity-auth` — Phase 2 Part 1 + Part 2, contains all of Phase 1's history too (branched from it, never diverged)
- `main` — not yet created as of this writing; see open items below

---

## 4. Status by phase

### Phase 1 — Core Messaging API: **complete**
Validate → sign → encrypt → route pipeline. In-memory message store (no DB — deliberate simplification). Full narrative in `docs/phase1-runbook.md`.

### Phase 2 Part 1 — Identity & OIDC: **complete**
Dedicated identity VM/VPC (peered to the app VPC), Keycloak deployed via Docker Compose, real OIDC token validation wired into the app. Full narrative in `docs/phase2-runbook-part1-identity-oidc.md`.

### Phase 2 Part 2 — RBAC, ABAC, SAML, SCIM: **complete**
All four built and verified end-to-end against real tokens/real Keycloak state. Full narrative in `docs/phase2-runbook-part2-rbac-abac-saml-scim.md`.

### Phases 3–8: not started

---

## 5. Test fixtures (Keycloak users/clients)

| Name | Type | Purpose |
|---|---|---|
| `kuldeep-admin` | User (**master realm**, not `swift-devsecops-lab`) | Permanent Keycloak admin |
| `test-initiator` | User | Has `payment-initiator` — RBAC/ABAC pass case |
| `test-approver` | User | Has `payment-approver` only — RBAC boundary (blocked) |
| `test-senior-approver` | User | Has both roles — ABAC-allow boundary |
| `test-auditor` | User | Has `payment-auditor` — reserved, no endpoint uses it yet |
| `swift-payment-api` | OIDC client | The app's own client |
| `swift-payment-api-saml` | SAML client | The app's SAML SP registration |
| `scim-client` | OIDC client (service account) | SCIM's machine-to-machine client |

---

## 6. Working conventions established

- **Every command in a runbook specifies which host to run it on** (Mac vs. specific VM).
- **Docker commands include explanatory comments** on what each flag does.
- **Password-safety pattern, used consistently in every test script:** `read -sp` (hidden prompt) → `--data @-` (stdin, not a visible `curl -d` argument) → `unset` immediately after use.
- **Redeploy containers with `--network` specified from the start**, not `docker network connect` on an already-running container.
- **One commit per logical capability**, not one giant commit — `git status` checked immediately after `git add`, before every commit, to confirm exactly the intended files are staged.
- **Verify a file's actual git status before deciding how to remove it** (`git log --all`, `diff`) — never assume.
- **Runbooks written incrementally alongside the build**, not reconstructed afterward.
- **PR/merge into `main` deferred until an entire phase is complete**, not per-feature.

---

## 7. Known open items (not blockers, just open)

- `main` branch not yet created — `phase-2-identity-auth` is ready to merge (contains all of Phase 1 + Phase 2 history cleanly)
- `POSTGRES_PASSWORD` should be rotated (was printed to a terminal in plaintext once during the SCIM-upgrade backup prep — low risk, lab-only, but a genuine hygiene item)
- Cross-VM SCIM calls unsupported (SCIM's audience check is tied to Keycloak's own hostname config, with no app-side workaround built yet — not currently needed)
- `swift-lab-vm`'s ephemeral external IP breaks the SAML client's redirect URI on every VM restart until manually re-checked and updated
- A possible future hardening step (GCP HTTPS Load Balancer + real public domain, to give both the browser and cross-VM traffic the same publicly-routable hostname) was discussed but deliberately deferred, pending a conversation with a mentor — not in scope for any phase yet
- `docs/MASTER-GUIDE.md` (a single linear narrative combining everything above) not yet built — deliberately deprioritized, "nice-to-have once more phases exist," not urgent with only Phase 2 done

---

## 8. Glossary pointer

A concepts glossary (RBAC vs. ABAC, OIDC vs. SAML vs. SCIM, policy-as-code, fail-closed defaults, service accounts, etc.) lives in `docs/phase2-runbook-part2-rbac-abac-saml-scim.md` §8 — not duplicated here.
