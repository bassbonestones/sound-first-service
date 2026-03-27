"""Tests for app/schemas/error_schemas.py - Error response models."""

import pytest

from app.schemas.error_schemas import (
    ErrorResponse,
    ValidationErrorItem,
    ValidationErrorResponse,
    ERROR_RESPONSES,
)


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_create_error_response(self):
        """Test creating a basic error response."""
        response = ErrorResponse(
            status_code=404,
            detail="Resource not found",
            path="/users/999",
        )
        assert response.error is True
        assert response.status_code == 404
        assert response.detail == "Resource not found"
        assert response.path == "/users/999"

    def test_create_with_different_status(self):
        """Test with 500 status code."""
        response = ErrorResponse(
            status_code=500,
            detail="Internal server error",
            path="/api/test",
        )
        assert response.status_code == 500

    def test_json_schema_extra_example(self):
        """Test that the model has example schema."""
        schema = ErrorResponse.model_config
        assert "json_schema_extra" in schema


class TestValidationErrorItem:
    """Tests for ValidationErrorItem model."""

    def test_create_validation_error_item(self):
        """Test creating a validation error item."""
        item = ValidationErrorItem(
            field="body.email",
            message="value is not a valid email address",
            type="value_error.email",
        )
        assert item.field == "body.email"
        assert item.message == "value is not a valid email address"
        assert item.type == "value_error.email"

    def test_create_multiple_items(self):
        """Test creating multiple validation error items."""
        items = [
            ValidationErrorItem(field="name", message="required", type="missing"),
            ValidationErrorItem(field="age", message="must be positive", type="value_error"),
        ]
        assert len(items) == 2
        assert items[0].field == "name"
        assert items[1].field == "age"


class TestValidationErrorResponse:
    """Tests for ValidationErrorResponse model."""

    def test_create_validation_error_response(self):
        """Test creating a validation error response."""
        response = ValidationErrorResponse(
            errors=[
                ValidationErrorItem(
                    field="body.email",
                    message="invalid email",
                    type="value_error.email",
                )
            ],
            path="/users",
        )
        assert response.error is True
        assert response.status_code == 422
        assert response.detail == "Validation error"
        assert len(response.errors) == 1
        assert response.errors[0].field == "body.email"
        assert response.path == "/users"

    def test_multiple_validation_errors(self):
        """Test response with multiple validation errors."""
        response = ValidationErrorResponse(
            errors=[
                ValidationErrorItem(field="name", message="required", type="missing"),
                ValidationErrorItem(field="email", message="invalid", type="value_error"),
                ValidationErrorItem(field="age", message="must be > 0", type="value_error"),
            ],
            path="/api/register",
        )
        assert len(response.errors) == 3

    def test_custom_status_code(self):
        """Test with custom status code."""
        response = ValidationErrorResponse(
            status_code=400,
            detail="Custom validation error",
            errors=[],
            path="/test",
        )
        assert response.status_code == 400
        assert response.detail == "Custom validation error"


class TestErrorResponses:
    """Tests for ERROR_RESPONSES constant."""

    def test_error_responses_has_expected_codes(self):
        """Test that ERROR_RESPONSES contains expected status codes."""
        expected_codes = [400, 401, 403, 404, 409, 422, 500, 503]
        for code in expected_codes:
            assert code in ERROR_RESPONSES

    def test_error_responses_structure(self):
        """Test that each response has model and description."""
        for code, response_def in ERROR_RESPONSES.items():
            assert "model" in response_def
            assert "description" in response_def
            assert isinstance(response_def["description"], str)

    def test_404_response_uses_error_response(self):
        """Test 404 uses ErrorResponse model."""
        assert ERROR_RESPONSES[404]["model"] == ErrorResponse

    def test_422_response_uses_validation_error_response(self):
        """Test 422 uses ValidationErrorResponse model."""
        assert ERROR_RESPONSES[422]["model"] == ValidationErrorResponse

    def test_descriptions_are_descriptive(self):
        """Test that descriptions contain useful info."""
        assert "Bad Request" in ERROR_RESPONSES[400]["description"]
        assert "Unauthorized" in ERROR_RESPONSES[401]["description"]
        assert "Forbidden" in ERROR_RESPONSES[403]["description"]
        assert "Not Found" in ERROR_RESPONSES[404]["description"]
        assert "Conflict" in ERROR_RESPONSES[409]["description"]
        assert "Validation" in ERROR_RESPONSES[422]["description"]
        assert "Internal" in ERROR_RESPONSES[500]["description"]
        assert "Unavailable" in ERROR_RESPONSES[503]["description"]
