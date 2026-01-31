Template Tags
=============

Encode UUIDs as display IDs directly in Django templates.

Setup
-----

Add ``django_display_ids`` to your ``INSTALLED_APPS``:

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       "django_display_ids",
   ]

Then load the template library in your templates:

.. code-block:: django

   {% load display_ids %}

Filter: ``display_id``
----------------------

Encode a UUID as a display ID:

.. code-block:: django

   {% load display_ids %}

   {{ some_uuid|display_id:"inv" }}
   {# Output: inv_2aUyqjCzEIiEcYMKj7TZtw #}

   {# With a model's UUID field #}
   {{ invoice.id|display_id:"inv" }}

   {# Foreign key UUID #}
   {{ order.customer_id|display_id:"cust" }}

The prefix argument is required and must be 1-16 lowercase letters.

.. note::

   For models with ``DisplayIDMixin``, use the ``display_id`` property directly:

   .. code-block:: django

      {{ invoice.display_id }}

   The filter is for encoding raw UUIDs that don't come from a mixin-enabled model.

Error Handling
--------------

Errors raise ``TemplateSyntaxError``:

- Value is not a UUID
- Invalid prefix format (must be 1-16 lowercase letters)

``None`` values return an empty string (not an error).

Examples
--------

Encoding foreign key UUIDs:

.. code-block:: django

   {% load display_ids %}

   <p>Customer: {{ order.customer_id|display_id:"cust" }}</p>
   <p>Invoice: {{ payment.invoice_id|display_id:"inv" }}</p>

Building URLs with display IDs:

.. code-block:: django

   {% load display_ids %}

   <a href="/customers/{{ customer.id|display_id:"cust" }}/">
       View Customer
   </a>

Loop over UUIDs:

.. code-block:: django

   {% load display_ids %}

   {% for uuid in related_ids %}
       <li>{{ uuid|display_id:"rel" }}</li>
   {% endfor %}
