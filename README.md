# DevSecOps Platform - Statistics & Device Registration

A comprehensive DevSecOps platform implementing microservices architecture with automated infrastructure provisioning, security-first design, and complete CI/CD pipelines.

## Overview

This project demonstrates a production-ready DevSecOps platform featuring:

- **2 Backend APIs** (FastAPI + MongoDB): Statistics collection and device registration services
- **1 Frontend Application** (Nginx + Vanilla JS): Web interface with OIDC authentication
- **Security**: HashiCorp Vault for secrets management, Keycloak for OIDC authentication
- **CI/CD**: Jenkins with declarative pipelines and shared library
- **Infrastructure as Code**: Terraform (Vault), Ansible (configuration), Helm (deployments)
- **Kubernetes**: Multi-environment deployments (develop, stage, production) on k3d

## Architecture

### Component Interaction Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BOOTSTRAP PHASE                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────────┐ ┌──────────┐  ┌──────────────┐
            │  k3d Cluster │ │  Vault   │  │   Keycloak   │
            │  (1+2 nodes) │ │  (HA)    │  │   (OIDC)     │
            └──────┬───────┘ └────┬─────┘  └──────┬───────┘
                   │              │                │
                   │         ┌────▼────┐          │
                   │         │Terraform│          │
                   │         │ (Vault) │          │
                   │         └────┬────┘          │
                   │              │                │
                   └──────────────┼────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │  Store Secrets in Vault │
                    │  - MongoDB credentials  │
                    │  - Keycloak clients     │
                    │  - Complete config      │
                    └────────────┬────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
        ┌──────────────┐  ┌─────────────┐  ┌──────────────┐
        │   Jenkins    │  │   MongoDB   │  │Ext. Secrets  │
        │   (JCasC)    │  │  Operator   │  │   Operator   │
        └──────┬───────┘  └──────┬──────┘  └──────┬───────┘
               │                 │                  │
               │                 │                  │
┌──────────────┴─────────────────┴──────────────────┴─────────────────┐
│                         RUNTIME PHASE                                 │
└───────────────────────────────────────────────────────────────────────┘
               │                                      │
               ▼                                      ▼
    ┌─────────────────────┐              ┌─────────────────────┐
    │  Jenkins Pipeline   │              │  External Secrets   │
    │  ┌─────────────┐    │              │  ┌──────────────┐   │
    │  │ Load Config │────┼──────────────┼─▶│ Sync Secrets │   │
    │  └─────────────┘    │              │  │ from Vault   │   │
    │  ┌─────────────┐    │              │  └──────┬───────┘   │
    │  │Deploy MongoDB│    │              │         │           │
    │  └─────────────┘    │              │         ▼           │
    │  ┌─────────────┐    │              │  ┌──────────────┐   │
    │  │Deploy Apps  │────┼──────────────┼─▶│ K8s Secrets  │   │
    │  │  (Parallel) │    │              │  └──────┬───────┘   │
    │  └─────────────┘    │              │         │           │
    └─────────────────────┘              └─────────┼───────────┘
               │                                    │
               ▼                                    ▼
    ┌──────────────────────────────────────────────────────────┐
    │              DEPLOYED APPLICATIONS                        │
    │  ┌─────────────────┐  ┌──────────────────┐  ┌─────────┐ │
    │  │ statistics-api  │  │device-regis-api  │  │frontend │ │
    │  │  (Public)       │──│  (Internal)      │  │ (Public)│ │
    │  │  Port: 8000     │  │  Port: 8000      │  │ Port: 80│ │
    │  └────────┬────────┘  └────────┬─────────┘  └────┬────┘ │
    │           │                    │                  │      │
    │           └──────┬─────────────┴──────────────────┘      │
    │                  ▼                                        │
    │        ┌──────────────────┐                              │
    │        │  MongoDB Replica │                              │
    │        │  (Per Environment)│                             │
    │        └──────────────────┘                              │
    └──────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   User Access Flow     │
                    │ ┌────────────────────┐ │
                    │ │1. User → Frontend  │ │
                    │ │2. Redirect Keycloak│ │
                    │ │3. Login + JWT      │ │
                    │ │4. Call Stats API   │ │
                    │ │5. Stats → Device   │ │
                    │ │6. Store MongoDB    │ │
                    │ └────────────────────┘ │
                    └────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Applications** | FastAPI (Python 3.11) | Backend APIs |
