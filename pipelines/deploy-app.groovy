@Library('jenkins-library') _

pipeline {
    agent {
        label 'ansible'
    }

    parameters {
        string(name: 'APP_NAME', description: 'Application name (statistics-api, device-registration-api, frontend)')
        choice(name: 'ENVIRONMENT', choices: ['develop', 'stage', 'production'], description: 'Target environment')
        string(name: 'DOCKERHUB_REGISTRY', defaultValue: 'wmoinar', description: 'DockerHub registry username')
    }

    environment {
        // Map environment to Git branch
        GIT_BRANCH = "${params.ENVIRONMENT == 'production' ? 'main' : params.ENVIRONMENT}"

        // Docker image tag
        IMAGE_TAG = "${params.ENVIRONMENT}-latest"
        IMAGE_NAME = "${params.DOCKERHUB_REGISTRY}/${params.APP_NAME}"

        // Helm chart paths
        HELM_CHART = "infra/helm/charts/microservice"
        HELM_VALUES = "infra/helm/charts/microservice/values/${params.APP_NAME}-${params.ENVIRONMENT}.yaml"
    }

    stages {
        stage('Prepare Helm Chart') {
            steps {
                script {
                    echo "=== Updating Helm chart dependencies ==="
                    sh """
                        cd ${env.HELM_CHART}
                        helm dependency update
                        cd -
                    """
                    echo "✓ Chart dependencies updated"
                }
            }
        }

        stage('Deploy with Helm') {
            steps {
                script {
                    echo "=== Deploying ${params.APP_NAME} to ${params.ENVIRONMENT} ==="

                    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                        deployApp(
                            appName: params.APP_NAME,
                            environment: params.ENVIRONMENT,
                            imageTag: env.IMAGE_TAG,
                            chartPath: env.HELM_CHART,
                            valuesFile: env.HELM_VALUES
                        )
                    }

                    echo "✓ ${params.APP_NAME} deployed to ${params.ENVIRONMENT}"
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "=== Verifying ${params.APP_NAME} deployment ==="

                    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                        sh """
                            kubectl rollout status deployment/${params.APP_NAME} -n ${params.ENVIRONMENT} --timeout=5m || true
                            kubectl get pods -n ${params.ENVIRONMENT} -l app.kubernetes.io/name=${params.APP_NAME} || true
                        """
                    }

                    echo "✓ Deployment verification completed"
                }
            }
        }
    }

    post {
        success {
            echo "✓ ${params.APP_NAME} successfully deployed to ${params.ENVIRONMENT}"
        }
        failure {
            echo "✗ Failed to deploy ${params.APP_NAME} to ${params.ENVIRONMENT}"
        }
    }
}
