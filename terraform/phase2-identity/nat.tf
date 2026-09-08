# nat.tf
# swift-idp-01 has no external IP by design (admin access goes through IAP, not
# a public IP). But private_ip_google_access only covers Google APIs — it does NOT
# give the VM a path to the general internet. Without this, apt-get/curl calls to
# deb.debian.org or download.docker.com fail outright, which is exactly what broke
# the Docker install startup script.
#
# Cloud NAT solves this: it lets instances in this VPC reach the internet
# for outbound requests, while still keeping them unreachable from the internet
# inbound (NAT is one-directional — outbound only).

resource "google_compute_router" "idp_router" {
  name    = "${var.idp_vpc_name}-router"
  network = google_compute_network.idp_vpc.id
  region  = var.region
}

resource "google_compute_router_nat" "idp_nat" {
  name                               = "${var.idp_vpc_name}-nat"
  router                             = google_compute_router.idp_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY" # Google manages NAT IPs automatically — no static IP needed
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY" # Keeps logs light — just enough to debug future connectivity issues
  }
}