| | Nginx + Vanilla JS | Frontend SPA |
| **Database** | MongoDB Community Operator | Document storage |
| **Authentication** | Keycloak | OIDC provider |
| **Secret Management** | HashiCorp Vault | Centralized secrets |
| | External Secrets Operator | K8s secrets sync |
| **CI/CD** | Jenkins | Automated pipelines |
| **IaC** | Terraform | Vault configuration |
| | Ansible | Service configuration |
| | Helm | Kubernetes deployments |
| **Orchestration** | Kubernetes (k3d) | Container orchestration |

## Project Structure

```
devsecops-demo/
├── infra/                          # Infrastructure automation
│   ├── ansible/                    # Configuration management
│   │   ├── jenkins/               # Jenkins setup & jobs
│   │   ├── keycloak/              # OIDC configuration
│   │   ├── mongodb/               # Database configuration
│   │   ├── vault/                 # Vault init/unseal
│   │   └── build-images.yml       # Docker image builds
│   ├── docker/                    # Custom Dockerfiles
│   │   └── jenkins-agent-ansible/ # Jenkins agent image
│   ├── helm/                      # Helm charts & values
│   │   ├── charts/
│   │   │   ├── common/           # Library chart (templates)
│   │   │   ├── microservice/     # Generic app chart
│   │   │   └── mongodb-environment/ # MongoDB per env
│   │   ├── external-secrets/     # ESO values
│   │   ├── frontend/             # Frontend manifests
│   │   ├── jenkins/              # Jenkins values
│   │   ├── keycloak/             # Keycloak values
│   │   ├── mongodb/              # MongoDB operator
│   │   └── vault/                # Vault HA values
│   ├── terraform/                # Terraform modules
│   │   └── vault/               # Vault policies & mounts
│   ├── bootstrap.py              # Main orchestrator
│   ├── requirements.txt          # Python dependencies
│   ├── secrets.local.yaml.example # Config template
│   └── secrets.local.yaml        # Your config (gitignored)
├── pipelines/                     # Jenkins pipelines
│   ├── DeployDevSecOpsApp.groovy # Main pipeline
│   ├── deploy-environment.groovy # Environment orchestrator
│   └── deploy-app.groovy         # App deployment
├── services/                      # Microservices
│   ├── common/                   # Shared libraries
│   │   ├── auth/                 # Keycloak integration
│   │   ├── database/             # MongoDB connection
│   │   └── health/               # Health checks
│   ├── device-registration-api/  # Device API
│   ├── statistics-api/           # Statistics API
│   └── frontend/                 # Web application
├── vars/                         # Jenkins shared library
│   ├── buildDockerImage.groovy
│   ├── configureKeycloakClient.groovy
│   ├── deployApp.groovy
│   ├── deployMongoDB.groovy
│   ├── gitCheckout.groovy
│   ├── loadConfig.groovy
│   ├── runAnsiblePlaybook.groovy
│   └── vault.groovy
├── images/                       # Evidence & screenshots
├── test.sh                       # Quick API test script
├── README.md                     # This file
├── LICENSE                       # MIT License
└── .gitignore                    # Git exclusions
```

## Prerequisites

### Required Tools

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** | Latest | Container runtime |
| **k3d** | v5.x | Local Kubernetes cluster |
| **kubectl** | v1.28+ | Kubernetes CLI |
| **helm** | v3.x | Package manager |
| **ansible** | v2.15+ | Configuration automation |
| **terraform** | v1.5+ | Infrastructure as Code |
| **python3** | 3.11+ | Bootstrap script |
| **jq** | Latest | JSON processing (for tests) |

