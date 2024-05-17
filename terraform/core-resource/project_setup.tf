resource "google_project_service" "enabled_project_apis" {
  for_each = local.project_api
  project  = var.gcp_project
  service  = each.value
}
