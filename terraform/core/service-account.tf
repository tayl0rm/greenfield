locals {
  discord_bot_service_account_roles = [
    "roles/compute.instanceAdmin.v1",
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
    "roles/logging.logWriter",
    "roles/iam.serviceAccountTokenCreator"
  ]
}

resource "google_service_account" "discord_service_account" {
  account_id   = var.valheim_core
  display_name = var.valheim_core
  description  = "A service account used by the Discord Bot to access GCP resources."
}

resource "google_project_iam_member" "discord_bot_service_account_iam" {
  for_each = toset(local.discord_bot_service_account_roles)

  project = var.gcp_project
  role = each.value
  member = "serviceAccount:${google_service_account.discord_service_account.email}"
}
