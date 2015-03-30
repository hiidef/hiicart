import base

from datetime import datetime, date, timedelta
from decimal import Decimal
from django.conf import settings

from hiicart.models import HiiCart, LineItem, RecurringLineItem

class AmazonPaymentsTestCase(base.HiiCartTestCase):
    """Amazon Payments related tests"""
    pass
