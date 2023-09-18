resource "google_compute_firewall" "valheim_core_firewall" {
  name    = "${var.valheim_core}-firewall"
  network = "core"
  allow {
    protocol = "udp"
    ports    = ["2456-2457"]
  }
  source_tags   = [var.valheim_core]
  source_ranges = ["0.0.0.0/0"]
}

