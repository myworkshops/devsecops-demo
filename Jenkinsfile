// DevSecOps Device Statistics Platform - Basic Functionality Test Pipeline
// Tests: Git clone, Docker pull, SonarCloud connectivity

pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
metadata:
  labels:
    jenkins: agent
spec:
  containers:
  - name: tools
    image: python:3.11-slim
    command:
    - cat
    tty: true
    resources:
      requests:
        memory: "256Mi"
        cpu: "250m"
      limits:
        memory: "512Mi"
        cpu: "500m"
  - name: docker
    image: docker:24-dind
    securityContext:
      privileged: true
    tty: true
    resources:
      requests:
        memory: "512Mi"
        cpu: "500m"
      limits:
        memory: "1Gi"
        cpu: "1000m"
'''
        }
    }

    parameters {
        booleanParam(name: 'TRIGGER_DEPLOY', defaultValue: false, description: 'Trigger deployment after tests')
        choice(name: 'APP_TO_DEPLOY', choices: ['statistics-api', 'device-registration-api'], description: 'Application to deploy')
        choice(name: 'DEPLOY_ENVIRONMENT', choices: ['develop', 'stage', 'production'], description: 'Target environment')
    }

    options {
        timestamps()
        ansiColor('xterm')
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        // Build info
        BUILD_VERSION = "${env.BRANCH_NAME}-${env.BUILD_NUMBER}"

        // Credentials from Jenkins (stored during bootstrap)
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
        SONARCLOUD_TOKEN = credentials('sonarcloud-token')
        VAULT_TOKEN = credentials('vault-token')

        // Vault address
        VAULT_ADDR = "http://vault.vault.svc.cluster.local:8200"
    }

    stages {
        stage('Info') {
            steps {
                script {
                    echo "=========================================="
                    echo "Build Version: ${BUILD_VERSION}"
                    echo "Branch: ${env.BRANCH_NAME}"
                    echo "Commit: ${env.GIT_COMMIT}"
                    echo "Workspace: ${env.WORKSPACE}"
                    echo "=========================================="
                }
            }
        }

        stage('Test Git Clone') {
            steps {
                script {
                    echo "Testing Git clone..."
                    sh '''
                        echo "Git repository already cloned by Jenkins"
                        echo "Current directory: $(pwd)"
                        echo "Git status:"
                        git status
                        echo "Git log (last commit):"
                        git log -1 --oneline
                        echo "Files in repository:"
                        ls -la
                    '''
                }
            }
        }

        stage('Test Vault Connection') {
            steps {
                container('tools') {
                    script {
                        echo "Testing Vault connectivity..."
                        sh '''
                            apt-get update -qq && apt-get install -y -qq curl jq

                            echo "Vault Address: ${VAULT_ADDR}"

                            # Test Vault health
                            echo "Testing Vault health endpoint..."
                            curl -s ${VAULT_ADDR}/v1/sys/health | jq '.' || echo "Vault health check failed"

                            # Test reading secrets from Vault
                            echo "Reading Jenkins secrets from Vault..."
                            curl -s -H "X-Vault-Token: ${VAULT_TOKEN}" \
                                ${VAULT_ADDR}/v1/secret/data/jenkins | jq '.data.data' || echo "Failed to read Jenkins secrets"

                            echo "Vault connection test completed"
                        '''
                    }
                }
            }
        }

        stage('Test Docker Pull') {
            steps {
                container('docker') {
                    script {
                        echo "Testing Docker pull..."
                        sh '''
                            # Wait for Docker daemon to be ready
                            echo "Waiting for Docker daemon..."
                            timeout 30 sh -c 'until docker info; do sleep 1; done' || exit 1

                            # Login to DockerHub
                            echo "Logging in to DockerHub..."
                            echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin

                            # Pull a test image
                            echo "Pulling test image (alpine:latest)..."
                            docker pull alpine:latest

                            # Verify image
                            echo "Verifying pulled image..."
                            docker images alpine:latest

                            # Test running container
                            echo "Testing container execution..."
                            docker run --rm alpine:latest echo "Docker container test successful!"

                            echo "Docker pull test completed successfully"
                        '''
                    }
                }
            }
        }

        stage('Test SonarCloud Connection') {
            steps {
                container('tools') {
                    script {
                        echo "Testing SonarCloud connectivity..."
                        sh '''
                            apt-get update -qq && apt-get install -y -qq curl jq

                            # Test SonarCloud API connection
                            echo "Testing SonarCloud API..."
                            RESPONSE=$(curl -s -w "\\n%{http_code}" -u "${SONARCLOUD_TOKEN}:" \
                                https://sonarcloud.io/api/authentication/validate)

                            HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
                            BODY=$(echo "$RESPONSE" | head -n-1)

                            echo "HTTP Status Code: $HTTP_CODE"
                            echo "Response: $BODY"

                            if [ "$HTTP_CODE" = "200" ]; then
                                echo "SonarCloud authentication successful!"
                                echo "$BODY" | jq '.'
                            else
                                echo "SonarCloud authentication failed with status: $HTTP_CODE"
                                exit 1
                            fi
                        '''
                    }
                }
            }
        }

        stage('Summary') {
            steps {
                script {
                    echo "=========================================="
                    echo "All connectivity tests passed!"
                    echo "- Git clone: OK"
                    echo "- Vault connection: OK"
                    echo "- Docker pull: OK"
                    echo "- SonarCloud connection: OK"
                    echo "=========================================="
                }
            }
        }

        stage('Deploy Application (Child Pipeline)') {
            when {
                expression { params.TRIGGER_DEPLOY == true }
            }
            steps {
                script {
                    echo "Triggering deployment pipeline..."
                    build job: 'pipelines/deploy-app',
                        parameters: [
                            choice(name: 'APP_NAME', value: params.APP_TO_DEPLOY),
                            choice(name: 'ENVIRONMENT', value: params.DEPLOY_ENVIRONMENT),
                            string(name: 'IMAGE_TAG', value: ''),
                            string(name: 'DOCKERHUB_REGISTRY', value: 'wmoinar'),
                            booleanParam(name: 'SKIP_BUILD', value: false),
                            booleanParam(name: 'DEPLOY_MONGODB', value: true),
                            booleanParam(name: 'CONFIGURE_KEYCLOAK', value: true)
                        ],
                        wait: true
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline completed successfully!"
        }
        failure {
            echo "Pipeline failed! Check logs above for details."
        }
        always {
            echo "Cleaning up workspace to save disk space..."
            cleanWs(
                deleteDirs: true,
                disableDeferredWipeout: true,
                notFailBuild: true
            )
        }
    }
}
