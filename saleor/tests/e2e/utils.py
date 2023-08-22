from ...account.models import Group
from ...graphql.tests.utils import get_graphql_content  # noqa: F401
from ...graphql.tests.utils import get_multipart_request_body  # noqa: F401
from .channel.utils import create_channel
from .product.utils import (
    create_category,
    create_product,
    create_product_channel_listing,
    create_product_type,
    create_product_variant,
    create_product_variant_channel_listing,
)
from .warehouse.utils import create_warehouse


def assign_permissions(api_client, permissions):
    user = api_client.user
    if user:
        group = Group.objects.create(
            name="admins",
            restricted_access_to_channels=False,
        )
        group.permissions.add(*permissions)
        user.groups.add(group)
    else:
        app = api_client.app
        if app:
            app.permissions.add(*permissions)


def prepare_product(e2e_staff_api_client_with_permissions):
    warehouse_data = create_warehouse(e2e_staff_api_client_with_permissions)
    warehouse_id = warehouse_data["id"]
    channel_slug = "test"
    warehouse_ids = [warehouse_id]
    channel_data = create_channel(
        e2e_staff_api_client_with_permissions,
        slug=channel_slug,
        warehouse_ids=warehouse_ids,
    )
    channel_id = channel_data["id"]

    product_type_data = create_product_type(
        e2e_staff_api_client_with_permissions,
    )
    product_type_id = product_type_data["id"]

    category_data = create_category(e2e_staff_api_client_with_permissions)
    category_id = category_data["id"]

    product_data = create_product(
        e2e_staff_api_client_with_permissions, product_type_id, category_id
    )
    product_id = product_data["id"]

    create_product_channel_listing(
        e2e_staff_api_client_with_permissions, product_id, channel_id
    )

    stocks = [
        {
            "warehouse": warehouse_id,
            "quantity": 5,
        }
    ]
    product_variant_data = create_product_variant(
        e2e_staff_api_client_with_permissions,
        product_id,
        stocks=stocks,
    )
    product_variant_id = product_variant_data["id"]

    create_product_variant_channel_listing(
        e2e_staff_api_client_with_permissions,
        product_variant_id,
        channel_id,
    )
    return (
        warehouse_id,
        channel_id,
        channel_slug,
        product_variant_id,
    )
