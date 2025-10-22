# Vault Terraform Configuration

Configures HashiCorp Vault with environment isolation for the DevSecOps platform.

## Resources Created

1. **KV Secrets Engine v2** - Three mounts: `secret-develop`, `secret-stage`, `secret-production`
2. **Vault Policies** - Read-only access per environment + admin policy
3. **Kubernetes Auth Backend** - Allows pod authentication with `vault-sa` ServiceAccount

## Usage

This configuration is automatically applied by `bootstrap.py`. For manual execution:

```bash
export VAULT_ADDR="http://<vault-ip>:8200"
export VAULT_TOKEN="<root-token>"
export TF_VAR_kubernetes_host=$(kubectl config view --raw -o jsonpath='{.clusters[].cluster.server}')
export TF_VAR_token_reviewer_jwt=$(kubectl create token vault-sa -n vault --duration=87600h)
export TF_VAR_kubernetes_ca_cert=$(kubectl config view --raw -o jsonpath='{.clusters[].cluster.certificate-authority-data}')

terraform init
terraform apply
```

## Secret Structure

```
secret-{env}/
├── mongodb/          # MongoDB credentials
├── keycloak/         # Keycloak client secrets
└── apis/             # API keys
```

## Notes

- All deployment steps are automated in `bootstrap.py`
- Never commit `terraform.tfstate` (contains sensitive data)
- In production: enable TLS, audit logging, and auto-unseal
