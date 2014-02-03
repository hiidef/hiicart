import hmac
import random
import time
import re
from urlparse import urlsplit, urlunsplit, parse_qs, urljoin

from django.contrib.sessions.backends.db import SessionStore
from hiicart.models import PaymentResponse
from hiicart.gateway.base import PaymentGatewayBase, CancelResult, SubmitResult, PaymentResult
from hiicart.gateway.authorizenet.forms import PaymentForm
from hiicart.gateway.authorizenet.ipn import AuthorizeNetIPN, FORM_MODEL_TRANSLATION
from hiicart.gateway.authorizenet.settings import SETTINGS as default_settings

POST_URL = "https://secure.authorize.net/gateway/transact.dll"
POST_TEST_URL = "https://test.authorize.net/gateway/transact.dll"


class AuthorizeNetGateway(PaymentGatewayBase):
    """Payment Gateway for Authorize.net."""

    def __init__(self, cart):
        super(AuthorizeNetGateway, self).__init__("authorizenet", cart, default_settings)
        self._require_settings(["MERCHANT_ID", "MERCHANT_KEY", 
                                "MERCHANT_PRIVATE_KEY"])

    def _is_valid(self):
        """Return True if gateway is valid."""
        return True

    def has_payment_result(self, request):
        response = self.get_response()
        if response:
            return True
        return False

    @property
    def submit_url(self):
        """Submit URL for current environment."""
        if self.settings["LIVE"]:
            return POST_URL
        else:
            return POST_TEST_URL

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
        self._update_with_cart_settings({'request':request})
        sequence = random.randint(10000, 99999)
        timestamp = int(time.time())
        hash_message = "%s^%s^%s^%s^" % (self.settings['MERCHANT_ID'],
                                         timestamp, timestamp, self.cart.total)
        fp_hash = hmac.new(str(self.settings['MERCHANT_KEY']), hash_message)
        data = {'submit_url': self.submit_url,
                'return_url': request.build_absolute_uri(),
                'cart_id': self.cart.cart_uuid,
                'x_invoice_num': timestamp,
                'x_fp_hash': fp_hash.hexdigest(),
                'x_fp_sequence': timestamp,
                'x_fp_timestamp': timestamp,
                'x_amount': self.cart.total,
                'x_login': self.settings['MERCHANT_ID'],
                'x_relay_url': self.settings['IPN_URL'],
                'x_relay_response': 'TRUE',
                'x_method': 'CC',
                'x_type': 'AUTH_CAPTURE',
                'x_version': '3.1'}
        if request.META.get('HTTP_X_FORWARDED_PROTO') == 'https':
            data['return_url'] = data['return_url'].replace('http:', 'https:')
        if not self.settings['LIVE']:
            # Set this value to false to get a real transaction # returned when running on
            # sandbox.  A real transaction is required to for testing refunds.
            data['x_test_request'] = 'FALSE'
        for model_field, form_field in FORM_MODEL_TRANSLATION.items():
            data[form_field] = getattr(self.cart, model_field)
        return data

    def get_response(self):
        """Get a payment result if it exists."""
        result = PaymentResponse.objects.filter(cart=self.cart)
        if result:
            return result[0]
        return None

    def set_response(self, data):
        """Store payment result for confirm_payment."""

        response, created = PaymentResponse.objects.get_or_create(cart=self.cart, defaults={
                'response_code': int(data['x_response_reason_code']),
                'response_text': data['x_response_reason_text']
                })
        if not created:
            response.response_code = int(data['x_response_reason_code'])
            response.response_text = data['x_response_reason_text']
            response.save()
        
        if response.response_code == 1:
            # Successful directly goto the payment_thanks page
            (scheme, host, path, paramstr, fragment) = list(urlsplit(data['return_url']))
            params = parse_qs(paramstr)

            if 'cd' in params:
                host = params['cd'][0]
                scheme = 'http'

            match = re.search(r'^(.*/checkout)(/[\w\-]+)$', path)
            if match:
                path = match.group(1)

            return_url = urlunsplit((scheme, host, path, paramstr, fragment))

            data['return_url'] = urljoin(return_url, "payment_thanks")
        else:
            # Mimic the braintree redirect behavior of appending http_status to the query string
            if '?' in data['return_url']:
                data['return_url'] = data['return_url'] + '&http_status=200'
            else:
                data['return_url'] = data['return_url'] + "?http_status=200"

    def confirm_payment(self, request):
        """
        Confirms payment result with AuthorizeNet.
        """
        response = self.get_response()
        if response:
            if response.response_code == 1:
                result = PaymentResult('transaction', success=True, status="APPROVED")
            else:
                result = PaymentResult('transaction', success=False, status="DECLINED", errors=response.response_text, 
                                       gateway_result=response.response_code)
        else:
            result = PaymentResult('transaction', success=False, status=None, errors="Failed to process transaction")
        return result
