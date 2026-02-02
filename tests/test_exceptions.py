"""Tests for exceptions module."""

import pytest

from django_display_ids.exceptions import (
    AmbiguousIdentifierError,
    DisplayIDLookupError,
    InvalidIdentifierError,
    MissingPrefixError,
    ObjectNotFoundError,
    UnknownPrefixError,
)


class TestDisplayIDLookupError:
    """Tests for base DisplayIDLookupError."""

    def test_is_exception(self):
        """DisplayIDLookupError is an Exception."""
        assert issubclass(DisplayIDLookupError, Exception)

    def test_can_be_raised(self):
        """DisplayIDLookupError can be raised and caught."""
        with pytest.raises(DisplayIDLookupError):
            raise DisplayIDLookupError("test error")


class TestInvalidIdentifierError:
    """Tests for InvalidIdentifierError."""

    def test_inherits_lookup_error(self):
        """InvalidIdentifierError inherits from DisplayIDLookupError."""
        assert issubclass(InvalidIdentifierError, DisplayIDLookupError)

    def test_attributes(self):
        """InvalidIdentifierError stores value and message."""
        error = InvalidIdentifierError("test-value", "custom message")
        assert error.value == "test-value"
        assert error.message == "custom message"
        assert str(error) == "custom message"

    def test_default_message(self):
        """InvalidIdentifierError has default message."""
        error = InvalidIdentifierError("test-value")
        assert error.value == "test-value"
        assert "Invalid identifier" in str(error)
        assert "test-value" in str(error)


class TestUnknownPrefixError:
    """Tests for UnknownPrefixError."""

    def test_inherits_lookup_error(self):
        """UnknownPrefixError inherits from DisplayIDLookupError."""
        assert issubclass(UnknownPrefixError, DisplayIDLookupError)

    def test_attributes(self):
        """UnknownPrefixError stores all attributes."""
        error = UnknownPrefixError("inv_abc123", actual="inv", expected="prod")
        assert error.value == "inv_abc123"
        assert error.actual == "inv"
        assert error.expected == "prod"

    def test_message_with_expected(self):
        """Message includes expected prefix when provided."""
        error = UnknownPrefixError("inv_abc123", actual="inv", expected="prod")
        message = str(error)
        assert "inv" in message
        assert "prod" in message
        assert "expected" in message.lower()

    def test_message_without_expected(self):
        """Message works without expected prefix."""
        error = UnknownPrefixError("inv_abc123", actual="inv")
        message = str(error)
        assert "inv" in message
        assert "Unknown prefix" in message


class TestMissingPrefixError:
    """Tests for MissingPrefixError."""

    def test_inherits_lookup_error(self):
        """MissingPrefixError inherits from DisplayIDLookupError."""
        assert issubclass(MissingPrefixError, DisplayIDLookupError)

    def test_with_model_name(self):
        """Message includes model name when provided."""
        error = MissingPrefixError(model_name="Invoice")
        assert error.model_name == "Invoice"
        assert "Invoice" in str(error)
        assert "display_id_prefix" in str(error)

    def test_without_model_name(self):
        """Message works without model name."""
        error = MissingPrefixError()
        assert error.model_name is None
        assert "no prefix configured" in str(error)


class TestObjectNotFoundError:
    """Tests for ObjectNotFoundError."""

    def test_inherits_lookup_error(self):
        """ObjectNotFoundError inherits from DisplayIDLookupError."""
        assert issubclass(ObjectNotFoundError, DisplayIDLookupError)

    def test_attributes(self):
        """ObjectNotFoundError stores all attributes."""
        error = ObjectNotFoundError("inv_abc123", model_name="Invoice")
        assert error.value == "inv_abc123"
        assert error.model_name == "Invoice"

    def test_message_with_model(self):
        """Message includes model name when provided."""
        error = ObjectNotFoundError("inv_abc123", model_name="Invoice")
        message = str(error)
        assert "Invoice" in message
        assert "inv_abc123" in message
        assert "not found" in message.lower()

    def test_message_without_model(self):
        """Message works without model name."""
        error = ObjectNotFoundError("inv_abc123")
        message = str(error)
        assert "inv_abc123" in message
        assert "not found" in message.lower()


class TestAmbiguousIdentifierError:
    """Tests for AmbiguousIdentifierError."""

    def test_inherits_lookup_error(self):
        """AmbiguousIdentifierError inherits from DisplayIDLookupError."""
        assert issubclass(AmbiguousIdentifierError, DisplayIDLookupError)

    def test_attributes(self):
        """AmbiguousIdentifierError stores all attributes."""
        error = AmbiguousIdentifierError("my-slug", count=3)
        assert error.value == "my-slug"
        assert error.count == 3

    def test_message(self):
        """Message includes value and count."""
        error = AmbiguousIdentifierError("my-slug", count=3)
        message = str(error)
        assert "my-slug" in message
        assert "3" in message
        assert "Ambiguous" in message


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_all_inherit_from_lookup_error(self):
        """All custom exceptions inherit from DisplayIDLookupError."""
        exceptions = [
            InvalidIdentifierError,
            UnknownPrefixError,
            MissingPrefixError,
            ObjectNotFoundError,
            AmbiguousIdentifierError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, DisplayIDLookupError)

    def test_catch_all_with_lookup_error(self):
        """All exceptions can be caught with DisplayIDLookupError."""
        exceptions = [
            InvalidIdentifierError("test"),
            UnknownPrefixError("test", actual="a"),
            MissingPrefixError(),
            ObjectNotFoundError("test"),
            AmbiguousIdentifierError("test", count=2),
        ]
        for exc in exceptions:
            with pytest.raises(DisplayIDLookupError):
                raise exc
