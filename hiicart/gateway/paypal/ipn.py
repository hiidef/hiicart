import urllib2
from django.utils.safestring import mark_safe
from hiicart.gateway.base import IPNBase
from hiicart.gateway.paypal.settings import SETTINGS as default_settings


POST_URL = "https://www.paypal.com/cgi-bin/webscr"
POST_TEST_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr"


def update_billing_info(cart, data):
    """Update a cart's billing info given the IPN data `data`."""
    # Consider any already in HiiCart correct
    cart.bill_email = cart.bill_email or data.get("payer_email", "")
    cart.ship_email = cart.ship_email or cart.bill_email
    cart.bill_first_name = cart.bill_first_name or data.get("first_name", "")
    cart.ship_first_name = cart.ship_first_name or cart.bill_first_name
    cart.bill_last_name = cart.bill_last_name or data.get("last_name", "")
    cart.ship_last_name = cart.ship_last_name or cart.bill_last_name
    street = data.get("address_street", "")
    cart.bill_street1 = cart.bill_street1 or street.split("\r\n")[0]
    cart.ship_street1 = cart.ship_street1 or street.split("\r\n")[0]
    if street.count("\r\n") > 0:
        cart.bill_street2 = cart.bill_street2 or street.split("\r\n")[1]
        cart.ship_street2 = cart.ship_street2 or cart.bill_street2
    cart.bill_city = cart.bill_city or data.get("address_city", "")
    cart.ship_city = cart.ship_city or cart.bill_city
    cart.bill_state = cart.bill_state or data.get("address_state", "")
    cart.ship_state = cart.ship_state or cart.bill_state
    cart.bill_postal_code = cart.bill_postal_code or data.get("address_zip", "")
    cart.ship_postal_code = cart.ship_postal_code or cart.bill_postal_code
    cart.bill_country = cart.bill_country or data.get("address_country_code", "")
    cart.ship_country = cart.ship_country or cart.bill_country

class PaypalIPN(IPNBase):
    """Paypal IPN Handler"""

    def __init__(self, cart, settings=default_settings):
        super(PaypalIPN, self).__init__("paypal", cart, settings)

    @property
    def submit_url(self):
        if self.settings["LIVE"]:
            url = POST_URL
        else:
            url = POST_TEST_URL
        return mark_safe(url)

    def accept_payment(self, data):
        """Accept a successful Paypal payment"""
        transaction_id = data["txn_id"]
        self.log.debug("IPN for transaction #%s received" % transaction_id)
        existing = self.cart.payment_class.objects.filter(transaction_id=transaction_id)
        if len(existing) and not all([p.state == "PENDING" for p in existing]):
            self.log.warn("IPN #%s, but found existing non-PENDING payments, already processed", transaction_id)
            return
        if not self.cart:
            self.log.warn("Unable to find purchase for IPN.")
            return
        # use the IPN data to update the cart's billing info
        update_billing_info(self.cart, data)
        # This save() is critical to persist cart details out to the DB before the Payment is saved
        # and subsequent signals are fired.
        self.cart.save()
        # If we received a previous IPN notifying us the tx was pending,
        # reuse the payment created during that IPN's processing.  Otherwise,
        # create a PENDING payment and save as PAID to ensure signaling
        if len(existing) == 1 and existing[0].state == "PENDING":
            payment = existing[0]
            payment.state = "PAID"
            payment.save()
        else:
            payment = self._create_payment(data["mc_gross"], transaction_id, "PENDING")
            payment.state = "PAID" # Ensure proper state transitions
            payment.save()

        if data.get("note", False):
            payment.notes.create(text="Comment via Paypal IPN: \n%s" % data["note"])

        self.cart.update_state()
        self.cart.save()


    def activate_subscription(self, data):
        """Send signal that a subscription has been activated."""
        if not self.cart:
            self.log.warn("Unable to find purchase for IPN.")
            return
        sku = data.get("item_number", None)
        if sku:
            recurring_by_sku = dict([(li.sku, li) for li in self.cart.recurring_lineitems])
            item = recurring_by_sku.get(sku)
        else:
            item = None
        if item:
            item.is_active = True
            item.save()
            self.cart.update_state()
            self.cart.save()

    def cancel_subscription(self, data):
        """Send signal that a subscription has been cancelled."""
        if not self.cart:
            self.log.warn("Unable to find purchase for IPN.")
            return
        sku = data.get("item_number", None)
        recurring_by_sku = dict([(li.sku, li) for li in self.cart.recurring_lineitems])
        item = recurring_by_sku.get(sku)
        if item:
            item.is_active = False
            item.save()
            self.cart.update_state()
            self.cart.save()

    def payment_pending(self, data):
        """Acknowledge that a payment on this transaction is pending by creating
        a PENDING payment (if necessary) and setting the cart state to PENDING."""
        tx = data["txn_id"]
        existing_payments = self.cart.payment_class.objects.filter(transaction_id=tx)
        # if all is well, there are no existing payments on this transaction
        # so we create a new one in the PENDING state and save it, then update
        # the cart state which should put the cart's state into PENDING as well
        if not len(existing_payments):
            payment = self._create_payment(data["mc_gross"], data["txn_id"], "PENDING")
            payment.save()
            self.cart.update_state()
            self.cart.save()
            return
        # if there are already payments, this might be a duplicate IPN
        if len(existing_payments) == 1 and existing_payments[0].state == "PENDING":
            self.log.warn("Payment Pending IPN received for transaction %s, but PENDING payment already exists." % tx)
        # or some unknown state we should log before the payments are updated
        else:
            states = [p.state for p in existing_payments]
            self.log.warn("Payment Pending notification received on transaction %s, but payments (%s) already exist." % (tx, states))

    def payment_refunded(self, data):
        """Accept a refund notification. mc_gross will be negative."""
        transaction_id = data["txn_id"]
        payment = self._create_payment(data["mc_gross"], transaction_id, "REFUND")
        self.cart.update_state()
        self.cart.save()

    def confirm_ipn_data(self, raw_data):
        """Confirm IPN data using string raw post data.

        Overcomes issues with unicode and urlencode.
        """
        raw_data += "&cmd=_notify-validate"
        req = urllib2.Request(self.submit_url)
        req.add_header("Content-type", "application/x-www-form-urlencoded")
        result = urllib2.urlopen(req, raw_data)
        ret = result.read()
        if ret == "VERIFIED":
            return True
        else:
            return False
