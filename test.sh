#!/bin/bash

# Quick API Test for develop environment

# 1. Obtain token from Keycloak
TOKEN=$(curl -s -X POST "http://keycloak.local/realms/develop/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password" \
    -d "client_id=statistics-frontend" \
    -d "username=operator-dev" \
    -d "password=dev-secret123" | jq -r '.access_token')

# 2. Verify token
echo "Token obtained: ${TOKEN:0:50}..."

# 3. Register login event
curl -v -X POST "http://statistics-api-dev.local/Log/auth" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"deviceType": "iOS"}'

# 4. Query statistics
curl "http://statistics-api-dev.local/Log/auth/statistics?deviceType=iOS" \
    -H "Authorization: Bearer $TOKEN"
