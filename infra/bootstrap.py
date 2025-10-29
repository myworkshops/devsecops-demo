#!/usr/bin/env python3
"""
Bootstrap script for DevSecOps Device Statistics Platform
Creates k3d cluster and orchestrates Ansible playbooks for deployment
"""

import argparse
import os
import subprocess
import sys
import time
import logging
import yaml
import tempfile
from pathlib import Path

# Logger will be configured in main() based on debug flag
logger = logging.getLogger(__name__)


class BootstrapError(Exception):
    """Custom exception for bootstrap failures"""
    pass


def run_command(cmd, check=True, show_output=False, cwd=None, env=None):
    """Execute shell command"""
    logger.debug(f"Executing: {' '.join(cmd)}")
    try:
        if show_output:
            result = subprocess.run(cmd, check=check, text=True, cwd=cwd, env=env)
        else:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True, cwd=cwd, env=env)
            if result.stdout:
                logger.debug(result.stdout.strip())
        return result
    except subprocess.CalledProcessError as e:
        if hasattr(e, 'stderr') and e.stderr:
            logger.error(f"Command failed: {e.stderr}")
        raise BootstrapError(f"Command failed: {' '.join(cmd)}")


def load_config():
    """Load secrets configuration"""
    config_file = Path('secrets.local.yaml')
    if not config_file.exists():
        raise BootstrapError(f"Configuration file not found: {config_file}")

    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def check_prerequisites():
    """Verify required tools are installed"""
    logger.info("Checking prerequisites...")

    tools = {
        'k3d': ['k3d', 'version'],
        'kubectl': ['kubectl', 'version', '--client'],
        'helm': ['helm', 'version'],
        'ansible': ['ansible', '--version'],
        'terraform': ['terraform', 'version'],
    }

    for tool, cmd in tools.items():
        try:
            result = run_command(cmd, check=False)
            if result.returncode != 0:
                raise BootstrapError(f"{tool} is not installed")
            logger.info(f"{tool} is installed")
        except FileNotFoundError:
            raise BootstrapError(f"{tool} is not installed. Please install it first.")


def cluster_exists(cluster_name):
    """Check if cluster exists"""
    result = run_command(['k3d', 'cluster', 'list'], check=False)
    return cluster_name in result.stdout


def create_cluster(cluster_name, servers, agents, skip_if_exists=False):
    """Create k3d cluster"""
    if cluster_exists(cluster_name):
        if skip_if_exists:
            logger.info(f"Cluster '{cluster_name}' already exists, skipping creation")
            return
        logger.warning(f"Cluster '{cluster_name}' already exists")
        user_input = input("Delete and recreate? (yes/no): ")
        if user_input.lower() == 'yes':
            logger.info(f"Deleting cluster '{cluster_name}'...")
            run_command(['k3d', 'cluster', 'delete', cluster_name])
        else:
            logger.info("Using existing cluster")
            return

    logger.info(f"Creating k3d cluster '{cluster_name}'...")
    logger.info(f"  Servers: {servers}, Agents: {agents}")

    cmd = [
        'k3d', 'cluster', 'create', cluster_name,
        '--servers', str(servers),
        '--agents', str(agents),
        '--port', '443:443@loadbalancer',
        '--port', '80:80@loadbalancer',
        '--wait'
    ]

    run_command(cmd)
    logger.info(f"Cluster '{cluster_name}' created")


def run_ansible_playbook(playbook_path, extra_vars=None, verbose=False):
    """Execute Ansible playbook"""
    logger.info(f"Running Ansible playbook: {playbook_path}")

    cmd = ['ansible-playbook', playbook_path]

    if verbose:
        cmd.append('-v')

    if extra_vars:
        for key, value in extra_vars.items():
            cmd.extend(['-e', f'{key}={value}'])

    # Set ANSIBLE_CONFIG to use the config in ansible directory
    env = os.environ.copy()
    env['ANSIBLE_CONFIG'] = 'ansible/ansible.cfg'

    run_command(cmd, show_output=verbose, cwd=None, env=env)
    logger.info(f"Playbook completed: {playbook_path}")


def add_helm_repo(name, url):
    """Add Helm repository"""
    logger.info(f"Adding Helm repository: {name}")
    run_command(['helm', 'repo', 'add', name, url])
    run_command(['helm', 'repo', 'update'])
    logger.info(f"Helm repository '{name}' added")


