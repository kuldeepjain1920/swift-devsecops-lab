# Decisions & Bugs Log

Chronological log of every real decision made and bug found across this project, with reasoning. Mirrors the same discipline used on the CSE636 capstone's `decisions.md` — a scannable record independent of the narrative runbooks, useful for interview prep ("tell me about a time you had to debug something tricky" has real, specific answers here) and for future-you re-orienting without re-reading full runbook prose.

**Numbering:** sequential across the whole project (D1, D2, ...), not reset per phase. Each entry is either a **Decision** (a deliberate choice among alternatives) or a **Bug** (something that broke, root cause, and the fix).

---

## Phase 1 — Core Messaging API

**D1 — Repo structure correction.**
Git had been initialized inside `app/` rather than at the true intended repo root. Corrected by moving Phase 1 into an `app/` subfolder with `terraform/` and `identity/` as sibling folders at the actual root, and adding a root-level `.gitignore` alongside `app/`'s existing one.

**D2 — In-memory message store for Phase 1.**
No real database in Phase 1 — messages are held in a Python dict for the life of the process. Deliberate simplification to demonstrate the validate → sign → encrypt → route pipeline without the added complexity of a persistence layer; real persistence was never in Phase 1's scope.

*(Phase 1 predates this decision-log discipline — most of its build detail lives narratively in `docs/phase1-runbook.md` rather than as discrete numbered entries here.)*

---

## Phase 2 Part 1 — Identity & OIDC

**D3 — Separate dedicated identity VM.**
Chose to provision `swift-idp-01` as its own VM (via Terraform) with its own dedicated VPC (`swift-idp-vpc`), bidirectionally peered to the Phase 1 app VPC — rather than reusing the Phase 1 VM. Keeps the identity plane and application plane genuinely separate, matching how a real org would isolate an IdP.

**B1 — e2-small capacity stockouts.**
`terraform apply` repeatedly failed to provision `swift-idp-01` in both `us-central1-a` and `us-central1-b` due to zone capacity exhaustion. **Fix:** moved the identity VM to `us-west1-b`. Since subnet/router/NAT are region-scoped resources, they had to be recreated for the new region; VPC, peering, and firewall rules were unaffected.

**D4 — Cloud NAT added.**
The identity VM has no external IP by design (private-only). `private_ip_google_access` alone only covers Google API traffic, not general internet egress (e.g., `apt-get`, Docker image pulls) — a Cloud NAT (router + NAT gateway) was required for that.

