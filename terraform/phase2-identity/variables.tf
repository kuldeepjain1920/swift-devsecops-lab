# variables.tf
# Centralizes all configurable inputs so this module is reusable and doesn't hardcode
# environment-specific values inside the resource definitions themselves.

variable "project_id" {
  description = "GCP project ID hosting all lab resources"
  type        = string
  default     = "swift-devsecops-lab-01" # Same project used in Phase 1
}

variable "region" {
  description = "GCP region for regional resources (subnets, VM)"
  type        = string
  default     = "us-west1" # Moved from us-central1 due to repeated e2-small capacity stockouts in both us-central1-a and us-central1-b
}

variable "zone" {
  description = "GCP zone for the identity VM"
  type        = string
  default     = "us-west1-b" # Moved from us-central1-a/b due to repeated e2-small capacity stockouts
}

# --- New identity VPC ---

variable "idp_vpc_name" {
  description = "Name of the new, dedicated VPC for identity infrastructure"
  type        = string
  default     = "swift-idp-vpc"
}

variable "idp_subnet_cidr" {
  description = "CIDR range for the identity VPC's subnet"
  type        = string
  default     = "10.20.0.0/24" # Deliberately non-overlapping with the app VPC's range
}

# --- Existing application VPC (Phase 1) — required for peering ---
# NOTE: fill these in with your Phase 1 VPC/subnet names once confirmed;
# defaults below assume GCP's auto-created "default" VPC, which is what
# most quick-start GCE deployments (like Phase 1) use unless changed.

variable "app_vpc_name" {
  description = "Name of the existing application VPC from Phase 1, to peer with"
  type        = string
  default     = "default"
}

# --- Identity VM ---

variable "idp_vm_name" {
  description = "Name of the Keycloak identity VM"
  type        = string
  default     = "swift-idp-01"
}

variable "idp_machine_type" {
  description = "Machine type for the identity VM (Keycloak is lightweight at lab scale)"
  type        = string
  default     = "e2-small"
}

variable "idp_image" {
  description = "Boot image for the identity VM"
  type        = string
  default     = "debian-cloud/debian-12"
}

variable "admin_source_ip_ranges" {
  description = "CIDR ranges allowed to reach the Keycloak admin console and SSH (your IP or VPN range — never 0.0.0.0/0 for admin access)"
  type        = list(string)
  default     = [] # Intentionally empty — must be set explicitly, see terraform.tfvars.example
}