### Install Tools (macOS)

```bash
# Docker Desktop
brew install --cask docker

# Kubernetes tools
brew install k3d kubectl helm

# Automation tools
brew install ansible terraform python@3.11 jq

# Verify installations
docker --version
k3d version
kubectl version --client
helm version
ansible --version
terraform --version
python3 --version
jq --version
```

### Install Tools (Linux)

```bash
# Docker
curl -fsSL https://get.docker.com | sh

# k3d
curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Ansible, Terraform, Python
sudo apt-get update
sudo apt-get install -y ansible terraform python3 python3-pip jq

# Verify installations
docker --version
k3d version
kubectl version --client
helm version
ansible --version
terraform --version
python3 --version
jq --version
```

### Python Dependencies

Install required Python packages:

```bash
cd infra
pip3 install -r requirements.txt
```

## Quick Start

### 1. Configure Secrets

Create your local configuration file (not versioned):

```bash
cd infra
cp secrets.local.yaml.example secrets.local.yaml
```

Edit `secrets.local.yaml` with your credentials:

```yaml
# Essential configuration (edit these values)
dockerhub:
  username: "your-dockerhub-username"
  password: "your-dockerhub-password"

github:
  username: "your-github-username"
  token: "ghp_xxxxxxxxxxxx"
  repository: "https://github.com/your-username/devsecops-demo.git"

keycloak:
  admin_password: "admin123"        # Change in production
  realms:
    - name: develop
      users:
        - username: admin-dev
          password: dev-secret123
          roles: [admin]
        - username: operator-dev
          password: dev-secret123
          roles: [operator]
    # ... stage and production realms

mongodb:
  develop:
    username: app_user
    password: dev-mongo-pass123     # Change in production
  # ... stage and production configs

jenkins:
  admin_password: "admin123"        # Change in production

vault:
  replicas: 2
```

**Important Notes:**
- **Never commit** `secrets.local.yaml` to version control
- Change default passwords for production use
- Store production secrets securely (e.g., password manager)
- Bootstrap will store these secrets in Vault automatically

### 2. Run Bootstrap

Deploy the entire infrastructure with one command:

```bash
cd infra
python3 bootstrap.py --servers 1 --agents 2 --cluster-name cka
```

**Bootstrap Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--servers N` | Number of k3d server nodes | 1 |
| `--agents N` | Number of k3d agent nodes | 2 |
| `--cluster-name NAME` | Cluster name | cka |
| `--skip-cluster` | Skip cluster creation | false |
| `--debug` | Enable debug logging | false |

**What Bootstrap Does:**

1. Validates required tools (docker, k3d, kubectl, helm, ansible, terraform)
2. Creates k3d cluster with LoadBalancer (ports 80, 443)
3. Deploys Vault HA (2 replicas) and auto-unseals
4. Applies Terraform configuration (Vault policies, K8s auth)
5. Stores secrets in Vault (`secret/data/config/complete`)
6. Deploys Keycloak with PostgreSQL backend
7. Creates realms, clients, users (admin, operator roles)
8. Deploys Jenkins with JCasC auto-configuration
9. Installs MongoDB Community Operator
10. Deploys External Secrets Operator
11. Builds and pushes Docker images (jenkins-agent, APIs, frontend)
12. Verifies all pods are running

**Expected Duration:** 10-15 minutes (depending on network speed)

### 3. Configure /etc/hosts

Add service hostnames to your hosts file:

```bash
sudo sh -c 'echo "127.0.0.1 vault.local jenkins.local keycloak.local app.local app-dev.local statistics-api-dev.local" >> /etc/hosts'
```

### 4. Access Services

After bootstrap completes, access services via Ingress:

#### Vault UI
```bash
# URL: http://vault.local
# Token: (displayed at end of bootstrap, also saved in infra/.vault-credentials.yml)
```

#### Keycloak Admin Console
```bash
# URL: http://keycloak.local
# User: admin
# Password: (from secrets.local.yaml → keycloak.admin_password)
```

#### Jenkins Dashboard
```bash
# URL: http://jenkins.local
# User: admin
# Password: (from secrets.local.yaml → jenkins.admin_password)
```

#### Frontend Application
```bash
# URL: http://app.local (or http://app-dev.local)
# Login with Keycloak user:
#   - admin-dev / dev-secret123 (admin role)
#   - operator-dev / dev-secret123 (operator role)
```

#### Statistics API (Swagger)
```bash
# URL: http://statistics-api-dev.local/docs
# Requires JWT token from Keycloak
```

**Alternative: Port-Forward (if Ingress issues)**

```bash
# Vault
kubectl port-forward -n vault svc/vault 8200:8200
# Access: http://localhost:8200

