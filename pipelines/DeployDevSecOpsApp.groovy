@Library('jenkins-library') _

pipeline {
    agent none

    parameters {
        string(name: 'GIT_REPOSITORY', description: 'Git repository URL')
        string(name: 'GIT_BRANCH', description: 'Git branch to build')
        string(name: 'GIT_CREDENTIALS_ID', description: 'Git credentials ID (configured in Jenkins)')
    }

    stages {
        stage('Load Configuration') {
            agent any
            steps {
                script {
                    echo '=== Loading configuration from Vault ==='
                    def config = loadConfig()

                    // Override parameters with config from Vault if not provided
                    if (!params.GIT_REPOSITORY) {
                        env.GIT_REPOSITORY = config.jenkins.git_repository
                    } else {
                        env.GIT_REPOSITORY = params.GIT_REPOSITORY
                    }

                    if (!params.GIT_CREDENTIALS_ID) {
                        env.GIT_CREDENTIALS_ID = config.jenkins.git_credentials_id
                    } else {
                        env.GIT_CREDENTIALS_ID = params.GIT_CREDENTIALS_ID
                    }

                    echo '✓ Configuration loaded successfully'
                }
            }
        }

        stage('Checkout Source Code') {
            agent any
            steps {
                script {
                    echo '=== Checking out source code ==='
                    echo "Repository: ${env.GIT_REPOSITORY}"
                    echo "Branch: ${params.GIT_BRANCH}"
                    echo "Credentials ID: ${env.GIT_CREDENTIALS_ID}"

                    gitCheckout(
                        repository: env.GIT_REPOSITORY,
                        branch: params.GIT_BRANCH,
                        credentialsId: env.GIT_CREDENTIALS_ID
                    )

                    echo '✓ Source code checked out successfully'
                }
            }
        }

        stage('Test: Verify Vault Integration') {
            agent any
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

        stage('Deploy All Environments') {
            agent none
            parallel {
                stage('Deploy Develop Environment') {
                    steps {
                        script {
                            echo '=== Deploying develop environment ==='
                            build job: 'deploy-environment',
                                parameters: [
                                    string(name: 'ENVIRONMENT', value: 'develop'),
                                    string(name: 'DOCKERHUB_REGISTRY', value: 'wmoinar')
                                ],
                                wait: false,
                                propagate: false
                        }
                    }
                }

                // Commented out - enable when ready for stage deployment
                // stage('Deploy Stage Environment') {
                //     steps {
                //         script {
                //             echo '=== Deploying stage environment ==='
                //             build job: 'deploy-environment',
                //                 parameters: [
                //                     string(name: 'ENVIRONMENT', value: 'stage'),
                //                     string(name: 'DOCKERHUB_REGISTRY', value: 'wmoinar')
                //                 ],
                //                 wait: false,
                //                 propagate: false
                //         }
                //     }
                // }

                // Commented out - enable when ready for production deployment
                // stage('Deploy Production Environment') {
                //     steps {
                //         script {
                //             echo '=== Deploying production environment ==='
                //             build job: 'deploy-environment',
                //                 parameters: [
                //                     string(name: 'ENVIRONMENT', value: 'production'),
                //                     string(name: 'DOCKERHUB_REGISTRY', value: 'wmoinar')
                //                 ],
                //                 wait: false,
                //                 propagate: false
                //         }
                //     }
                // }
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
