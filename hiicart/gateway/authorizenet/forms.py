from datetime import datetime
from django import forms
from django.forms.util import ErrorDict

PAYMENT_FIELDS = {'credit_card__number': 'x_card_num',
                  'credit_card__cvv': 'x_card_code',
                  'credit_card__exp_date': 'x_exp_date',
                  'credit_card__expiration_month': 'x_exp_date',
                  'billing__first_name': 'x_first_name',
                  'billing__last_name': 'x_last_name',
                  'billing__street_address': 'x_address',
                  'billing__locality': 'x_city',
                  'billing__region': 'x_state',
                  'billing__postal_code': 'x_zip',
                  'billing__country_code_alpha2': 'x_country',
                  'customer__phone': 'x_phone',
                  'shipping__first_name': 'x_ship_to_first_name',
                  'shipping__last_name': 'x_ship_to_last_name',
                  'shipping__street_address': 'x_ship_to_address',
                  'shipping__locality': 'x_ship_to_city',
                  'shipping__region': 'x_ship_to_state',
                  'shipping__postal_code': 'x_ship_to_zip',
                  'shipping__country_code_alpha2': 'x_ship_to_country'}

EXPIRATION_MONTH_CHOICES = [(i, "%02d" % i) for i in range(1, 13)]
EXPIRATION_YEAR_CHOICES = range(datetime.now().year, datetime.now().year + 10)


class PaymentForm(forms.Form):
    """
    Authorize.net payment form.
    """
    return_url = forms.CharField()
    cart_id = forms.CharField()
    x_invoice_num = forms.CharField()
    x_amount = forms.CharField()
    x_fp_sequence = forms.CharField()
    x_fp_timestamp = forms.CharField()
    x_fp_hash = forms.CharField()
    x_relay_response = forms.CharField()
    x_relay_url = forms.CharField()
    x_login = forms.CharField()
    x_method = forms.CharField()
    x_type = forms.CharField()
    x_test_request = forms.CharField()
    x_version = forms.CharField()
    x_card_num = forms.CharField(max_length=16)
    x_card_code = forms.CharField(min_length=3, max_length=4)
    x_exp_date = forms.CharField(max_length=7) # MM/YY, MMYY, MM-YY, MM-YYYY
    x_first_name = forms.CharField(max_length=255)
    x_last_name = forms.CharField(max_length=255)
    x_address = forms.CharField(max_length=80)
    x_city = forms.CharField(max_length=50)
    x_state = forms.CharField(max_length=50)
    x_zip = forms.CharField(max_length=30)
    x_country = forms.CharField(max_length=2)
    x_phone = forms.CharField(max_length=30)
    x_ship_to_first_name = forms.CharField(max_length=255)
    x_ship_to_last_name = forms.CharField(max_length=255)
    x_ship_to_address = forms.CharField(max_length=80)
    x_ship_to_city = forms.CharField(max_length=50)
    x_ship_to_state = forms.CharField(max_length=50)
    x_ship_to_zip = forms.CharField(max_length=30)
    x_ship_to_country = forms.CharField(max_length=2)

    def __init__(self, *args, **kwargs):
        super(PaymentForm, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        if key in PAYMENT_FIELDS:
            key = PAYMENT_FIELDS[key]
        try:
            return self[key]
        except KeyError:
            return object.__getattribute__(self, key)

    def set_transaction(self, data):
        self._submit_url = data['submit_url']
        for key in data:
            if key[:2] == 'x_' or key == "return_url" or key == "cart_id":
                if self.is_bound:
                    self.data[key] = data[key]
                else:
                    self.fields[key].initial = data[key]

    def set_result(self, result):
        """
        Use the results of the gateway payment confirmation to set
        validation errors on the form.
        """
        self._errors = ErrorDict()
        self.is_bound = True
        if not result.success:
            # See http://www.authorize.net/support/merchant/Transaction_Response/Response_Reason_Codes_and_Response_Reason_Text.htm
            #  For testing data http://www.authorize.net/files/ErrorGenerationGuide.pdf
            if result.gateway_result == 6:
                name = "x_card_num"
            elif result.gateway_result == 7:
                name = "x_exp_date"
            elif result.gateway_result == 8:
                name = "x_exp_date"
            elif result.gateway_result == 78:
                name = "x_card_code"
            elif result.gateway_result == 65:
                name = "x_card_code"
            else:
                name = forms.forms.NON_FIELD_ERRORS
            self._errors[name] = self.error_class([result.errors])

    def hidden_fields(self):
        """
        Get hidden fields required for this form.
        """
        return [self['return_url'],
                self['cart_id'],
                self['x_invoice_num'],
                self['x_amount'],
                self['x_fp_hash'],
                self['x_fp_sequence'],
                self['x_relay_response'],
                self['x_relay_url'],
                self['x_login'],
                self['x_version'],
                self['x_fp_timestamp'],
                self['x_method'],
                self['x_type'],
                self['x_test_request']]

    @property
    def action(self):
        """
        Action to post the form to.
        """
        return self._submit_url
