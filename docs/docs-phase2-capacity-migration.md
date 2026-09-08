## Troubleshooting: e2-small capacity exhaustion (ZONE_RESOURCE_POOL_EXHAUSTED)

### Symptom
`terraform apply` (or `gcloud compute instances start`) fails with:
```
Error: Error waiting for instance to create: The zone '...' does not have
enough resources available to fulfill the request.
```
Hit this in us-central1-a on initial VM creation, again on a later start attempt,
and again in us-central1-b — a real, recurring capacity constraint, not a fluke.

### Fix path 1: Same-region zone change (cheap, minimal blast radius)
Only the VM's `zone` variable changes. Zone is a mutable placement choice within
already-existing regional infrastructure (subnet, router, NAT), so nothing else
is touched.

```hcl
# variables.tf
variable "zone" {
  default = "us-central1-b"  # was us-central1-a
}
```
```bash
terraform plan   # expect: 1 to add, 0 to change, 1 to destroy (VM only)
terraform apply
```

### Fix path 2: Cross-region move (bigger change, needed when the whole region is constrained)
`region` is immutable on subnet, router, and NAT resources — GCP has no "move"
operation for these, only destroy-in-old-region / create-in-new-region.
Terraform shows this explicitly via `# forces replacement` next to `region`
in the plan output.

```hcl
# variables.tf
variable "region" {
  default = "us-west1"   # was us-central1
}
variable "zone" {
  default = "us-west1-b" # was us-central1-b
}
```
```bash
terraform plan   # expect: ~4 to add, 0 to change, ~3 to destroy
                 # (subnet, router, NAT all replaced; VM created fresh)
terraform apply
```

VPC, VPC peering, and firewall rules are NOT region-scoped, so none of those
show up in the plan — only subnet/router/NAT/VM.

### Terraform's actual apply order (dependency-graph driven, not manual)
1. Destroy subnet + NAT in parallel (NAT has no dependency on subnet)
2. Destroy router only after NAT is gone (NAT depends on router)
3. Create router first in the new region
4. Create NAT once router exists (depends on it)
5. Create subnet (independent — runs on its own timeline)
6. Create VM last, once the new subnet exists (VM's network_interface
   references the subnet directly)

Note: VM does NOT have a direct Terraform dependency on NAT, even though it
needs NAT for its startup script to reach the internet. If NAT is slow to
create, the VM could theoretically boot before NAT is ready and its Docker
install would fail the same way the original no-NAT issue did — worth
re-running `sudo google_metadata_script_runner startup` manually if that happens.

### Post-move checklist
- [ ] Update zone flag in every subsequent gcloud command (ssh, scp, describe)
- [ ] Re-copy docker-compose.yml + .env to the new VM (fresh disk — nothing persists)
- [ ] Re-verify Docker installed via startup script log
- [ ] Re-bring-up Keycloak containers
- [ ] Confirm app VPC (default, auto-mode) already has a subnet in the new
      region automatically — no peering changes needed either way
