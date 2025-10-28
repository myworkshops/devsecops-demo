@Library('jenkins-library') _

pipeline {
    agent any

    parameters {
        choice(name: 'APP_NAME', choices: ['statistics-api', 'device-registration-api', 'frontend'], description: 'Application')
        choice(name: 'ENVIRONMENT', choices: ['develop', 'stage', 'production'], description: 'Environment')
        string(name: 'IMAGE_TAG', defaultValue: '', description: 'Image tag (empty = auto)')
        string(name: 'DOCKERHUB_REGISTRY', defaultValue: 'wmoinar', description: 'Registry')
        booleanParam(name: 'SKIP_BUILD', defaultValue: false, description: 'Skip build')
        booleanParam(name: 'DEPLOY_MONGODB', defaultValue: true, description: 'Deploy MongoDB (API only)')
        booleanParam(name: 'CONFIGURE_KEYCLOAK', defaultValue: true, description: 'Configure Keycloak (API only)')
    }

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        VAULT_TOKEN = credentials('vault-token')
        KEYCLOAK_ADMIN = credentials('keycloak-admin-credentials')
        VAULT_ADDR = "http://vault.vault.svc.cluster.local:8200"

        GIT_SHA = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
        COMPUTED_IMAGE_TAG = "${params.IMAGE_TAG ?: "${params.ENVIRONMENT}-${GIT_SHA}"}"

        // Determine if frontend or backend API
        IS_FRONTEND = "${params.APP_NAME == 'frontend' ? 'true' : 'false'}"

        // Adjust paths based on app type
        APP_SOURCE_PATH = "${params.APP_NAME == 'frontend' ? 'frontend' : 'services/' + params.APP_NAME}"
        DOCKERFILE_PATH = "${params.APP_NAME == 'frontend' ? 'frontend/Dockerfile' : 'services/' + params.APP_NAME + '/Dockerfile'}"

        DOCKER_IMAGE = "${params.DOCKERHUB_REGISTRY}/${params.APP_NAME}:${COMPUTED_IMAGE_TAG}"
        HELM_CHART_PATH = "infra/helm/charts/microservice"
        HELM_VALUES_FILE = "infra/helm/charts/microservice/values/${params.APP_NAME}-${params.ENVIRONMENT}.yaml"
    }

    stages {
        stage('Info') {
            steps {
                script {
                    echo "Deploying ${params.APP_NAME} to ${params.ENVIRONMENT}"
                    echo "Image: ${DOCKER_IMAGE}"
                }
            }
        }

        stage('Validate Paths') {
            steps {
                script {
                    sh """
                        test -d ${APP_SOURCE_PATH} || (echo "Source not found: ${APP_SOURCE_PATH}" && exit 1)
                        test -f ${DOCKERFILE_PATH} || (echo "Dockerfile not found: ${DOCKERFILE_PATH}" && exit 1)
                        test -d ${HELM_CHART_PATH} || (echo "Chart not found: ${HELM_CHART_PATH}" && exit 1)
                        test -f ${HELM_VALUES_FILE} || (echo "Values file not found: ${HELM_VALUES_FILE}" && exit 1)
                    """
                }
            }
        }

        stage('Build Docker Image') {
            when {
                expression { params.SKIP_BUILD == false }
            }
            steps {
                script {
                    echo "Building image: ${DOCKER_IMAGE}"

                    buildDockerImage(
                        imageName: "${params.DOCKERHUB_REGISTRY}/${params.APP_NAME}",
                        imageTag: "${COMPUTED_IMAGE_TAG}",
                        dockerfilePath: "${DOCKERFILE_PATH}",
                        buildContext: "${APP_SOURCE_PATH}"
                    )
                }
            }
        }

        stage('Push Docker Image') {
            when {
                expression { params.SKIP_BUILD == false }
            }
            steps {
                script {
                    echo "Pushing image to DockerHub"

                    sh 'echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin'
                    sh "docker push ${DOCKER_IMAGE}"

                    if (params.ENVIRONMENT == 'develop') {
                        sh """
                            docker tag ${DOCKER_IMAGE} ${params.DOCKERHUB_REGISTRY}/${params.APP_NAME}:latest
                            docker push ${params.DOCKERHUB_REGISTRY}/${params.APP_NAME}:latest
                        """
                    }
                }
            }
        }

        stage('Configure Keycloak') {
            when {
                allOf {
                    expression { params.CONFIGURE_KEYCLOAK == true }
                    expression { params.APP_NAME != 'frontend' }
                }
            }
            steps {
                script {
                    echo "Configuring Keycloak client for ${params.APP_NAME}"

                    configureKeycloakClient(
                        environment: params.ENVIRONMENT,
                        clientId: "${params.APP_NAME}-${params.ENVIRONMENT}",
                        vaultToken: env.VAULT_TOKEN,
                        keycloakAdminUser: env.KEYCLOAK_ADMIN_USR,
                        keycloakAdminPassword: env.KEYCLOAK_ADMIN_PSW
                    )
                }
            }
        }

        stage('Deploy MongoDB') {
            when {
                allOf {
                    expression { params.DEPLOY_MONGODB == true }
                    expression { params.APP_NAME != 'frontend' }
                }
            }
            steps {
                script {
                    echo "Deploying MongoDB for ${params.ENVIRONMENT}"

                    deployMongoDB(
                        environment: params.ENVIRONMENT,
                        vaultToken: env.VAULT_TOKEN
                    )
                }
            }
        }

        stage('Deploy Application') {
            steps {
                script {
                    echo "Deploying ${params.APP_NAME}"

                    deployApp(
                        appName: params.APP_NAME,
                        environment: params.ENVIRONMENT,
                        imageTag: COMPUTED_IMAGE_TAG,
                        chartPath: HELM_CHART_PATH,
                        valuesFile: HELM_VALUES_FILE
                    )
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                script {
                    echo "Verifying deployment"

                    sh """
                        helm status ${params.APP_NAME} -n ${params.ENVIRONMENT}
                        kubectl get pods -n ${params.ENVIRONMENT} -l app=${params.APP_NAME}
                        kubectl wait --for=condition=available --timeout=300s \
                            deployment/${params.APP_NAME} -n ${params.ENVIRONMENT}
                    """
                }
            }
        }
    }

    post {
        success {
            echo "Deployment successful"
        }
        failure {
            echo "Deployment failed"
        }
        always {
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
    }
}
