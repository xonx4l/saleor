from django.db import models

from ...core.models import SortableModel
from ...page.models import Page, PageType
from .base import AssociatedAttributeManager


class AssignedPageAttributeValue(SortableModel):
    value = models.ForeignKey(
        "AttributeValue",
        on_delete=models.CASCADE,
        related_name="pagevalueassignment",
    )
    # assignment = models.ForeignKey(
    #     "AssignedPageAttribute",
    #     on_delete=models.CASCADE,
    #     related_name="pagevalueassignment",
    # )
    new_page = models.ForeignKey(
        Page,
        null=True,
        related_name="attributevalues",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = (("value", "new_page"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.new_page.attributevalues.all()  # type: ignore


# class AssignedPageAttribute(BaseAssignedAttribute):
#     """Associate a page type attribute and selected values to a given page."""
#
#     page = models.ForeignKey(
#     Page, related_name="attributes", on_delete=models.CASCADE
#     )
#     assignment = models.ForeignKey(
#         "AttributePage", on_delete=models.CASCADE, related_name="pageassignments"
#     )
#     values = models.ManyToManyField(
#         "AttributeValue",
#         blank=True,
#         related_name="pageassignments",
#         through=AssignedPageAttributeValue,
#     )
#
#     class Meta:
#         unique_together = (("page", "assignment"),)
#


class AttributePage(SortableModel):
    attribute = models.ForeignKey(
        "Attribute", related_name="attributepage", on_delete=models.CASCADE
    )
    page_type = models.ForeignKey(
        PageType, related_name="attributepage", on_delete=models.CASCADE
    )

    objects = AssociatedAttributeManager()

    class Meta:
        unique_together = (("attribute", "page_type"),)
        ordering = ("sort_order", "pk")

    def get_ordering_queryset(self):
        return self.page_type.attributepage.all()
