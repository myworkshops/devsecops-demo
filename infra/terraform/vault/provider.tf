terraform {
  required_version = ">= 1.5.0"

  required_providers {
    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.7.0"
    }
  }
}

provider "vault" {
  address = var.vault_addr
  token   = var.vault_token

  # Skip TLS verification for local development
  # In production, set this to true and provide proper certificates
  skip_tls_verify = true
}
