from hiicart.gateway.base import IPNBase
from hiicart.gateway.veritrans_air.settings import SETTINGS as default_settings

class VeritransAirIPN(IPNBase):
    """Veritrans Air IPN handler"""

    def __init__(self, cart, settings=default_settings):
        super(VeritransAirIPN, self).__init__("veritrans_air", cart, settings)

    def accept_payment(self, data):
        """Accept a successful Veritrans payment"""
        transaction_id = data["orderId"]
        self.log.debug("Veritrans Air IPN for order #%s received" % transaction_id)
        existing = self.cart.payment_class.objects.filter(transaction_id=transaction_id)
        if len(existing) and not all([p.state == "PENDING" for p in existing]):
            self.log.warn("IPN #%s, but found existing non-PENDING payments, already processed", transaction_id)
            return
        if not self.cart:
            self.log.warn("Unable to find purchase for IPN.")
            return

        # If we received a previous IPN notifying us the tx was pending,
        # reuse the payment created during that IPN's processing.  Otherwise,
        # create a PENDING payment and save as PAID to ensure signaling
        if len(existing) == 1 and existing[0].state == "PENDING":
            payment = existing[0]
            payment.state = "PAID"
            payment.save()
        else:
            payment = self._create_payment(self.cart.total, transaction_id, "PENDING")
            payment.state = "PAID" # Ensure proper state transitions
            payment.save()

        self.cart.update_state()
        self.cart.save()        

    def payment_pending(self, data):
        """Acknowledge that a payment on this transaction is pending by creating
        a PENDING payment (if necessary) and setting the cart state to PENDING."""
        transaction_id = data["orderId"]
        existing_payments = self.cart.payment_class.objects.filter(transaction_id=transaction_id)
        # if all is well, there are no existing payments on this transaction
        # so we create a new one in the PENDING state and save it, then update
        # the cart state which should put the cart's state into PENDING as well
        if not len(existing_payments):
            payment = self._create_payment(self.cart.total, transaction_id, "PENDING")
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

    def confirm_ipn_data(self, data):
        """Confirm IPN data """

        check = True
        required = ['orderId','mStatus','mErrMsg','vResultCode','merchantEncryptionKey']
        for field in required:
            if field not in data:
                return False

        gateway = self.cart.get_gateway()
        merchant_encryption_key = gateway.get_merchant_encryption_key().replace("+",' ')

        return data['merchantEncryptionKey'] == merchant_encryption_key
