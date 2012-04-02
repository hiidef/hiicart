import hashlib

from datetime import datetime
from decimal import Decimal
from hiicart.gateway.base import IPNBase, PaymentResult
from hiicart.gateway.authorizenet.settings import SETTINGS as default_settings
from hiicart.models import CART_TYPES

FORM_MODEL_TRANSLATION = {"ship_first_name": "x_ship_to_first_name",
                          "ship_last_name": "x_ship_to_last_name",
                          "ship_street1": "x_ship_to_address",
                          "ship_city": "x_ship_to_city",
                          "ship_state": "x_ship_to_state",
                          "ship_postal_code": "x_ship_to_zip",
                          "ship_country": "x_ship_to_country",
                          "ship_phone": "x_phone",
                          "bill_first_name": "x_first_name",
                          "bill_last_name": "x_last_name",
                          "bill_street1": "x_address",
                          "bill_city": "x_city",
                          "bill_state": "x_state",
                          "bill_postal_code": "x_zip",
                          "bill_country": "x_country",
                          "bill_phone": "x_phone",
                         }

BRAINTREE_STATUS = {"PAID": ["settled"],
                    "PENDING": ["authorized", "authorizing",
                                "submitted_for_settlement"],
                    "FAILED": ["failed", "gateway_rejected",
                               "processor_declined", "settlement_failed"],
                    "CANCELLED": ["voided"]}


class AuthorizeNetIPN(IPNBase):
    """Authorize.net IPN Handler."""

    def __init__(self, cart):
        super(AuthorizeNetIPN, self).__init__("authorizenet", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY", 
                                "MERCHANT_PRIVATE_KEY"])

    def confirm_ipn_data(self, data):
        """
        Confirm the data coming from Authorize.net
        """
        message = "%s%s%s%s" % (self.settings['MERCHANT_PRIVATE_KEY'],
                                self.settings['MERCHANT_ID'],
                                data['x_trans_id'],
                                data['x_amount'])
        m = hashlib.md5(message)
        return data['x_MD5_Hash'] == m.hexdigest().upper()

    def _record_payment(self, data):
        """Create a new payment record."""
        if not self.cart:
            return
        if data['x_response_code'] == '1':
            state = "PAID"
        elif data['x_response_code'] == '4':
            state = "PENDING"
        else:
            return
        payment = self.cart.payments.filter(transaction_id=data['x_trans_id'])
        if payment:
            if payment[0].state != state:
                payment[0].state = state
                payment[0].save()
                return payment[0]
        else:
            payment = self._create_payment(data['x_amount'],
                                           data['x_trans_id'], state)
            payment.save()
            return payment

    def record_form_data(self, data):
        """Save form data to display back to user if payment validation fales"""
        if not self.cart:
            return
        for model_field, form_field in FORM_MODEL_TRANSLATION.items():
            if form_field in data and data[form_field]:
                setattr(self.cart, model_field, data[form_field])
        self.cart.save()

    def accept_payment(self, data):
        """Save a new order using details from a transaction."""
        if not self.cart:
            return
        self.cart._cart_state = "SUBMITTED"
        self.cart.save()
        self._record_payment(data)
        self.cart.update_state()
