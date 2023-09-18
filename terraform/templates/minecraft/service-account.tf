locals {
  minecraft_core_service_account_roles = [
    "roles/compute.instanceAdmin.v1",
    "roles/storage.objectViewer",
    "roles/storage.objectCreator",
    "roles/logging.logWriter"
  ]
}

resource "google_service_account" "minecraft_core_service_account" {
  account_id   = var.minecraft_core
  display_name = var.minecraft_core
  description  = "A service account used by the Minecraft Core game server to access GCP resources."
}

resource "google_project_iam_member" "minecraft_core_service_account_iam" {
  for_each = toset(local.minecraft_core_service_account_roles)

  role = each.value
  member = "serviceAccount:${google_service_account.minecraft_core_service_account}"
}
