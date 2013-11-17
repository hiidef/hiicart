import urllib
import httplib2
from cgi import parse_qs

from decimal import Decimal
from datetime import datetime
from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict
from dateutil.relativedelta import relativedelta

from hiicart.gateway.base import PaymentGatewayBase, SubmitResult, GatewayError, CancelResult
from hiicart.gateway.paypal_express.settings import SETTINGS as default_settings
from hiicart.models import HiiCartError

NVP_SIGNATURE_TEST_URL = "https://api-3t.sandbox.paypal.com/nvp"
NVP_SIGNATURE_URL = "https://api-3t.paypal.com/nvp"
REDIRECT_URL = "https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=%s"
REDIRECT_TEST_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=%s"

NO_SHIPPING = {
    "REQUIRE": "2",
    "NO": "1",
    "YES": "0"
}
ALLOW_NOTE = {
    "YES": "1",
    "NO": "0"
}
RECURRING_PAYMENT = {
    "YES": "1",
    "NO": "0"
}
BILLING_PERIOD = {
    "DAY": "Day",
    "WEEK": "Week",
    "MONTH": "Month",
    "YEAR": "Year"
}


class PaypalExpressCheckoutGateway(PaymentGatewayBase):
    """Paypal Express Checkout processor"""

    def __init__(self, cart):
        super(PaypalExpressCheckoutGateway, self).__init__('paypal_express', cart, default_settings)
        self._require_settings(['API_USERNAME', 'API_PASSWORD', 'API_SIGNATURE'])

    @property
    def _nvp_url(self):
        """URL to post NVP API call to"""
        if self.settings['LIVE']:
            url = NVP_SIGNATURE_URL
        else:
            url = NVP_SIGNATURE_TEST_URL
        return mark_safe(url)

    def _do_nvp(self, method, params_dict):
        http = httplib2.Http()
        params_dict['method'] = method
        params_dict['user'] = self.settings['API_USERNAME']
        params_dict['pwd'] = self.settings['API_PASSWORD']
        params_dict['signature'] = self.settings['API_SIGNATURE']
        params_dict['version'] = self.settings['API_VERSION']
        if self.settings.get("BN"):
            params_dict["bn"] = self.settings["BN"]
        encoded_params = urllib.urlencode(params_dict)

        response, content = http.request(self._nvp_url, 'POST', encoded_params)
        response_dict = parse_qs(content)
        for k, v in response_dict.iteritems():
            if type(v) == list:
                response_dict[k] = v[0]
        if response_dict['ACK'] != 'Success':
            raise GatewayError("Error calling Paypal Express %s" % method)
        return response_dict

    def _create_redirect_url(self, token):
        """Construct user redirect url from token"""
        if self.settings['LIVE']:
            base = REDIRECT_URL
        else:
            base = REDIRECT_TEST_URL
        return base % token

    def _get_billing_address_params(self, keyprefix=''):
        params = SortedDict()
        params[keyprefix + 'shiptoname'] = '%s %s' % (self.cart.bill_first_name, self.cart.bill_last_name)
        params[keyprefix + 'shiptostreet'] = self.cart.bill_street1
        params[keyprefix + 'shiptostreet2'] = self.cart.bill_street2
        params[keyprefix + 'shiptocity'] = self.cart.bill_city
        params[keyprefix + 'shiptostate'] = self.cart.bill_state
        params[keyprefix + 'shiptocountrycode'] = self.cart.bill_country
        params[keyprefix + 'shiptozip'] = self.cart.bill_postal_code
        return params

    def _is_immediate_payment(self, item):
        return item.recurring_start is None or item.recurring_start.date() == datetime.today()

    def _get_checkout_data(self):
        """Populate request params from shopping cart"""
        params = SortedDict()

        # Urls for returning user after leaving Paypal
        if self.settings.get('RETURN_URL'):
            return_url = self.settings['RETURN_URL']
            if '?' in return_url:
                return_url += '&cart='
            else:
                return_url += '?cart='
            return_url += self.cart._cart_uuid
            params['returnurl'] = return_url

        if self.settings.get('CANCEL_URL'):
            params['cancelurl'] = self.settings['CANCEL_URL']

        params['localecode'] = self.settings['LOCALE']

        if self.settings.get('NO_SHIPPING'):
            params['noshipping'] = self.settings['NO_SHIPPING']
        else:
            params['noshipping'] = NO_SHIPPING['YES']

        params['allownote'] = '1'

        # We don't support parallel payments, so all PAYMENTREQUEST fields will
        # just use this one prefix
        pre = 'paymentrequest_0_'

        params[pre + 'invnum'] = self.cart.cart_uuid
        params[pre + 'currencycode'] = self.settings['CURRENCY_CODE']

        do_immediate_payment = False
        if len(self.cart.recurring_lineitems) == 0:
            do_immediate_payment = True
        else:
            item = self.cart.recurring_lineitems[0]
            do_immediate_payment = self._is_immediate_payment(item)

        if do_immediate_payment:
            # Total cost of transaction to customer, including shipping, handling, and tax if known
            params[pre + 'amt'] = self.cart.total.quantize(Decimal('.01'))
            # Sub-total of all items in order
            params[pre + 'itemamt'] = self.cart.sub_total.quantize(Decimal('.01'))
            # Shipping amount
            params[pre + 'shippingamt'] = self.cart.shipping.quantize(Decimal('.01')) if self.cart.shipping else Decimal('0.00')
            # Tax amount
            params[pre + 'taxamt'] = self.cart.tax.quantize(Decimal('.01')) if self.cart.tax else Decimal('0.00')
        else:
            # No initial payment for this recurring payment
            params[pre + 'amt'] = '0.00'
            params['maxamt'] = self.cart.total.quantize(Decimal('0.01'))

        # Not using parallel payments, so this is always Sale
        params[pre + 'paymentaction'] = 'Sale'
        params[pre + 'notifyurl'] = self.settings['IPN_URL']

        # Populate line items
        pre = 'l_paymentrequest_0_'

        # Add recurring line item
        idx = 0
        if len(self.cart.recurring_lineitems) > 1:
            self.log.error("Cannot have more than one subscription in one order for Paypal. Only processing the first one for %s", self.cart)
        if len(self.cart.recurring_lineitems) > 0:
            item = self.cart.recurring_lineitems[0]
            params['l_billingtype%i' % idx] = 'RecurringPayments'
            params['l_billingagreementdescription%i' % idx] = item.description
            params[pre + 'name%i' % idx] = item.name
            params[pre + 'number%i' % idx] = item.sku

            if self._is_immediate_payment(item):
                # No delay to start of recurring billing, so we need to set up an initial payment.
                # We'll push the start of the recurring billing back by one cycle when we create the
                # recurring payment profile.
                params[pre + 'amt%i' % idx] = item.recurring_price
            else:
                params[pre + 'amt%i' % idx] = '0.00'
            # Recurring charge, duration, frequency, trial are all set with CreateRecurringPaymentsProfile
            idx += 1

        # Add one-time line items
        for item in self.cart.one_time_lineitems:
            params[pre + 'name%i' % idx] = item.name
            params[pre + 'desc%i' % idx] = item.description
            params[pre + 'amt%i' % idx] = item.total.quantize(Decimal('.01'))
            params[pre + 'qty%i' % idx] = item.quantity
            params[pre + 'number%i' % idx] = item.sku
            idx += 1

        if self.cart.bill_street1:
            params['addroverride'] = '0'
            params['email'] = self.cart.bill_email
            params.update(self._get_billing_address_params(pre))

        return params

    def _get_recurring_data(self):
        """Populate request params for establishing recurring payments"""
        pre = 'paymentrequest_0_'
        params = SortedDict()

        if len(self.cart.recurring_lineitems) == 0:
            raise GatewayError("The cart must have at least one recurring item to use recurring payments")
        if len(self.cart.recurring_lineitems) > 1:
            self.log.error("Cannot have more than one subscription in one order for Paypal. Only processing the first one for %s", self.cart)

        item = self.cart.recurring_lineitems[0]

        params['currencycode'] = self.settings['CURRENCY_CODE']
        params['amt'] = item.recurring_price
        params['desc'] = item.description
        params['shippingamt'] = item.recurring_shipping
        params['profilereference'] = self.cart.cart_uuid
        if self._is_immediate_payment(item):
            # We already created an initial payment, so move the recurring start out by one billing cycle
            if item.duration_unit == 'MONTH':
                delta = relativedelta(months=item.duration)
            elif item.duration_unit == 'DAY':
                delta = relativedelta(days=item.duration)
            startdate = datetime.today() + delta
        else:
            startdate = item.recurring_start

        params['profilestartdate'] = startdate.isoformat()

        params['billingperiod'] = BILLING_PERIOD[item.duration_unit]
        params['billingfrequency'] = item.duration

        if item.trial:
            params['trialbillingperiod'] = item.duration_unit
            params['trialbillingfrequency'] = item.duration
            params['trialtotalbillingcycles'] = item.trial_length
            params['trialamt'] = item.trial_price

        if self.cart.bill_street1:
            params.update(self._get_billing_address_params(pre))

        params['email'] = self.cart.bill_email

        return params

    def _update_cart_details(self, details):
        pre = 'PAYMENTREQUEST_0_'

        # Fill in shipping information
        property_names = {
                'EMAIL': 'ship_email',
                pre + 'SHIPTOSTREET': 'ship_street1',
                pre + 'SHIPTOSTREET2': 'ship_street2',
                pre + 'SHIPTOCITY': 'ship_city',
                pre + 'SHIPTOSTATE': 'ship_state',
                pre + 'SHIPTOZIP': 'ship_postal_code',
                pre + 'SHIPTOCOUNTRYCODE': 'ship_country'
                }
        for pp_field, cart_field in property_names.iteritems():
            setattr(self.cart, cart_field, getattr(self.cart, cart_field) or details.get(pp_field, ''))

        shiptoname = details.get(pre + 'SHIPTONAME', '')
        if shiptoname:
            name_parts = shiptoname.split(' ')
            firstname = ' '.join(name_parts[:-1])
            lastname = name_parts[-1]
        else:
            firstname = details.get('FIRSTNAME', '')
            lastname = details.get('LASTNAME', '')
        self.cart.ship_first_name = self.cart.ship_first_name or firstname
        self.cart.ship_last_name = self.cart.ship_last_name or lastname

        self.cart.save()

    def submit(self, collect_address=False, cart_settings_kwargs=None):
        """Submit order details to the gateway.

        * Server POSTs an API call to Paypal
        * Paypal returns a response that includes an URL to redirect the user to"""
        self._update_with_cart_settings(cart_settings_kwargs)

        params = self._get_checkout_data()
        response = self._do_nvp('SetExpressCheckout', params)

        token = response['TOKEN']
        url = self._create_redirect_url(token)
        return SubmitResult('url', url, session_args={'hiicart_paypal_express_token': token})

    def get_details(self, token):
        """Get details from Paypal about payer and payment."""
        params = {'token': token}
        response = self._do_nvp('GetExpressCheckoutDetails', params)

        payerid = response['PAYERID']
        self._update_cart_details(response)
        # TODO: user-defined callback on get_details to update cart?

        if self.settings.get("CONFIRM_URL"):
            url = self.settings["CONFIRM_URL"]
        else:
            # No confirm_url specified, so assume we go straight to finalizing the order
            url = self.settings["FINALIZE_URL"]
        if '?' in url:
            url += '&cart='
        else:
            url += '?cart='
        url += self.cart._cart_uuid

        session_args = {
            'hiicart_paypal_express_token': token,
            'hiicart_paypal_express_payerid': payerid
            }
        return SubmitResult('url', url, session_args=session_args)

    def finalize(self, token, payerid):
        """Complete payment on Paypal after user has confirmed."""
        params = {}
        params['token'] = token
        params['payerid'] = payerid

        if len(self.cart.recurring_lineitems) > 0:
            item = self.cart.recurring_lineitems[0]

            if self._is_immediate_payment(item):
                params.update(self._get_checkout_data())
                self._do_nvp('DoExpressCheckoutPayment', params)

            # Subscription is activated with CreateRecurringPaymentsProfile
            params = {}
            params['token'] = token
            params['payerid'] = payerid
            params.update(self._get_recurring_data())
            response = self._do_nvp('CreateRecurringPaymentsProfile', params)
            profileid = response['PROFILEID']
            status = response['PROFILESTATUS']
            item.payment_token = profileid
            if status == 'ActiveProfile':
                item.is_active = True
            else:
                item.is_active = False
            item.save()
        else:
            # Submit for immediate payment
            params.update(self._get_checkout_data())
            self._do_nvp('DoExpressCheckoutPayment', params)

        url = self.settings["COMPLETE_URL"]
        return SubmitResult('url', url)

    def _is_valid(self):
        """Return True if gateway is valid."""
        # Can't validate credentials with Paypal AFAIK
        return True

    def cancel_recurring(self, profileid=None):
        """Cancel recurring items with gateway. Returns a CancelResult."""
        if not profileid:
            item = self.cart.recurring_lineitems[0]
            profileid = item.payment_token

        params = {
            'profileid': profileid,
            'action': 'cancel',
        }

        self._do_nvp('ManageRecurringPaymentsProfileStatus', params)
        # make sure the line item is not acitive
        item = self.cart.recurring_lineitems[0]
        item.is_active = False
        item.save()
        self.cart.update_state()
        return CancelResult(None)

    def refund_payment(self, payment, reason=None):
        """
        Refund the full amount of this payment
        """
        self.refund(payment, payment.amount, reason)
        payment.state = 'REFUND'
        payment.save()

    def refund(self, payment, amount, reason=None):
        """Refund a payment."""
        params = {'transactionid': payment.transaction_id}
        if payment.amount == amount:
            params['refundtype'] = 'Full'
        else:
            params.update({
                'refundtype': 'Partial',
                'amt': str(amount.quantize(Decimal('.01')))
            })

        self._do_nvp('RefundTransaction', params)
        return SubmitResult(None)

    def charge_recurring(self, grace_period=None):
        """This Paypal API doesn't support manually charging subscriptions."""
        pass

    def sanitize_clone(self):
        """Nothing to fix here."""
        pass
