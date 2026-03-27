"""Tests for app/exceptions.py - Custom exception hierarchy."""

import pytest

from app.exceptions import (
    # Base
    SoundFirstException,
    # Resource Not Found (404)
    ResourceNotFoundError,
    UserNotFoundError,
    SessionNotFoundError,
    MaterialNotFoundError,
    CapabilityNotFoundError,
    InstrumentNotFoundError,
    StepNotFoundError,
    FocusCardNotFoundError,
    TeachingModuleNotFoundError,
    # Validation (400)
    ValidationError,
    InvalidInputError,
    InvalidStateError,
    ConfigurationError,
    # Business Logic (422)
    BusinessLogicError,
    SessionInProgressError,
    CapabilityRequirementError,
    MaterialProcessingError,
    # External Service (503)
    ExternalServiceError,
    AudioRenderingError,
    MusicXMLParsingError,
    DatabaseConnectionError,
    # Authorization (403)
    AuthorizationError,
    PermissionDeniedError,
)


# =============================================================================
# Base Exception Tests
# =============================================================================


class TestSoundFirstException:
    """Tests for the base SoundFirstException class."""

    def test_default_values(self):
        """Test exception with no arguments uses defaults."""
        exc = SoundFirstException()
        assert exc.message == "An error occurred"
        assert exc.code == "INTERNAL_ERROR"
        assert exc.status_code == 500
        assert exc.context == {}

    def test_custom_message(self):
        """Test exception with custom message."""
        exc = SoundFirstException(message="Custom error message")
        assert exc.message == "Custom error message"
        assert str(exc) == "Custom error message"

    def test_custom_code(self):
        """Test exception with custom code."""
        exc = SoundFirstException(code="CUSTOM_CODE")
        assert exc.code == "CUSTOM_CODE"

    def test_custom_context(self):
        """Test exception with context data."""
        context = {"key": "value", "count": 42}
        exc = SoundFirstException(context=context)
        assert exc.context == {"key": "value", "count": 42}

    def test_to_dict(self):
        """Test to_dict() method produces correct structure."""
        exc = SoundFirstException(
            message="Test error",
            code="TEST_CODE",
            context={"test_id": 123},
        )
        result = exc.to_dict()
        assert result == {
            "error": True,
            "status_code": 500,
            "code": "TEST_CODE",
            "detail": "Test error",
            "context": {"test_id": 123},
        }

    def test_repr(self):
        """Test __repr__ method."""
        exc = SoundFirstException(message="Test", code="TEST")
        assert repr(exc) == "SoundFirstException(message='Test', code='TEST')"


# =============================================================================
# Resource Not Found Tests (404)
# =============================================================================


class TestResourceNotFoundError:
    """Tests for ResourceNotFoundError and subclasses."""

    def test_default_values(self):
        """Test base ResourceNotFoundError defaults."""
        exc = ResourceNotFoundError()
        assert exc.message == "Resource not found"
        assert exc.code == "RESOURCE_NOT_FOUND"
        assert exc.status_code == 404


class TestUserNotFoundError:
    """Tests for UserNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = UserNotFoundError()
        assert exc.message == "User not found"
        assert exc.code == "USER_NOT_FOUND"
        assert exc.status_code == 404
        assert exc.context == {}

    def test_with_user_id(self):
        """Test with user_id in context."""
        exc = UserNotFoundError(user_id=123)
        assert exc.context == {"user_id": 123}

    def test_with_custom_message(self):
        """Test with custom message."""
        exc = UserNotFoundError(user_id=456, message="User 456 does not exist")
        assert exc.message == "User 456 does not exist"
        assert exc.context == {"user_id": 456}


class TestSessionNotFoundError:
    """Tests for SessionNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = SessionNotFoundError()
        assert exc.message == "Session not found"
        assert exc.code == "SESSION_NOT_FOUND"
        assert exc.status_code == 404

    def test_with_session_id(self):
        """Test with session_id in context."""
        exc = SessionNotFoundError(session_id=100)
        assert exc.context == {"session_id": 100}

    def test_with_mini_session_id(self):
        """Test with mini_session_id in context."""
        exc = SessionNotFoundError(mini_session_id=50)
        assert exc.context == {"mini_session_id": 50}

    def test_with_both_ids(self):
        """Test with both session_id and mini_session_id."""
        exc = SessionNotFoundError(session_id=100, mini_session_id=50)
        assert exc.context == {"session_id": 100, "mini_session_id": 50}


