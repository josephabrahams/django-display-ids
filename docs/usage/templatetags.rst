Templates
=========

For a ``DisplayIDModel`` instance, use its property:

.. code-block:: django

   {{ invoice.display_id }}

For any other UUID, such as a foreign key, use the ``display_id`` filter with a
prefix. It needs ``"django_display_ids"`` in ``INSTALLED_APPS``:

.. code-block:: django

   {% load display_ids %}

   <a href="/customers/{{ invoice.customer_id|display_id:"cust" }}/">Customer</a>

The value can be a ``uuid.UUID`` or a hyphenated UUID string in either case.
``None`` renders as an empty string. Anything else, or a prefix that isn't 1
to 16 lowercase letters, raises ``TemplateSyntaxError``.
