import base64
import httplib2
import xml.etree.cElementTree as ET
from decimal import Decimal

from django.template import Context, loader

from hiicart.gateway.base import PaymentGatewayBase, SubmitResult, CancelResult
from hiicart.gateway.google.settings import SETTINGS as default_settings
from hiicart.lib.unicodeconverter import convertToUTF8


class GoogleGateway(PaymentGatewayBase):
    """Payment Gateway for Google Checkout."""

    def __init__(self, cart):
        super(GoogleGateway, self).__init__("google", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY"])

    @property
    def _cart_url(self):
        """URL to post the Checkout cart to."""
        if self.settings["LIVE"]:
            base = "https://checkout.google.com/api/checkout/v2/merchantCheckout/Merchant/%s"
        else:
            base = "https://sandbox.google.com/checkout/api/checkout/v2/merchantCheckout/Merchant/%s"
        return base % self.settings["MERCHANT_ID"]

    @property
    def _order_url(self):
        """URL for the Order Processing API."""
        if self.settings["LIVE"]:
            base = "https://checkout.google.com/api/checkout/v2/request/Merchant/%s"
        else:
            base = "https://sandbox.google.com/checkout/api/checkout/v2/request/Merchant/%s"
        return base % self.settings["MERCHANT_ID"]

    def _is_valid(self):
        """Return True if gateway is valid."""
        # TODO: Query Google to validate credentials
        return True

    def _send_xml(self, url, xml):
        """Send a command to the Checkout Order Processing API."""
        http = httplib2.Http()
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Authorization": "Basic %s" % self.get_basic_auth()}
        return http.request(url, "POST", xml, headers=headers)

    def cancel_items(self, payment, items=None, reason=None):
        self._update_with_cart_settings({'request': None})
        transaction_id = payment.transaction_id
        template = loader.get_template("gateway/google/cancel-items.xml")
        ctx = Context({"transaction_id": transaction_id,
                       "reason": reason,
                       "comment": None,
                       "items": items})
        cancel_xml = convertToUTF8(template.render(ctx))
        response, content = self._send_xml(self._order_url, cancel_xml)
        # make sure the line item is not acitive
        item = self.cart.recurring_lineitems[0]
        item.is_active = False
        item.save()
        self.cart.update_state()
        return CancelResult(None)

    def cancel_recurring(self):
        return self.cancel_items(self.cart.payments.filter(state='PAID').order_by('-created')[0])

    def charge_recurring(self, grace_period=None):
        """HiiCart doesn't currently support manually charging subscriptions with Google Checkout"""
        pass

    def get_basic_auth(self):
        """Get the base64 encoded string for Basic auth"""
        return base64.b64encode("%s:%s" % (self.settings["MERCHANT_ID"],
                                           self.settings["MERCHANT_KEY"]))

    def sanitize_clone(self):
        """Remove any gateway-specific changes to a cloned cart."""
        pass

    def submit(self, collect_address=False, cart_settings_kwargs=None):
        """Submit a cart to Google Checkout.

        Google Checkout's submission process is:
          * Construct an xml representation of the cart
          * Post the xml to Checkout, using HTTP Basic Auth
          * Checkout returns a url to redirect the user to"""
        # Construct cart xml
        self._update_with_cart_settings(cart_settings_kwargs)
        template = loader.get_template("gateway/google/cart.xml")
        ctx = Context({"cart": self.cart,
                       "continue_shopping_url": self.settings.get("SHOPPING_URL", None),
                       "edit_cart_url": self.settings.get("EDIT_URL", None),
                       "currency": self.settings["CURRENCY"]})
        cart_xml = convertToUTF8(template.render(ctx))
        response, content = self._send_xml(self._cart_url, cart_xml)
        xml = ET.XML(content)
        url = xml.find("{http://checkout.google.com/schema/2}redirect-url").text
        return SubmitResult("url", url)

    def refund_payment(self, payment, reason=None):
        """
        Refund the full amount of this payment
        """
        self.refund(payment, payment.amount, reason)
        payment.state = 'REFUND'
        payment.save()

    def refund(self, payment, amount, reason=None):
        """Refund a payment."""
        self._update_with_cart_settings({'request': None})

        template = loader.get_template("gateway/google/refund.xml")
        ctx = Context({"transaction_id": payment.transaction_id,
                       "reason": reason,
                       "comment": None,
                       "currency": self.settings["CURRENCY"],
                       "amount": Decimal(amount).quantize(Decimal('.01'))})
        refund_xml = convertToUTF8(template.render(ctx))
        response, content = self._send_xml(self._order_url, refund_xml)
        return SubmitResult(None)