def deploy_vault(replicas):
    """Deploy Vault using Helm"""
    logger.info("Deploying HashiCorp Vault...")

    # Add HashiCorp Helm repo
    add_helm_repo('hashicorp', 'https://helm.releases.hashicorp.com')

    # Install Vault with HA configuration
    cmd = [
        'helm', 'upgrade', '--install', 'vault',
        'hashicorp/vault',
        '--namespace', 'vault',
        '--create-namespace',
        '-f', 'helm/vault/values.yaml',
        '--set', f'server.ha.replicas={replicas}'
    ]

    run_command(cmd)
    logger.info("Vault deployed successfully")


def deploy_keycloak(admin_password, postgresql_password):
    """Deploy Keycloak using Helm"""
    logger.info("Deploying Keycloak...")

    # Add Bitnami Helm repo
    add_helm_repo('bitnami', 'https://charts.bitnami.com/bitnami')

    # Install Keycloak with configuration using bitnamilegacy images
    cmd = [
        'helm', 'upgrade', '--install', 'keycloak',
        'bitnami/keycloak',
        '--namespace', 'keycloak',
        '--create-namespace',
        '-f', 'helm/keycloak/values.yaml',
        '--set', f'auth.adminPassword={admin_password}',
        '--set', f'image.registry=docker.io',
        '--set', f'image.repository=bitnamilegacy/keycloak',
        '--set', f'postgresql.image.registry=docker.io',
        '--set', f'postgresql.image.repository=bitnamilegacy/postgresql',
        '--set', f'postgresql.auth.password={postgresql_password}'
    ]

    run_command(cmd)
    logger.info("Keycloak deployed successfully")


def deploy_jenkins(admin_password, git_repository, git_library_branch, git_credentials_id, github_token):
    """Deploy Jenkins using Helm"""
    logger.info("Deploying Jenkins...")

    # Add Jenkins Helm repo
    add_helm_repo('jenkins', 'https://charts.jenkins.io')

    # Install Jenkins with configuration
    cmd = [
        'helm', 'upgrade', '--install', 'jenkins',
        'jenkins/jenkins',
        '--namespace', 'jenkins',
        '--create-namespace',
        '-f', 'helm/jenkins/values.yaml',
        '--set', f'controller.admin.password={admin_password}',
        '--set', f'controller.initContainerEnv[0].name=GIT_REPOSITORY',
        '--set', f'controller.initContainerEnv[0].value={git_repository}',
        '--set', f'controller.initContainerEnv[1].name=GIT_LIBRARY_BRANCH',
        '--set', f'controller.initContainerEnv[1].value={git_library_branch}',
        '--set', f'controller.initContainerEnv[2].name=GITHUB_CREDENTIALS_ID',
        '--set', f'controller.initContainerEnv[2].value={git_credentials_id}',
        '--set', f'controller.initContainerEnv[3].name=GITHUB_TOKEN',
        '--set', f'controller.initContainerEnv[3].value={github_token}',
        '--set', f'controller.containerEnv[0].name=GIT_REPOSITORY',
        '--set', f'controller.containerEnv[0].value={git_repository}',
        '--set', f'controller.containerEnv[1].name=GIT_LIBRARY_BRANCH',
        '--set', f'controller.containerEnv[1].value={git_library_branch}',
        '--set', f'controller.containerEnv[2].name=GITHUB_CREDENTIALS_ID',
        '--set', f'controller.containerEnv[2].value={git_credentials_id}',
        '--set', f'controller.containerEnv[3].name=GITHUB_TOKEN',
        '--set', f'controller.containerEnv[3].value={github_token}',
        '--wait',
        '--timeout', '10m'
    ]

    run_command(cmd)
    logger.info("Jenkins deployed successfully")


def deploy_mongodb():
    """Deploy MongoDB Community Operator cluster-wide"""
    logger.info("Deploying MongoDB Community Operator...")

    # Add MongoDB Helm repo
    add_helm_repo('mongodb', 'https://mongodb.github.io/helm-charts')

    # Install MongoDB Community Operator cluster-wide (watches all namespaces)
    cmd = [
        'helm', 'upgrade', '--install', 'mongodb-operator',
        'mongodb/community-operator',
        '--namespace', 'mongodb-operator',
        '--create-namespace',
        '-f', 'helm/mongodb/values.yaml',
        '--set', 'operator.watchNamespace=*',
        '--wait',
        '--timeout', '5m'
    ]

    run_command(cmd)
    logger.info("MongoDB Community Operator deployed successfully")


