from ...product.models import Product
from ..models import Attribute, AttributeValue


def get_product_attributes(product: Product):
    """Get product attributes filtered by product_type.

    ProductType defines which attributes can be assigned to a product and
    we have to filter out the attributes on the instance by the ones attached to the
    product_type.
    """

    return Attribute.objects.filter(
        attributeproduct__product_type_id=product.product_type_id,
    ).order_by("attributeproduct__sort_order")


def get_product_attribute_values(product: Product, attribute: Attribute):
    """Get values assigned to a product.

    Note: this doesn't filter out attributes that might have been unassigned from the
    product type.
    """
    return AttributeValue.objects.filter(
        productvalueassignment__product_id=product.pk, attribute_id=attribute.pk
    ).order_by("productvalueassignment__sort_order")
