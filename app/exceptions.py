"""Custom exception hierarchy for Sound First application.

This module provides a structured exception hierarchy that enables:
- Consistent error handling across the application
- Automatic HTTP status code mapping
- Structured logging with context
- Machine-readable error codes for client handling

Exception Hierarchy:
    SoundFirstException (base)
    ├── ResourceNotFoundError (404)
    │   ├── UserNotFoundError
    │   ├── SessionNotFoundError
    │   ├── MaterialNotFoundError
    │   ├── CapabilityNotFoundError
    │   └── InstrumentNotFoundError
    ├── ValidationError (400)
    │   ├── InvalidInputError
    │   ├── InvalidStateError
    │   └── ConfigurationError
    ├── BusinessLogicError (422)
    │   ├── SessionInProgressError
    │   ├── CapabilityRequirementError
    │   └── MaterialProcessingError
    ├── ExternalServiceError (503)
    │   ├── AudioRenderingError
    │   ├── MusicXMLParsingError
    │   └── DatabaseConnectionError
    └── AuthorizationError (403)
        └── PermissionDeniedError

Usage:
    from app.exceptions import UserNotFoundError, InvalidInputError

    # Raise with context
    raise UserNotFoundError(user_id=123)
    raise InvalidInputError("Email format invalid", field="email")

    # Custom error codes for client handling
    raise BusinessLogicError(
        message="Session already in progress",
        code="SESSION_IN_PROGRESS",
        context={"session_id": 456}
    )
"""

from typing import Any, Optional


class SoundFirstException(Exception):
    """Base exception for all Sound First application errors.

    Attributes:
        message: Human-readable error description
        code: Machine-readable error code for client handling
        status_code: HTTP status code for API responses
        context: Additional context data for logging/debugging
    """

    default_message: str = "An error occurred"
    default_code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": True,
            "status_code": self.status_code,
            "code": self.code,
            "detail": self.message,
            "context": self.context,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"


# =============================================================================
# Resource Not Found Errors (404)
# =============================================================================