class TestMaterialNotFoundError:
    """Tests for MaterialNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = MaterialNotFoundError()
        assert exc.message == "Material not found"
        assert exc.code == "MATERIAL_NOT_FOUND"

    def test_with_material_id(self):
        """Test with material_id in context."""
        exc = MaterialNotFoundError(material_id=789)
        assert exc.context == {"material_id": 789}


class TestCapabilityNotFoundError:
    """Tests for CapabilityNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = CapabilityNotFoundError()
        assert exc.message == "Capability not found"
        assert exc.code == "CAPABILITY_NOT_FOUND"

    def test_with_capability_id(self):
        """Test with capability_id in context."""
        exc = CapabilityNotFoundError(capability_id=42)
        assert exc.context == {"capability_id": 42}

    def test_with_capability_name(self):
        """Test with capability_name in context."""
        exc = CapabilityNotFoundError(capability_name="reading_treble_clef")
        assert exc.context == {"capability_name": "reading_treble_clef"}

    def test_with_both_id_and_name(self):
        """Test with both id and name."""
        exc = CapabilityNotFoundError(capability_id=42, capability_name="test")
        assert exc.context == {"capability_id": 42, "capability_name": "test"}


class TestInstrumentNotFoundError:
    """Tests for InstrumentNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = InstrumentNotFoundError()
        assert exc.message == "Instrument not found"
        assert exc.code == "INSTRUMENT_NOT_FOUND"

    def test_with_instrument_id(self):
        """Test with instrument_id in context."""
        exc = InstrumentNotFoundError(instrument_id=5)
        assert exc.context == {"instrument_id": 5}

    def test_with_instrument_name(self):
        """Test with instrument_name in context."""
        exc = InstrumentNotFoundError(instrument_name="violin")
        assert exc.context == {"instrument_name": "violin"}

    def test_with_both_id_and_name(self):
        """Test with both id and name."""
        exc = InstrumentNotFoundError(instrument_id=5, instrument_name="violin")
        assert exc.context == {"instrument_id": 5, "instrument_name": "violin"}


class TestStepNotFoundError:
    """Tests for StepNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = StepNotFoundError()
        assert exc.message == "Step not found"
        assert exc.code == "STEP_NOT_FOUND"

    def test_with_step_id(self):
        """Test with step_id in context."""
        exc = StepNotFoundError(step_id=10)
        assert exc.context == {"step_id": 10}


class TestFocusCardNotFoundError:
    """Tests for FocusCardNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = FocusCardNotFoundError()
        assert exc.message == "Focus card not found"
        assert exc.code == "FOCUS_CARD_NOT_FOUND"

    def test_with_focus_card_id(self):
        """Test with focus_card_id in context."""
        exc = FocusCardNotFoundError(focus_card_id=25)
        assert exc.context == {"focus_card_id": 25}


class TestTeachingModuleNotFoundError:
    """Tests for TeachingModuleNotFoundError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = TeachingModuleNotFoundError()
        assert exc.message == "Teaching module not found"
        assert exc.code == "TEACHING_MODULE_NOT_FOUND"

    def test_with_module_id(self):
        """Test with module_id in context."""
        exc = TeachingModuleNotFoundError(module_id=15)
        assert exc.context == {"module_id": 15}


# =============================================================================
# Validation Error Tests (400)
# =============================================================================


class TestValidationError:
    """Tests for ValidationError base class."""

    def test_default_values(self):
        """Test default message and code."""
        exc = ValidationError()
        assert exc.message == "Validation failed"
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == 400


class TestInvalidInputError:
    """Tests for InvalidInputError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = InvalidInputError()
        assert exc.message == "Invalid input"
        assert exc.code == "INVALID_INPUT"
        assert exc.status_code == 400

    def test_with_message(self):
        """Test with custom message."""
        exc = InvalidInputError(message="Email format invalid")
        assert exc.message == "Email format invalid"

    def test_with_field(self):
        """Test with field in context."""
        exc = InvalidInputError(field="email")
        assert exc.context == {"field": "email"}

    def test_with_value(self):
        """Test with value in context (converted to string)."""
        exc = InvalidInputError(value=12345)
        assert exc.context == {"value": "12345"}

    def test_with_all_params(self):
        """Test with message, field, and value."""
        exc = InvalidInputError(
            message="Invalid email format",
            field="email",
            value="not-an-email",
        )
        assert exc.message == "Invalid email format"
        assert exc.context == {"field": "email", "value": "not-an-email"}


class TestInvalidStateError:
    """Tests for InvalidStateError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = InvalidStateError()
        assert exc.message == "Invalid state for operation"
        assert exc.code == "INVALID_STATE"

    def test_with_current_state(self):
        """Test with current_state in context."""
        exc = InvalidStateError(current_state="pending")
        assert exc.context == {"current_state": "pending"}

    def test_with_expected_states(self):
        """Test with expected_states in context."""
        exc = InvalidStateError(expected_states=["active", "paused"])
        assert exc.context == {"expected_states": ["active", "paused"]}

    def test_with_all_params(self):
        """Test with message and state info."""
        exc = InvalidStateError(
            message="Cannot complete session in pending state",
            current_state="pending",
            expected_states=["active"],
        )
        assert exc.message == "Cannot complete session in pending state"
        assert exc.context == {
            "current_state": "pending",
            "expected_states": ["active"],
        }


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = ConfigurationError()
        assert exc.message == "Configuration error"
        assert exc.code == "CONFIGURATION_ERROR"
        assert exc.status_code == 400

    def test_with_custom_message(self):
        """Test with custom message."""
        exc = ConfigurationError(message="Missing API key")
        assert exc.message == "Missing API key"


