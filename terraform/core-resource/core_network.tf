module "core_network" {
  source                  = "github.com/tayl0rm/terraform-modules/gcp-network"
  gcp_project             = var.gcp_project
  name                    = var.network
  subnetwork_cidr         = "10.1.0.0/26"
  auto_create_subnetworks = false
}
