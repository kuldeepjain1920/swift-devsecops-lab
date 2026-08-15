# vm.tf
# Provisions the identity VM itself and bootstraps Docker via a startup script,
# so Keycloak can be brought up with `docker compose up` immediately after
# the VM is created — no manual SSH setup steps required.

resource "google_compute_instance" "idp_vm" {
  name         = var.idp_vm_name
  machine_type = var.idp_machine_type
  zone         = var.zone
  tags         = ["idp-vm"] # Matches firewall target_tags above

  boot_disk {
    initialize_params {
      image = var.idp_image
      size  = 20 # GB — enough for Docker images + Keycloak + Postgres data
    }
  }

  network_interface {
    network    = google_compute_network.idp_vpc.id
    subnetwork = google_compute_subnetwork.idp_subnet.id
    # No external IP by default — intentional. Admin access should go through
    # IAP tunneling or a bastion, not a public IP. Uncomment access_config{} only
    # if you need a temporary public IP for initial testing.
    # access_config {}
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Installs Docker Engine + Compose plugin on first boot so Keycloak
    # can be deployed immediately without manual SSH setup.
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  EOF

  labels = {
    phase = "phase2-identity" # Tags this resource for cost/usage tracking by lab phase
  }
}