# =============================================================================
# Business Logic Error Tests (422)
# =============================================================================


class TestBusinessLogicError:
    """Tests for BusinessLogicError base class."""

    def test_default_values(self):
        """Test default message and code."""
        exc = BusinessLogicError()
        assert exc.message == "Business rule violation"
        assert exc.code == "BUSINESS_LOGIC_ERROR"
        assert exc.status_code == 422


class TestSessionInProgressError:
    """Tests for SessionInProgressError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = SessionInProgressError()
        assert exc.message == "A session is already in progress"
        assert exc.code == "SESSION_IN_PROGRESS"
        assert exc.status_code == 422

    def test_with_session_id(self):
        """Test with session_id in context."""
        exc = SessionInProgressError(session_id=999)
        assert exc.context == {"session_id": 999}


class TestCapabilityRequirementError:
    """Tests for CapabilityRequirementError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = CapabilityRequirementError()
        assert exc.message == "Capability requirements not met"
        assert exc.code == "CAPABILITY_REQUIREMENT"

    def test_with_required_capability(self):
        """Test with required_capability in context."""
        exc = CapabilityRequirementError(required_capability="advanced_rhythm")
        assert exc.context == {"required_capability": "advanced_rhythm"}

    def test_with_levels(self):
        """Test with user_level and required_level."""
        exc = CapabilityRequirementError(user_level=0.3, required_level=0.5)
        assert exc.context == {"user_level": 0.3, "required_level": 0.5}

    def test_with_all_params(self):
        """Test with all parameters."""
        exc = CapabilityRequirementError(
            required_capability="sight_reading",
            user_level=0.2,
            required_level=0.8,
        )
        assert exc.context == {
            "required_capability": "sight_reading",
            "user_level": 0.2,
            "required_level": 0.8,
        }


class TestMaterialProcessingError:
    """Tests for MaterialProcessingError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = MaterialProcessingError()
        assert exc.message == "Material processing failed"
        assert exc.code == "MATERIAL_PROCESSING_ERROR"

    def test_with_material_id(self):
        """Test with material_id in context."""
        exc = MaterialProcessingError(material_id=555)
        assert exc.context == {"material_id": 555}

    def test_with_message_and_id(self):
        """Test with custom message and material_id."""
        exc = MaterialProcessingError(
            message="Failed to parse MusicXML",
            material_id=555,
        )
        assert exc.message == "Failed to parse MusicXML"
        assert exc.context == {"material_id": 555}


# =============================================================================
# External Service Error Tests (503)
# =============================================================================


class TestExternalServiceError:
    """Tests for ExternalServiceError base class."""

    def test_default_values(self):
        """Test default message and code."""
        exc = ExternalServiceError()
        assert exc.message == "External service unavailable"
        assert exc.code == "EXTERNAL_SERVICE_ERROR"
        assert exc.status_code == 503


class TestAudioRenderingError:
    """Tests for AudioRenderingError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = AudioRenderingError()
        assert exc.message == "Audio rendering failed"
        assert exc.code == "AUDIO_RENDERING_ERROR"
        assert exc.status_code == 503

    def test_with_renderer(self):
        """Test with renderer in context."""
        exc = AudioRenderingError(renderer="fluidsynth")
        assert exc.context == {"renderer": "fluidsynth"}

    def test_with_message_and_renderer(self):
        """Test with custom message and renderer."""
        exc = AudioRenderingError(
            message="Soundfont file not found",
            renderer="timidity",
        )
        assert exc.message == "Soundfont file not found"
        assert exc.context == {"renderer": "timidity"}


