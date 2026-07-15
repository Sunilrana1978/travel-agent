terraform {
  backend "gcs" {
    bucket = "travel-agent-502518-terraform-state"
    prefix = "travel-agent/prod"
  }
}
