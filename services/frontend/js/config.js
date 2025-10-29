// Configuration
const CONFIG = {
    keycloak: {
        url: 'http://keycloak.local',
        realm: 'develop',
        clientId: 'statistics-frontend'
    },
    api: {
        baseUrl: 'http://statistics-api-dev.local'
    }
    // Note: Frontend URL is detected dynamically using window.location.origin
};
