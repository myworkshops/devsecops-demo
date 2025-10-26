#!/usr/bin/env groovy

/**
 * Read a secret value from HashiCorp Vault
 *
 * @param path Vault secret path (e.g., 'secret/data/github')
 * @param key The key within the secret to retrieve
 * @return The secret value
 */
def getSecret(String path, String key) {
    def vaultUrl = env.VAULT_URL ?: 'http://vault.vault.svc.cluster.local:8200'

    withCredentials([string(credentialsId: 'vault-token', variable: 'VAULT_TOKEN')]) {
        def response = sh(
            script: """
                curl -s -H "X-Vault-Token: \${VAULT_TOKEN}" \\
                     -H "X-Vault-Request: true" \\
                     ${vaultUrl}/v1/${path}
            """,
            returnStdout: true
        ).trim()

        def jsonResponse = readJSON text: response

        if (jsonResponse.data && jsonResponse.data.data && jsonResponse.data.data[key]) {
            return jsonResponse.data.data[key]
        } else {
            error "Failed to retrieve key '${key}' from path '${path}'"
        }
    }
}

/**
 * Write a secret value to HashiCorp Vault
 *
 * @param path Vault secret path (e.g., 'secret/data/github')
 * @param key The key to store
 * @param value The value to store
 */
def writeSecret(String path, String key, Object value) {
    def vaultUrl = env.VAULT_URL ?: 'http://vault.vault.svc.cluster.local:8200'

    withCredentials([string(credentialsId: 'vault-token', variable: 'VAULT_TOKEN')]) {
        // Read existing data first to merge
        def existingData = [:]
        try {
            def response = sh(
                script: """
                    curl -s -H "X-Vault-Token: \${VAULT_TOKEN}" \\
                         -H "X-Vault-Request: true" \\
                         ${vaultUrl}/v1/${path}
                """,
                returnStdout: true
            ).trim()

            def jsonResponse = readJSON text: response
            if (jsonResponse.data && jsonResponse.data.data) {
                existingData = jsonResponse.data.data
            }
        } catch (Exception e) {
            echo "No existing data at ${path}, creating new secret"
        }

        // Merge new key-value
        existingData[key] = value

        // Write back to Vault
        def payload = writeJSON(
            returnText: true,
            json: [data: existingData]
        )

        sh """
            curl -s -X PUT \\
                 -H "X-Vault-Token: \${VAULT_TOKEN}" \\
                 -H "X-Vault-Request: true" \\
                 -H "Content-Type: application/json" \\
                 -d '${payload}' \\
                 ${vaultUrl}/v1/${path}
        """

        echo "✓ Written key '${key}' to path '${path}'"
    }
}

/**
 * Read all secrets from a Vault path and write to JSON file
 *
 * @param secretPaths Map of secret names to Vault paths
 * @param outputFile Output JSON file path (default: 'secrets.json')
 * @return Map of retrieved secrets
 */
def getAllSecrets(Map secretPaths, String outputFile = 'secrets.json') {
    def secrets = [:]

    secretPaths.each { name, pathInfo ->
        def path = pathInfo.path
        def keys = pathInfo.keys ?: []

        echo "Retrieving secrets from: ${path}"

        def secretData = [:]
        keys.each { key ->
            secretData[key] = getSecret(path, key)
        }

        secrets[name] = secretData
        echo "✓ Retrieved ${keys.size()} keys from ${name}"
    }

    // Write secrets to JSON file
    writeJSON file: outputFile, json: secrets, pretty: 4
    echo "✓ All secrets written to ${outputFile}"

    return secrets
}
