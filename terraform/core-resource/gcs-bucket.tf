resource "google_storage_bucket" "game_server_backups" {
  name          = "${var.core}-backups"
  location      = "EU"
  force_destroy = true
}
