import pytest

from ..product.utils.prepare_product import prepare_product
from ..shipping_zone.utils.shipping_method import create_shipping_method
from ..shipping_zone.utils.shipping_method_channel_listing import (
    create_shipping_method_channel_listing,
)
from ..shipping_zone.utils.shipping_zone import create_shipping_zone
from .utils import (
    checkout_create,
    checkout_delivery_method_update,
    raw_checkout_complete,
)


@pytest.mark.e2e
def test_should_be_able_to_create_order_with_no_payment_CORE_0111(
    e2e_staff_api_client_with_permissions,
):
    # Before
    (warehouse_id, channel_id, channel_slug, product_variant_id) = prepare_product(
        e2e_staff_api_client_with_permissions
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
    create_shipping_method_channel_listing(
        e2e_staff_api_client_with_permissions, shipping_method_id, channel_id
    )

    # Step 1 - Create checkout.
    lines = [
        {"variantId": product_variant_id, "quantity": 1},
    ]
    checkout_data = checkout_create(
        e2e_staff_api_client_with_permissions,
        lines,
        channel_slug,
        email="testEmail@example.com",
        set_default_billing_address=True,
        set_default_shipping_address=True,
    )
    checkout_id = checkout_data["id"]

    assert checkout_data["isShippingRequired"] is True
    assert checkout_data["deliveryMethod"] is None
    assert checkout_data["shippingMethod"] is None
    shipping_method_id = checkout_data["shippingMethods"][0]["id"]

    # Step 2 - Set shipping address and DeliveryMethod for checkout
    checkout_data = checkout_delivery_method_update(
        e2e_staff_api_client_with_permissions,
        checkout_id,
        shipping_method_id,
    )
    assert checkout_data["deliveryMethod"]["id"] == shipping_method_id

    # Step 3 - Checkout complete results in the order creation
    raw_checkout_complete(e2e_staff_api_client_with_permissions, checkout_id)
    # order_data = data["order"]
    # assert order_data["id"] is not None
    # assert order_data["isShippingRequired"] is True
    # assert order_data["paymentStatus"] == "NOT_CHARGED"
    # assert order_data["status"] == "UNCONFIRMED"
    # assert order_data["isPaid"] is False

    # errors = data["errors"]
    # assert errors == []
