variable "valheim_core" {
  default     = "valheim"
  description = "Generic name for resources dedicated to the Valheim server."
}

variable "region" {
  default     = "europe-west1"
  description = "Default GCP region for Valheim server resources."
}

variable "gcp_project" {
  default     = "ga-test-project-503ca"
  description = "Default GCP Project to deploy all resources into."
}
