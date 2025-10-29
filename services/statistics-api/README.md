# Statistics API

Public-facing API for storing device login events and retrieving device type statistics.

## Endpoints

### POST /Log/auth
Store a user login event with device type.

**Authentication:** Required (Keycloak JWT)

**Request:**
```json
{
  "user_id": "user123",
  "device_type": "mobile"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login event stored successfully",
  "event_id": "507f1f77bcf86cd799439011"
}
```

### GET /Log/auth/statistics
Retrieve statistics showing count of devices by type.

**Authentication:** Required (Keycloak JWT)

**Response:**
```json
{
  "total_events": 150,
  "statistics": [
    {"device_type": "mobile", "count": 80},
    {"device_type": "desktop", "count": 50},
    {"device_type": "tablet", "count": 20}
  ]
}
```

## Health Endpoints

- `GET /health` - Basic health check
- `GET /ready` - Readiness probe (checks MongoDB)
- `GET /live` - Liveness probe

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Run locally
uvicorn app.main:app --reload
```

## Deployment

- **Access:** Public (via Ingress)
- **Service Type:** LoadBalancer/NodePort
- **Port:** 8000
