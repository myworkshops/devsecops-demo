variable "vault_addr" {
  description = "Vault server address"
  type        = string
  default     = "http://vault.vault.svc.cluster.local:8200"
}

variable "vault_token" {
  description = "Vault root token for authentication"
  type        = string
  sensitive   = true
}

variable "kubernetes_host" {
  description = "Kubernetes API server host"
  type        = string
}

variable "token_reviewer_jwt" {
  description = "Service Account JWT token for Kubernetes authentication"
  type        = string
  sensitive   = true
}

variable "kubernetes_ca_cert" {
  description = "Kubernetes CA certificate (base64 encoded)"
  type        = string
  sensitive   = true
}

variable "environments" {
  description = "List of environments to create resources for"
  type        = list(string)
  default     = ["develop", "stage", "production"]
}
