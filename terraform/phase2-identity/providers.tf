# providers.tf
# Declares which provider (Google Cloud) Terraform should use and pins its version
# so that `terraform init` fetches a predictable, repeatable provider release.

terraform {
  required_version = ">= 1.5.0" # Minimum Terraform CLI version this config is tested against

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Pin to the 5.x series of the Google provider
    }
  }

  # Uncomment and configure this block once you're ready to store state remotely
  # (recommended before Phase 6, so multiple phases can share/reference state safely).
  # backend "gcs" {
  #   bucket = "swift-devsecops-lab-tfstate"
  #   prefix = "phase2-identity"
  # }
}

provider "google" {
  project = var.project_id # GCP project to deploy into (swift-devsecops-lab-01)
  region  = var.region     # Default region for regional resources
}
