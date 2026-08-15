# peering.tf
# Connects the new identity VPC to the existing Phase 1 application VPC via
# VPC Network Peering. This lets the FastAPI service reach Keycloak (and vice versa)
# over private internal IPs, without exposing either service to the public internet.
#
# Peering is deliberately two directional resources — GCP requires both sides
# to declare the peering relationship before traffic flows.

data "google_compute_network" "app_vpc" {
  name = var.app_vpc_name # References the existing Phase 1 VPC by name (not managed here)
}

resource "google_compute_network_peering" "idp_to_app" {
  name         = "idp-to-app-peering"
  network      = google_compute_network.idp_vpc.self_link
  peer_network = data.google_compute_network.app_vpc.self_link
}

resource "google_compute_network_peering" "app_to_idp" {
  name         = "app-to-idp-peering"
  network      = data.google_compute_network.app_vpc.self_link
  peer_network = google_compute_network.idp_vpc.self_link
}
