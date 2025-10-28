#!/usr/bin/env groovy

def call(Map config) {
    def playbook = config.playbook
    def extraVars = config.extraVars ?: [:]
    def inventory = config.inventory ?: 'localhost,'

    echo "=== Running Ansible playbook: ${playbook} ==="

    // Build extra-vars string
    def extraVarsStr = extraVars.collect { k, v -> "${k}='${v}'" }.join(' ')

    sh """
        cd infra
        ANSIBLE_CONFIG=ansible/ansible.cfg \
        ansible-playbook ${playbook} \
            -i ${inventory} \
            -e "${extraVarsStr}"
    """

    echo "✓ Ansible playbook executed successfully"
}