**D5 — Separate IAP SSH firewall rule.**
Added a firewall rule allowing `35.235.240.0/20` (Google's IAP range) for SSH, distinct from the existing admin-IP-restricted SSH rule — required specifically for `gcloud compute ssh --tunnel-through-iap` to function.

**D6 — Keycloak via Docker Compose, dev mode.**
Deployed as Postgres + Keycloak 26.0 in `start-dev` mode via Compose, matching the project's general "get it working, then harden" approach — production-mode Keycloak (`start` + real certs) explicitly deferred to Phase 3.

**D7 — Port 8080 (HTTP), not 8443 (HTTPS), for the app-VPC firewall rule.**
Keycloak's `start-dev` mode has no working HTTPS listener without an explicitly configured keystore. Real TLS deferred to Phase 3 (PKI/mTLS) — this is the origin of the `verify=True` TODO that recurs throughout Phase 2.

**B2 — Broken admin console from a hostname split attempt.**
Tried setting `KC_HOSTNAME`/`KC_HOSTNAME_ADMIN` as two different full URLs (`http://10.20.0.2:8080` for app-facing token issuance, `http://localhost:8080` for admin access) to get both audiences working cleanly. This broke the browser admin console entirely — Keycloak's admin JS performs a third-party-cookie check that loads an iframe directly from `authServerUrl` (the 10.20.0.2 value), which the Mac browser has no route to (private VPC IP, no route outside the SSH tunnel). **Fix:** reverted to a single `KC_HOSTNAME=localhost`. The issuer mismatch this reintroduces for the app's own token validation was instead solved entirely in application code (see D8).

**D8 — Decoupled `KC_BASE_URL`/`ISSUER` in `oidc.py`, rather than a true split-hostname Keycloak config.**
`KC_BASE_URL=http://10.20.0.2:8080` drives the actual JWKS fetch/connectivity; `ISSUER` is separately hardcoded to `http://localhost:8080/realms/{realm}` to match what Keycloak actually stamps into issued tokens. **Options considered:** (1) a true Keycloak-side split-hostname setup — rejected, since the real blocker (the Mac browser having no route to a private VPC IP) can't be fixed by any Keycloak-side hostname config; (2) the app-side decoupling actually chosen; (3) a GCP HTTPS Load Balancer with a real public domain and TLS cert, giving both the browser and `swift-lab-vm` the same publicly-routable hostname — the "real" fix, but explicitly deferred as a possible future hardening step (planned to discuss with a mentor), not current Phase 2 scope.

**B3 — `oidc.py` file permissions baked into the Docker image.**
The file had restrictive local permissions (`-rw-------`) that carried through into the built image, causing a `PermissionError` on import inside the container. **Fix:** `chmod 644` before rebuilding.

**B4 — "Account is not fully set up" on password-grant token requests.**
Error `resolve_required_actions` occurred despite the affected user's `requiredActions` array being confirmed empty via the Admin REST API, and every other realm/client setting checking out clean. **Root cause:** Keycloak 26's User Profile feature (Realm settings → User profile) was dynamically enforcing "Required field" on `email`/`firstName`/`lastName` at every login — a separate mechanism from the per-user `requiredActions` array. **Fix:** toggled Required field off for those three attributes.

**B5 — `/whoami` 500 error from a self-referential JWKS URL.**
`JWKS_URL` was being built *from* the hardcoded `ISSUER` (`localhost:8080`) — but inside the container, `localhost` refers to the container itself, causing `Connection refused`. **Fix:** decoupled the two properly — `KC_BASE_URL` (`10.20.0.2:8080`) drives `JWKS_URL` for actual connectivity, while `ISSUER` stays separately hardcoded for the token issuer-matching comparison only.

**B6 — "Invalid audience" on token validation.**
Keycloak's default access tokens set `aud=["account"]`, not the client ID. **Options considered:** a simpler workaround checking the `azp` (authorized party) claim instead; the proper fix — adding an explicit Audience mapper. **Chosen:** the Audience mapper (Included Client Audience: `swift-payment-api`, added to both access token and introspection) — the production-aligned choice, since real deployments shouldn't rely on `azp`-checking as a substitute for a correctly scoped audience.

**D9 — Credentials kept in a personal password manager, not any repo file.**
Explicit interim decision — centralizing into Vault/GCP Secret Manager is planned for Phase 4, not before.

---

## Phase 2 Part 2 — RBAC, ABAC, SAML, SCIM

### RBAC

**B7 — Missing volume mount on redeploy.**
`FileNotFoundError: ./keys/signing_key.pem` — the redeploy `docker run` omitted `-v ~/keys:/app/keys:ro`. The signing key lives on the VM host filesystem by design (never baked into the image). **Fix:** added the mount to every subsequent redeploy.

**B8 — `noexec` on `/home` blocking script execution.**
`chmod +x test_rbac.sh` followed by `./test_rbac.sh` failed with `Permission denied`, despite correct permissions. `mount | grep home` revealed `/home` mounted `noexec` (deliberate VM hardening). **Fix:** run scripts via `bash script.sh` instead of `./script.sh`.

**B9 — `kuldeep-admin` targeted the wrong realm.**
Admin API calls for `kuldeep-admin` initially targeted `realms/swift-devsecops-lab`. **Root cause:** `kuldeep-admin` is a **master-realm** user (the permanent replacement for Keycloak's bootstrap admin), not a realm user like the test fixtures. **Fix:** admin-cli requests for `kuldeep-admin` target `realms/master`.

**D10 — Script-based testing over manual `curl`.**
Built a reusable `~/test_rbac.sh` rather than ad-hoc commands each session — enforces the password-safety pattern (`read -sp`, `--data @-`, `unset`) consistently and makes reruns after a redeploy trivial.

### ABAC / OPA

**D11 — OPA as a sidecar on `swift-lab-vm`, not co-located with Keycloak.**
**Options considered:** co-locate with Keycloak on `swift-idp-01` (matches the originally planned repo layout, but repeats the cross-VPC firewall-rule pattern already learned). **Chosen:** sidecar on `swift-lab-vm` — since OPA is only ever called by the app itself, this instead teaches container-to-container Docker networking, a genuinely new concept for the project.

**D12 — Recreate containers with `--network` from the start (Option B), not `docker network connect`.**
Discovered mid-session that `swift-payment-api` was still on Docker's default bridge network after `swift-lab-net` was created — meaning name-based resolution to `opa` wouldn't work. **Options considered:** `docker network connect` on the already-running container (non-disruptive, quick fix); stop/rm/recreate with `--network` from the start. **Chosen:** the latter, as the standing approach for this and all future redeploys — cleaner going forward since every redeploy needs the flag anyway.

**B10 — Redundant inline `import httpx`.**
`check_opa_authorization()` had its own local `import httpx`, even though the module already imports it at the top level. Harmless (Python no-ops a repeat import) but misleading. **Fix:** removed before the ABAC commit.

**D13 — `test-senior-approver` as a new permanent fixture, not a temporary role grant.**
**Options considered:** temporarily grant `payment-approver` to `test-initiator` for one test, then revert; create a dedicated permanent user. **Chosen:** the permanent user — a grant-then-revert pattern depends on remembering to revert, risking silent role drift if forgotten.

### SAML

**D14 — Basic SAML flow only; signature verification deferred to Phase 3.**
Full assertion signature verification needs a proper library (`python3-saml`/`signxml`) and correct certificate handling. Consistent with the existing `verify=True` JWKS TODO already deferred to Phase 3 — same underlying PKI dependency surfacing in a second place, not a new gap.

**B11 — "Client not found" on the IdP-initiated SSO URL.**
The SSO URL path doesn't key off Client ID at all — it needs the separate **"IDP-Initiated SSO URL Name"** field (Settings tab, blank by default). **Fix:** explicitly set it to match the client ID.

**B12 — Identical junk role attribute across different users.**
`test-initiator` and `test-approver` both returned `Role: ["offline_access"]` in their SAML assertions — the tell that nothing was reflecting real per-user data. **Root cause:** SAML clients don't automatically include realm roles the way OIDC clients do. **Fix:** added an explicit Role list mapper (attribute name `Role`, Single Role Attribute on).

**Known gap — ephemeral external IP.** `swift-lab-vm`'s external IP is not reserved. The SAML client's redirect URI/Master SAML Processing URL (and the `allow-lab-app` firewall rule) both go stale on every VM stop/start until manually updated.

### SCIM

**D15 — Upgrade Keycloak to native SCIM support, over a third-party plugin or a build-your-own receiver.**
**Options considered:** (1) third-party plugin (`scim-for-keycloak`) — rejected, needs a custom image with a plugin JAR, and the maintained version requires an enterprise license past older Keycloak versions; (2) build a SCIM *receiver* into `swift-payment-api` itself, mirroring the SAML SP pattern — zero risk, but less realistic since it simulates rather than uses a genuine IdP; (3) **chosen: upgrade Keycloak (26.0 → 26.7.2) and use its native SCIM API directly** — more realistic identity-platform pattern; the real upgrade risk was mitigated with a `pg_dump` backup taken first.

**B13 — 404 despite the `scim-api` feature flag being enabled.**
Server log: `WARN ... SCIM API is not enabled for realm 'swift-devsecops-lab'`. **Root cause:** the server-wide feature flag only makes the *capability* available; SCIM must ALSO be explicitly enabled per-realm via a separate `scimApiEnabled` attribute — settable only via `kcadm.sh`/Admin API, no console UI exists for this yet. **Fix:** `kcadm.sh update realms/swift-devsecops-lab -s scimApiEnabled=true`.

**B14 — The audience trap.**
`401 Invalid token audience`, even though the token's `aud` claim correctly contained the configured value. **Root cause:** Keycloak's SCIM validator compares the audience against its own internally configured `KC_HOSTNAME` (hardcoded to `localhost`, per D8/B2's decision) — not against whatever IP the caller happens to be using. The mapper had been set to `10.20.0.2` (matching the OIDC connectivity pattern), which never matches `localhost`. **Fix:** changed the mapper's audience to `http://localhost:8080/realms/swift-devsecops-lab/scim/v2`. **Considered and rejected:** changing `KC_HOSTNAME` to the VM's IP instead — already tried and reverted once (B2) for breaking the admin console; doing it again for SCIM's sake would just reintroduce that same documented failure.

**Known gap — cross-VM SCIM audience.** The current setup only works for SCIM calls made directly against `swift-idp-01` via `localhost`. A future cross-VM caller (e.g., `swift-payment-api` itself) would need an app-side decoupling trick — but SCIM's audience check happens *inside Keycloak*, so there's no equivalent of the OIDC `ISSUER`/`KC_BASE_URL` split available here. Not yet solved.

---

## Documentation & operations

**D16 — Separate `docs/operations-runbook.md` for cross-phase session mechanics.**
The narrative phase runbooks embed `docker`/`gcloud` commands in feature-specific context; the repeated start/stop/health-check mechanics used every session don't belong to any single feature. Consolidated into one dedicated doc instead.

**D17 — Credentials/secrets metadata kept in a separate, local-only file — never inside the committed operations runbook.**
Since the repo is public, even metadata (what secrets exist, where they're stored, how to regenerate) is more useful to an attacker than nothing — a roadmap, even without values. **Chosen convention:** `secure-notes/<filename>`, with the entire `secure-notes/` directory gitignored (not individual filenames), so anything added later is automatically excluded without remembering to update `.gitignore` each time.

**B15 — Stray duplicate runbook file.**
`docs/phase1-runbook_after_lab_completion.md` sat untracked locally, confirmed via `diff` to be byte-identical to the already-tracked `docs/phase1-runbook.md`, and via `git log --all` to have never been tracked on any branch. **Fix:** removed via plain `rm` (not `git rm`, since git never tracked it) — verified the working tree was clean afterward.

**B16 — Wrong active `gcloud` project.**
`gcloud config list` showed `project = cse636-capstone-iac` — a leftover from unrelated coursework, not this project. **Fix:** `gcloud config set project swift-devsecops-lab-01`. **Follow-on bug:** the account then set (`kuldeepjainphotos@gmail.com`) lacked permission on that project ID — resolved by confirming the correct project ID has a `-01` suffix not present in the console's display name (`gcloud projects list --filter="name:swift-devsecops-lab"` surfaced the real ID).

**B17 — `POSTGRES_PASSWORD` printed in plaintext.**
While confirming DB credentials ahead of the pre-SCIM-upgrade backup, `docker exec keycloak-postgres env | grep POSTGRES` printed the actual password value to the terminal. Low risk (lab-only, internal-only Postgres, never left the VM's own console) but a genuine rotation candidate — tracked in `secure-notes/credentials-index.md`.

**Environment note — `swift-lab-vm` runs Container-Optimized OS (COS).** No `apt-get`/general package manager by design (container-only image) — host-level tools like `tree` aren't installable; use `find`, or run a tool inside a throwaway container instead.
