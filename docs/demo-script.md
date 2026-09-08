# Demo Script — 15-Minute Walkthrough

A live-demo script for showing this project to an interviewer or reviewer. Each section has a target time, the exact commands to run, and what to say while running them. Practice once end-to-end before using this live — timings assume you're not troubleshooting.

**Before starting:** both VMs should already be running (start them ~5 minutes before the demo begins, per `docs/operations-runbook.md`, so nothing is waiting on VM boot time during the actual walkthrough). Re-check `swift-lab-vm`'s external IP and update the SAML client if it's changed (§4 of the operations runbook) — do this before the demo, not during it.

---

## 0. Setup (before the interviewer joins — not part of the timed 15 minutes)

**Where: your Mac**
```bash
gcloud compute instances list
# Confirm both swift-idp-01 and swift-lab-vm show RUNNING
```

Open two terminal tabs, SSH'd in and ready:
```bash
# Tab 1
gcloud compute ssh swift-idp-01 --zone us-west1-b --tunnel-through-iap

# Tab 2
gcloud compute ssh swift-lab-vm --zone us-central1-a --tunnel-through-iap
```

Have a browser tab open (private/incognito, so no stale Keycloak session interferes) at the ready but not yet navigated anywhere.

---

## 1. The pitch (1 minute, no commands)

*"This is a payment-message API modeled loosely on SWIFT's message flow — validate, sign, encrypt, route. On top of that I built a full identity and authorization layer: OIDC, SAML, and SCIM as three different identity protocols talking to a real Keycloak instance, plus two layers of authorization — role-based and attribute-based, the second one via a policy engine called OPA. I'll show all of it live against real infrastructure, not mocked."*

---

## 2. RBAC + ABAC — the core authorization story (5 minutes)

This is the centerpiece: one endpoint, two independent authorization layers, four real users proving all four combinations.

**Where: swift-lab-vm (Tab 2)**
```bash
bash ~/test_rbac.sh
```

While it runs (prompts for four passwords — have them ready, typed from memory or pasted from your password manager, not read aloud):

*"First call: test-initiator, a normal payment under the threshold — 201, goes through the full pipeline. Second: test-approver, a completely different role, tries the same call — 403, and you can see the exact error names the role it's missing. Third — this is the interesting one — test-initiator again, but now a large amount. Same role that just succeeded, but this time it's blocked. That's not RBAC anymore — that's a second authorization layer, OPA, evaluating a policy that says large amounts need dual authorization. Fourth: a user with both roles, same large amount — now it's allowed."*

**What to point at in the output:**
- The two different 403 error messages — one says `"Requires one of roles..."` (RBAC), the other says `"OPA policy denied: amount..."` (ABAC) — call out that these are genuinely two different systems, not one masking the other
- The `acked` status and the encrypted `account_number` in the successful response — proves the full Phase 1 pipeline actually ran, not just an auth check in isolation

---

## 3. The policy itself (2 minutes)

**Where: your Mac** (have this file already open in an editor, or `cat` it)
```bash
cat identity/opa/policies/payment_authz.rego
```

*"This is the actual policy — it's not Python if-statements scattered through the app, it's a separate declarative file, versioned and testable on its own."*

```bash
opa test identity/opa/policies/ identity/opa/tests/ -v
```

*"These three tests run completely offline, no VM, no network — I can validate policy logic changes before ever deploying them."*

---

## 4. SAML — a second identity protocol (3 minutes)

**Where: browser**

Navigate to:
```
http://localhost:8080/realms/swift-devsecops-lab/protocol/saml/clients/swift-payment-api-saml
```
*(assumes the admin tunnel from setup is still open — if not, reopen: `gcloud compute ssh swift-idp-01 --zone us-west1-b --tunnel-through-iap -- -L 8080:localhost:8080`)*

Log in as `test-initiator`.

*"Keycloak just built a signed XML assertion and POSTed it straight to my app — no redirect page, just a form auto-submit. My app decoded it, parsed the XML, and here's the response."*

**Point at the returned JSON:**
- `name_id` matching the user that just logged in
- The `Role` attribute showing `payment-initiator` specifically (not a generic placeholder — mention this took a real fix, a missing role mapper, if asked about debugging)
- The `"note": "Signature NOT verified"` field — *"I'm upfront about this — verifying the signature needs real certificate handling, which is scoped into my next phase, PKI and machine identity. I flagged it explicitly in the code rather than silently skipping it."*

---

## 5. SCIM — identity lifecycle, not just login (3 minutes)

**Where: swift-idp-01 (Tab 1)**
```bash
bash ~/test_scim.sh
```

*"This is a different problem from OIDC and SAML — those only fire when someone logs in. If someone leaves the company and never logs in again, a login-only system's stale account lives forever. SCIM is how an identity provider pushes lifecycle changes — create, deactivate — independent of any login."*

**Point at the output:**
- The `201` with a real generated user ID
- The `200` on the PATCH deactivating it
- The final `kcadm.sh` check showing `enabled: false` — *"That's Keycloak's own admin API confirming this landed on a real user record, not just a SCIM-layer response."*

*(Mention if relevant: "Keycloak's native SCIM support is brand new — I actually upgraded Keycloak mid-project specifically to get it, with a database backup first in case the upgrade broke anything.")*

---

## 6. Close (1 minute, no commands)

*"Everything you just saw is running on real GCP infrastructure — two VMs, a real Keycloak instance, real Postgres — not mocked or stubbed. I've documented every real bug I hit along the way in a decisions log, including root causes, not just the fixes — happy to walk through any of those in more depth."*

Have `docs/decisions.md` open and ready in case they want to see it.

---

## Fallback plan if something breaks live

- **VM/container won't start:** have `docker logs <container>` output from a recent successful run ready to show as a screenshot/screen-share fallback, and narrate what it *should* show.
- **SAML redirect fails:** almost certainly the ephemeral-IP issue (§4 of the operations runbook) — acknowledge it directly: *"This is a known limitation I've documented — the VM's IP isn't reserved, so it changes on restart. In a real deployment this would sit behind a static IP or load balancer."* This is a good answer, not a bad one — it shows you understand the gap.
- **A password doesn't work:** have `secure-notes/credentials-index.md`'s regeneration steps memorized well enough to reset one live if truly necessary, or skip that one test case and move on — don't let one failed step derail the whole demo.

---

## Command cheat-sheet (copy-paste order, no narration)

```bash
# Setup
gcloud compute instances list
gcloud compute ssh swift-idp-01 --zone us-west1-b --tunnel-through-iap
gcloud compute ssh swift-lab-vm --zone us-central1-a --tunnel-through-iap

# RBAC/ABAC (swift-lab-vm)
bash ~/test_rbac.sh

# Policy (Mac)
cat identity/opa/policies/payment_authz.rego
opa test identity/opa/policies/ identity/opa/tests/ -v

# SAML (browser)
# http://localhost:8080/realms/swift-devsecops-lab/protocol/saml/clients/swift-payment-api-saml

# SCIM (swift-idp-01)
bash ~/test_scim.sh
```
