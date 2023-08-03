from typing import TYPE_CHECKING, Iterable, Set, Union

from ..page.models import Page
from ..product.models import Product, ProductVariant
from .models import (
    AssignedPageAttributeValue,
    AssignedProductAttribute,
    AssignedProductAttributeValue,
    AssignedVariantAttribute,
    AssignedVariantAttributeValue,
    Attribute,
    AttributeValue,
)

AttributeAssignmentType = Union[AssignedVariantAttribute, AssignedProductAttribute]
T_INSTANCE = Union[Product, ProductVariant, Page]

if TYPE_CHECKING:
    from .models import AttributePage, AttributeProduct, AttributeVariant


def associate_attribute_values_to_instance(
    instance: T_INSTANCE,
    attribute: Attribute,
    *values: AttributeValue,
) -> Union[None, AttributeAssignmentType]:
    """Assign given attribute values to a product or variant.

    Note: be aware this function invokes the ``set`` method on the instance's
    attribute association. Meaning any values already assigned or concurrently
    assigned will be overridden by this call.
    """
    values_ids = {value.pk for value in values}

    # Ensure the values are actually form the given attribute
    validate_attribute_owns_values(attribute, values_ids)

    # Associate the attribute and the passed values
    return _associate_attribute_to_instance(instance, attribute, *values)


def validate_attribute_owns_values(attribute: Attribute, value_ids: Set[int]) -> None:
    """Check given value IDs are belonging to the given attribute.

    :raise: AssertionError
    """
    attribute_actual_value_ids = set(attribute.values.values_list("pk", flat=True))
    found_associated_ids = attribute_actual_value_ids & value_ids
    if found_associated_ids != value_ids:
        raise AssertionError("Some values are not from the provided attribute.")


def _associate_attribute_to_instance(
    instance: T_INSTANCE,
    attribute: Attribute,
    *values: AttributeValue,
) -> Union[None, AttributeAssignmentType]:
    """Associate a given attribute to an instance.

    For a given instance assign an attribute to it and set values based on *values.

    Note: this will clean any value that already exist there.

    This function is under rebuilding while we move away from intermediate models
    for attribute relations

    See:
    https://github.com/saleor/saleor/issues/12881
    """
    if isinstance(instance, Page):
        instance.new_attributes.add(attribute)

        for i in AssignedPageAttributeValue.objects.filter(
            new_page=instance, value__attribute_id=attribute.id
        ):
            i.delete()

        # Create new assignments
        for value in values:
            obj, _ = AssignedPageAttributeValue.objects.get_or_create(
                new_page=instance, value=value
            )

        sort_assigned_attribute_values(instance, attribute, values)
        return None

    assignment: AttributeAssignmentType

    if isinstance(instance, Product):
        attribute_rel: Union[
            "AttributeProduct", "AttributeVariant", "AttributePage"
        ] = instance.product_type.attributeproduct.get(attribute_id=attribute.pk)

        assignment, _ = AssignedProductAttribute.objects.get_or_create(
            product=instance, assignment=attribute_rel
        )
        assignment.values.set(values)

        sort_assigned_attribute_values_using_assignment(instance, assignment, values)
        return assignment

    if isinstance(instance, ProductVariant):
        attribute_variant = instance.product.product_type.attributevariant.get(
            attribute_id=attribute.pk
        )

        assignment, _ = AssignedVariantAttribute.objects.get_or_create(
            variant=instance, assignment=attribute_variant
        )
        assignment.values.set(values)

        sort_assigned_attribute_values_using_assignment(instance, assignment, values)
        return assignment

    raise AssertionError(f"{instance.__class__.__name__} is unsupported")


def sort_assigned_attribute_values_using_assignment(
    instance: T_INSTANCE,
    assignment: AttributeAssignmentType,
    values: Iterable[AttributeValue],
) -> None:
    """Sort assigned attribute values based on values list order."""
    instance_to_value_assignment_mapping = {
        "ProductVariant": ("variantvalueassignment", AssignedVariantAttributeValue),
        "Product": ("productvalueassignment", AssignedProductAttributeValue),
    }
    assignment_lookup, assignment_model = instance_to_value_assignment_mapping[
        instance.__class__.__name__
    ]
    values_pks = [value.pk for value in values]

    values_assignment = list(
        getattr(assignment, assignment_lookup).select_related("value")
    )
    values_assignment.sort(key=lambda e: values_pks.index(e.value.pk))
    for index, value_assignment in enumerate(values_assignment):
        value_assignment.sort_order = index

    assignment_model.objects.bulk_update(values_assignment, ["sort_order"])


def sort_assigned_attribute_values(
    instance: Page,
    attribute: Attribute,
    values: Iterable[AttributeValue],
) -> None:
    values_pks = [value.pk for value in values]

    values_assignment = list(
        instance.attributevalues.filter(value__attribute_id=attribute.pk)
    )
    values_assignment.sort(key=lambda e: values_pks.index(e.value_id))
    for index, value_assignment in enumerate(values_assignment):
        value_assignment.sort_order = index

    AssignedPageAttributeValue.objects.bulk_update(values_assignment, ["sort_order"])


def get_page_attributes(page: Page):
    return Attribute.objects.filter(
        attributepage__page_type_id=page.page_type_id,
    ).order_by("attributepage__sort_order")


def get_page_attribute_values(page: Page, attribute: Attribute):
    return AttributeValue.objects.filter(
        pagevalueassignment__new_page_id=page.pk, attribute_id=attribute.pk
    ).order_by("pagevalueassignment__sort_order")
