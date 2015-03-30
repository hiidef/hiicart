import base

from datetime import datetime, date, timedelta
from decimal import Decimal
from django.conf import settings

from hiicart.models import HiiCart, LineItem, RecurringLineItem

def has_required_settings():
    """Returns True if the Google gateway has settings, False otherwise."""
    from hiicart.settings import SETTINGS
    google = SETTINGS.get("GOOGLE", {})
    if not google.get("MERCHANT_ID") and google.get("MERCHANT_KEY"):
        return False
    return True

class GoogleCheckoutTestCase(base.HiiCartTestCase):
    """Google Checkout related tests"""

    def test_submit(self):
        """Test submitting a cart to Google, checking we get a url back."""
        if not has_required_settings():
            print "\nValid Google MERCHANT_ID & MERCHANT_KEY required for Google Checkout tests."
            return
        self.assertEqual(self.cart.state, "OPEN")
        result = self.cart.submit("google")
        self.assertEqual(result.type, "url")
        self.assertNotEqual(result.url, None)
        self.assertEqual(self.cart.state, "SUBMITTED")

    def test_submit_recurring(self):
        """Test submitting a cart with recurring items to Google."""
        if not has_required_settings():
            print "\nValid Google MERCHANT_ID & MERCHANT_KEY required for Google Checkout tests."
            return
        self._add_recurring_item()
        self.assertEqual(self.cart.state, "OPEN")
        result = self.cart.submit("google")
        self.assertEqual(result.type, "url")
        self.assertNotEqual(result.url, None)
        self.assertEqual(self.cart.state, "SUBMITTED")

    def test_submit_recurring_delayed(self):
        """Test submitting a cart with recurring items to Google."""
        if not has_required_settings():
            print "\nValid Google MERCHANT_ID & MERCHANT_KEY required for Google Checkout tests."
            return
        self._add_recurring_item()
        ri = self.cart.recurring_lineitems[0]
        ri.recurring_start = datetime.now() + timedelta(days=7)
        ri.save()
        self.assertEqual(self.cart.state, "OPEN")
        result = self.cart.submit("google")
        self.assertEqual(result.type, "url")
        self.assertNotEqual(result.url, None)
        self.assertEqual(self.cart.state, "SUBMITTED")
