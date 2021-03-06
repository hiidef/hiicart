import urllib2
from hiicart.gateway.base import IPNBase
from hiicart.gateway.paypal2.settings import SETTINGS as default_settings


class Paypal2IPN(IPNBase):
    """Payment Gateway for Paypal Website Payments Pro."""

    def __init__(self, cart):
        super(Paypal2IPN, self).__init__("paypal2", cart, default_settings)

    def accept_payment(self, data):
        """Accept a PayPal payment IPN."""
        # TODO: Should this simple mirror/reuse what's in gateway.paypal?
        transaction_id = data["txn_id"]
        self.log.debug("IPN for transaction #%s received" % transaction_id)
        if self.cart.payment_class.objects.filter(transaction_id=transaction_id).count() > 0:
            self.log.warn("IPN #%s, already processed", transaction_id)
            return
        if not self.cart:
            self.log.warn("Unable to find purchase for IPN.")
            return
        payment = self._create_payment(data["mc_gross_1"], transaction_id, "PENDING")
        payment.state = "PAID" # Ensure proper state transitions
        payment.save()
        if data.get("note", False):
            payment.notes.create(text="Comment via IPN: \n%s" % data["note"])
        self.cart.bill_email = self.cart.bill_email or data.get("payer_email", "")
        self.cart.ship_email = self.cart.ship_email or self.cart.bill_email
        self.cart.bill_first_name = self.cart.bill_first_name or data.get("first_name", "")
        self.cart.ship_first_name = self.cart.ship_first_name or self.cart.bill_first_name
        self.cart.bill_last_name = self.cart.bill_last_name or data.get("last_name", "")
        self.cart.ship_last_name = self.cart.ship_last_name or self.cart.bill_last_name
        self.cart.update_state()
        self.cart.save()

    def accept_recurring_payment(self, data):
        transaction_id = data["txn_id"]
        self.log.debug("IPN for transaction #%s received" % transaction_id)
        if self.cart.payment_class.objects.filter(transaction_id=transaction_id).count() > 0:
            self.log.warn("IPN #%s, already processed", transaction_id)
            return
        if not self.cart:
            self.log.warn("Unable to find purchase for IPN.")
            return
        payment = self._create_payment(data["mc_gross"], transaction_id, "PENDING")
        payment.state = "PAID" # Ensure proper state transitions
        payment.save()
        if data.get("note", False):
            payment.notes.create(text="Comment via IPN: \n%s" % data["note"])
        self.cart.update_state()
        self.cart.save()

    def confirm_ipn_data(self, raw_data):
        """Confirm IPN data using string raw post data.

        Using the raw data overcomes issues with unicode and urlencode.
        """
        # TODO: This is common to all Paypal gateways. It should be shared.
        if self.settings["LIVE"]:
            submit_url = "https://www.paypal.com/cgi-bin/webscr"
        else:
            submit_url = "https://www.sandbox.paypal.com/cgi-bin/webscr"
        raw_data += "&cmd=_notify-validate"
        req = urllib2.Request(submit_url)
        req.add_header("Content-type", "application/x-www-form-urlencoded")
        result = urllib2.urlopen(req, raw_data).read()
        return urllib2.urlopen(req, raw_data).read() == "VERIFIED"

    def recurring_payment_profile_cancelled(self, data):
        """Notification that a recurring profile was cancelled."""
        # TODO: Support more than one profile in a cart
        #       Can ri.payment_token be used to id the profile?
        ri = self.cart.recurring_lineitems[0]
        ri.is_active = True
        ri.save()

    def recurring_payment_profile_created(self, data):
        """Notification that a recurring profile was created."""
        # TODO: Support more than one profile in a cart
        #       Can ri.payment_token be used to id the profile?
        ri = self.cart.recurring_lineitems[0]
        ri.is_active = True
        ri.save()

