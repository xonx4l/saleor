from typing import Iterable, Set, Union

from ..page.models import Page
from ..product.models import Product, ProductVariant
from .models import (
    AssignedPageAttribute,
    AssignedPageAttributeValue,
    AssignedProductAttributeValue,
    AssignedVariantAttribute,
    AssignedVariantAttributeValue,
    Attribute,
    AttributeProduct,
    AttributeValue,
)

AttributeAssignmentType = Union[AssignedVariantAttribute, AssignedPageAttribute]
T_INSTANCE = Union[Product, ProductVariant, Page]


def disassociate_attributes_from_instance(
    instance: Product,
    *attributes: Attribute,
) -> None:
    """Remove attribute assigned to an instance.

    This has to remove a FK to Attribute from Product instance and
    remove all value assignments related to that same product and attribute.
    """
    AssignedProductAttributeValue.objects.filter(
        product_id=instance.pk, value__attribute__in=attributes
    ).delete()


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


def validate_product_type_owns_attribute(
    instance: Product, *attributes: Attribute
) -> None:
    """Check given value IDs are belonging to the given attribute.

    :raise: AssertionError
    """
    allowed_attribute_ids: Set[int] = set(
        AttributeProduct.objects.filter(
            product_type_id=instance.product_type_id
        ).values_list("attribute_id", flat=True)
    )
    attribute_ids_to_check: Set[int] = set([attribute.pk for attribute in attributes])
    found_associated_ids = allowed_attribute_ids & attribute_ids_to_check
    if found_associated_ids != attribute_ids_to_check:
        raise AssertionError(
            "Some attributes are not assigned to the associated ProductType."
        )


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
    if isinstance(instance, Product):
        # Clear all assignments that don't match the values we'd like to assign
        AssignedProductAttributeValue.objects.filter(
            product_id=instance.pk, value__attribute=attribute
        ).exclude(value__in=values).delete()

        # Create new assignments
        for value in values:
            obj, _ = AssignedProductAttributeValue.objects.get_or_create(
                product=instance, value=value
            )

        sort_assigned_attribute_values(instance, attribute, values)
        return None

    assignment: AttributeAssignmentType

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

    if isinstance(instance, Page):
        attribute_page = instance.page_type.attributepage.get(attribute_id=attribute.pk)

        assignment, _ = AssignedPageAttribute.objects.get_or_create(
            page=instance, assignment=attribute_page
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
        "Page": ("pagevalueassignment", AssignedPageAttributeValue),
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
    instance: Product,
    attribute: Attribute,
    values: Iterable[AttributeValue],
) -> None:
    values_pks = [value.pk for value in values]

    values_assignment = list(
        AssignedProductAttributeValue.objects.filter(
            value__attribute_id=attribute.pk, product_id=instance.pk
        ).select_related("value")
    )

    values_assignment.sort(key=lambda e: values_pks.index(e.value.pk))
    for index, value_assignment in enumerate(values_assignment):
        value_assignment.sort_order = index

    AssignedProductAttributeValue.objects.bulk_update(values_assignment, ["sort_order"])
