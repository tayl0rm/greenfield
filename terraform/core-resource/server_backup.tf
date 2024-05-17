module "backup_bucket" {
  source      = "github.com/tayl0rm/terraform-modules/gcs-bucket"
  gcp_project = var.gcp_project
  name        = "tayl0rm-server-backup"
}
