@Library('jenkins-library') _

pipeline {
    agent any

    parameters {
        string(name: 'GIT_REPOSITORY', description: 'Git repository URL')
        string(name: 'GIT_BRANCH', description: 'Git branch to build')
        string(name: 'GIT_CREDENTIALS_ID', description: 'Git credentials ID (configured in Jenkins)')
    }

    environment {
        VAULT_URL = 'http://vault.vault.svc.cluster.local:8200'
    }

    stages {
        stage('Checkout Source Code') {
            steps {
                script {
                    echo '=== Checking out source code ==='
                    echo "Repository: ${params.GIT_REPOSITORY}"
                    echo "Branch: ${params.GIT_BRANCH}"
                    echo "Credentials ID: ${params.GIT_CREDENTIALS_ID}"

                    gitCheckout(
                        repository: params.GIT_REPOSITORY,
                        branch: params.GIT_BRANCH,
                        credentialsId: params.GIT_CREDENTIALS_ID
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
