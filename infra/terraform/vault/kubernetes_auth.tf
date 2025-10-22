# Kubernetes Authentication Backend Configuration
# Allows Kubernetes pods to authenticate to Vault using their ServiceAccount tokens

resource "vault_auth_backend" "kubernetes" {
  type = "kubernetes"
  path = "kubernetes"

  description = "Kubernetes authentication backend for pod-to-Vault authentication"
}

resource "vault_kubernetes_auth_backend_config" "this" {
  backend = vault_auth_backend.kubernetes.path

  kubernetes_host    = var.kubernetes_host
  token_reviewer_jwt = var.token_reviewer_jwt
  kubernetes_ca_cert = base64decode(var.kubernetes_ca_cert)
}

# Kubernetes Auth Roles for each environment
# Each role is bound to the vault-sa ServiceAccount in its respective namespace

resource "vault_kubernetes_auth_backend_role" "develop" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "develop"
  bound_service_account_names      = ["vault-sa"]
  bound_service_account_namespaces = ["develop"]

  token_policies = [vault_policy.develop.name]
  token_ttl      = 3600  # 1 hour
}

resource "vault_kubernetes_auth_backend_role" "stage" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "stage"
  bound_service_account_names      = ["vault-sa"]
  bound_service_account_namespaces = ["stage"]

  token_policies = [vault_policy.stage.name]
  token_ttl      = 3600  # 1 hour
}

resource "vault_kubernetes_auth_backend_role" "production" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "production"
  bound_service_account_names      = ["vault-sa"]
  bound_service_account_namespaces = ["production"]

  token_policies = [vault_policy.production.name]
  token_ttl      = 3600  # 1 hour
}

# Output the auth backend path and role names
output "kubernetes_auth" {
  description = "Kubernetes auth backend configuration"
  value = {
    backend_path = vault_auth_backend.kubernetes.path
    roles = {
      develop    = vault_kubernetes_auth_backend_role.develop.role_name
      stage      = vault_kubernetes_auth_backend_role.stage.role_name
      production = vault_kubernetes_auth_backend_role.production.role_name
    }
  }
}
