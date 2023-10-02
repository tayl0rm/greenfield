provider "google" {
    credentials = var.GOOGLE_CREDENTIALS
    version = ">= 4.8.0"
    project = var.gcp_project
    region  = var.region
}