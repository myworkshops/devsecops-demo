"""Data models for Device Registration API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeviceRegistration(BaseModel):
    """Device registration data."""
    userKey: str = Field(..., description="User identifier")
    deviceType: str = Field(..., description="Device type (iOS/Android/Watch/TV)")
    device_name: Optional[str] = Field(None, description="Optional device name")

    class Config:
        json_schema_extra = {
            "example": {
                "userKey": "user123",
                "deviceType": "iOS"
            }
        }


class DeviceRegistrationResponse(BaseModel):
    """Response for device registration."""
    statusCode: int = Field(..., description="HTTP status code")

    class Config:
        json_schema_extra = {
            "example": {
                "statusCode": 200
            }
        }
