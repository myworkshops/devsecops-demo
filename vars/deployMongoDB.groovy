#!/usr/bin/env groovy

def call(Map config) {
    def environment = config.environment
    def vaultToken = config.vaultToken

    echo "=== Deploying MongoDB for environment: ${environment} ==="

    // Configure MongoDB credentials in Vault
    runAnsiblePlaybook(
        playbook: 'infra/ansible/mongodb/configure-vault-secrets.yml',
        extraVars: [
            target_env: environment,
            vault_token: vaultToken
        ]
    )

    // Update Helm dependencies for mongodb-environment chart
    sh """
        cd infra/helm/charts/mongodb-environment
        helm dependency update
        cd -
    """

    // Deploy MongoDB Helm chart
    sh """
        helm upgrade --install mongodb-${environment} \
            infra/helm/charts/mongodb-environment \
            --values infra/helm/charts/mongodb-environment/values/${environment}.yaml \
            --namespace ${environment} \
            --create-namespace \
            --wait \
            --timeout 10m
    """

    // Verify deployment
    sh """
        kubectl get mongodbcommunity -n ${environment}
        kubectl get pods -n ${environment} -l app=mongodb
    """

    echo "MongoDB deployed successfully"
}
