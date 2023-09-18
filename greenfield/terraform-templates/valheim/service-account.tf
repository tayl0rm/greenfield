locals {
  valheim_core_service_account_roles = [
    "roles/compute.instanceAdmin.v1",
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
    "roles/logging.logWriter"
  ]
}

resource "google_service_account" "valheim_core_service_account" {
  account_id   = var.valheim_core
  display_name = var.valheim_core
  description  = "A service account used by the Valheim Core game server to access GCP resources."
}

resource "google_project_iam_member" "valheim_core_service_account_iam" {
  for_each = toset(local.valheim_core_service_account_roles)

  project = var.gcp_project
  role = each.value
  member = "serviceAccount:${google_service_account.valheim_core_service_account.email}"
}
