#!/usr/bin/env groovy

/**
 * Checkout code from Git repository using Jenkins Git plugin
 *
 * @param repository Git repository URL
 * @param branch Branch to checkout (default: 'main')
 * @param credentialsId Jenkins credentials ID for Git authentication
 */
def call(Map config = [:]) {
    def repository = config.repository ?: error("repository parameter is required")
    def branch = config.branch ?: 'main'
    def credentialsId = config.credentialsId ?: error("credentialsId parameter is required")

    echo "=== Checking out Git repository ==="
    echo "Repository: ${repository}"
    echo "Branch: ${branch}"
    echo "Credentials ID: ${credentialsId}"

    checkout([
        $class: 'GitSCM',
        branches: [[name: "*/${branch}"]],
        doGenerateSubmoduleConfigurations: false,
        extensions: [
            [$class: 'CleanBeforeCheckout'],
            [$class: 'CloneOption', depth: 1, noTags: false, shallow: true]
        ],
        userRemoteConfigs: [[
            url: repository,
            credentialsId: credentialsId
        ]]
    ])

    // Display latest commit info
    sh '''
        echo "Latest commit:"
        git log -1 --oneline
        echo "Current branch:"
        git branch --show-current || echo "Detached HEAD"
    '''

    echo "✓ Code checked out successfully"
}
