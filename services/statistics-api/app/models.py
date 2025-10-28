"""Data models for Statistics API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LoginEvent(BaseModel):
    """Login event data."""
    deviceType: str = Field(..., description="Device type (iOS/Android/Watch/TV)")
    timestamp: Optional[datetime] = Field(default=None, description="Event timestamp (internal)")

    class Config:
        json_schema_extra = {
            "example": {
                "deviceType": "iOS"
            }
        }


class LoginEventResponse(BaseModel):
    """Response for login event creation - PDF specification."""
    statusCode: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Response message")

    class Config:
        json_schema_extra = {
            "example": {
                "statusCode": 200,
                "message": "success"
            }
        }


class StatisticsResponse(BaseModel):
    """Response containing device statistics - PDF specification."""
    deviceType: str = Field(..., description="Device type queried")
    count: int = Field(..., description="Number of registrations for this device type")

    class Config:
        json_schema_extra = {
            "example": {
                "deviceType": "iOS",
                "count": 150
            }
        }
