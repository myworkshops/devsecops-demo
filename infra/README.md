# Infrastructure Automation

Automated DevSecOps infrastructure deployment for k3d cluster with Vault, Keycloak, Jenkins, MongoDB, and External Secrets Operator.

## Prerequisites

- **Docker** (running)
- **k3d** v5.x
- **kubectl** v1.28+
- **helm** v3.x
- **ansible** v2.15+
- **terraform** v1.5+
- **python3** 3.11+

## Quick Start

### 1. Configuration

Copy and customize secrets:
```bash
cp secrets.local.yaml.example secrets.local.yaml
# Edit secrets.local.yaml with your credentials
```

### 2. Deploy Infrastructure

```bash
python3 bootstrap.py
```

**Options:**
- `--servers N` - Number of k3d server nodes (default: 1)
- `--agents N` - Number of k3d agent nodes (default: 2)
- `--cluster-name NAME` - Cluster name (default: cka)
- `--skip-cluster` - Skip cluster creation (use existing)
- `--debug` - Enable debug logging

**Example:**
```bash
python3 bootstrap.py --servers 1 --agents 2 --cluster-name dev
```

## What Gets Deployed

The bootstrap script deploys the following stack:

### 1. **k3d Cluster**
- 1 server node + 2 agent nodes (configurable)
- Loadbalancer ports: 80, 443

### 2. **HashiCorp Vault** (HA mode)
- Namespace: `vault`
- 2 replicas with Raft storage
- Auto-initialized and unsealed
- Kubernetes auth enabled

### 3. **Keycloak** (OIDC)
- Namespace: `keycloak`
- PostgreSQL backend
- Realms: dev, staging, prod
- Roles: admin, operator
- Auto-configured users per realm

### 4. **Jenkins** (CI/CD)
- Namespace: `jenkins`
- JCasC auto-configuration
- Shared library configured
- Vault integration for secrets

### 5. **MongoDB Community Operator**
- Namespace: `mongodb`
- Ready for MongoDB deployments

### 6. **External Secrets Operator**
- Namespace: `external-secrets`
- Syncs secrets from Vault to K8s

## Infrastructure Components

```
├── ansible/              # Ansible playbooks
│   ├── keycloak/        # Keycloak configuration
│   ├── jenkins/         # Jenkins setup
│   ├── vault/           # Vault init/unseal
│   └── verify-*.yml     # Verification playbooks
├── helm/                # Helm values
│   ├── vault/
│   ├── keycloak/
│   ├── jenkins/
│   ├── mongodb/
│   └── external-secrets/
├── terraform/           # Terraform modules
│   └── vault/          # Vault policies & secrets engines
├── bootstrap.py        # Main deployment script
└── secrets.local.yaml  # Your credentials (not versioned)
```

## Accessing Services

After deployment, access services via port-forward:

**Vault:**
```bash
kubectl port-forward -n vault svc/vault 8200:8200
# URL: http://localhost:8200
# Token: Check bootstrap output
```

**Keycloak:**
```bash
kubectl port-forward -n keycloak svc/keycloak 8080:80
# URL: http://localhost:8080
# User: admin / <from secrets.local.yaml>
```

**Jenkins:**
```bash
kubectl port-forward -n jenkins svc/jenkins 8080:8080
# URL: http://localhost:8080
# User: admin / <from secrets.local.yaml>
```

## Verification

Check all pods are running:
```bash
kubectl get pods --all-namespaces
```

Run verification playbook:
```bash
cd ansible && ansible-playbook verify-cluster.yml
```

## Cleanup

```bash
k3d cluster delete cka
```

## Troubleshooting

**Vault not unsealing:**
- Check Vault pods: `kubectl logs -n vault vault-0`
- Verify unseal keys in `secrets/vault-credentials.yaml`

**Keycloak not starting:**
- Check PostgreSQL: `kubectl logs -n keycloak keycloak-postgresql-0`
- Verify password in secrets.local.yaml

**Jenkins jobs not configured:**
- Check shared library: `kubectl logs -n jenkins jenkins-0`
- Verify git credentials in Vault

## Security Notes

- **Never commit** `secrets.local.yaml` to version control
- All secrets stored in Vault
- Keycloak admin credentials from secrets file
- Jenkins uses Vault for CI/CD secrets
