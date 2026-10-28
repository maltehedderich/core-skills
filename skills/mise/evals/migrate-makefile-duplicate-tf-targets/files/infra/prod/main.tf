terraform {
  required_version = ">= 1.9"
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "~> 1.48"
    }
  }
}

variable "db_password" {
  type      = string
  sensitive = true
}

resource "hcloud_server" "api" {
  name        = "acme-api-prod"
  server_type = "cx22"
  image       = "ubuntu-24.04"
}
