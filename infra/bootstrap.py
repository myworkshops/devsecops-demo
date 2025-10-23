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

    run_command(cmd, show_output=verbose)
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

        # Step 6: Verify Vault pods are running
        logger.info("Waiting for Vault pods to be running...")
        run_ansible_playbook('ansible/verify-pods.yml', {
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

        # Step 9: Setup Kubernetes auth for Vault
        logger.info("Setting up Kubernetes authentication for Vault...")
        run_ansible_playbook('ansible/vault/setup-k8s-auth.yml', verbose=args.debug)

        # Step 10: Load Vault credentials for Terraform
        vault_creds_file = Path('.vault-credentials.yml')
        if not vault_creds_file.exists():
            raise BootstrapError("Vault credentials file not found")

        with open(vault_creds_file, 'r') as f:
            vault_creds = yaml.safe_load(f)

        # Step 11: Load Kubernetes auth configuration
        k8s_auth_file = Path('.vault-k8s-auth.yml')
        if not k8s_auth_file.exists():
            raise BootstrapError("Kubernetes auth configuration file not found")

        with open(k8s_auth_file, 'r') as f:
            k8s_auth_config = yaml.safe_load(f)

        # Step 12: Apply Terraform configuration for Vault
        logger.info("Configuring Vault with Terraform...")
        apply_terraform('terraform/vault', vault_creds, k8s_auth_config)

        logger.info("=" * 70)
        logger.info("Bootstrap Complete: Infrastructure Ready")
        logger.info("=" * 70)
        logger.info("Vault URL: http://localhost:8200")
        logger.info(f"Vault Token: {vault_creds['vault']['root_token']}")

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
