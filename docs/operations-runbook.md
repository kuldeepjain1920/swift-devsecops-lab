# Operations Runbook — Session Start / Stop

**Last verified working:** 2026-09-08
**Purpose:** the repeated, cross-phase mechanics of bringing this lab up and down — not tied to any single feature, unlike the phase runbooks. If a step here goes stale, update the date above once re-verified.
**Secrets:** none live in this file. See your local credentials index (`secure-notes/`, gitignored) for what each secret is and how to regenerate it.

---

## Quick reference

| Container | Runs on | Zone | Port(s) | Purpose |
|---|---|---|---|---|
| `keycloak` | swift-idp-01 | us-west1-b | 8080 (HTTP), 8443 (HTTPS) | Identity provider — OIDC, SAML, SCIM |
| `keycloak-postgres` | swift-idp-01 | us-west1-b | 5432 (internal only, not host-mapped) | Keycloak's database |
| `swift-payment-api` | swift-lab-vm | us-central1-a | 8000 | The FastAPI app |
| `opa` | swift-lab-vm | us-central1-a | 8181 (internal only, via `swift-lab-net`, not host-mapped) | ABAC policy engine |

| VM | Zone | Internal IP | External IP |
|---|---|---|---|
| `swift-idp-01` | us-west1-b | 10.20.0.2 | none needed (admin access via IAP tunnel only) |
| `swift-lab-vm` | us-central1-a | 10.128.0.2 | **ephemeral** — reassigned on every stop/start, see §4 below |

Docker network: `swift-lab-net` (user-defined bridge, on `swift-lab-vm` only) — lets `swift-payment-api` and `opa` resolve each other by container name.

---

## 1. Full start sequence

**Where: your Mac** — start both VMs:
```bash
gcloud compute instances start swift-idp-01 --zone us-west1-b
gcloud compute instances start swift-lab-vm --zone us-central1-a
```

**Where: your Mac** — open the admin console tunnel (separate terminal, leave running for the session):
```bash
gcloud compute ssh swift-idp-01 --zone us-west1-b --tunnel-through-iap -- -L 8080:localhost:8080
```
Browser: `http://localhost:8080/admin`

**Where: swift-idp-01** (new terminal, SSH in normally):
```bash
gcloud compute ssh swift-idp-01 --zone us-west1-b --tunnel-through-iap
```
Then start Keycloak + Postgres — use `docker compose up -d` rather than individual `docker start` commands, so Compose's `depends_on` ordering (Postgres before Keycloak) is honored automatically:
```bash
cd ~/keycloak
docker compose up -d
```

**Where: swift-lab-vm** (new terminal):
```bash
gcloud compute ssh swift-lab-vm --zone us-central1-a --tunnel-through-iap
```
Start OPA before the app — not strictly required (the app calls OPA lazily per request), but keeps the health-check step below meaningful in order:
```bash
docker start opa
docker start swift-payment-api
```

### Health checks — confirm all four before doing anything else

**Where: swift-idp-01**
```bash
docker logs keycloak --tail 20
# Expect: normal startup log, no exceptions

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/realms/swift-devsecops-lab/scim/v2/Users
# Expect: 401 (endpoint exists, needs auth). A 404 here means scimApiEnabled
# didn't survive the restart — re-check via kcadm.sh (see §5).
```

**Where: swift-lab-vm**
```bash
docker logs swift-payment-api --tail 20
# Expect: "Application startup complete", no traceback

docker exec swift-payment-api python3 -c "import httpx; print(httpx.get('http://opa:8181/health').text)"
# Expect: {}
```

---

## 2. Full stop sequence

**Where: swift-idp-01**
```bash
docker stop keycloak keycloak-postgres
```

**Where: swift-lab-vm**
```bash
docker stop swift-payment-api opa
```

**Where: your Mac**
```bash
gcloud compute instances stop swift-idp-01 --zone us-west1-b
gcloud compute instances stop swift-lab-vm --zone us-central1-a
```

Stopping the VMs directly (skipping the container-stop step above) is also safe — GCP's VM shutdown stops Docker's containers as part of the normal OS shutdown anyway. The explicit container-stop is just cleaner, giving each container its own graceful shutdown window first.

---

## 3. Admin console tunnel (quick reference)

```bash
gcloud compute ssh swift-idp-01 --zone us-west1-b --tunnel-through-iap -- -L 8080:localhost:8080
```
Browser: `http://localhost:8080/admin`

---

## 4. SAML: re-check the ephemeral external IP every session

`swift-lab-vm`'s external IP is **not reserved** — it's very likely different after every stop/start. The SAML client's redirect URI and Master SAML Processing URL are both hardcoded to a specific IP, so a stale value will silently break SAML testing with no obvious error pointing at "the IP changed."

**Where: your Mac** — check the current IP:
```bash
gcloud compute instances describe swift-lab-vm --zone us-central1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

If it's different from last session:

**Where: browser, admin console** → Clients → `swift-payment-api-saml` → Settings:
- **Valid redirect URIs**: update to `http://<new IP>:8000/saml/acs*`
- **Master SAML Processing URL**: update to `http://<new IP>:8000/saml/acs`
- Save

Also worth a quick check that the `allow-lab-app` firewall rule still matches your current public IP, since that's a separate `/32` rule that can also drift (your home/current IP, not the VM's):
```bash
curl -s -4 ifconfig.me
gcloud compute firewall-rules list --format="table(name,sourceRanges.list(),allowed[].map().firewall_rule().list())"
```

---

## 5. `kcadm.sh` sessions expire between VM restarts (and sometimes within a session)

Any `kcadm.sh` command inside the `keycloak` container will fail with `Session has expired` if the last login was more than a short while ago. Re-authenticate before running any admin CLI command (enabling `scimApiEnabled`, resetting a test user's password, etc.):

**Where: swift-idp-01**
```bash
docker exec -it keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user kuldeep-admin
# (hidden password prompt — no --password flag, keeps it out of bash history and `ps aux`)
```
