provider "google" {
  version     = ">= 4.8.0"
  project     = var.gcp_project
  region      = var.region
}
