terraform {
  backend "gcs" {
    bucket      = "terraform_state_backup"
    prefix      = "terraform/state/game-servers/valheim"
  }
}
