module "discord_bot" {
  source         = "github.com/tayl0rm/terraform-modules/gce-instance"
  gcp_project    = var.gcp_project
  name           = var.bot
  machine_type   = "e2-mirco"
  compute_image  = "europe-west1-docker.pkg.dev/ga-test-project-503ca/core/discord-bot/discord-bot:latest"
  network        = var.network
  subnetwork     = "${var.network}-subnetwork"
  startup_script = "python3 discord_bot/bot.python"

  firewall_protocol = "tcp"
  firewall_port     = ["22"]
  firewall_source   = ["35.235.240.0/20"]

  service_account_roles = [
    "roles/viewer",
    "roles/compute.instanceAdmin.v1"
  ]
}

module "core_network" {
  source                  = "github.com/tayl0rm/terraform-modules/gcp-network"
  gcp_project             = var.gcp_project
  name                    = var.network
  subnetwork_cidr         = "10.1.0.0/26"
  auto_create_subnetworks = false
}

//module "backup_bucket" {
//  source      = "github.com/tayl0rm/terraform-modules/gcs-bucket"
//  gcp_project = var.gcp_project
//  name        = "tayl0rm-server-backup"
// }
