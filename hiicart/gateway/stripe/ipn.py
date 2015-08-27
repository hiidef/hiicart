from decimal import Decimal
from hiicart.gateway.base import IPNBase
from hiicart.gateway.stripe.settings import SETTINGS as default_settings


class StripeIPN(IPNBase):
    """Stripe IPN Handler."""

    def __init__(self, cart):
        super(StripeIPN, self).__init__("stripe", cart, default_settings)
        self._require_settings(["PUBLISHABLE_KEY", "PRIVATE_KEY"])

    @property
    def is_recurring(self):
        return len(self.cart.recurring_lineitems) > 0

    def _record_payment(self, charge):
        """Create a new payment record."""
        if not self.cart:
            return
        if charge.paid:
            state = 'PAID'
        else:
            state = 'FAILED'

        payment = self.cart.payments.filter(transaction_id=charge.id)
        if payment:
            if payment[0].state != state:
                payment[0].state = state
                payment[0].save()
                return payment[0]
        else:
            if self.settings['CURRENCY_CODE'] == 'JPY':
                amount = charge.amount
            else:
                amount = float(charge.amount) / 100.0
            amount = Decimal(str(amount))
            payment = self._create_payment(amount, charge.id, state)
            payment.save()
            return payment


    def accept_payment(self, charge):
        payment = self._record_payment(charge)
        if payment:
            self.cart.update_state()
            self.cart.save()
