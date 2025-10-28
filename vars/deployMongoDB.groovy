#!/usr/bin/env groovy

def call(Map config) {
    def environment = config.environment

    echo "=== Deploying MongoDB for environment: ${environment} ==="

    // Get Vault token from Jenkins credential
    def vaultToken = vault.getVaultToken()

    // Run Ansible playbook to configure MongoDB secrets in Vault and deploy
    runAnsiblePlaybook(
        playbook: 'infra/ansible/mongodb/configure-vault-secrets.yml',
        extraVars: [
            target_env: environment,
            vault_token: vaultToken
        ],
        inventory: 'localhost,'
    )

    echo "✓ MongoDB deployed successfully"
}
