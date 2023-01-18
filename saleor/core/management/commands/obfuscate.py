from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.crypto import get_random_string

from ....account import search
from ....account.models import Address, User
from ....order.models import Order
from ....order.search import prepare_order_search_vector_value

from ... import anonymize
from ...postgres import FlatConcatSearchVector


class Command(BaseCommand):
    help = "Obfuscates sensitive data e.g. customer addresses."

    def handle(self, **options):
        self.handle_addresses()
        self.handle_customers()
        self.handle_orders()

    def handle_addresses(self):
        for address in Address.objects.iterator():
            address = anonymize.obfuscate_address(address)
            address.save()

    def handle_customers(self):
        customers = User.objects.filter(is_staff=False, is_superuser=False)
        for customer in customers.iterator():
            customer = self.obfuscate_customer(customer)
            customer.save()

    def obfuscate_customer(self, customer):
        timestamp = str(timezone.now())
        email = (
            f"{hash(timestamp + get_random_string(length=5))}@example.com"
        )
        customer.email = email
        customer.first_name = anonymize.obfuscate_string(customer.first_name)
        customer.last_name = anonymize.obfuscate_string(customer.last_name)
        customer.note = anonymize.obfuscate_string(customer.note)
        customer.avatar = None

        customer.search_document = search.prepare_user_search_document_value(
            customer, attach_addresses_data=False
        )
        return customer

    def handle_orders(self):
        for order in Order.objects.iterator():
            order.user_email = anonymize.obfuscate_email(order.user_email)
            order.search_vector = FlatConcatSearchVector(
                *prepare_order_search_vector_value(order)
            )
            order.save()