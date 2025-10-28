// Main application logic
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[APP] DOMContentLoaded event fired');

    // Check if we're on the app page
    if (!document.getElementById('registerForm')) {
        console.log('[APP] Not on app page, exiting');
        return;
    }

    console.log('[APP] On app page, checking for authorization code...');

    // Check for authorization code in URL (callback from Keycloak)
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    if (code) {
        console.log('[APP] Authorization code found in URL');
        // Exchange code for token
        const success = await auth.exchangeCode(code);
        if (!success) {
            console.error('[APP] Token exchange failed, redirecting to login');
            window.location.href = '/login.html';
            return;
        }
        console.log('[APP] Token exchange successful, cleaning URL');
        // Remove code from URL and reload to ensure clean state
        window.history.replaceState({}, document.title, '/app.html');
        // Force check authentication after token exchange
        if (!auth.isAuthenticated()) {
            console.error('[APP] Token validation failed after exchange, redirecting to login');
            window.location.href = '/login.html';
            return;
        }
        console.log('[APP] Token validated successfully after exchange');
    } else {
        console.log('[APP] No authorization code in URL');
        // Check authentication
        console.log('[APP] Checking authentication status...');
        if (!auth.isAuthenticated()) {
            console.error('[APP] User not authenticated, redirecting to login');
            window.location.href = '/login.html';
            return;
        }
    }

    console.log('[APP] User authenticated');

    // Display user info
    const userInfo = auth.getUserInfo();
    const userName = userInfo.preferred_username || userInfo.sub;
    console.log('[APP] User name:', userName);
    document.getElementById('userName').textContent = userName;

    // Logout handler
    document.getElementById('logoutBtn').addEventListener('click', () => {
        auth.logout();
    });

    // Register form handler
    const registerForm = document.getElementById('registerForm');
    const registerBtn = document.getElementById('registerBtn');
    const registerMessage = document.getElementById('registerMessage');

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log('[APP] Register form submitted');

        const deviceType = document.getElementById('registerDevice').value;
        console.log('[APP] Device type:', deviceType);

        if (!deviceType) {
            console.warn('[APP] No device type selected');
            showMessage(registerMessage, 'Please select a device type', 'error');
            return;
        }

        // Disable button
        registerBtn.disabled = true;
        registerBtn.textContent = 'Registering...';

        const url = `${CONFIG.api.baseUrl}/Log/auth`;
        const token = auth.getToken();
        console.log('[APP] POST URL:', url);
        console.log('[APP] Token:', token ? token.substring(0, 20) + '...' : 'null');

        try {
            console.log('[APP] Sending POST request...');
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    deviceType: deviceType
                })
            });

            console.log('[APP] Response status:', response.status);
            console.log('[APP] Response headers:', Object.fromEntries(response.headers.entries()));

            const data = await response.json();
            console.log('[APP] Response data:', data);

            if (response.ok && data.statusCode === 200) {
                console.log('[APP] Registration successful');
                showMessage(registerMessage, 'Login event registered successfully!', 'success');
                registerForm.reset();
            } else {
                console.error('[APP] Registration failed:', data);
                showMessage(registerMessage, 'Failed to register login event. Please try again.', 'error');
            }
        } catch (error) {
            console.error('[APP] Register error:', error);
            console.error('[APP] Error stack:', error.stack);
            showMessage(registerMessage, 'Network error. Please try again later.', 'error');
        } finally {
            registerBtn.disabled = false;
            registerBtn.textContent = 'Register';
        }
    });

    // Statistics form handler
    const statsForm = document.getElementById('statsForm');
    const queryBtn = document.getElementById('queryBtn');
    const statsMessage = document.getElementById('statsMessage');
    const statsResult = document.getElementById('statsResult');

    statsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        console.log('[APP] Statistics form submitted');

        const deviceType = document.getElementById('statsDevice').value;
        console.log('[APP] Query device type:', deviceType);

        if (!deviceType) {
            console.warn('[APP] No device type selected for query');
            showMessage(statsMessage, 'Please select a device type', 'error');
            return;
        }

        // Disable button
        queryBtn.disabled = true;
        queryBtn.textContent = 'Querying...';

        // Hide previous results
        statsResult.style.display = 'none';
        statsMessage.style.display = 'none';

        const url = `${CONFIG.api.baseUrl}/Log/auth/statistics?deviceType=${encodeURIComponent(deviceType)}`;
        const token = auth.getToken();
        console.log('[APP] GET URL:', url);
        console.log('[APP] Token:', token ? token.substring(0, 20) + '...' : 'null');

        try {
            console.log('[APP] Sending GET request...');
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            console.log('[APP] Response status:', response.status);
            console.log('[APP] Response headers:', Object.fromEntries(response.headers.entries()));

            const data = await response.json();
            console.log('[APP] Response data:', data);

            if (response.ok) {
                if (data.count === -1) {
                    console.error('[APP] Statistics returned -1 count');
                    showMessage(statsMessage, 'Statistics not available. Please try again later.', 'error');
                } else {
                    console.log('[APP] Statistics retrieved successfully:', data);
                    // Display results
                    document.getElementById('resultDeviceType').textContent = data.deviceType;
                    document.getElementById('resultCount').textContent = data.count;
                    statsResult.style.display = 'block';
                }
            } else {
                console.error('[APP] Statistics query failed');
                showMessage(statsMessage, 'Failed to retrieve statistics. Please try again.', 'error');
            }
        } catch (error) {
            console.error('[APP] Statistics error:', error);
            console.error('[APP] Error stack:', error.stack);
            showMessage(statsMessage, 'Network error. Please try again later.', 'error');
        } finally {
            queryBtn.disabled = false;
            queryBtn.textContent = 'Query Statistics';
        }
    });
});

// Helper function to show messages
function showMessage(element, message, type) {
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}
