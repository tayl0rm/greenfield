module "valheim_server" {
  source        = "github.com/tayl0rm/terraform-modules/gce-instance"
  gcp_project   = "ga-test-project-503ca"
  name          = var.valheim_server
  compute_image = "europe-west1-docker.pkg.dev/ga-test-project-503ca/core/valheim/valheim-core:latest"
  network       = var.network
  subnetwork    = var.subnetwork

  startup_script = file("scripts/vm_startup_script.sh")

  firewall_protocol = "udp"
  firewall_port     = "2456-2457"
  firewall_source   = "0.0.0.0/0"

  service_account_roles = [
    "roles/storage.objectUser",
    "roles/viewer"
  ]
}