class ResourceNotFoundError(SoundFirstException):
    """Base class for resource not found errors."""

    default_message = "Resource not found"
    default_code = "RESOURCE_NOT_FOUND"
    status_code = 404


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a requested user does not exist."""

    default_message = "User not found"
    default_code = "USER_NOT_FOUND"

    def __init__(self, user_id: Optional[int] = None, **kwargs: Any) -> None:
        context = kwargs.pop("context", {})
        if user_id is not None:
            context["user_id"] = user_id
        super().__init__(context=context, **kwargs)


class SessionNotFoundError(ResourceNotFoundError):
    """Raised when a requested session does not exist."""

    default_message = "Session not found"
    default_code = "SESSION_NOT_FOUND"

    def __init__(
        self,
        session_id: Optional[int] = None,
        mini_session_id: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if session_id is not None:
            context["session_id"] = session_id
        if mini_session_id is not None:
            context["mini_session_id"] = mini_session_id
        super().__init__(context=context, **kwargs)


class MaterialNotFoundError(ResourceNotFoundError):
    """Raised when a requested material does not exist."""

    default_message = "Material not found"
    default_code = "MATERIAL_NOT_FOUND"

    def __init__(self, material_id: Optional[int] = None, **kwargs: Any) -> None:
        context = kwargs.pop("context", {})
        if material_id is not None:
            context["material_id"] = material_id
        super().__init__(context=context, **kwargs)


class CapabilityNotFoundError(ResourceNotFoundError):
    """Raised when a requested capability does not exist."""

    default_message = "Capability not found"
    default_code = "CAPABILITY_NOT_FOUND"

    def __init__(
        self,
        capability_id: Optional[int] = None,
        capability_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if capability_id is not None:
            context["capability_id"] = capability_id
        if capability_name is not None:
            context["capability_name"] = capability_name
        super().__init__(context=context, **kwargs)


class InstrumentNotFoundError(ResourceNotFoundError):
    """Raised when a requested instrument does not exist."""

    default_message = "Instrument not found"
    default_code = "INSTRUMENT_NOT_FOUND"

    def __init__(
        self,
        instrument_id: Optional[int] = None,
        instrument_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if instrument_id is not None:
            context["instrument_id"] = instrument_id
        if instrument_name is not None:
            context["instrument_name"] = instrument_name
        super().__init__(context=context, **kwargs)


class StepNotFoundError(ResourceNotFoundError):
    """Raised when a requested step does not exist."""

    default_message = "Step not found"
    default_code = "STEP_NOT_FOUND"

    def __init__(self, step_id: Optional[int] = None, **kwargs: Any) -> None:
        context = kwargs.pop("context", {})
        if step_id is not None:
            context["step_id"] = step_id
        super().__init__(context=context, **kwargs)


class FocusCardNotFoundError(ResourceNotFoundError):
    """Raised when a requested focus card does not exist."""

    default_message = "Focus card not found"
    default_code = "FOCUS_CARD_NOT_FOUND"

    def __init__(self, focus_card_id: Optional[int] = None, **kwargs: Any) -> None:
        context = kwargs.pop("context", {})
        if focus_card_id is not None:
            context["focus_card_id"] = focus_card_id
        super().__init__(context=context, **kwargs)


class TeachingModuleNotFoundError(ResourceNotFoundError):
    """Raised when a requested teaching module does not exist."""

    default_message = "Teaching module not found"
    default_code = "TEACHING_MODULE_NOT_FOUND"

    def __init__(self, module_id: Optional[int] = None, **kwargs: Any) -> None:
        context = kwargs.pop("context", {})
        if module_id is not None:
            context["module_id"] = module_id
        super().__init__(context=context, **kwargs)


# =============================================================================
# Validation Errors (400)
# =============================================================================


class ValidationError(SoundFirstException):
    """Base class for validation errors."""

    default_message = "Validation failed"
    default_code = "VALIDATION_ERROR"
    status_code = 400


class InvalidInputError(ValidationError):
    """Raised when input data is invalid."""

    default_message = "Invalid input"
    default_code = "INVALID_INPUT"

    def __init__(
        self,
        message: Optional[str] = None,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if field is not None:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
        super().__init__(message=message, context=context, **kwargs)


class InvalidStateError(ValidationError):
    """Raised when an operation is attempted in an invalid state."""

    default_message = "Invalid state for operation"
    default_code = "INVALID_STATE"

    def __init__(
        self,
        message: Optional[str] = None,
        current_state: Optional[str] = None,
        expected_states: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if current_state is not None:
            context["current_state"] = current_state
        if expected_states is not None:
            context["expected_states"] = expected_states
        super().__init__(message=message, context=context, **kwargs)


class ConfigurationError(ValidationError):
    """Raised when configuration is invalid or missing."""

    default_message = "Configuration error"
    default_code = "CONFIGURATION_ERROR"


# =============================================================================
# Business Logic Errors (422)
# =============================================================================


class BusinessLogicError(SoundFirstException):
    """Base class for business logic errors."""

    default_message = "Business rule violation"
    default_code = "BUSINESS_LOGIC_ERROR"
    status_code = 422


class SessionInProgressError(BusinessLogicError):
    """Raised when attempting an operation while a session is in progress."""

    default_message = "A session is already in progress"
    default_code = "SESSION_IN_PROGRESS"

    def __init__(self, session_id: Optional[int] = None, **kwargs: Any) -> None:
        context = kwargs.pop("context", {})
        if session_id is not None:
            context["session_id"] = session_id
        super().__init__(context=context, **kwargs)


class CapabilityRequirementError(BusinessLogicError):
    """Raised when capability requirements are not met."""

    default_message = "Capability requirements not met"
    default_code = "CAPABILITY_REQUIREMENT"

    def __init__(
        self,
        required_capability: Optional[str] = None,
        user_level: Optional[float] = None,
        required_level: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if required_capability is not None:
            context["required_capability"] = required_capability
        if user_level is not None:
            context["user_level"] = user_level
        if required_level is not None:
            context["required_level"] = required_level
        super().__init__(context=context, **kwargs)


class MaterialProcessingError(BusinessLogicError):
    """Raised when material processing fails."""

    default_message = "Material processing failed"
    default_code = "MATERIAL_PROCESSING_ERROR"

    def __init__(
        self,
        message: Optional[str] = None,
        material_id: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if material_id is not None:
            context["material_id"] = material_id
        super().__init__(message=message, context=context, **kwargs)


# =============================================================================
# External Service Errors (503)
# =============================================================================


class ExternalServiceError(SoundFirstException):
    """Base class for external service errors."""

    default_message = "External service unavailable"
    default_code = "EXTERNAL_SERVICE_ERROR"
    status_code = 503


class AudioRenderingError(ExternalServiceError):
    """Raised when audio rendering fails."""

    default_message = "Audio rendering failed"
    default_code = "AUDIO_RENDERING_ERROR"

    def __init__(
        self,
        message: Optional[str] = None,
        renderer: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if renderer is not None:
            context["renderer"] = renderer
        super().__init__(message=message, context=context, **kwargs)


class MusicXMLParsingError(ExternalServiceError):
    """Raised when MusicXML parsing fails."""

    default_message = "MusicXML parsing failed"
    default_code = "MUSICXML_PARSING_ERROR"

    def __init__(
        self,
        message: Optional[str] = None,
        material_id: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if material_id is not None:
            context["material_id"] = material_id
        super().__init__(message=message, context=context, **kwargs)


class DatabaseConnectionError(ExternalServiceError):
    """Raised when database connection fails."""

    default_message = "Database connection failed"
    default_code = "DATABASE_CONNECTION_ERROR"
    status_code = 503


# =============================================================================
# Authorization Errors (403)
# =============================================================================


class AuthorizationError(SoundFirstException):
    """Base class for authorization errors."""

    default_message = "Not authorized"
    default_code = "AUTHORIZATION_ERROR"
    status_code = 403


class PermissionDeniedError(AuthorizationError):
    """Raised when user lacks permission for an operation."""

    default_message = "Permission denied"
    default_code = "PERMISSION_DENIED"

    def __init__(
        self,
        message: Optional[str] = None,
        required_permission: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context = kwargs.pop("context", {})
        if required_permission is not None:
            context["required_permission"] = required_permission
        super().__init__(message=message, context=context, **kwargs)


# =============================================================================
# Convenience Exports
# =============================================================================

__all__ = [
    # Base
    "SoundFirstException",
    # Resource Not Found (404)
    "ResourceNotFoundError",
    "UserNotFoundError",
    "SessionNotFoundError",
    "MaterialNotFoundError",
    "CapabilityNotFoundError",
    "InstrumentNotFoundError",
    "StepNotFoundError",
    "FocusCardNotFoundError",
    "TeachingModuleNotFoundError",
    # Validation (400)
    "ValidationError",
    "InvalidInputError",
    "InvalidStateError",
    "ConfigurationError",
    # Business Logic (422)
    "BusinessLogicError",
    "SessionInProgressError",
    "CapabilityRequirementError",
    "MaterialProcessingError",
    # External Service (503)
    "ExternalServiceError",
    "AudioRenderingError",
    "MusicXMLParsingError",
    "DatabaseConnectionError",
    # Authorization (403)
    "AuthorizationError",
    "PermissionDeniedError",
]
