terraform {
  backend "gcs" {
    bucket      = "mtaylor-terraform-state-backup"
    prefix      = "terraform/state/core-resources"
  }
}
