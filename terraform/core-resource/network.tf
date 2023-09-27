resource "google_compute_network" "game_server_vpc_network" {
  name                    = var.core
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "game_server_subnetwork" {
  name          = "${var.core}-subnetwork"
  ip_cidr_range = "10.1.0.0/24"
  region        = var.region
  network       = google_compute_network.game_server_vpc_network.id
}
