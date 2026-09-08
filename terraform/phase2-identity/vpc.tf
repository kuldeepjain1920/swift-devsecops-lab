# vpc.tf
# Creates a dedicated VPC for identity infrastructure, isolated from the Phase 1
# application VPC. This models real-world network segmentation between the
# identity/security plane and the application plane.

resource "google_compute_network" "idp_vpc" {
  name                    = var.idp_vpc_name
  auto_create_subnetworks = false # Custom-mode VPC — we define subnets explicitly, no default sprawl
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "idp_subnet" {
  name          = "${var.idp_vpc_name}-subnet"
  ip_cidr_range = var.idp_subnet_cidr
  region        = var.region
  network       = google_compute_network.idp_vpc.id

  # Enables Cloud NAT / Private Google Access if needed later without recreating the subnet
  private_ip_google_access = true
}
