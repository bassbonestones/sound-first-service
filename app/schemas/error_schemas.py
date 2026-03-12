"""Common error response schemas for API documentation."""
from pydantic import BaseModel
from typing import List, Optional


class ErrorResponse(BaseModel):
    """Standard error response returned by all error handlers."""
    error: bool = True
    status_code: int
    detail: str
    path: str

    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "status_code": 404,
                "detail": "Resource not found",
                "path": "/users/999"
            }
        }


class ValidationErrorItem(BaseModel):
    """Single validation error detail."""
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Response for 422 validation errors with field-level details."""
    error: bool = True
    status_code: int = 422
    detail: str = "Validation error"
    errors: List[ValidationErrorItem]
    path: str

    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "status_code": 422,
                "detail": "Validation error",
                "errors": [
                    {
                        "field": "body.email",
                        "message": "value is not a valid email address",
                        "type": "value_error.email"
                    }
                ],
                "path": "/users"
            }
        }


# Common response definitions for use in route decorators
ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad Request - Invalid input"},
    401: {"model": ErrorResponse, "description": "Unauthorized - Authentication required"},
    403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
    404: {"model": ErrorResponse, "description": "Not Found - Resource doesn't exist"},
    409: {"model": ErrorResponse, "description": "Conflict - Database constraint violation"},
    422: {"model": ValidationErrorResponse, "description": "Validation Error - Invalid request data"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
    503: {"model": ErrorResponse, "description": "Service Unavailable - Database error"},
}
