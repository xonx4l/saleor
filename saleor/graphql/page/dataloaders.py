from collections import defaultdict

from ...attribute.models import AttributePage
from ...attribute.utils import get_page_attribute_values, get_page_attributes
from ...page.models import Page, PageType
from ...permission.enums import PagePermissions
from ..attribute.dataloaders import AttributesByAttributeId
from ..core.dataloaders import DataLoader
from ..utils import get_user_or_app_from_context

# from promise import Promise


class PageByIdLoader(DataLoader):
    context_key = "page_by_id"

    def batch_load(self, keys):
        pages = Page.objects.using(self.database_connection_name).in_bulk(keys)
        return [pages.get(page_id) for page_id in keys]


class PageTypeByIdLoader(DataLoader):
    context_key = "page_type_by_id"

    def batch_load(self, keys):
        page_types = PageType.objects.using(self.database_connection_name).in_bulk(keys)
        return [page_types.get(page_type_id) for page_type_id in keys]


class PagesByPageTypeIdLoader(DataLoader):
    """Loads pages by pages type ID."""

    context_key = "pages_by_pagetype"

    def batch_load(self, keys):
        pages = Page.objects.using(self.database_connection_name).filter(
            page_type_id__in=keys
        )

        pagetype_to_pages = defaultdict(list)
        for page in pages:
            pagetype_to_pages[page.page_type_id].append(page)

        return [pagetype_to_pages[key] for key in keys]


class PageAttributesByPageTypeIdLoader(DataLoader):
    """Loads page attributes by page type ID."""

    context_key = "page_attributes_by_pagetype"

    def batch_load(self, keys):
        requestor = get_user_or_app_from_context(self.context)
        if (
            requestor
            and requestor.is_active
            and requestor.has_perm(PagePermissions.MANAGE_PAGES)
        ):
            qs = AttributePage.objects.using(self.database_connection_name).all()
        else:
            qs = AttributePage.objects.using(self.database_connection_name).filter(
                attribute__visible_in_storefront=True
            )

        page_type_attribute_pairs = qs.filter(page_type_id__in=keys).values_list(
            "page_type_id", "attribute_id"
        )

        page_type_to_attributes_map = defaultdict(list)
        for page_type_id, attr_id in page_type_attribute_pairs:
            page_type_to_attributes_map[page_type_id].append(attr_id)

        def map_attributes(attributes):
            attributes_map = {attr.id: attr for attr in attributes}
            return [
                [
                    attributes_map[attr_id]
                    for attr_id in page_type_to_attributes_map[page_type_id]
                ]
                for page_type_id in keys
            ]

        return (
            AttributesByAttributeId(self.context)
            .load_many(set(attr_id for _, attr_id in page_type_attribute_pairs))
            .then(map_attributes)
        )


class AttributeValuesByPageIdLoader(DataLoader):
    context_key = "attributevalues_by_page"

    def batch_load(self, keys):
        pages = Page.objects.filter(pk__in=keys)

        assigned_page_map = defaultdict(list)
        for page in pages:
            qs = get_page_attributes(page).using(self.database_connection_name)

            for attribute in qs.iterator():
                values = get_page_attribute_values(page, attribute).using(
                    self.database_connection_name
                )

                assigned_page_map[page.id].append(
                    {
                        "attribute": attribute,
                        "values": values,
                    }
                )

        return [assigned_page_map[key] for key in keys]


class SelectedAttributesByPageIdLoader(DataLoader):
    context_key = "selectedattributes_by_page"

    def batch_load(self, page_ids):
        ret = AttributeValuesByPageIdLoader(self.context).load_many(page_ids)
        return ret
