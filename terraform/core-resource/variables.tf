variable "core" {
  default     = "core"
  description = "Generic name for resources dedicated to the game servers."
}

variable "bot" {
  default     = "discord-bot"
  description = "Generic name for resources dedicated to the Discord bot."
}

variable "region" {
  default     = "europe-west1"
  description = "Default GCP region for Valheim server resources."
}

variable "gcp_project" {
  default     = "ga-test-project-503ca"
  description = "Default GCP Project to deploy all resources into."
}

variable "network" {
  default = "core"
  type    = string
}
