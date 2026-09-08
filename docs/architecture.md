# Architecture

Consolidated system design across everything built so far — Phase 1 (core messaging API) and Phase 2 (identity, authorization, and additional protocols). Individual phase runbooks (`docs/phase1-runbook.md`, `docs/phase2-runbook-part1-identity-oidc.md`, `docs/phase2-runbook-part2-rbac-abac-saml-scim.md`) go into the *why* and the incidents behind each piece; this document is the *what* — one whole-project picture.

---

## 1. System overview

```mermaid
graph TB
    subgraph "Your Mac"
        Browser[Browser]
        CLI["gcloud / docker / curl"]
    end

    subgraph "Identity VPC (swift-idp-vpc) — us-west1"
        IdpVM["swift-idp-01<br/>10.20.0.2<br/>Keycloak 26.7.2 + Postgres 16<br/>(OIDC, SAML, SCIM)"]
    end

    subgraph "App VPC (default) — us-central1"
        subgraph AppVM["swift-lab-vm — 10.128.0.2"]
            subgraph Net["swift-lab-net (Docker bridge network)"]
                App["swift-payment-api<br/>FastAPI"]
                OPA["OPA sidecar<br/>:8181"]
                App -- "http://opa:8181" --> OPA
            end
        end
    end

    Browser -- "Admin console (via IAP tunnel)<br/>SAML SSO redirect" --> IdpVM
    Browser -- "SAML assertion POST" --> App
    CLI -- "Token requests, SCIM calls" --> IdpVM
    App -- "JWKS fetch, token validation" --> IdpVM
    App -- "Signs & encrypts messages using<br/>local key material" --> App
```

**The two VPCs are bidirectionally peered** — the identity plane (`swift-idp-vpc`) and application plane (default VPC) are deliberately kept as separate networks, matching how a real organization would isolate an identity provider from the applications that consume it.

---

## 2. Component inventory

| Component | Runs on | Purpose |
|---|---|---|
| `swift-payment-api` | swift-lab-vm | FastAPI app — the actual "SWIFT-adjacent" payment message service (Phase 1), now with a full identity/authorization layer (Phase 2) |
| `opa` | swift-lab-vm | Open Policy Agent — evaluates ABAC (attribute-based) authorization decisions via Rego policy |
| `keycloak` | swift-idp-01 | Identity provider — OIDC, SAML, and SCIM all served from here |
| `keycloak-postgres` | swift-idp-01 | Keycloak's backing database |

---

## 3. Phase 1: Core messaging API

The foundational pipeline every request passes through, regardless of which Phase 2 auth layer gates it:

```mermaid
graph LR
    A[Incoming message] --> B[Validate]
    B --> C[Sign]
    C --> D[Encrypt sensitive fields]
    D --> E[Route]
    E --> F[Audit log each transition]
```

- **Validate** — schema/business-rule checks against the message
- **Sign** — RSA signature over the canonical message bytes, applied *before* encryption so a downstream verifier can check integrity without needing to decrypt first
- **Encrypt** — AES encryption of the `account_number` field specifically, not the whole message
- **Route** — delivers the message (simulated in this lab)
- **Audit log** — every status transition (`submitted` → `validated` → `signed` → `acked`/`nacked`) is logged

**Storage:** in-memory only for this lab — no database in Phase 1. A deliberate simplification to demonstrate the pipeline itself without the added complexity of persistence, which was never in scope.

---

## 4. Phase 2: Identity & Authorization

### 4.1 Authentication layer (OIDC)

```mermaid
sequenceDiagram
    participant Client
    participant Keycloak
    participant App as swift-payment-api

    Client->>Keycloak: Password grant (username/password)
    Keycloak-->>Client: JWT access token (roles in realm_access.roles)
    Client->>App: Request + Bearer token
    App->>Keycloak: Fetch JWKS (cached 1hr)
    App->>App: Verify signature, issuer, audience
    App-->>Client: Decoded claims (if valid) or 401
```

Every subsequent authorization layer (RBAC, ABAC) builds on top of this — none of them replace OIDC validation, they add checks *after* it succeeds.

### 4.2 Authorization layers (RBAC + ABAC)

```mermaid
graph TB
    Request[POST /messages] --> RBAC{RBAC:<br/>has payment-initiator role?}
    RBAC -- No --> Deny403a[403 — wrong role]
    RBAC -- Yes --> ABAC{ABAC/OPA:<br/>amount <= 10000<br/>OR also has payment-approver?}
    ABAC -- No --> Deny403b[403 — OPA policy denied]
    ABAC -- Yes --> Pipeline[Phase 1 pipeline:<br/>validate/sign/encrypt/route]
```

Two independent, composable layers — a request must clear both. RBAC answers "does this role have permission at all"; ABAC answers a finer question that depends on the specific request (the dollar amount), evaluated by OPA against a Rego policy external to the application code.

### 4.3 SAML

