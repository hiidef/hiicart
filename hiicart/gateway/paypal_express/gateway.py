import urllib
import httplib2
from cgi import parse_qs

from decimal import Decimal
from datetime import datetime
from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict

from hiicart.gateway.base import PaymentGatewayBase, SubmitResult, GatewayError
from hiicart.gateway.paypal_express.settings import SETTINGS as default_settings

NVP_SIGNATURE_TEST_URL = "https://api-3t.sandbox.paypal.com/nvp"
NVP_SIGNATURE_URL = "https://api-3t.paypal.com/nvp"
REDIRECT_URL = "https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=%s"
REDIRECT_TEST_URL = "https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=%s"

NO_SHIPPING = {
    "REQUIRE": "2",
    "NO" : "1",
    "YES" : "0"
    }
ALLOW_NOTE = {
    "YES" : "1",
    "NO" : "0"
    }
RECURRING_PAYMENT = {
    "YES" : "1",
    "NO" : "0"
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
        encoded_params = urllib.urlencode(params_dict)

        response, content = http.request(self._nvp_url, 'POST', encoded_params)
        response_dict = parse_qs(content)
        for k, v in response_dict.iteritems():
            if type(v) == list:
                response_dict[k] = v[0]
        if response_dict['ACK'] != 'Success':
            raise GatewayError("Error calling Paypal %s" % method)
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
        params[keyprefix+'shiptoname'] = '%s %s' % (self.cart.bill_first_name, self.car.bill_last_name)
        params[keyprefix+'shiptostreet'] = self.cart.bill_street1
        params[keyprefix+'shiptostreet2'] = self.cart.bill_street2
        params[keyprefix+'shiptocity'] = self.cart.bill_city
        params[keyprefix+'shiptostate'] = self.cart.bill_state
        params[keyprefix+'shiptocountrycode'] = self.cart.bill_country
        params[keyprefix+'shiptozip'] = self.cart.bill_zip
        return params
    
    def _get_checkout_data(self):
        """Populate request params from shopping cart"""
        params = SortedDict()

        # Urls for returning user after leaving Paypal
        if self.settings.get('RETURN_URL'):
            params['returnurl'] = self.settings['RETURN_URL']
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
        
        params[pre+'invnum'] = self.cart.cart_uuid
        params[pre+'currencycode'] = self.settings['CURRENCY_CODE']
        if len(self.cart.recurring_lineitems) == 0:
            # Total cost of transaction to customer, including shipping, handling, and tax if known
            params[pre+'amt'] = self.cart.total.quantize(Decimal('.01'))
            # Sub-total of all items in order
            params[pre+'itemamt'] = self.cart.sub_total.quantize(Decimal('.01'))
            # Shipping amount
            params[pre+'shippingamt'] = self.cart.shipping.quantize(Decimal('.01')) if self.cart.shipping else Decimal('0.00')
            # Tax amount
            params[pre+'taxamt'] = self.cart.tax.quantize(Decimal('.01')) if self.cart.tax else Decimal('0.00')
        else:
            # Use MAXAMT and INITAMT instead to cover initial and recurring charges
            params[pre+'amt'] = '0.00'
            params['maxamt'] = self.cart.total.quantize(Decimal('0.01'))
        # Not using parallel payments, so this is always Sale
        params[pre+'paymentaction'] = 'Sale'
        params[pre+'notifyurl'] = self.settings['IPN_URL']

        pre = 'l_paymentrequest_0_'

        if len(self.cart.recurring_lineitems) > 1:
            self.log.error("Cannot have more than one subscription in one order for Paypal. Only processing the first one for %s", self.cart)
        if len(self.cart.recurring_lineitems) > 0:
            item = self.cart.recurring_lineitems[0]
            params['l_billingtype0'] = 'RecurringPayments'
            params['l_billingagreementdescription0' ] = item.description
            # Initial charge, recurring charge, duratiom, frequency, trial are all set with CreateRecurringPaymentsProfile
        else:
            idx = 0
            for item in self.cart.one_time_lineitems:
                params[pre+'name%i' % idx] = item.name
                params[pre+'desc%i' % idx] = item.description
                params[pre+'amt%i' % idx] = item.total.quantize(Decimal('.01'))
                params[pre+'qty%i' % idx] = item.quantity
                params[pre+'number%i' % idx] = item.sku
                idx += 1

        if self.cart.bill_street1:
            params['addroverride'] = '0'
            params['email'] = self.cart.bill_email
            params.update(self._get_billing_address_params(pre))

        return params

    def _get_recurring_data(self):
        """Populate request params for establishing recurring payments"""
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
        params['profilestartdate'] = item.recurring_start.isoformat() if item.recurring_start else datetime.utcnow().isoformat()

        params['billingperiod'] = item.duration_unit
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
        params = {'token' : token}
        response = self._do_nvp('GetExpressCheckoutDetails', params)

        payerid = response['PAYERID']
        # TODO: user-defined callback on get_details to update cart?
        
        if self.settings.get("CONFIRM_URL"):
            url = self.settings["CONFIRM_URL"]
        else:
            # No confirm_url specified, so assume we go straight to finalizing the order
            url = self.settings["FINALIZE_URL"]
        
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
            # Subscription is activated with CreateRecurringPaymentsProfile
            params.update(self._get_recurring_data())
            response = self._do_nvp('CreateRecurringPaymentsProfile', params)
            profileid = response['PROFILEID']
            status = response['STATUS']
            item = self.cart.recurring_lineitems[0]
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