# Jenkins
kubectl port-forward -n jenkins svc/jenkins 8080:8080
# Access: http://localhost:8080

# Keycloak
kubectl port-forward -n keycloak svc/keycloak 8080:80
# Access: http://localhost:8080
```

## Testing the APIs

### Quick Test Script

A test script is provided for rapid validation:

```bash
# Make script executable
chmod +x test.sh

# Run tests against develop environment
./test.sh

# Expected output:
# ✅ Token obtained successfully
# ✅ Login event registered
# ✅ Statistics retrieved
```

### Manual API Testing

#### 1. Obtain JWT Token

```bash
TOKEN=$(curl -s -X POST "http://keycloak.local/realms/develop/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password" \
    -d "client_id=statistics-frontend" \
    -d "username=operator-dev" \
    -d "password=dev-secret123" | jq -r '.access_token')

echo "Token: ${TOKEN:0:50}..."
```

#### 2. Register Login Event

```bash
curl -X POST "http://statistics-api-dev.local/Log/auth" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "deviceType": "iOS"
    }'
```

**Expected Response:**
```json
{
    "success": true,
    "message": "Login event registered successfully",
    "event_id": "507f1f77bcf86cd799439011"
}
```

#### 3. Query Statistics

```bash
curl "http://statistics-api-dev.local/Log/auth/statistics?deviceType=iOS" \
    -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
    "device_type": "iOS",
    "event_count": 5
}
```

## Verification

### Check All Pods

```bash
kubectl get pods --all-namespaces
```

**Expected Output:**
```
NAMESPACE          NAME                                READY   STATUS    RESTARTS
vault              vault-0                             1/1     Running   0
vault              vault-1                             1/1     Running   0
keycloak           keycloak-0                          1/1     Running   0
keycloak           keycloak-postgresql-0               1/1     Running   0
jenkins            jenkins-0                           2/2     Running   0
mongodb-operator   mongodb-kubernetes-operator-...     1/1     Running   0
external-secrets   external-secrets-...                1/1     Running   0
develop            mongodb-develop-0                   2/2     Running   0
develop            statistics-api-...                  1/1     Running   0
develop            device-registration-api-...         1/1     Running   0
develop            frontend-...                        1/1     Running   0
```

### Run Verification Playbook

```bash
cd infra/ansible
ansible-playbook verify-cluster.yml
```

### Check Jenkins Jobs

```bash
# Access Jenkins: http://jenkins.local
# Jobs should be automatically created:
# - DeployDevSecOpsApp
# - deploy-environment
# - deploy-app
```

### Verify External Secrets Sync

```bash
# Check SecretStore
kubectl get secretstore -n develop

# Check ExternalSecrets
kubectl get externalsecrets -n develop

