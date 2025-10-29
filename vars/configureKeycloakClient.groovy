#!/usr/bin/env groovy

def call(Map config) {
    def environment = config.environment
    def clientId = config.clientId
    def vaultToken = config.vaultToken
    def keycloakAdminUser = config.keycloakAdminUser
    def keycloakAdminPassword = config.keycloakAdminPassword

    echo "=== Configuring Keycloak client: ${clientId} in ${environment} ==="

    runAnsiblePlaybook(
        playbook: 'ansible/keycloak/create-client.yml',
        extraVars: [
            target_env: environment,
            client_id: clientId,
            keycloak_admin_user: keycloakAdminUser,
            keycloak_admin_password: keycloakAdminPassword,
            vault_token: vaultToken
        ]
    )

    echo "Keycloak client configured successfully"
}
