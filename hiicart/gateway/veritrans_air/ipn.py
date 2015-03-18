from django.contrib.contenttypes.models import ContentType
from hiicart.gateway.base import IPNBase
from hiicart.gateway.veritrans_air.settings import SETTINGS as default_settings

class VeritransAirIPN(IPNBase):
    """Veritrans Air IPN handler"""

    def __init__(self, cart, settings=default_settings):
        super(VeritransAirIPN, self).__init__("veritrans_air", cart, settings)

    def accept_payment(self, data):
        """Accept a successful Veritrans payment"""
        transaction_id = data["orderId"]
        if data.get('csvType'):
            message = "Marking CSV order %s PAID" % transaction_id
        else:
            message = "Veritrans Air IPN for order #%s received" % transaction_id
        self.log.debug(message)
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
        else:
            payment = self._create_payment(self.cart.total, transaction_id, "PENDING")
        # If credit card payment, mark payment as PAID.
        # For Convenience store payments: they will be marked PAID at
        # time of payment. Since COMPLETED cart with PENDING payment isn't
        # enough to distinguish a conv. store payment, make a Note.
        if 'cvsType' not in data and data['vResultCode'].startswith('D001'):
            cart = self.cart
            content_type = ContentType.objects.get_for_model(cart)
            cart.notes.get_or_create(
                content_type=content_type,
                object_id=cart.pk,
                text__startswith='CVS Payment:',
                defaults={'text': 'CVS Payment:true'},
            )[0]
            cart._cart_state = 'COMPLETED'
        else:
            payment.state = "PAID" # Ensure proper state transitions
            payment.save()
            self.cart.update_state()

        self.cart.save()
        if 'cvsType' in data:
            # trigger the cart state change event for any receivers looking for
            # Payments being marked PAID
            self.cart.cart_state_changed.send(
                sender=self.__class__.__name__,
                cart=self.cart,
                old_state=self.cart._old_state,
                new_state=self.cart.state
            )

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

        required = ['orderId','mStatus','mErrMsg','vResultCode','merchantEncryptionKey']
        for field in required:
            if field not in data:
                return False

        gateway = self.cart.get_gateway()
        merchant_encryption_key = gateway.get_merchant_encryption_key().replace("+",' ')

        return data['merchantEncryptionKey'] == merchant_encryption_key

    def confirm_cvs_ipn_data(self, data):
        """Make sure all the right fields are in the data.  There's no merchant key to check."""
        required = ['orderId','numberOfNotify','cvsType','receiptDate','rcvAmount', 'pushTime', 'pushId', 'receiptNo', 'dummy']
        for field in required:
            if field not in data:
                return False
        return True