def deploy_external_secrets():
    """Deploy External Secrets Operator using Helm"""
    logger.info("Deploying External Secrets Operator...")

    # Add External Secrets Helm repo
    add_helm_repo('external-secrets', 'https://charts.external-secrets.io')

    # Install External Secrets Operator
    cmd = [
        'helm', 'upgrade', '--install', 'external-secrets',
        'external-secrets/external-secrets',
        '--namespace', 'external-secrets',
        '--create-namespace',
        '-f', 'helm/external-secrets/values.yaml',
        '--wait',
        '--timeout', '5m'
    ]

    run_command(cmd)
    logger.info("External Secrets Operator deployed successfully")


def apply_terraform(directory, vault_credentials, k8s_auth_config):
    """Apply Terraform configuration"""
    logger.info(f"Applying Terraform configuration in {directory}...")

    tf_dir = Path(directory)
    if not tf_dir.exists():
        raise BootstrapError(f"Terraform directory not found: {directory}")

    # Start port-forward to Vault in background
    logger.debug("Starting port-forward to Vault...")
    port_forward = subprocess.Popen(
        ['kubectl', 'port-forward', '-n', 'vault', 'vault-0', '8200:8200'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        # Wait for port-forward to establish
        time.sleep(3)

        # Set environment variables for Vault
        env = os.environ.copy()
        env['VAULT_ADDR'] = 'http://localhost:8200'
        env['VAULT_TOKEN'] = vault_credentials['vault']['root_token']
        env['TF_IN_AUTOMATION'] = 'true'

        # Prepare Terraform variables
        tf_vars = [
            '-var', f'vault_addr=http://localhost:8200',
            '-var', f'vault_token={vault_credentials["vault"]["root_token"]}',
            '-var', f'kubernetes_host={k8s_auth_config["kubernetes"]["host"]}',
            '-var', f'token_reviewer_jwt={k8s_auth_config["kubernetes"]["token_reviewer_jwt"]}',
            '-var', f'kubernetes_ca_cert={k8s_auth_config["kubernetes"]["ca_cert"]}'
        ]

        # Initialize Terraform
        logger.info("Initializing Terraform...")
        run_command(['terraform', 'init'], cwd=str(tf_dir), env=env)

        # Apply Terraform
        logger.info("Applying Terraform configuration...")
        run_command(['terraform', 'apply', '-auto-approve'] + tf_vars, cwd=str(tf_dir), env=env)

        logger.info("Terraform configuration applied successfully")

    finally:
        # Stop port-forward
        logger.debug("Stopping port-forward...")
        port_forward.terminate()
        port_forward.wait()


def main():
    parser = argparse.ArgumentParser(
        description='Bootstrap DevSecOps Platform on k3d',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--cluster-name', default='cka', help='Cluster name (default: cka)')
    parser.add_argument('--servers', type=int, default=1, help='Server nodes (default: 1)')
    parser.add_argument('--agents', type=int, default=2, help='Agent nodes (default: 2)')
    parser.add_argument('--skip-cluster', action='store_true', help='Skip cluster creation if exists')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # Configure logging
    log_format = '%(asctime)s - %(levelname)s - %(message)s'

    if args.debug:
        # Debug mode: console + file with DEBUG level
        logging.basicConfig(
            level=logging.DEBUG,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('bootstrap.log', mode='w')
            ]
        )
    else:
        # Normal mode: console only with INFO level
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[logging.StreamHandler(sys.stdout)]
        )

    logger.info("=" * 70)
    logger.info("DevSecOps Device Statistics Platform - Bootstrap")
    logger.info("=" * 70)

    try:
        # Step 1: Load configuration
        config = load_config()

        # Step 2: Check prerequisites
        check_prerequisites()

        # Step 3: Create k3d cluster
        create_cluster(args.cluster_name, args.servers, args.agents, args.skip_cluster)

        # Step 4: Verify cluster with Ansible
        logger.info("Verifying cluster with Ansible...")
        run_ansible_playbook('ansible/verify-cluster.yml', verbose=args.debug)

        # Step 5: Deploy Vault
        deploy_vault(config['vault']['replicas'])

        # Step 6: Wait for Vault pods to be running (before init)
        logger.info("Waiting for Vault pods to be running...")
        run_ansible_playbook('ansible/verify-pods-running.yml', {
            'namespace': 'vault',
            'label_selector': 'app.kubernetes.io/name=vault'
        }, verbose=args.debug)

        # Step 7: Initialize Vault
        logger.info("Initializing Vault...")
        run_ansible_playbook('ansible/vault/init.yml', verbose=args.debug)

        # Step 8: Unseal Vault
        logger.info("Unsealing Vault cluster...")
        run_ansible_playbook('ansible/vault/unseal.yml', {
            'vault_replicas': config['vault']['replicas']
        }, verbose=args.debug)

        # Step 9: Verify Vault pods are ready (after unseal)
        logger.info("Waiting for Vault pods to be ready...")
        run_ansible_playbook('ansible/verify-pods.yml', {
            'namespace': 'vault',
            'label_selector': 'app.kubernetes.io/name=vault'
        }, verbose=args.debug)

        # Step 9.5: Create Vault Ingress
        logger.info("Creating Vault Ingress...")
        run_command(['kubectl', 'apply', '-f', 'helm/vault/ingress.yaml'])
        logger.info("Vault Ingress created (accessible at http://vault.local)")

        # Step 10: Load Vault credentials for Terraform
        vault_creds_file = Path('.vault-credentials.yml')
        if not vault_creds_file.exists():
            raise BootstrapError("Vault credentials file not found")

        with open(vault_creds_file, 'r') as f:
            vault_creds = yaml.safe_load(f)
        
        # Step 12: Load Kubernetes auth configuration
        k8s_auth_file = Path('.vault-k8s-auth.yml')
        if not k8s_auth_file.exists():
            raise BootstrapError("Kubernetes auth configuration file not found")

        with open(k8s_auth_file, 'r') as f:
            k8s_auth_config = yaml.safe_load(f)

        # Step 13: Apply Terraform configuration for Vault
        logger.info("Configuring Vault with Terraform...")
        apply_terraform('terraform/vault', vault_creds, k8s_auth_config)

        # Step 14: Store application secrets in Vault
        logger.info("Storing application secrets in Vault...")

        # Start port-forward to Vault
        logger.debug("Starting port-forward to Vault...")
        vault_port_forward = subprocess.Popen(
            ['kubectl', 'port-forward', '-n', 'vault', 'svc/vault', '8200:8200'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        try:
            # Wait for port-forward to establish
            time.sleep(5)

            # Store secrets in Vault (includes complete configuration)
            run_ansible_playbook('ansible/vault/store-secrets.yml', {
                'vault_token': vault_creds['vault']['root_token']
            }, verbose=args.debug)

            logger.info("Application secrets and configuration stored in Vault successfully")

            # Setup Kubernetes auth for Vault
            logger.info("Setting up Kubernetes authentication for Vault...")
            run_ansible_playbook('ansible/vault/setup-k8s-auth.yml', {
                'vault_token': vault_creds['vault']['root_token']
            },verbose=args.debug)

        finally:
            # Terminate port-forward
            vault_port_forward.terminate()
            vault_port_forward.wait()

        # Step 15: Deploy Keycloak
        deploy_keycloak(config['keycloak']['admin_password'], config['keycloak']['postgresql_password'])

        # Step 16: Verify Keycloak pods are ready
        logger.info("Waiting for Keycloak pods to be ready...")
        run_ansible_playbook('ansible/verify-pods.yml', {
            'namespace': 'keycloak',
            'label_selector': 'app.kubernetes.io/name=keycloak'
        }, verbose=args.debug)

        # Step 16.5: Create Keycloak Ingress
        logger.info("Creating Keycloak Ingress...")
        run_command(['kubectl', 'apply', '-f', 'helm/keycloak/ingress.yaml'])
        logger.info("Keycloak Ingress created (accessible at http://keycloak.local)")

        # Step 17: Configure Keycloak (realms, roles, users)
        logger.info("Configuring Keycloak...")

        # Start port-forward to Vault in background
        logger.debug("Starting port-forward to Vault...")
        vault_port_forward = subprocess.Popen(
            ['kubectl', 'port-forward', '-n', 'vault', 'svc/vault', '8200:8200'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Start port-forward to Keycloak in background
        logger.debug("Starting port-forward to Keycloak...")
        keycloak_port_forward = subprocess.Popen(
            ['kubectl', 'port-forward', '-n', 'keycloak', 'svc/keycloak', '8080:80'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            # Wait for port-forwards to establish
            time.sleep(5)

            # Run Keycloak configuration playbook
            run_ansible_playbook('ansible/keycloak/configure.yml', {
                'vault_token': vault_creds['vault']['root_token']
            }, verbose=args.debug)

            logger.info("Keycloak configuration completed")

            # Create Keycloak clients (both public and confidential)
            if 'clients' in config.get('keycloak', {}):
                logger.info("Creating Keycloak clients...")
                for client in config['keycloak']['clients']:
                    client_id = client['client_id']
                    is_public = client.get('public_client', False)

                    # Determine which environments to create this client in
                    # Option 1: Client has 'environments' list (for API clients)
                    # Option 2: Client has 'redirect_uris' or 'web_origins' dict (for frontend clients)
                    if 'environments' in client:
                        # API-style: environments list
                        environments = client['environments']
                    else:
                        # Frontend-style: extract from redirect_uris or web_origins keys
                        environments = list(client.get('redirect_uris', {}).keys()) or \
                                     list(client.get('web_origins', {}).keys()) or \
                                     [realm_config['name'] for realm_config in config['keycloak']['realms']]

                    # Create client in each environment
                    for realm in environments:
                        # Append environment suffix for confidential clients
                        full_client_id = f"{client_id}-{realm}" if not is_public else client_id

                        logger.info(f"Creating client '{full_client_id}' in realm '{realm}'...")

                        # Prepare redirect URIs and web origins for this environment
                        redirect_uris = client.get('redirect_uris', {}).get(realm, ['*'])
                        web_origins = client.get('web_origins', {}).get(realm, ['*'])

                        # Write temporary vars file for complex data structures
                        temp_vars = {
                            'target_env': realm,
                            'client_id': full_client_id,
                            'client_name': client.get('name', full_client_id),
                            'client_description': client.get('description', f'OIDC client for {full_client_id}'),
                            'public_client': is_public,
                            'redirect_uris': redirect_uris,
                            'web_origins': web_origins,
                            'keycloak_admin_user': 'admin',
                            'keycloak_admin_password': config['keycloak']['admin_password'],
                            'vault_token': vault_creds['vault']['root_token'],
                            'keycloak_server_url': 'http://localhost:8080',
                            'vault_server_url': 'http://localhost:8200'
                        }

                        # Create temporary vars file
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                            yaml.dump(temp_vars, f)
                            temp_vars_file = f.name

                        try:
                            # Run playbook with vars file
                            cmd = ['ansible-playbook', 'ansible/keycloak/create-client.yml']
                            cmd.extend(['-e', f'@{temp_vars_file}'])
                            if args.debug:
                                cmd.append('-v')

                            env = os.environ.copy()
                            env['ANSIBLE_CONFIG'] = 'ansible/ansible.cfg'

                            run_command(cmd, show_output=args.debug, cwd=None, env=env)
                        finally:
                            # Clean up temp file
                            os.unlink(temp_vars_file)

                        logger.info(f"Client '{full_client_id}' created in realm '{realm}'")

        finally:
            # Stop port-forwards
            logger.debug("Stopping port-forwards...")
            keycloak_port_forward.terminate()
            vault_port_forward.terminate()
            keycloak_port_forward.wait()
            vault_port_forward.wait()

        # Step 18: Deploy Jenkins
        deploy_jenkins(
            config['jenkins']['admin_password'],
            config['jenkins']['git_repository'],
            config['jenkins']['git_library_branch'],
            config['jenkins']['git_credentials_id'],
            config['jenkins']['github_token']
        )

        # Step 19: Verify Jenkins pods are ready
        logger.info("Waiting for Jenkins pods to be ready...")
        run_ansible_playbook('ansible/verify-pods.yml', {
            'namespace': 'jenkins',
            'label_selector': 'app.kubernetes.io/component=jenkins-controller'
        }, verbose=args.debug)

        # Step 19.5: Create Jenkins Ingress
        logger.info("Creating Jenkins Ingress...")
        run_command(['kubectl', 'apply', '-f', 'helm/jenkins/ingress.yaml'])
        logger.info("Jenkins Ingress created (accessible at http://jenkins.local)")

        # Step 20: Configure Jenkins (credentials, jobs)
        logger.info("Configuring Jenkins...")

        # Start port-forward to Vault in background
        logger.debug("Starting port-forward to Vault...")
        vault_port_forward = subprocess.Popen(
            ['kubectl', 'port-forward', '-n', 'vault', 'svc/vault', '8200:8200'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Start port-forward to Jenkins in background
        logger.debug("Starting port-forward to Jenkins...")
        jenkins_port_forward = subprocess.Popen(
            ['kubectl', 'port-forward', '-n', 'jenkins', 'svc/jenkins', '8080:8080'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            # Wait for port-forwards to establish
            time.sleep(10)

            # Run Jenkins configuration playbook
            run_ansible_playbook('ansible/jenkins/configure.yml', {
                'vault_token': vault_creds['vault']['root_token']
            }, verbose=args.debug)

            # Create Jenkins pipeline jobs
            logger.info("Creating Jenkins pipeline jobs...")
            run_ansible_playbook('ansible/jenkins/create-jobs.yml', {}, verbose=args.debug)

            logger.info("Jenkins configuration completed")

        finally:
            # Stop port-forwards
            logger.debug("Stopping port-forwards...")
            jenkins_port_forward.terminate()
            jenkins_port_forward.wait()
            vault_port_forward.terminate()
            vault_port_forward.wait()

        # Step 21: Deploy MongoDB Community Operator cluster-wide
        deploy_mongodb()

        # Step 22: Verify MongoDB Operator pods are ready
        logger.info("Waiting for MongoDB Operator pods to be ready...")
        run_ansible_playbook('ansible/verify-pods.yml', {
            'namespace': 'mongodb-operator',
            'label_selector': 'name=mongodb-kubernetes-operator'
        }, verbose=args.debug)

        # Step 22b: Configure MongoDB secrets in Vault
        logger.info("Configuring MongoDB secrets in Vault...")

        # Start port-forward to Vault in background
        logger.debug("Starting port-forward to Vault...")
        vault_port_forward = subprocess.Popen(
            ['kubectl', 'port-forward', '-n', 'vault', 'svc/vault', '8200:8200'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            # Wait for port-forward to establish
            time.sleep(5)

            for target_env in config['mongodb']:
                logger.info(f"Storing MongoDB secrets for environment: {target_env}")
                run_ansible_playbook('ansible/mongodb/configure-vault-secrets.yml', {
                    'vault_token': vault_creds['vault']['root_token'],
                    'target_env': target_env
                }, verbose=args.debug)

            logger.info("MongoDB secrets stored in Vault successfully")
        finally:
            # Terminate port-forward
            logger.debug("Stopping port-forward to Vault...")
            vault_port_forward.terminate()
            vault_port_forward.wait()

        # Step 23: Deploy External Secrets Operator
        deploy_external_secrets()

        # Step 24: Verify External Secrets Operator pods are ready
        logger.info("Waiting for External Secrets Operator pods to be ready...")
        run_ansible_playbook('ansible/verify-pods.yml', {
            'namespace': 'external-secrets',
            'label_selector': 'app.kubernetes.io/name=external-secrets'
        }, verbose=args.debug)

        # Step 25: Build and push Docker images for develop environment
        logger.info("=" * 70)
        logger.info("Building and pushing Docker images for develop environment...")
        logger.info("=" * 70)

        run_ansible_playbook('ansible/build-images.yml', {
            'target_env': 'develop'
        }, verbose=args.debug)

        logger.info("All Docker images built and pushed successfully")

        logger.info("=" * 70)
        logger.info("Bootstrap Complete: Infrastructure Ready")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Access URLs (add to /etc/hosts: 127.0.0.1 vault.local jenkins.local keycloak.local):")
        logger.info("")
        logger.info("  Vault:    http://vault.local")
        logger.info(f"    Token:  {vault_creds['vault']['root_token']}")
        logger.info("")
        logger.info("  Jenkins:  http://jenkins.local")
        logger.info(f"    Admin:  admin / {config['jenkins']['admin_password']}")
        logger.info("")
        logger.info("  Keycloak: http://keycloak.local")
        logger.info(f"    Admin:  admin / {config['keycloak']['admin_password']}")
        logger.info("")
        logger.info("Configuration stored in Vault at: secret/config/complete")
        logger.info("Kubeconfig credential created in Jenkins with ID: kubeconfig")
        logger.info("")
        logger.info("Docker images built and pushed:")
        logger.info(f"  - {config['jenkins']['dockerhub_username']}/jenkins-agent-ansible:latest")
        logger.info(f"  - {config['jenkins']['dockerhub_username']}/statistics-api:develop-latest")
        logger.info(f"  - {config['jenkins']['dockerhub_username']}/device-registration-api:develop-latest")
        logger.info(f"  - {config['jenkins']['dockerhub_username']}/statistics-frontend:develop-latest")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Add hosts entries: sudo sh -c 'echo \"127.0.0.1 vault.local jenkins.local keycloak.local\" >> /etc/hosts'")
        logger.info("  2. Access Jenkins at http://jenkins.local")
        logger.info("  3. Run DeployDevSecOpsApp pipeline to deploy all environments")
        logger.info("=" * 70)

    except BootstrapError as e:
        logger.error(f"Bootstrap failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
