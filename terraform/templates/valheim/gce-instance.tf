resource "google_compute_address" "valheim_core_instance_ip" {
  name         = "${var.valheim_core}-server-ip"
  address_type = "EXTERNAL"
  purpose      = "GCE_ENDPOINT"
}

resource "google_compute_instance" "valheim_core_instance" {
  name         = "${var.valheim_core}-server"
  machine_type = "e2-medium"
  zone         = "${var.region}-b"
  tags         = [var.valheim_core, "troubleshooting"]

  boot_disk {
    initialize_params {
      image = "europe-west1-docker.pkg.dev/ga-test-project-503ca/core/valheim-core:latest" # Custom Valheim image in Artifact Registry
    }
  }

  network_interface {
    network    = "core"
    subnetwork = "core-subnetwork"
    network_ip = google_compute_address.valheim_core_instance_ip.address
  }

  service_account {
    email  = google_service_account.valheim_core_service_account.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = "echo hi > /test.txt"
}
