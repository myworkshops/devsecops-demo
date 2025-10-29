#!/usr/bin/env groovy

def call(Map config) {
    def appName = config.appName
    def environment = config.environment
    def imageTag = config.imageTag ?: 'latest'
    def chartPath = config.chartPath
    def valuesFile = config.valuesFile ?: "${chartPath}/values-${environment}.yaml"

    echo "=== Deploying ${appName} to ${environment} ==="

    sh """
        helm upgrade --install ${appName} ${chartPath} \
            --values ${valuesFile} \
            --set image.tag=${imageTag} \
            --namespace ${environment} \
            --create-namespace \
            --wait \
            --timeout 10m
    """

    echo "✓ ${appName} deployed successfully"
}
