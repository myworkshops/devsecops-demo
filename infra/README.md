# Infrastructure Bootstrap

Automated deployment of the DevSecOps platform on k3d.

## Prerequisites

- Python 3.11+
- k3d 5.6+
- kubectl 1.28+
- helm 3.12+
- ansible 2.15+

## Quick Start

```bash
# Install Ansible collections
cd ansible
ansible-galaxy collection install -r requirements.yml

# Run bootstrap
cd ..
python3 bootstrap.py

# Custom configuration
python3 bootstrap.py --cluster-name production --servers 3 --agents 3
```

## What it Does

1. Creates k3d cluster with specified topology
2. Verifies all nodes are Ready
3. (Next phases: Vault, Keycloak, MongoDB, Jenkins, Applications)

## Structure

```
infra/
├── bootstrap.py              # Main bootstrap script
├── secrets.local.yaml        # Local secrets (not versioned)
├── ansible/
│   ├── verify-cluster.yml    # Verify nodes are ready
│   └── requirements.yml      # Ansible collections
└── terraform/
    └── vault/                # Vault configuration
```
