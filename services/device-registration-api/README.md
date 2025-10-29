# Device Registration API

Internal-only API for registering device types for users.

## Endpoints

### POST /Device/register
Register a device type for a user.

**Authentication:** Required (Keycloak JWT with 'admin' or 'operator' role)

**Request:**
```json
{
  "user_id": "user123",
  "device_type": "mobile",
  "device_name": "iPhone 15"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device registered successfully",
  "registration_id": "507f1f77bcf86cd799439011"
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

- **Access:** Internal only (ClusterIP service)
- **Service Type:** ClusterIP
- **Port:** 8000
- **RBAC:** Requires 'admin' or 'operator' role
