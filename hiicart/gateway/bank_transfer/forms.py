from django import forms
from django.forms.util import ErrorDict

FORM_MODEL_TRANSLATION = {
    'billing__first_name': 'bill_first_name',
    'billing__last_name': 'bill_last_name',
    'billing__street_address': 'bill_street1',
    'billing__extended_address': 'bill_street2',
    'billing__locality': 'bill_city',
    'billing__region': 'bill_state',
    'billing__postal_code': 'bill_postal_code',
    'billing__country_code_alpha2': 'bill_country',
    'customer__phone': 'bill_phone',
    'shipping__first_name': 'ship_first_name',
    'shipping__last_name': 'ship_last_name',
    'shipping__street_address': 'ship_street1',
    'shipping__extended_address': 'ship_street2',
    'shipping__locality': 'ship_city',
    'shipping__region': 'ship_state',
    'shipping__postal_code': 'ship_postal_code',
    'shipping__country_code_alpha2': 'ship_country'
}

class PaymentForm(forms.Form):

    billing__first_name = forms.CharField(max_length=255)
    billing__last_name = forms.CharField(max_length=255)
    billing__street_address = forms.CharField(max_length=80)
    billing__extended_address = forms.CharField(max_length=80, required=False)
    billing__locality = forms.CharField(max_length=50)
    billing__region = forms.CharField(max_length=50)
    billing__postal_code = forms.CharField(max_length=30)
    billing__country_code_alpha2 = forms.CharField(max_length=2)
    customer__phone = forms.CharField(max_length=30, required=False)
    shipping__first_name = forms.CharField(max_length=255)
    shipping__last_name = forms.CharField(max_length=255)
    shipping__street_address = forms.CharField(max_length=80)
    shipping__extended_address = forms.CharField(max_length=80, required=False)
    shipping__locality = forms.CharField(max_length=50)
    shipping__region = forms.CharField(max_length=50)
    shipping__postal_code = forms.CharField(max_length=30)
    shipping__country_code_alpha2 = forms.CharField(max_length=2)

    def __getitem__(self, name):
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError("Key %r not found in Form" % name)
        return forms.forms.BoundField(self, field, name)

    def set_transaction(self, data):
        import ipdb; ipdb.set_trace()
        self._submit_url = data.pop('submit_url')
        for k, v in data.iteritems():
            if self.is_bound:
                self.data[k] = v
            else:
                self.fields[k].initial = v

    def set_result(self, result):
        self.is_bound = True
        if result.errors:
            self._errors = result.errors
        else:
            self._errors = ErrorDict()
            if not result.success:
                self._errors[forms.forms.NON_FIELD_ERRORS] = self.error_class([result.errors])

    @property
    def action(self):
        """
        Action to post the form to.
        """
        return self._submit_url