```mermaid
sequenceDiagram
    participant Browser
    participant Keycloak as Keycloak (IdP)
    participant App as swift-payment-api (SP)

    Browser->>Keycloak: Navigate to IdP-initiated SSO URL, log in
    Keycloak-->>Browser: HTML auto-POST form with signed SAML assertion
    Browser->>App: POST /saml/acs (SAMLResponse)
    App->>App: Decode base64, parse XML, extract NameID + attributes
    App-->>Browser: JSON response (name_id, roles)
```

`swift-payment-api` acts as the SAML **Service Provider**; Keycloak is the **Identity Provider**. IdP-initiated flow — no AuthnRequest generator needed on the app side. **Signature verification is not implemented** (decode/parse only) — deferred to Phase 3 alongside the OIDC JWKS `verify=True` gap, since both need the same underlying PKI/certificate work.

### 4.4 SCIM

```mermaid
sequenceDiagram
    participant Script as Test script (playing the IdP role)
    participant Keycloak

    Script->>Keycloak: Client-credentials grant (scim-client)
    Keycloak-->>Script: Access token (audience = SCIM base URL)
    Script->>Keycloak: POST /scim/v2/Users (create)
    Keycloak-->>Script: 201, real Keycloak user created
    Script->>Keycloak: PATCH /scim/v2/Users/{id} (active: false)
    Keycloak-->>Script: 200, user deactivated
```

Keycloak itself is the SCIM service provider (native support, added via a 26.0 → 26.7.2 upgrade). No application code involved — SCIM operates directly on Keycloak's own user store, provable via the identical `id` showing up through both the SCIM API and Keycloak's normal Admin API/console.

---

## 5. Authorization decision matrix

The four combinations that fully exercise both authorization layers together:

| Caller | Amount | RBAC | ABAC | Result |
|---|---|---|---|---|
| `test-initiator` | ≤ $10,000 | Pass | Pass | 201 |
| `test-approver` | any | **Fail** | (not reached) | 403 (RBAC) |
| `test-initiator` | > $10,000 | Pass | **Fail** | 403 (ABAC) |
| `test-senior-approver` | > $10,000 | Pass | Pass | 201 |

---

## 6. Network topology

| From | To | Path |
|---|---|---|
| Your Mac browser | Keycloak admin console | SSH tunnel (`--tunnel-through-iap -L 8080:localhost:8080`) |
| Your Mac browser | `swift-payment-api` (SAML callback) | Direct, over `swift-lab-vm`'s ephemeral external IP, firewall-restricted to your IP |
| `swift-payment-api` | Keycloak (JWKS, token validation) | Cross-VPC, via peering, over `10.20.0.2:8080` |
| `swift-payment-api` | OPA | Same-host, via `swift-lab-net` Docker bridge network, container-name resolution |
| Any CLI (SCIM, admin API testing) | Keycloak | Depends on where run — `localhost:8080` when run directly on `swift-idp-01`; `10.20.0.2:8080` cross-VM |

**Known asymmetry:** the app-facing token issuer is hardcoded to `localhost` (matching Keycloak's own `KC_HOSTNAME` config, needed to keep the browser-based admin console working), while actual connectivity for JWKS fetches and cross-VM calls goes through the real internal IP. This split (`ISSUER` vs `KC_BASE_URL` in `oidc.py`) is the direct consequence of the browser having no route to a private VPC IP — see `docs/decisions.md` D8/B2 for the full reasoning.

---

## 7. Deliberate simplifications and their deferral targets

| Gap | Deferred to |
|---|---|
| No real TLS on Keycloak (`start-dev`, HTTP not HTTPS) | Phase 3 |
| SAML assertion signature not verified | Phase 3 |
| OIDC JWKS fetch uses `verify=False`-equivalent (no cert validation) | Phase 3 |
| Credentials in a personal password manager, not Vault/GSM | Phase 4 |
| No real database (Phase 1's in-memory store) | Not yet scheduled |
| Cross-VM SCIM calls unsupported (audience check tied to Keycloak's own hostname) | Not yet needed |

---

## 8. Repository structure

```
swift-devsecops-lab/
├── app/                          # Phase 1: FastAPI service
│   ├── src/
│   │   ├── api/                  # routes.py, validation.py, routing.py, audit.py
│   │   ├── auth/                 # oidc.py (OIDC/RBAC/ABAC/SCIM client code)
│   │   ├── crypto/               # signing.py, encryption.py
│   │   └── models/                # message.py
│   └── requirements.txt
├── terraform/
│   └── phase2-identity/          # VPC, VM, NAT, firewall rules for swift-idp-01
├── identity/
│   ├── keycloak/                 # docker-compose.yml
│   └── opa/
│       ├── policies/             # payment_authz.rego
│       └── tests/                # payment_authz_test.rego
├── docs/                         # all runbooks, architecture, decisions log
└── secure-notes/                 # gitignored — credentials metadata only, no values
```
