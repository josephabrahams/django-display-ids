"""Tests for models module."""

import uuid

import pytest

from django_display_ids.encoding import encode_display_id
from django_display_ids.models import DisplayIDModel, get_model_for_prefix

from .models import Invoice, Order, Product


@pytest.mark.django_db
class TestDisplayIDModel:
    """Tests for DisplayIDModel."""

    def test_display_id(self):
        invoice = Invoice.objects.create(name="Test Invoice")
        assert invoice.display_id == encode_display_id("inv", invoice.id)

    def test_display_id_none_without_uuid(self):
        """An instance whose UUID field is empty has no display ID yet."""
        assert Invoice(id=None).display_id is None

    def test_get_display_id_prefix_classmethod(self):
        """get_display_id_prefix returns correct prefix."""
        assert Invoice.get_display_id_prefix() == "inv"
        assert Product.get_display_id_prefix() == "prod"

    def test_plain_models_have_no_prefix_method(self):
        """Order doesn't extend DisplayIDModel, so it has no get_display_id_prefix."""
        assert not hasattr(Order, "get_display_id_prefix")


class TestCustomFieldNames:
    """Tests for custom field name configuration."""

    def test_display_id_uses_custom_uuid_field(self):
        """display_id encodes the model's uuid_field, not the primary key."""
        uid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        product = Product(uid=uid)
        assert product.display_id == encode_display_id("prod", uid)

    def test_display_id_uses_uuid_field_setting(self, settings):
        """Without uuid_field on the model, the UUID_FIELD setting is used.

        Pointing it at the empty slug column gives no display ID, which shows
        the setting was read.
        """
        settings.DISPLAY_IDS = {"UUID_FIELD": "slug"}
        invoice = Invoice(id=uuid.uuid4(), slug=None)
        assert invoice.display_id is None


class TestPrefixRegistry:
    """Tests for prefix collision detection."""

    @pytest.fixture(autouse=True)
    def _isolated_registry(self, monkeypatch):
        """Models defined in these tests mustn't leak into the global registry."""
        from django_display_ids import models as models_module

        monkeypatch.setattr(
            models_module, "_prefix_registry", dict(models_module._prefix_registry)
        )

    def test_get_model_for_prefix(self):
        """get_model_for_prefix returns registered model name."""
        assert get_model_for_prefix("inv") == "Invoice"
        assert get_model_for_prefix("prod") == "Product"

    def test_get_model_for_unregistered_prefix(self):
        """get_model_for_prefix returns None for unregistered prefix."""
        assert get_model_for_prefix("unknown") is None

    def test_prefix_collision_raises_error(self):
        """Defining duplicate prefix raises ValueError at class definition."""
        with pytest.raises(ValueError, match="already used"):
            # This should fail at class definition time
            class DuplicateInvoice(DisplayIDModel):
                display_id_prefix = "inv"  # Already used by Invoice

                class Meta:
                    app_label = "tests"

    def test_same_class_name_in_another_module_collides(self):
        """A different model that happens to share the class name still collides."""
        with pytest.raises(ValueError, match=r"already used by tests\.models\.Invoice"):

            class Invoice(DisplayIDModel):  # same name as tests.models.Invoice
                __module__ = "billing.models"
                display_id_prefix = "inv"

                class Meta:
                    app_label = "billing"

    def test_reregistering_same_model_is_allowed(self):
        """Re-importing a module registers the same model again without error."""
        from django_display_ids.models import _register_prefix

        _register_prefix("inv", Invoice)
        assert get_model_for_prefix("inv") == "Invoice"

    def test_abstract_models_are_registered(self):
        """Abstract models with prefixes are registered.

        This is intentional - registering abstract models ensures collision
        detection works across the inheritance hierarchy. If an abstract base
        claims a prefix, concrete subclasses that don't override it will
        inherit it, and other models cannot reuse it.
        """

        # Define an abstract model
        class AbstractModel(DisplayIDModel):
            display_id_prefix = "abstract"

            class Meta:
                abstract = True
                app_label = "tests"

        # Abstract models are registered for collision detection
        assert get_model_for_prefix("abstract") == "AbstractModel"

    @pytest.mark.parametrize("prefix", ["", "Invalid123", "waytoolongprefix123"])
    def test_invalid_prefix_fails_at_class_definition(self, prefix):
        with pytest.raises(ValueError, match="1-16 lowercase letters"):
            type(
                "BadPrefixModel",
                (DisplayIDModel,),
                {
                    "__module__": __name__,
                    "display_id_prefix": prefix,
                    "Meta": type("Meta", (), {"app_label": "tests"}),
                },
            )


@pytest.mark.django_db
class TestDisplayIDModelWithDatabase:
    """Tests requiring database access."""

    def test_display_id_after_save(self):
        """display_id is available after saving."""
        invoice = Invoice(name="Test Invoice")
        # Before save, id might be set by default
        invoice.save()
        assert invoice.display_id is not None
        assert invoice.display_id.startswith("inv_")

    def test_display_id_with_explicit_uuid(self):
        """display_id works with explicitly set UUID."""
        explicit_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        invoice = Invoice.objects.create(id=explicit_uuid, name="Test Invoice")

        expected = encode_display_id("inv", explicit_uuid)
        assert invoice.display_id == expected

    def test_display_id_survives_refresh(self):
        """display_id is consistent after refresh_from_db."""
        invoice = Invoice.objects.create(name="Test Invoice")
        original_display_id = invoice.display_id

        invoice.refresh_from_db()
        assert invoice.display_id == original_display_id
