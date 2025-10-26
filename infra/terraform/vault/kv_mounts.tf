# KV Secrets Engine v2 for each environment
# These will store MongoDB credentials, API secrets, and Keycloak client secrets

# Admin secrets mount for platform credentials (Keycloak, etc.)
resource "vault_mount" "kv_admin" {
  path        = "secret"
  type        = "kv"
  description = "KV v2 secrets engine for platform administrative secrets"

  options = {
    version = "2"
  }
}

resource "vault_mount" "kv_develop" {
  path        = "secret-develop"
  type        = "kv"
  description = "KV v2 secrets engine for develop environment"

  options = {
    version = "2"
  }
}

resource "vault_mount" "kv_stage" {
  path        = "secret-stage"
  type        = "kv"
  description = "KV v2 secrets engine for stage environment"

  options = {
    version = "2"
  }
}

resource "vault_mount" "kv_production" {
  path        = "secret-production"
  type        = "kv"
  description = "KV v2 secrets engine for production environment"

  options = {
    version = "2"
  }
}

# Output the mount paths for reference
output "kv_mounts" {
  description = "KV mount paths for each environment"
  value = {
    develop    = vault_mount.kv_develop.path
    stage      = vault_mount.kv_stage.path
    production = vault_mount.kv_production.path
  }
}
