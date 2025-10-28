#!/usr/bin/env groovy

def call(Map config) {
    def imageName = config.imageName
    def imageTag = config.imageTag ?: 'latest'
    def dockerfilePath = config.dockerfilePath
    def buildContext = config.buildContext ?: '.'

    echo "=== Building Docker image: ${imageName}:${imageTag} ==="

    sh """
        docker build \
            -t ${imageName}:${imageTag} \
            -f ${dockerfilePath} \
            ${buildContext}
    """

    echo "✓ Docker image built successfully"

    return "${imageName}:${imageTag}"
}
