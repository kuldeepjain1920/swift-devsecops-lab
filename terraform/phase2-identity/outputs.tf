# outputs.tf
# Surfaces useful values after `terraform apply` so they're easy to reference
# when configuring Keycloak or writing the runbook, without digging through the console.

output "idp_vm_internal_ip" {
  description = "Internal IP of the identity VM — used by the app VPC to reach Keycloak"
  value       = google_compute_instance.idp_vm.network_interface[0].network_ip
}

output "idp_vpc_self_link" {
  description = "Self-link of the identity VPC, useful for verifying the peering config"
  value       = google_compute_network.idp_vpc.self_link
}

output "idp_subnet_cidr" {
  description = "CIDR range of the identity subnet — reference this when writing app-side firewall rules"
  value       = google_compute_subnetwork.idp_subnet.ip_cidr_range
}
