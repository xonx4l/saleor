from typing import List

from ....celeryconf import app
from ...models import AssignedProductAttributeValue

from django.db import transaction
from django.db import connection

# batch size to make sure that task is completed in 1 second
# and we don't use too much memory
BATCH_SIZE = 5000


def update_product_assignment(ids: List[int]):
    """Assign product_id to a new field on assignedproductattributevalue.

    Take the values from attribute_assignedproductattribute to product_id.
    The old field has already been deleted in Django State operations so we need
    to use raw SQL to get the value and copy the assignment from the old table.
    """

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE attribute_assignedproductattributevalue
                SET product_id = (
                    SELECT product_id
                    FROM attribute_assignedproductattribute
                    WHERE attribute_assignedproductattributevalue.assignment_id = attribute_assignedproductattribute.id
                )
                WHERE id in %s;
                """,  # noqa
                ids,
            )


@app.task
def assign_products_to_attribute_values_task():
    # Order events proceed from the newest to the oldest
    assigned_values = AssignedProductAttributeValue.objects.filter(
        product__isnull=True
    ).order_by("-pk")
    ids = list(assigned_values.values_list("pk", flat=True)[:BATCH_SIZE])

    # If we found data, queue next execution of the task
    if ids:
        update_product_assignment(ids)
        assign_products_to_attribute_values_task.delay()
