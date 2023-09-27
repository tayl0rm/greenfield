resource "google_compute_address" "discord_bot_instance_ip" {
  name         = "${var.bot}-ip"
  address_type = "EXTERNAL"
  purpose      = "GCE_ENDPOINT"
}

resource "google_compute_instance" "discord_bot_instance" {
  name         = "${var.bot}-server"
  machine_type = "e2-micro"
  zone         = "${var.region}-b"
  tags         = [var.bot, "troubleshooting"]

  boot_disk {
    initialize_params {
      image = "europe-west1-docker.pkg.dev/ga-test-project-503ca/core/discord-bot/discord-bot:latest" # Discord Bot image in Artifact Registry
    }
  }

  network_interface {
    network    = google_compute_network.game_server_vpc_network.name
    subnetwork = google_compute_subnetwork.game_server_subnetwork.name
    network_ip = google_compute_address.discord_bot_instance_ip.address
  }

  service_account {
    email  = google_service_account.discord_service_account.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = "python3 discord_bot/bot.py"
}
