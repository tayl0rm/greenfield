resource "google_compute_firewall" "core_firewall" {
  name    = "${var.core}-troubleshooting-firewall"
  network = google_compute_network.game_server_vpc_network.name
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  source_tags   = ["troubleshooting"]
  source_ranges = ["35.235.240.0/20"] # Google IAP Service CIDR
}

