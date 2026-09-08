# firewall.tf
# Locks down the identity VPC by default and only opens exactly what's needed:
#   - SSH + Keycloak admin console: restricted to your own IP/VPN range
#   - Keycloak service ports (OIDC/SAML endpoints): reachable only from the
#     peered application VPC's subnet, never from the public internet
# This is the network-level enforcement of "identity infra isn't publicly exposed."

resource "google_compute_firewall" "allow_admin_ssh" {
  name    = "${var.idp_vpc_name}-allow-admin-ssh"
  network = google_compute_network.idp_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.admin_source_ip_ranges # e.g. your home/office IP in CIDR form
  target_tags   = ["idp-vm"]
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "${var.idp_vpc_name}-allow-iap-ssh"
  network = google_compute_network.idp_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # Google's fixed IAP forwarding range — required because the VM has no external IP,
  # so `gcloud compute ssh` connects via IAP tunneling instead of direct SSH.
  # IAP's traffic originates from this range, NOT from your own public IP.
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["idp-vm"]
}

resource "google_compute_firewall" "allow_admin_console" {
  name    = "${var.idp_vpc_name}-allow-admin-console"
  network = google_compute_network.idp_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["8080", "8443"] # Keycloak HTTP/HTTPS admin + auth endpoints
  }

  source_ranges = var.admin_source_ip_ranges # Same restricted range as SSH
  target_tags   = ["idp-vm"]
}

resource "google_compute_firewall" "allow_app_vpc_to_keycloak" {
  name    = "${var.idp_vpc_name}-allow-app-vpc-oidc"
  network = google_compute_network.idp_vpc.name

  allow {
    protocol = "tcp"
    # Using 8080 (HTTP) instead of 8443 (HTTPS) as a DELIBERATE, TEMPORARY choice.
    # Keycloak's start-dev mode does not serve HTTPS without an explicitly
    # configured keystore (KC_HTTPS_CERTIFICATE_FILE/KEY_FILE) — attempting to
    # use 8443 without one results in a broken TLS listener (connection resets
    # mid-handshake). Rather than hand-roll a self-signed keystore now, this is
    # intentionally deferred to Phase 3 (PKI, certificates & machine identity),
    # which will issue Keycloak a real certificate as part of that phase's scope.
    # TODO(Phase 3): switch back to 8443 once Keycloak has a proper cert.
    ports    = ["8080", "8443"] # Only the HTTP/HTTPS OIDC/SAML endpoints — not the admin port
  }

  # Restricted to the Phase 1 app subnet's CIDR range, not the whole internet.
  # Confirmed via `gcloud compute networks subnets list` — us-central1's auto-mode
  # subnet on the "default" VPC, where swift-lab-vm (10.128.0.2) actually lives.
  source_ranges = ["10.128.0.0/20"]
  target_tags   = ["idp-vm"]
}

# Implicit deny-all for everything else — GCP VPCs deny by default,
# so no explicit "deny" rule is needed for unlisted ports/sources.
