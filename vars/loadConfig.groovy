#!/usr/bin/env groovy

/**
 * Load complete configuration from Vault (secrets.local.yaml stored as JSON)
 *
 * Usage:
 *   def config = loadConfig()
 *   echo "Vault replicas: ${config.vault.replicas}"
 *   echo "MongoDB password: ${config.mongodb.develop.password}"
 *   echo "Keycloak client: ${config.keycloak.clients[0].client_id}"
 *   echo "Web origins develop: ${config.keycloak.clients[0].web_origins.develop}"
 *
 * @return Map containing complete configuration (navigable object)
 */
def call() {
    echo "=== Loading configuration from Vault ==="

    try {
        // Use vault.getSecret to read the complete config stored as JSON string
        def configJson = vault.getSecret('secret/data/config/complete', 'data')

        // Parse JSON string to Map
        def config = readJSON text: configJson

        echo "✓ Configuration loaded from Vault successfully"

        return config

    } catch (Exception e) {
        error("Failed to load configuration from Vault: ${e.message}")
    }
}
