# Vault Policies for Environment Isolation
# Each environment gets read-only access to its own KV mount

resource "vault_policy" "develop" {
  name = "develop"

  policy = <<EOT
# Allow reading secrets from develop KV mount
path "secret-develop/data/*" {
  capabilities = ["read", "list"]
}

# Allow reading metadata
path "secret-develop/metadata/*" {
  capabilities = ["read", "list"]
}
EOT
}

resource "vault_policy" "stage" {
  name = "stage"

  policy = <<EOT
# Allow reading secrets from stage KV mount
path "secret-stage/data/*" {
  capabilities = ["read", "list"]
}

# Allow reading metadata
path "secret-stage/metadata/*" {
  capabilities = ["read", "list"]
}
EOT
}

resource "vault_policy" "production" {
  name = "production"

  policy = <<EOT
# Allow reading secrets from production KV mount
path "secret-production/data/*" {
  capabilities = ["read", "list"]
}

# Allow reading metadata
path "secret-production/metadata/*" {
  capabilities = ["read", "list"]
}
EOT
}

# Admin policy for manual secret management
resource "vault_policy" "admin" {
  name = "admin"

  policy = <<EOT
# Full access to all secret mounts
path "secret-*/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage auth methods
path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

# Manage policies
path "sys/policies/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Manage mounts
path "sys/mounts/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOT
}

# Output the policy names
output "policies" {
  description = "Created Vault policies"
  value = {
    develop    = vault_policy.develop.name
    stage      = vault_policy.stage.name
    production = vault_policy.production.name
    admin      = vault_policy.admin.name
  }
}
