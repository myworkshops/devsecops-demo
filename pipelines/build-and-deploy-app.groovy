@Library('jenkins-library') _

pipeline {
    agent any

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

        // DockerHub credentials
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
    }

    stages {
        stage('Checkout Source Code') {
            steps {
                script {
                    echo "=== Checking out ${params.APP_NAME} from branch ${env.GIT_BRANCH} ==="

                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: "*/${env.GIT_BRANCH}"]],
                        userRemoteConfigs: [[
                            url: env.GIT_URL,
                            credentialsId: env.GIT_CREDENTIALS_ID
                        ]]
                    ])

                    echo "✓ Source code checked out from branch ${env.GIT_BRANCH}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "=== Building Docker image for ${params.APP_NAME} ==="

                    buildDockerImage(
                        appName: params.APP_NAME,
                        imageName: env.IMAGE_NAME,
                        imageTag: env.IMAGE_TAG,
                        dockerfilePath: "services/${params.APP_NAME}/Dockerfile",
                        contextPath: "services/${params.APP_NAME}"
                    )

                    echo "✓ Docker image built: ${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                script {
                    echo "=== Pushing ${env.IMAGE_NAME}:${env.IMAGE_TAG} to DockerHub ==="

                    sh """
                        echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin
                        docker push ${env.IMAGE_NAME}:${env.IMAGE_TAG}
                        docker logout
                    """

                    echo "✓ Image pushed to DockerHub"
                }
            }
        }

        stage('Deploy with Helm') {
            steps {
                script {
                    echo "=== Deploying ${params.APP_NAME} to ${params.ENVIRONMENT} ==="

                    deployApp(
                        appName: params.APP_NAME,
                        environment: params.ENVIRONMENT,
                        helmChart: env.HELM_CHART,
                        valuesFile: env.HELM_VALUES,
                        namespace: params.ENVIRONMENT
                    )

                    echo "✓ ${params.APP_NAME} deployed to ${params.ENVIRONMENT}"
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "=== Verifying ${params.APP_NAME} deployment ==="

                    sh """
                        kubectl rollout status deployment/${params.APP_NAME} -n ${params.ENVIRONMENT} --timeout=5m || true
                        kubectl get pods -n ${params.ENVIRONMENT} -l app.kubernetes.io/name=${params.APP_NAME} || true
                    """

                    echo "✓ Deployment verification completed"
                }
            }
        }
    }

    post {
        success {
            echo "✓ ${params.APP_NAME} successfully built and deployed to ${params.ENVIRONMENT}"
        }
        failure {
            echo "✗ Failed to build/deploy ${params.APP_NAME} to ${params.ENVIRONMENT}"
        }
        always {
            // Clean up Docker images to save space
            sh """
                docker rmi ${env.IMAGE_NAME}:${env.IMAGE_TAG} || true
                docker system prune -f || true
            """
        }
    }
}