# Check synced secrets
kubectl get secrets -n develop
```

## Evidence

Deployment evidence and screenshots are available in the `images/` directory:

```bash
ls -la images/
```

**Included Evidence:**
- Bootstrap execution logs
- Keycloak realm configuration
- Vault secrets structure
- Jenkins pipeline runs
- API Swagger documentation
- Frontend authentication flow
- MongoDB deployment
- External Secrets sync status

## CI/CD Pipelines

### Pipeline Architecture

```
Main Pipeline (DeployDevSecOpsApp)
├── Load Config from Vault (loadConfig())
├── Checkout Source Code (gitCheckout())
├── Test Vault Integration (getAllSecrets())
└── Deploy Environments (Parallel)
    ├── deploy-environment (develop)
    │   ├── Load Config (retry: 3x)
    │   ├── Deploy MongoDB (deployMongoDB())
    │   └── Deploy Apps (Parallel, retry: 3x)
    │       ├── deploy-app (statistics-api)
    │       ├── deploy-app (device-registration-api)
    │       └── deploy-app (frontend)
    ├── deploy-environment (stage) [Commented]
    └── deploy-environment (production) [Commented]
```

### Shared Library Functions

Located in `vars/`:

- `loadConfig()` - Loads complete configuration from Vault
- `deployApp()` - Deploys application with Helm
- `deployMongoDB()` - Deploys MongoDB per environment
- `vault.groovy` - Vault HTTP API operations
- `gitCheckout()` - Git repository checkout
- `buildDockerImage()` - Docker image build & push
- `runAnsiblePlaybook()` - Ansible execution wrapper
- `configureKeycloakClient()` - Keycloak client creation

### Triggering Pipelines

Pipelines are automatically configured in Jenkins during bootstrap. To manually trigger:

```bash
# Access Jenkins: http://jenkins.local
# Select "DeployDevSecOpsApp"
# Click "Build Now"
```

## Troubleshooting

### Bootstrap Fails

```bash
# Check Docker is running
docker ps

# Check k3d cluster
k3d cluster list

# Restart cluster
k3d cluster delete cka
python3 bootstrap.py
```

### Pods Not Running

```bash
# Check pod status
kubectl get pods -n develop

# Check pod logs
kubectl logs -n develop <pod-name>

# Describe pod for events
kubectl describe pod -n develop <pod-name>
```

### Vault Not Unsealing

```bash
# Check Vault logs
kubectl logs -n vault vault-0

# Manual unseal (if needed)
cd infra/ansible
ansible-playbook vault/unseal.yml
```

### Keycloak Connection Issues

```bash
# Check Keycloak pod
kubectl logs -n keycloak keycloak-0

# Check PostgreSQL
kubectl logs -n keycloak keycloak-postgresql-0

# Restart Keycloak
kubectl rollout restart statefulset -n keycloak keycloak
```

### API Authentication Fails

```bash
# Verify Keycloak is accessible
curl http://keycloak.local/realms/develop/.well-known/openid-configuration

# Check API logs
kubectl logs -n develop deployment/statistics-api

# Verify secrets are synced
kubectl get externalsecrets -n develop
kubectl describe externalsecret statistics-api-client-secrets -n develop
```

## Cleanup

Remove all resources:

```bash
# Delete k3d cluster
k3d cluster delete cka

