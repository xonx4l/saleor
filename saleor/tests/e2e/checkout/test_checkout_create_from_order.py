import pytest

from ..orders.utils.draft_order import draft_order_create
from ..orders.utils.order_lines import order_lines_create
from ..shipping_zone.utils.shipping_method import create_shipping_method
from ..shipping_zone.utils.shipping_method_channel_listing import (
    create_shipping_method_channel_listing,
)
from ..shipping_zone.utils.shipping_zone import create_shipping_zone
from ..utils import prepare_product
from .utils import checkout_create_from_order


@pytest.mark.e2e
def test_checkout_create_from_order_core_0104(e2e_staff_api_client_with_permissions):
    # Before
    (warehouse_id, channel_id, channel_slug, product_variant_id) = prepare_product(
        e2e_staff_api_client_with_permissions
    )
    data = draft_order_create(
        e2e_staff_api_client_with_permissions,
        channel_id,
    )

    channel_ids = [channel_id]
    warehouse_ids = [warehouse_id]
    shipping_zone_data = create_shipping_zone(
        e2e_staff_api_client_with_permissions,
        warehouse_ids=warehouse_ids,
        channel_ids=channel_ids,
    )
    shipping_zone_id = shipping_zone_data["id"]

    shipping_method_data = create_shipping_method(
        e2e_staff_api_client_with_permissions, shipping_zone_id
    )
    shipping_method_id = shipping_method_data["id"]
    order_id = data["order"]["id"]
    order_lines = [{"variantId": product_variant_id, "quantity": 1, "price": 100}]
    order_data = order_lines_create(
        e2e_staff_api_client_with_permissions, order_id, order_lines
    )
    create_shipping_method_channel_listing(
        e2e_staff_api_client_with_permissions, shipping_method_id, channel_id
    )
    order_product_variant_id = order_data["order"]["lines"][0]["variant"]
    order_product_quantity = order_data["order"]["lines"][0]["quantity"]

    # Step 1 - Create checkout from order

    checkout_data = checkout_create_from_order(
        e2e_staff_api_client_with_permissions, order_id
    )
    checkout_id = checkout_data["checkout"]["id"]
    assert checkout_id is not None
    errors = checkout_data["errors"]
    assert errors == []
    checkout_lines = checkout_data["checkout"]["lines"]
    assert checkout_lines != []

    checkout_product_variant_id = checkout_lines[0]["variant"]["id"]
    checkout_product_quantity = checkout_lines[0]["quantity"]
    order_product_variant_id_value = order_product_variant_id["id"]

    assert checkout_product_variant_id == order_product_variant_id_value
    assert checkout_product_quantity == order_product_quantity
