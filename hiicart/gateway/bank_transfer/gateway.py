from hiicart.gateway.base import PaymentGatewayBase, TransactionResult, SubmitResult, GatewayError, CancelResult
from hiicart.gateway.bank_transfer.forms import PaymentForm, FORM_MODEL_TRANSLATION

class BankTransferGateway(PaymentGatewayBase):
    """Bank Transfer processor"""

    def __init__(self, cart):
        super(BankTransferGateway, self).__init__('bank_transfer', cart)

    @property
    def form(self):
        """Returns an instance of PaymentForm."""
        return PaymentForm()

    def confirm_payment(self, request):
        """
        Records billing and shipping info for Bank Transfers
        """
        form = PaymentForm(request.POST)

        if form.is_valid():
            self.cart.ship_first_name = form.cleaned_data['shipping__first_name'] or self.cart.ship_first_name
            self.cart.ship_last_name = form.cleaned_data['shipping__last_name'] or self.cart.ship_last_name
            self.cart.ship_street1 = form.cleaned_data['shipping__street_address'] or self.cart.ship_street1
            self.cart.ship_street2 = form.cleaned_data['shipping__extended_address'] or self.cart.ship_street2
            self.cart.ship_city = form.cleaned_data['shipping__locality'] or self.cart.ship_city
            self.cart.ship_state = form.cleaned_data['shipping__region'] or self.cart.ship_state
            self.cart.ship_postal_code = form.cleaned_data['shipping__postal_code'] or self.cart.ship_postal_code
            self.cart.ship_country = form.cleaned_data['shipping__country_code_alpha2'] or self.cart.ship_country
            self.cart.ship_phone = form.cleaned_data['customer__phone'] or self.cart.ship_phone
            self.cart.bill_first_name = form.cleaned_data['billing__first_name'] or self.cart.bill_first_name
            self.cart.bill_last_name = form.cleaned_data['billing__last_name'] or self.cart.bill_last_name
            self.cart.bill_street1 = form.cleaned_data['billing__street_address'] or self.cart.bill_street1
            self.cart.bill_street2 = form.cleaned_data['billing__extended_address'] or self.cart.bill_street2
            self.cart.bill_city = form.cleaned_data['billing__locality'] or self.cart.bill_city
            self.cart.bill_state = form.cleaned_data['billing__region'] or self.cart.bill_state
            self.cart.bill_postal_code = form.cleaned_data['billing__postal_code'] or self.cart.bill_postal_code
            self.cart.bill_country = form.cleaned_data['billing__country_code_alpha2'] or self.cart.bill_country
            self.cart.bill_phone = form.cleaned_data['customer__phone'] or self.cart.bill_phone
            self.cart.save()

            return TransactionResult(
                transaction_id=self.cart.id,
                success=True,
                status='success')

        else:
            return TransactionResult(
                transaction_id=None,
                success=False,
                status='failed',
                errors=form._errors)

    def submit(self, collect_address=False, cart_settings_kwargs=None):
        """
        Simply returns the gateway type to let the frontend know how to proceed.
        """
        return SubmitResult("direct")

    def start_transaction(self, request, **kwargs):
        """
        Bank Transfers don't need anything special to start a transaction.
        Just get the URL for the form action.
        """
        data = {'submit_url': kwargs.get('submit_url')}
        for f, m in FORM_MODEL_TRANSLATION.iteritems():
            data[f] = getattr(self.cart, m)
        return data

    def prepare_cart(self):
        """Update cart"""

        self.cart.payments.create(amount=self.cart.total, gateway=self.cart.gateway.upper(), state='PENDING', transaction_id=None)

        self.cart._cart_state = "COMPLETED"
        self.cart.send_notifications = False
        self.cart.save()

    def _is_valid(self):
            """Return True if gateway is valid."""
            return True

    def refund_payment(self, payment, reason=None):
        """
        Refund the full amount of this payment
        """
        pass

    def refund(self, payment, amount, reason=None):
        """Refund a payment."""
        return SubmitResult(None)

    def sanitize_clone(self):
        """Nothing to fix here."""
        pass
