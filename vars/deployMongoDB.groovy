#!/usr/bin/env groovy

def call(Map config) {
    def environment = config.environment

    echo "=== Deploying MongoDB for environment: ${environment} ==="

    // MongoDB credentials are already in Vault from bootstrap
    // External Secrets Operator will sync them automatically

    withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        // Update Helm dependencies for mongodb-environment chart
        sh """
            cd infra/helm/charts/mongodb-environment
            helm dependency update
            cd -
        """

        // Deploy MongoDB Helm chart
        sh """
            helm upgrade --install mongodb-${environment} \
                infra/helm/charts/mongodb-environment \
                --values infra/helm/charts/mongodb-environment/values/${environment}.yaml \
                --namespace ${environment} \
                --create-namespace \
                --wait \
                --timeout 10m
        """

        // Verify deployment
        sh """
            kubectl get mongodbcommunity -n ${environment} || echo "MongoDB not yet created"
            kubectl get pods -n ${environment} -l app=mongodb || echo "MongoDB pods not yet running"
        """
    }

    echo "✓ MongoDB deployed successfully"
}
