@Library('jenkins-library') _

pipeline {
    agent any

    environment {
        VAULT_URL = 'http://vault.vault.svc.cluster.local:8200'
        GIT_CREDENTIALS_ID = 'github-credentials'
    }

    stages {
        stage('Retrieve Configuration from Vault') {
            steps {
                script {
                    echo '=== Retrieving configuration from Vault ==='

                    // Get Git repository and token from Vault
                    env.GIT_REPOSITORY = vault.getSecret('secret/data/github', 'repository')
                    env.GIT_BRANCH = 'main'  // Default branch

                    echo "Repository: ${env.GIT_REPOSITORY}"
                    echo "Branch: ${env.GIT_BRANCH}"
                    echo "Credentials ID: ${env.GIT_CREDENTIALS_ID}"
                    echo '✓ Configuration retrieved from Vault'
                }
            }
        }

        stage('Checkout Source Code') {
            steps {
                script {
                    echo '=== Checking out source code ==='

                    gitCheckout(
                        repository: env.GIT_REPOSITORY,
                        branch: env.GIT_BRANCH,
                        credentialsId: env.GIT_CREDENTIALS_ID
                    )

                    echo '✓ Source code checked out successfully'
                }
            }
        }

        stage('Test: Verify Vault Integration') {
            steps {
                script {
                    echo '=== Testing Vault integration ==='

                    // Retrieve all secrets and save to secrets.json
                    def secretsConfig = [
                        github: [
                            path: 'secret/data/github',
                            keys: ['token', 'repository']
                        ],
                        dockerhub: [
                            path: 'secret/data/dockerhub',
                            keys: ['username', 'password']
                        ],
                        sonarcloud: [
                            path: 'secret/data/sonarcloud',
                            keys: ['token']
                        ]
                    ]

                    vault.getAllSecrets(secretsConfig, 'secrets.json')

                    def secrets = readJSON file: 'secrets.json'
                    echo "GitHub repository: ${secrets.github.repository}"
                    echo "DockerHub username: ${secrets.dockerhub.username}"
                    echo "SonarCloud token present: ${secrets.sonarcloud.token ? 'Yes' : 'No'}"

                    echo '✓ Vault integration test completed successfully'
                    echo '✓ All secrets retrieved and saved to secrets.json'
                }
            }
        }
    }

    post {
        always {
            echo '=== Pipeline completed ==='
            // Clean up sensitive files
            sh 'rm -f secrets.json || true'
        }
        success {
            echo '✓ DeployDevSecOpsApp pipeline executed successfully'
        }
        failure {
            echo '✗ DeployDevSecOpsApp pipeline failed'
        }
    }
}