class TestMusicXMLParsingError:
    """Tests for MusicXMLParsingError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = MusicXMLParsingError()
        assert exc.message == "MusicXML parsing failed"
        assert exc.code == "MUSICXML_PARSING_ERROR"

    def test_with_material_id(self):
        """Test with material_id in context."""
        exc = MusicXMLParsingError(material_id=123)
        assert exc.context == {"material_id": 123}

    def test_with_message_and_id(self):
        """Test with custom message and material_id."""
        exc = MusicXMLParsingError(
            message="Invalid XML structure",
            material_id=456,
        )
        assert exc.message == "Invalid XML structure"
        assert exc.context == {"material_id": 456}


class TestDatabaseConnectionError:
    """Tests for DatabaseConnectionError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = DatabaseConnectionError()
        assert exc.message == "Database connection failed"
        assert exc.code == "DATABASE_CONNECTION_ERROR"
        assert exc.status_code == 503


# =============================================================================
# Authorization Error Tests (403)
# =============================================================================


class TestAuthorizationError:
    """Tests for AuthorizationError base class."""

    def test_default_values(self):
        """Test default message and code."""
        exc = AuthorizationError()
        assert exc.message == "Not authorized"
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == 403


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError."""

    def test_default_values(self):
        """Test default message and code."""
        exc = PermissionDeniedError()
        assert exc.message == "Permission denied"
        assert exc.code == "PERMISSION_DENIED"
        assert exc.status_code == 403

    def test_with_required_permission(self):
        """Test with required_permission in context."""
        exc = PermissionDeniedError(required_permission="admin")
        assert exc.context == {"required_permission": "admin"}

    def test_with_message_and_permission(self):
        """Test with custom message and permission."""
        exc = PermissionDeniedError(
            message="Admin access required for this operation",
            required_permission="admin:write",
        )
        assert exc.message == "Admin access required for this operation"
        assert exc.context == {"required_permission": "admin:write"}


# =============================================================================
# Integration Tests
# =============================================================================


class TestExceptionInheritance:
    """Tests for exception inheritance hierarchy."""

    def test_resource_not_found_is_sound_first_exception(self):
        """Test that ResourceNotFoundError inherits from SoundFirstException."""
        exc = ResourceNotFoundError()
        assert isinstance(exc, SoundFirstException)

    def test_user_not_found_is_resource_not_found(self):
        """Test that UserNotFoundError inherits from ResourceNotFoundError."""
        exc = UserNotFoundError()
        assert isinstance(exc, ResourceNotFoundError)
        assert isinstance(exc, SoundFirstException)

    def test_validation_error_is_sound_first_exception(self):
        """Test that ValidationError inherits from SoundFirstException."""
        exc = ValidationError()
        assert isinstance(exc, SoundFirstException)

    def test_business_logic_error_is_sound_first_exception(self):
        """Test that BusinessLogicError inherits from SoundFirstException."""
        exc = BusinessLogicError()
        assert isinstance(exc, SoundFirstException)

    def test_external_service_error_is_sound_first_exception(self):
        """Test that ExternalServiceError inherits from SoundFirstException."""
        exc = ExternalServiceError()
        assert isinstance(exc, SoundFirstException)

    def test_authorization_error_is_sound_first_exception(self):
        """Test that AuthorizationError inherits from SoundFirstException."""
        exc = AuthorizationError()
        assert isinstance(exc, SoundFirstException)


class TestExceptionRaising:
    """Tests for raising and catching exceptions."""

    def test_raise_user_not_found(self):
        """Test raising and catching UserNotFoundError."""
        with pytest.raises(UserNotFoundError) as exc_info:
            raise UserNotFoundError(user_id=123)
        assert exc_info.value.context["user_id"] == 123

    def test_raise_invalid_input(self):
        """Test raising and catching InvalidInputError."""
        with pytest.raises(InvalidInputError) as exc_info:
            raise InvalidInputError(message="Bad email", field="email")
        assert exc_info.value.message == "Bad email"
        assert exc_info.value.context["field"] == "email"

    def test_catch_as_parent_class(self):
        """Test catching a specific error as its parent class."""
        with pytest.raises(ResourceNotFoundError):
            raise MaterialNotFoundError(material_id=456)

    def test_catch_as_base_class(self):
        """Test catching any error as SoundFirstException."""
        with pytest.raises(SoundFirstException):
            raise PermissionDeniedError(required_permission="admin")
