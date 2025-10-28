@Library('jenkins-library') _

pipeline {
    agent any

    parameters {
        choice(name: 'ENVIRONMENT', choices: ['develop', 'stage', 'production'], description: 'Target environment to deploy')
        string(name: 'DOCKERHUB_REGISTRY', defaultValue: 'wmoinar', description: 'DockerHub registry username')
    }

    environment {
        VAULT_URL = 'http://vault.vault.svc.cluster.local:8200'
    }

    stages {
        stage('Deploy Infrastructure') {
            parallel {
                stage('Deploy MongoDB') {
                    steps {
                        script {
                            echo "=== Deploying MongoDB for ${params.ENVIRONMENT} ==="
                            deployMongoDB(
                                environment: params.ENVIRONMENT
                            )
                            echo "✓ MongoDB deployed for ${params.ENVIRONMENT}"
                        }
                    }
                }

                stage('Configure Keycloak Client') {
                    steps {
                        script {
                            echo "=== Configuring Keycloak client for ${params.ENVIRONMENT} ==="

                            // Only configure the public frontend client (shared by all apps)
                            configureKeycloakClient(
                                environment: params.ENVIRONMENT,
                                clientId: "statistics-frontend"
                            )

                            echo "✓ Keycloak client configured for ${params.ENVIRONMENT}"
                        }
                    }
                }
            }
        }

        stage('Build and Deploy Applications') {
            parallel {
                stage('Deploy statistics-api') {
                    steps {
                        script {
                            echo "=== Building and deploying statistics-api to ${params.ENVIRONMENT} ==="
                            build job: 'build-and-deploy-app',
                                parameters: [
                                    string(name: 'APP_NAME', value: 'statistics-api'),
                                    string(name: 'ENVIRONMENT', value: params.ENVIRONMENT),
                                    string(name: 'DOCKERHUB_REGISTRY', value: params.DOCKERHUB_REGISTRY)
                                ],
                                wait: true,
                                propagate: true
                        }
                    }
                }

                stage('Deploy device-registration-api') {
                    steps {
                        script {
                            echo "=== Building and deploying device-registration-api to ${params.ENVIRONMENT} ==="
                            build job: 'build-and-deploy-app',
                                parameters: [
                                    string(name: 'APP_NAME', value: 'device-registration-api'),
                                    string(name: 'ENVIRONMENT', value: params.ENVIRONMENT),
                                    string(name: 'DOCKERHUB_REGISTRY', value: params.DOCKERHUB_REGISTRY)
                                ],
                                wait: true,
                                propagate: true
                        }
                    }
                }

                stage('Deploy frontend') {
                    steps {
                        script {
                            echo "=== Building and deploying frontend to ${params.ENVIRONMENT} ==="
                            build job: 'build-and-deploy-app',
                                parameters: [
                                    string(name: 'APP_NAME', value: 'frontend'),
                                    string(name: 'ENVIRONMENT', value: params.ENVIRONMENT),
                                    string(name: 'DOCKERHUB_REGISTRY', value: params.DOCKERHUB_REGISTRY)
                                ],
                                wait: true,
                                propagate: true
                        }
                    }
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "=== Verifying ${params.ENVIRONMENT} deployment ==="

                    sh """
                        echo "Pods in ${params.ENVIRONMENT} namespace:"
                        kubectl get pods -n ${params.ENVIRONMENT} || true

                        echo ""
                        echo "Services in ${params.ENVIRONMENT} namespace:"
                        kubectl get services -n ${params.ENVIRONMENT} || true

                        echo ""
                        echo "Ingresses in ${params.ENVIRONMENT} namespace:"
                        kubectl get ingress -n ${params.ENVIRONMENT} || true
                    """

                    echo "✓ ${params.ENVIRONMENT} environment deployed successfully"
                }
            }
        }
    }

    post {
        success {
            echo "✓ Environment ${params.ENVIRONMENT} deployed successfully"
        }
        failure {
            echo "✗ Failed to deploy environment ${params.ENVIRONMENT}"
        }
    }
}