# Remove generated files (optional)
rm -f infra/.vault-credentials.yml
rm -f infra/.vault-k8s-auth.yml
```

## Next Steps

### High Priority - Security & Quality Gates

- [ ] **SAST Integration** - Add Bandit scan to pipeline (detect code vulnerabilities)
- [ ] **SCA Integration** - Add pip-audit for dependency scanning (CVE detection)
- [ ] **Container Scanning** - Integrate Trivy for image vulnerability scanning
- [ ] **SonarCloud Integration** - Quality Gate for code quality metrics
- [ ] **Pre-commit Hooks** - Prevent secrets and sensitive data in repository
- [ ] **Helm Linting** - Add `helm lint` to validate chart syntax
- [ ] **Ansible Linting** - Add `ansible-lint` for playbook validation

### Medium Priority - CI/CD Enhancement

- [ ] **Automated Testing** - Unit tests with ≥85% coverage requirement
- [ ] **Integration Tests** - API tests against deployed services
- [ ] **PR Approval Process** - Implement approval gates for develop/stage/production
  - Develop: Auto-merge after CI pass
  - Stage: Require 1 reviewer approval
  - Production: Require 2 reviewer approvals + security scan pass
- [ ] **Semantic Versioning** - Implement semver + git tagging
- [ ] **Changelog Generation** - Automated changelog from commits
- [ ] **Rollback Strategy** - One-click rollback to previous version
- [ ] **Canary Deployments** - Gradual rollout with traffic splitting
- [ ] **Blue-Green Deployments** - Zero-downtime deployments
- [ ] **Post-deployment Validation** - Smoke tests after each deployment

### Low Priority - Observability & Operations

- [ ] **Monitoring Stack** - Prometheus + Grafana for metrics
- [ ] **Distributed Tracing** - Jaeger or Zipkin for request tracing
- [ ] **Centralized Logging** - ELK or Loki for log aggregation
- [ ] **Alerting** - PagerDuty or Slack integration for alerts
- [ ] **Structured Logging** - JSON logs with correlation IDs
- [ ] **Performance Testing** - k6 or Locust load testing
- [ ] **Chaos Engineering** - Chaos Mesh for resilience testing

### Infrastructure - High Availability & Disaster Recovery

- [ ] **MongoDB Replication** - Multi-replica setup per environment
  - Develop: 1 replica (acceptable for testing)
  - Stage: 3 replicas with auto-failover
  - Production: 5 replicas across availability zones
- [ ] **Database Backups** - Automated daily backups with retention policy
  - Develop: 7 days retention
  - Stage: 30 days retention
  - Production: 90 days retention + offsite storage
- [ ] **Backup Restoration Testing** - Monthly DR drills
- [ ] **Vault HA** - Already implemented (2 replicas), add backup strategy
- [ ] **Multi-cluster Setup** - Active-passive or active-active for DR
- [ ] **Network Policies** - K8s network policies for pod isolation
- [ ] **Pod Disruption Budgets** - Ensure minimum availability during updates
- [ ] **Resource Quotas** - Prevent resource exhaustion
- [ ] **Horizontal Pod Autoscaling** - Auto-scale based on CPU/memory/RPS
- [ ] **Persistent Volume Backups** - Snapshot strategy for stateful services

### Documentation

- [ ] **API Documentation** - Expand OpenAPI/Swagger specs
- [ ] **Architecture Decision Records (ADR)** - Document key decisions
- [ ] **Runbooks** - Step-by-step operational procedures
- [ ] **Security Policies** - Document security controls and compliance
- [ ] **Onboarding Guide** - New developer setup guide

### Advanced Features

- [ ] **Multi-tenancy** - Support multiple organizations
- [ ] **Rate Limiting** - API rate limiting per client
- [ ] **API Gateway** - Kong or Istio for advanced routing
- [ ] **Service Mesh** - Istio for traffic management and security
- [ ] **GitOps** - ArgoCD or FluxCD for declarative deployments
- [ ] **Policy Enforcement** - OPA (Open Policy Agent) for policy as code
- [ ] **Secret Rotation** - Automated secret rotation for Vault
- [ ] **Certificate Management** - cert-manager for automatic TLS certificates

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FastAPI framework for rapid API development
- HashiCorp Vault for secrets management
- Keycloak for OIDC authentication
- MongoDB Community Operator for database management
- External Secrets Operator for K8s secrets sync
- Jenkins for CI/CD automation

## Support

For issues or questions:
- Open an issue in the repository
- Check `images/` directory for deployment evidence
- Review `infra/ansible/verify-cluster.yml` for health checks
- Consult Jenkins logs at http://jenkins.local

---

**Built with ❤️ using DevSecOps best practices**
