// Authentication module
class Auth {
    constructor() {
        this.token = localStorage.getItem('access_token');
        this.userInfo = null;
    }

    // Login with Keycloak using Authorization Code Flow
    login() {
        const authUrl = `${CONFIG.keycloak.url}/realms/${CONFIG.keycloak.realm}/protocol/openid-connect/auth`;
        // Use window.location.origin to dynamically detect the frontend URL
        const redirectUri = `${window.location.origin}/app.html`;

        const params = new URLSearchParams({
            client_id: CONFIG.keycloak.clientId,
            redirect_uri: redirectUri,
            response_type: 'code',
            scope: 'openid profile email'
        });

        window.location.href = `${authUrl}?${params.toString()}`;
    }

    // Exchange authorization code for tokens
    async exchangeCode(code) {
        console.log('[AUTH] Starting token exchange...');
        console.log('[AUTH] Code:', code.substring(0, 20) + '...');

        const tokenUrl = `${CONFIG.keycloak.url}/realms/${CONFIG.keycloak.realm}/protocol/openid-connect/token`;
        // Use window.location.origin to dynamically detect the frontend URL
        const redirectUri = `${window.location.origin}/app.html`;

        console.log('[AUTH] Token URL:', tokenUrl);
        console.log('[AUTH] Redirect URI:', redirectUri);
        console.log('[AUTH] Client ID:', CONFIG.keycloak.clientId);

        const params = new URLSearchParams({
            grant_type: 'authorization_code',
            client_id: CONFIG.keycloak.clientId,
            code: code,
            redirect_uri: redirectUri
        });

        try {
            console.log('[AUTH] Sending token request...');
            const response = await fetch(tokenUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: params.toString()
            });

            console.log('[AUTH] Response status:', response.status);
            console.log('[AUTH] Response headers:', Object.fromEntries(response.headers.entries()));

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[AUTH] Token exchange failed:', errorText);
                throw new Error('Failed to exchange code for token: ' + response.status);
            }

            const data = await response.json();
            console.log('[AUTH] Token received successfully');
            console.log('[AUTH] Token type:', data.token_type);
            console.log('[AUTH] Expires in:', data.expires_in);

            this.token = data.access_token;
            localStorage.setItem('access_token', this.token);

            // Decode token to get user info
            this.userInfo = this.decodeToken(this.token);
            console.log('[AUTH] User info:', this.userInfo);

            return true;
        } catch (error) {
            console.error('[AUTH] Token exchange error:', error);
            console.error('[AUTH] Error stack:', error.stack);
            return false;
        }
    }

    // Decode JWT token
    decodeToken(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));

            return JSON.parse(jsonPayload);
        } catch (error) {
            console.error('Token decode error:', error);
            return null;
        }
    }

    // Check if user is authenticated
    isAuthenticated() {
        if (!this.token) return false;

        if (!this.userInfo) {
            this.userInfo = this.decodeToken(this.token);
        }

        // Check token expiration
        const now = Math.floor(Date.now() / 1000);
        return this.userInfo && this.userInfo.exp > now;
    }

    // Get user information
    getUserInfo() {
        if (!this.userInfo) {
            this.userInfo = this.decodeToken(this.token);
        }
        return this.userInfo;
    }

    // Get access token
    getToken() {
        return this.token;
    }

    // Logout
    logout() {
        localStorage.removeItem('access_token');
        this.token = null;
        this.userInfo = null;

        const logoutUrl = `${CONFIG.keycloak.url}/realms/${CONFIG.keycloak.realm}/protocol/openid-connect/logout`;
        // Use window.location.origin to dynamically detect the frontend URL
        const redirectUri = `${window.location.origin}/login.html`;

        window.location.href = `${logoutUrl}?redirect_uri=${encodeURIComponent(redirectUri)}`;
    }
}

// Initialize auth instance
const auth = new Auth();

// Handle login button on login page
if (document.getElementById('loginBtn')) {
    document.getElementById('loginBtn').addEventListener('click', () => {
        auth.login();
    });
}
