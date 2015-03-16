import urllib
import httplib2
import hashlib
import random
from cgi import parse_qs

from decimal import Decimal
from datetime import datetime
from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict
from django.shortcuts import render_to_response
from dateutil.relativedelta import relativedelta

from hiicart.gateway.base import PaymentGatewayBase, TransactionResult, SubmitResult, GatewayError, CancelResult
from hiicart.gateway.veritrans_air.settings import SETTINGS as default_settings
from hiicart.gateway.veritrans_air.forms import PaymentForm, FORM_MODEL_TRANSLATION
from hiicart.models import HiiCartError, PaymentResponse

TOKEN_ENDPOINT = "https://air.veritrans.co.jp/web/commodityRegist.action"
PAYMENT_ENDPOINT = "https://air.veritrans.co.jp/web/paymentStart.action"


class VeritransAirGateway(PaymentGatewayBase):
    """Veritrans Air processor"""

    def __init__(self, cart):
        super(VeritransAirGateway, self).__init__('veritrans_air', cart, default_settings)
        self._require_settings(['MERCHANT_ID', 'MERCHANT_ID'])

    def _get_token(self, params_dict):
        #httplib2.debuglevel = 1
        http = httplib2.Http()
        params_dict['MERCHANT_ID'] = self.settings['MERCHANT_ID']
        params_dict['SESSION_ID'] = self.settings['SESSION_ID']
        params_dict["SETTLEMENT_TYPE"] = self.settings["SETTLEMENT_TYPE"]
        if self.settings['LIVE']:
            params_dict["DUMMY_PAYMENT_FLAG"] = "0"
        else:
            params_dict["DUMMY_PAYMENT_FLAG"] = "1"

        params_pairs = []
        for (key, val) in params_dict.iteritems():
            if isinstance(val, (list, tuple)):
                for v in val:
                    params_pairs.append((key, unicode(v).encode('utf-8')))
            else:
                params_pairs.append((key, unicode(val).encode('utf-8')))

        encoded_params = urllib.urlencode(params_pairs)

        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Accept-Language': 'ja'}
        response, content = http.request(TOKEN_ENDPOINT, 'POST', body=encoded_params, headers=headers)
        response_dict = {}
        for line in content.splitlines():
            key, val = line.split("=")
            response_dict[key]=val
        
        if 'ERROR_MESSAGE' in response_dict:
            raise GatewayError("Error getting token from Veritrans Air: %s" % response_dict['ERROR_MESSAGE'])
        return response_dict


    def _get_checkout_data(self):
        """Populate request params from shopping cart"""
        params = SortedDict()

        # Urls for returning user after leaving Veritrans
        if self.settings.get('FINISH_PAYMENT_RETURN_URL'):
            finish_url = self.settings['FINISH_PAYMENT_RETURN_URL']
            if '?' in finish_url:
                finish_url += '&cart='
            else:
                finish_url += '?cart='
            finish_url += self.cart._cart_uuid
            params['FINISH_PAYMENT_RETURN_URL'] = finish_url

        if self.settings.get('FINISH_PAYMENT_ACCESS_URL'):
            params['FINISH_PAYMENT_ACCESS_URL'] = self.settings['FINISH_PAYMENT_ACCESS_URL']

        if self.settings.get('PUSH_URL'):
            params['PUSH_URL'] = self.settings['PUSH_URL']

        if self.settings.get('CARD_CAPTURE_FLAG'):
            params['CARD_CAPTURE_FLAG'] = self.settings['CARD_CAPTURE_FLAG']

        if self.settings.get('UNFINISH_PAYMENT_RETURN_URL'):
            params['UNFINISH_PAYMENT_RETURN_URL'] = self.settings['UNFINISH_PAYMENT_RETURN_URL']

        if self.settings.get('ERROR_PAYMENT_RETURN_URL'):
            params['ERROR_PAYMENT_RETURN_URL'] = self.settings['ERROR_PAYMENT_RETURN_URL']

        params['ORDER_ID'] = self.cart.id
        params['AMOUNT'] = Decimal(self.cart.total).quantize(Decimal('1'))

        params['MERCHANTHASH'] = hashlib.sha512(b"%s,%s,%s,%s,%s" % (self.settings["MERCHANT_KEY"], 
                                                                    self.settings["MERCHANT_ID"],
                                                                    self.settings["SETTLEMENT_TYPE"],
                                                                    params['ORDER_ID'],
                                                                    params['AMOUNT'])
                                                ).hexdigest()
        
        if self.cart.shipping:
            params['SHIPPING_AMOUNT'] = self.cart.shipping.quantize(Decimal('1'))

        params["MAILADDRESS"] = self.cart.bill_email

        # params['NAME1'] = self.cart.bill_first_name
        # params['NAME2'] = self.cart.bill_last_name
        # params['ADDRESS1'] = self.cart.bill_street1
        # params['ADDRESS2'] = self.cart.bill_city
        # params['ADDRESS3'] = self.cart.bill_state
        # params['ZIP_CODE'] = self.cart.bill_postal_code
        # params['TELEPHONE_NO'] = self.cart.bill_phone
        # params['MAILADDRESS'] = self.cart.bill_email

        # Add one-time line items
        # params['COMMODITY_ID'] = []
        # params['COMMODITY_UNIT'] = []
        # params['COMMODITY_NUM'] = []
        # params['COMMODITY_NAME'] = []
        # for item in self.cart.one_time_lineitems:
        #     params['COMMODITY_NAME'].append(item.name)
        #     params['COMMODITY_UNIT'].append(item.unit_price.quantize(Decimal('1')))
        #     params['COMMODITY_NUM'].append(item.quantity)
        #     params['COMMODITY_ID'].append(item.sku)

        return params


    def confirm_payment(self, request):
        """
        Records billing and shipping info for Veritrans AIR
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

    def set_merchant_encryption_key(self, key):
        response, created = PaymentResponse.objects.get_or_create(cart=self.cart, defaults={
                'response_code': 0,
                'response_text': key
                })
        if not created:
            response.response_code = 0
            response.response_text = key
            response.save()

    def get_merchant_encryption_key(self):
        responses = PaymentResponse.objects.filter(cart=self.cart)
        if len(responses):
            return responses[0].response_text
        else:
            return None

    def submit(self, collect_address=False, cart_settings_kwargs=None):
        """
        Simply returns the gateway type to let the frontend know how to proceed.
        """
        return SubmitResult("direct")

    def start_transaction(self, request, **kwargs):
        """
        Veritrans Air doesn't need anything special to start a transaction before tokenization.
        Just get the URL for the form action.
        """
        data = {'submit_url': kwargs.get('submit_url')}
        for f, m in FORM_MODEL_TRANSLATION.iteritems():
            data[f] = getattr(self.cart, m)
        return data

    @property
    def form(self):
        """Returns an instance of PaymentForm."""
        return PaymentForm()

    def redirect_view(self, cart_settings_kwargs=None):
        """Submit order details to the gateway."""
        self._update_with_cart_settings(cart_settings_kwargs)

        params = self._get_checkout_data()
        response = self._get_token(params)

        self.cart._cart_state = "SUBMITTED"
        self.cart.save()

        self.set_merchant_encryption_key(response.get('MERCHANT_ENCRYPTION_KEY'))

        fields = {
            'BROWSER_ENCRYPTION_KEY': response['BROWSER_ENCRYPTION_KEY'],
            'ORDER_ID': params['ORDER_ID'],
            'MERCHANT_ID': self.settings['MERCHANT_ID']      
            }        
        context = {"url": PAYMENT_ENDPOINT, "fields": fields}        

        response = render_to_response('gateway/veritrans_air/payment.html', context)
        return response

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
