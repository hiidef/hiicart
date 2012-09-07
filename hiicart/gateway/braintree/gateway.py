import logging
import braintree

from django.template import Context, loader

from hiicart.gateway.base import PaymentGatewayBase, CancelResult, SubmitResult, TransactionResult, SubscriptionResult, GatewayError
from hiicart.gateway.braintree.forms import make_form
from hiicart.gateway.braintree.ipn import BraintreeIPN
from hiicart.gateway.braintree.settings import SETTINGS as default_settings
from hiicart.gateway.braintree.tasks import update_payment_status
from hiicart.models import HiiCart

log = logging.getLogger('hiicart.gateway.braintree.gateway')


class BraintreeGateway(PaymentGatewayBase):
    """Payment Gateway for Braintree."""

    def __init__(self, cart):
        super(BraintreeGateway, self).__init__("braintree", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY",
                                "MERCHANT_PRIVATE_KEY"])
        braintree.Configuration.configure(self.environment,
                                          self.settings["MERCHANT_ID"],
                                          self.settings["MERCHANT_KEY"],
                                          self.settings["MERCHANT_PRIVATE_KEY"])

    def _is_valid(self):
        """Return True if gateway is valid."""
        # TODO: Query Braintree to validate credentials
        return True

    @property
    def is_recurring(self):
        return len(self.cart.recurring_lineitems) > 0

    @property
    def environment(self):
        """Determine which Braintree environment to use."""
        if self.settings["LIVE"]:
            return braintree.Environment.Production
        else:
            return braintree.Environment.Sandbox

    def submit(self, collect_address=False, cart_settings_kwargs=None, submit=False):
        """
        Simply returns the gateway type to let the frontend know how to proceed.
        """
        return SubmitResult("direct")

    @property
    def form(self):
        """Returns an instance of PaymentForm."""
        return make_form(self.is_recurring)()

    def start_transaction(self, request):
        """
        Submits transaction details to Braintree and returns form data.
        If we're processing a one-time sale, submit the transaction for settlement
        right away. Otherwise, if we're starting a subscription, create the credit
        card on Braintree and create a subscription with the payment method token
        after confirmation.
        """
        redirect_url = request.build_absolute_uri(request.path)
        if self.is_recurring:
            tr_data = braintree.Customer.tr_data_for_create({
                'customer': {
                    'credit_card': {
                        'options': {
                            'verify_card': True
                        }
                    }
                }},
                redirect_url)
        else:
            tr_data = braintree.Transaction.tr_data_for_sale({
                "transaction": {
                    "type": "sale",
                    "order_id": self.cart.cart_uuid,
                    "amount": self.cart.total,
                    "options": {
                        "submit_for_settlement": True
                    }
                }},
                redirect_url)
        return tr_data

    def confirm_payment(self, request, gateway_dict=None):
        """
        Confirms payment result with Braintree.

        This method should be called after the Braintree transaction redirect
        to determine the payment result. It expects the request to contain the
        query string coming back from Braintree.
        """
        result_class = SubscriptionResult if self.is_recurring else TransactionResult

        try:
            result = braintree.TransparentRedirect.confirm(request.META['QUERY_STRING'])
        except Exception, e:
            errors = {'non_field_errors': 'Request to payment gateway failed.'}
            return result_class(transaction_id=None,
                                success=False, status=None, errors=errors,
                                gateway_result=None)

        if result.is_success:
            handler = BraintreeIPN(self.cart)
            if self.is_recurring:
                credit_card = result.customer.credit_cards[0]
                create_result = handler.create_subscription(credit_card, gateway_dict=gateway_dict)
                transaction_id = None
                status = 'success'
                created = create_result.success
                gateway_result = create_result.gateway_result
            else:
                created = handler.new_order(result.transaction)
                transaction_id = result.transaction.id
                status = result.transaction.status
                gateway_result = result
            if created:
                return result_class(transaction_id=transaction_id,
                                    success=True, status=status,
                                    gateway_result=gateway_result)

        errors = {}
        transaction_id = None
        status = None
        obj = getattr(result, 'transaction', None) or getattr(result, 'credit_card_verification', None)
        if obj:
            transaction_id = getattr(obj, 'id', None)
            status = getattr(obj, 'status', None)
            if status == 'processor_declined':
                errors = {'non_field_errors': getattr(obj, 'processor_response_text', 'There was an error communicating with the gateway')}
            elif status == 'gateway_rejected':
                errors = {'non_field_errors': getattr(obj, 'gateway_rejection_reason', 'The card was declined')}
        else:
            message = getattr(result, 'message', None)
            errors = {'non_field_errors': message}
            if result.errors:
                for error in result.errors.deep_errors:
                    errors[error.attribute] = error.message

        return result_class(transaction_id=transaction_id,
                            success=False, status=status, errors=errors,
                            gateway_result=result)

    def update_payment_status(self, transaction_id, cart_class=HiiCart):
        try:
            update_payment_status.apply_async(args=[self.cart.id, transaction_id], kwargs={'cart_class': cart_class}, countdown=300)
        except Exception, e:
            log.error("Error updating payment status for transaction %s: %s" % (transaction_id, e))

    def create_discount_args(self, discount_id, num_billing_cycles=1, quantity=1, existing_discounts=None):
        if not existing_discounts:
            args = {
                'discounts': {
                    'add': [
                        {
                            'inherited_from_id': discount_id,
                            'number_of_billing_cycles': num_billing_cycles,
                            'quantity': quantity
                        }
                    ]
                }
            }
        else:
            existing_cycles = existing_discounts[0].number_of_billing_cycles
            args = {
                'discounts': {
                    'update': [
                        {
                            'existing_id': discount_id,
                            'number_of_billing_cycles': existing_cycles + num_billing_cycles,
                            'quantity': quantity
                        }
                    ]
                }
            }

        return args

    def apply_discount(self, subscription_id, discount_id, num_billing_cycles=1, quantity=1):
        """
        Apply a discount to an existing subscription.
        """
        subscription = braintree.Subscription.find(subscription_id)
        existing_discounts = filter(lambda d: d.id == discount_id, subscription.discounts)
        args = self.create_discount_args(discount_id, num_billing_cycles, quantity, existing_discounts)
        result = braintree.Subscription.update(subscription_id, args)
        errors = {}
        if result.is_success:
            status = 'success'
        else:
            errors['non_field_errors'] = getattr(result, 'message', 'There was an error applying the discount')
            status = 'error'

        return SubscriptionResult(transaction_id=subscription_id,
                                  success=result.is_success, status=status, errors=errors,
                                  gateway_result=result)

    def cancel_recurring(self):
        """
        Cancel a cart's subscription.
        """
        if not self.is_recurring:
            return None
        subscription_id = self.cart.recurring_lineitems[0].payment_token
        result = braintree.Subscription.cancel(subscription_id)
        return SubscriptionResult(transaction_id=subscription_id,
                                  success=result.is_success, status=result.subscription.status,
                                  gateway_result=result)

    def charge_recurring(self, grace_period=None):
        """
        Charge a cart's recurring item, if necessary.
        NOTE: Currently only one recurring item is supported per cart,
              so charge the first one found.
        We use braintree's subscriptions for recurring billing, so we don't manually
        charge recurring payments. Instead, we poll braintree to get new
        payments/transactions.
        """
        if not grace_period:
            grace_period = self.settings.get("CHARGE_RECURRING_GRACE_PERIOD", None)
        recurring = [li for li in self.cart.recurring_lineitems if li.is_active]
        if not recurring or not recurring[0].is_expired(grace_period=grace_period):
            return
        item = recurring[0]

        handler = BraintreeIPN(self.cart)
        result = braintree.Subscription.find(item.payment_token)
        transactions = result.transactions
        for t in transactions:
            handler.accept_payment(t)

    def start_update(self, request):
        """
        Start the process of updating payment information for a subscription.
        """
        if not self.is_recurring:
            raise NotImplementedError("Only recurring subscriptions can be updated")

        redirect_url = request.build_absolute_uri(request.path)

        subscription_id = self.cart.recurring_lineitems[0].payment_token
        subscription = braintree.Subscription.find(subscription_id)
        payment_method_token = subscription.payment_method_token
        customers = braintree.Customer.search(braintree.CustomerSearch.payment_method_token == payment_method_token)
        customers = list(customers.items)
        customer = customers[0]

        tr_data = braintree.Customer.tr_data_for_update({
            'customer_id': customer.id,
            'customer': {
                'credit_card': {
                    'options': {
                        'verify_card': True,
                        'make_default': True
                    }
                }
            }
        }, redirect_url)

        return tr_data

    def confirm_update(self, request):
        """
        Confirms credit card update result with Braintree.
        """
        try:
            result = braintree.TransparentRedirect.confirm(request.META['QUERY_STRING'])
        except Exception, e:
            errors = {'non_field_errors': 'Request to payment gateway failed.'}
            return SubscriptionResult(transaction_id=None,
                                success=False, status=None, errors=errors,
                                gateway_result=None)

        if result.is_success:
            subscription_id = self.cart.recurring_lineitems[0].payment_token
            for cc in result.customer.credit_cards:
                if cc.default:
                    payment_method_token = cc.token
            sub_result = braintree.Subscription.update(subscription_id, {
                'payment_method_token': payment_method_token
            })
            return SubscriptionResult(transaction_id=None,
                    success=True, status='success', gateway_result=result)

        errors = {}
        status = None
        verification = getattr(result, 'credit_card_verification', None)
        if verification:
            status = getattr(obj, 'status', None)
            if status == 'processor_declined':
                errors = {'non_field_errors': getattr(obj, 'processor_response_text', 'There was an error communicating with the gateway')}
            elif status == 'gateway_rejected':
                errors = {'non_field_errors': getattr(obj, 'gateway_rejection_reason', 'The card was declined')}
        else:
            message = getattr(result, 'message', None)
            errors = {'non_field_errors': message}
            if result.errors:
                for error in result.errors.deep_errors:
                    errors[error.attribute] = error.message

        return SubscriptionResult(transaction_id=None,
                            success=False, status=status, errors=errors,
                            gateway_result=result)

    def change_subscription_amount(self, subscription_id, new_price):
        result = braintree.Subscription.update(subscription_id, {
            'price': new_price,
            'options': {
                'prorate_charged': True,
                'revert_subscription_on_proration_failure': False
            }
        })
        return SubscriptionResult(transaction_id=None, success=result.is_success, status=None, errors={}, gateway_result=result)

    def refund_payment(self, payment, reason=None):
        result = self.refund(payment, payment.amount)
        payment.state = 'REFUND'
        payment.save()
        return result

    def refund(self, payment, amount, reason=None):
        result = braintree.Transaction.refund(payment.transaction_id, amount)
        if result.is_success:
            self._create_payment(amount * -1, result.transaction.id, 'REFUND')
        return TransactionResult(transaction_id=result.transaction.id, success=result.is_success, status=None, errors={}, gateway_result=result)
