from __future__ import absolute_import # Fix conflicting stripe module names
import stripe as stripe_api
import logging
from django import forms
from hiicart.gateway.base import PaymentGatewayBase, SubmitResult, TransactionResult
from hiicart.gateway.stripe.ipn import StripeIPN
from hiicart.gateway.stripe.forms import PaymentForm, FORM_MODEL_TRANSLATION
from hiicart.gateway.stripe.settings import SETTINGS as default_settings

log = logging.getLogger('hiicart.gateway.stripe.gateway')


class StripeGateway(PaymentGatewayBase):
    """Payment Gateway for Stripe."""

    def __init__(self, cart):
        super(StripeGateway, self).__init__("stripe", cart, default_settings)
        self._require_settings(["PUBLISHABLE_KEY", "PRIVATE_KEY"])

    def _is_valid(self):
        """Return True if gateway is valid."""
        # TODO: Query Stripe to validate credentials
        return True

    @property
    def is_recurring(self):
        return len(self.cart.recurring_lineitems) > 0

    def submit(self, collect_address=False, cart_settings_kwargs=None, submit=False):
        """
        Simply returns the gateway type to let the frontend know how to proceed.
        """
        return SubmitResult("direct")

    @property
    def form(self):
        """Returns an instance of PaymentForm."""
        return PaymentForm()

    def start_transaction(self, request, **kwargs):
        """
        Stripe doesn't need anything special to start a transaction before tokenization.
        Just get the URL for the form action.
        """
        data = {'submit_url': request.path, 'stripe_publishable_key': self.settings['PUBLISHABLE_KEY']}
        for f, m in FORM_MODEL_TRANSLATION.iteritems():
            data[f] = getattr(self.cart, m)
        return data

    def save_payment_cart(self, form):
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

    def charge_amount(self, amount, api_key, token, **kwargs):
        # TODO: there's not anything to actually do, I just wanted to
        # acknowledge that this is terrible
        if self.settings['CURRENCY_CODE'] == 'JPY':
            amount = int(amount)
        else:
            amount = int(amount * 100)  # amount in cents
        charge = stripe_api.Charge.create(
            api_key=api_key,
            amount=amount,
            currency=self.settings['CURRENCY_CODE'],
            source=token,
            description="Order #%s (%s)" % (self.cart.id, self.cart.bill_email),
            **kwargs,
        )
        return charge

    def confirm_payment(self, request):
        """
        Charges tokenized credit card on Stripe.
        """
        form = PaymentForm(request.POST)

        if form.is_valid():
            self.save_payment_cart(form)
            token_id = form.cleaned_data['stripe_token']
            try:
                charge = self.charge_amount(self.cart.total, self.settings['PRIVATE_KEY'], token_id)
            except stripe_api.StripeError as e:
                return TransactionResult(
                    transaction_id=None,
                    success=False,
                    status='failed',
                    errors={forms.forms.NON_FIELD_ERRORS: [e.message]})

            self.cart._cart_state = "SUBMITTED"
            self.cart.save()

            handler = StripeIPN(self.cart)
            handler.accept_payment(charge)

            return TransactionResult(
                transaction_id=charge.id,
                success=True,
                status='success')
        else:
            return TransactionResult(
                transaction_id=None,
                success=False,
                status='failed',
                errors=form._errors)

    def confirm_rev_share_payments(self, request, platform_key, charge_data):
        form = PaymentForm(request.POST)
        if form.is_valid():
            self.save_payment_cart(form)
            token_id = form.cleaned_data['stripe_token']
            customer = stripe_api.Customer.create(
                api_key=platform_key,
                source=token_id,
                description="Customer for Order %s" % self.cart.pk
            )
            charge_keys = []
            try:
                for cd in charge_data:
                    token = stripe.Token.create(
                        customer=customer.id,
                        stripe_account=cd['stripe_account']  # store's account
                    )
                    kwargs = {
                        'application_fee': cd['application_fee'],
                        'stripe_account': cd['stripe_account'],
                    }
                    charge = self.charge_amount(charge_data['amount'], platform_key, token.id, **kwargs)
                    charge_keys.append([charge, cd['stripe_account']])
            except stripe_api.StripeError as e:
                for charge, key in charge_keys:
                    stripe_api.Refund.create(api_key=key, charge=charge.id)
                return TransactionResult(
                    transaction_id=None,
                    success=False,
                    status='failed',
                    errors={forms.forms.NON_FIELD_ERRORS: [e.message]})

            self.cart._cart_state = "SUBMITTED"
            self.cart.save()

            handler = StripeIPN(self.cart)
            for charge in charges:
                handler.accept_payment(charge)

            # We have multiple charges, but whatever, I don't think it matters
            return TransactionResult(
                transaction_id=charge.id,
                success=True,
                status='success')
