import base

from datetime import datetime, date, timedelta
from decimal import Decimal
from django.conf import settings

from hiicart.models import HiiCart, LineItem, RecurringLineItem

class PaypalTestCase(base.HiiCartTestCase):
    """Paypal related tests"""
    pass

class PaypalIpnTestCase(base.HiiCartTestCase):
    """Tests of the PaypalIPN."""
    pass
