terraform {
  required_version = ">= 1.17"
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
  validation {
    condition     = length(var.db_password) > 0
    error_message = "db_password is empty. Set TF_VAR_db_password."
  }
}

resource "hcloud_server" "web" {
  name        = "acme-web-development"
  server_type = "cx22"
  image       = "ubuntu-24.04"
}
