# -*- coding: utf-8 -*-

"""HiiCart Data Models."""

import copy
import django
import logging
import uuid

from django.utils import timezone
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.dispatch import Signal
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.safestring import mark_safe
from hiicart.settings import SETTINGS as hiicart_settings

logger = logging.getLogger("hiicart.models")

SHIPPING_CHOICES = [
    ("0", "No Shipping Charges"),
    ("1", "Pay Shipping Once"),
    ("2", "Pay Shipping Each Billing Cycle"),
]

SUBSCRIPTION_UNITS = [
    ("DAY", "Days"),
    ("MONTH", "Months"),
]

HIICART_STATES = [
    # the cart has been created, but not yet submitted to the gateway
    ("OPEN", "Open"),
    # the cart has been submitted to the gateway.  since the inclusion
    # of the "PENDING" state, this state means that the user has been
    # sent to the gateway, but the gateway has not notified us that the
    # user has completed their part of the payment process yet
    ("SUBMITTED", "Submitted"),
    # the gateway has notified us that some kind of transaction on this
    # cart has been started and the final payment on it is pending (ie.
    # the user has actually submitted payment details, but the payment has
    # not yet completed, for echecks, credit delays, etc)
    ("PENDING", "Pending"),
    # FIXME: document ABANDONED cart state
    ("ABANDONED", "Abandoned"),
    # payment has been made and the gateway has notified us via the IPN
    # (or via polling for some gateways, ex. braintree).
    ("COMPLETED", "Completed"),
    # active subscription
    ("RECURRING", "Recurring"),
    # subscription cancelled at gateway but not expired yet
    ("PENDCANCEL", "Pending Cancellation"),
    # FIXME: document REFUND cart state
    ("REFUND", "Refunded"),
    # FIXME: document PARTREFUND cart state
    ("PARTREFUND", "Partially Refunded"),
    # FIXME: document CANCELLED cart state
    ("CANCELLED", "Cancelled"),
]

PAYMENT_STATES = [
    ("PENDING", "Pending"),
    ("PAID", "Paid"),
    ("FAILED", "Failed"),
    ("REFUND", "Refund"),
    ("CANCELLED", "Cancelled"),
]

# valid state transitions for a cart;  if the current state is a key in this dict,
# then the only valid new state is one in the value of that key

VALID_TRANSITIONS = {
    # PENDING is here because it seems like the submission step is skippable somehow, but
    # generally we only expect to get to PENDING from SUBMITTED
    "OPEN": ["SUBMITTED", "ABANDONED", "COMPLETED", "RECURRING", "PENDING", "PENDCANCEL", "CANCELLED"],
    "SUBMITTED": ["COMPLETED", "PENDING", "RECURRING", "PENDCANCEL", "CANCELLED"],
    "ABANDONED": [],
    "COMPLETED": ["RECURRING", "PENDCANCEL", "CANCELLED", "REFUND", "PARTREFUND"],
    "PARTREFUND": ["REFUND","CANCELLED"],
    "REFUND": ["CANCELLED"],
    "RECURRING": ["PENDCANCEL", "CANCELLED"],
    "PENDING": ["COMPLETED", "PENDING", "RECURRING", "PENDCANCEL", "CANCELLED"],
    "PENDCANCEL": ["CANCELLED"],
    "CANCELLED": [],
}

# storage for cart classes (classes whose meta is HiiCartMetaClass)
CART_TYPES = []


class HiiCartError(Exception):
    pass


class HiiCartMetaclass(models.base.ModelBase):
    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, HiiCartBase)]
            attrs['lineitem_types'] = set()
            attrs['recurring_lineitem_types'] = set()
            attrs['one_time_lineitem_types'] = set()

            attrs['cart_state_changed'] = Signal(
                providing_args=["cart", "new_state", "old_state"]
            )
        except NameError:
            # This is HiiCartBase
            parents = False
        new_class = super(HiiCartMetaclass, cls).__new__(cls, name, bases, attrs)
        if parents:
            CART_TYPES.append(new_class)

        return new_class


class HiiCartBase(models.Model):
    """
    Collects information about an order and tracks its state.

    Facilitates the cart being submitted to a payment gateway and some
    subscription management functions.
    """
    __metaclass__ = HiiCartMetaclass

    _cart_state = models.CharField(choices=HIICART_STATES, max_length=16, default="OPEN", db_index=True)
    _cart_uuid = models.CharField(max_length=36, db_index=True)
    gateway = models.CharField(max_length=16, null=True, blank=True)
    notes = generic.GenericRelation("Note")
    # Redirection targets after purchase completes
    failure_url = models.URLField(null=True)
    success_url = models.URLField(null=True)
    # Total fields
    # sub_total and total are '_' so we can recalculate them on the fly
    discount = models.DecimalField("Discount", max_digits=18, decimal_places=2, blank=True, null=True)
    _sub_total = models.DecimalField("Subtotal", max_digits=18, decimal_places=2, blank=True, null=True)
    _total = models.DecimalField("Total", max_digits=18, decimal_places=2)
    tax = models.DecimalField("Tax", max_digits=18, decimal_places=2, blank=True, null=True)
    tax_rate = models.DecimalField("Tax Rate", max_digits=6, decimal_places=5, blank=True, null=True)
    tax_country = models.CharField("Tax Country", max_length=2, blank=True, null=True)
    tax_region = models.CharField("Tax Region", max_length=127, blank=True, null=True)
    shipping = models.DecimalField("Shipping Cost", max_digits=18, decimal_places=2, blank=True, null=True)
    shipping_option_name = models.CharField(max_length=75, blank=True, null=True)
    # Customer Info
    ship_first_name = models.CharField("First name", max_length=255, default="")
    ship_last_name = models.CharField("Last name", max_length=255, default="")
    ship_email = models.EmailField("Email", max_length=255, default="")
    ship_phone = models.CharField("Phone Number", max_length=30, default="")
    ship_street1 = models.CharField("Street", max_length=80, default="")
    ship_street2 = models.CharField("Street 2", max_length=80, default="")
    ship_city = models.CharField("City", max_length=50, default="")
    ship_state = models.CharField("State", max_length=50, default="")
    ship_postal_code = models.CharField("Zip Code", max_length=30, default="")
    ship_country = models.CharField("Country", max_length=2, default="")
    bill_first_name = models.CharField("First name", max_length=255, default="")
    bill_last_name = models.CharField("Last name", max_length=255, default="")
    bill_email = models.EmailField("Email", max_length=255, default="")
    bill_phone = models.CharField("Phone Number", max_length=30, default="")
    bill_street1 = models.CharField("Street", max_length=80, default="")
    bill_street2 = models.CharField("Street", max_length=80, default="")
    bill_city = models.CharField("City", max_length=50, default="")
    bill_state = models.CharField("State", max_length=50, default="")
    bill_postal_code = models.CharField("Zip Code", max_length=30, default="")
    bill_country = models.CharField("Country", max_length=2, default="")
    thankyou = models.CharField("Thank you message.", max_length=255, blank=True, null=True, default=None)
    fulfilled = models.BooleanField(default=False)
    custom_id = models.CharField(max_length=255, blank=True, null=True, default=None)
    created = models.DateTimeField("Created", auto_now_add=True)
    last_updated = models.DateTimeField("Last Updated", auto_now=True)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """Override in order to keep track of changes to state."""
        super(HiiCartBase, self).__init__(*args, **kwargs)
        self._old_state = self.state
        self.hiicart_settings = hiicart_settings

    def __unicode__(self):
        if self.id:
            return "#%s %s" % (self.id, self.state)
        else:
            return "(unsaved) %s" % self.state

    @classmethod
    def register_lineitem_type(cart_class, recurring=False):
        def register_decorator(cls):
            cart_class.lineitem_types.add(cls)
            if recurring:
                cart_class.recurring_lineitem_types.add(cls)
            else:
                cart_class.one_time_lineitem_types.add(cls)
            return cls
        return register_decorator

    @classmethod
    def set_payment_class(cart_class, payment_class):
        cart_class.payment_class = payment_class
        return payment_class

    @property
    def lineitems(self):
        return self._get_lineitems(self.lineitem_types)

    @property
    def recurring_lineitems(self):
        return self._get_lineitems(self.recurring_lineitem_types)

    @property
    def one_time_lineitems(self):
        return self._get_lineitems(self.one_time_lineitem_types)

    def _get_lineitems(self, cls_list):
        l = [cls.objects.filter(cart=self) for cls in cls_list]
        return [item for sublist in l for item in sublist]

    def _is_valid_transition(self, old, new):
        """
        Validate a proposed state transition.

        This prevents cases like an account going from CANCELLED to
        PENDCANCEL when a user cancels the subscription. As far as the
        system is concerned, it should be pending cancellation, but it's
        been marked as cancelled by another part of the system or an admin.
        See VALID_TRANSITIONS.
        """
        return new in VALID_TRANSITIONS[old]

    def _recalc(self):
        """Recalculate totals"""
        self._sub_total = self.sub_total
        self._total = self.total

    @property
    def cart_uuid(self):
        """UUID identifying this cart to gateways. Populated on initial save."""
        return self._cart_uuid

    @property
    def state(self):
        """State of the cart. Read-only. Use update_state or set_state to change."""
        return self._cart_state

    @property
    def sub_total(self):
        """Current sub_total, calculated from lineitems."""
        return sum([li.sub_total or 0 for li in self.lineitems])

    @property
    def total(self):
        """Current total, calculated from lineitems."""
        return sum([li.total or 0 for li in self.lineitems]) + (self.tax or 0) + (self.shipping or 0) - (self.discount or 0)

    def adjust_expiration(self, newdate):
        """
        DEVELOPMENT ONLY: Adjust subscription end date.  Won't actually change
        when Google or PP will bill next subscription.
        """
        if self.hiicart_settings["LIVE"]:
            raise HiiCartError("Development only functionality.")
        if self.state != "PENDCANCEL" and self.state != "RECURRING":
            return
        delta = self.get_expiring_lineitem().expiration_delta
        new_date = newdate - delta
        for p in self.payments.all():
            if p.created > new_date:
                p.created = new_date
                p.save()

    def cancel_if_expired(self, grace_period=None):
        """Mark this cart as cancelled if recurring lineitems have expired."""
        if self.state != "PENDCANCEL" and self.state != "RECURRING":
            return
        if all([r.is_expired(grace_period) for r in self.recurring_lineitems]):
            self.set_state("CANCELLED")

    def cancel_recurring(self, skip_pendcancel=False):
        """
        Cancel any recurring items in the cart.

        skip_pendcancel skips the pending cancellation state and marks
        the cart as cancelled.
        """
        gateway = self.get_gateway()
        response = gateway.cancel_recurring()
        if skip_pendcancel:
            self.set_state("CANCELLED")
        self.update_state()
        return response

    def charge_recurring(self, grace_period=None):
        """
        Charge recurring purchases if necessary.

        Charges recurring items with the gateway, if possible. An optional
        grace period can be provided to avoid premature charging. This is
        provided since the gateway might be in another timezone, causing
        a mismatch between when an account can be charged.
        """
        gateway = self.get_gateway()
        gateway.charge_recurring(grace_period)
        self.update_state()

    def clone(self):
        """Clone this cart in the OPEN state."""
        dupe = copy.copy(self)
        # This method only works when id and pk have been cleared
        dupe.pk = None
        dupe.id = None
        dupe.set_state("OPEN", validate=False)
        dupe.gateway = None
        # Clear out any gateway-specific actions that might've been taken
        gateway = self.get_gateway()
        if gateway is not None:
            gateway.sanitize_clone(dupe)
        # Need to save before we can attach lineitems
        dupe.save()
        for item in self.lineitems:
            item.clone(dupe)
        return dupe

    def get_expiration(self):
        """Get expiration of recurring item or None if there are no recurring items."""
        return max([r.get_expiration() for r in self.recurring_lineitems])

    def get_expiring_lineitem(self):
        return max([(r.get_expiration(), r) for r in self.recurring_lineitems])[1]

    def get_gateway(self):
        """Get the PaymentGateway associated with this cart or None if cart has not been submitted yet.."""
        if self.gateway is None:
            return None
        return self._get_gateway(self.gateway)

    def _get_gateway(self, name):
        # importing now prevents circular import issues.
        from hiicart.gateway.amazon.gateway import AmazonGateway
        from hiicart.gateway.comp.gateway import CompGateway
        from hiicart.gateway.google.gateway import GoogleGateway
        from hiicart.gateway.paypal.gateway import PaypalGateway
        from hiicart.gateway.paypal2.gateway import Paypal2Gateway
        from hiicart.gateway.paypal_adaptive.gateway import PaypalAPGateway
        from hiicart.gateway.paypal_express.gateway import PaypalExpressCheckoutGateway
        from hiicart.gateway.veritrans_air.gateway import VeritransAirGateway
        from hiicart.gateway.braintree.gateway import BraintreeGateway
        from hiicart.gateway.authorizenet.gateway import AuthorizeNetGateway
        from hiicart.gateway.stripe.gateway import StripeGateway

        """Factory to get payment gateways."""
        gateways = {
            'amazon': AmazonGateway,
            'comp': CompGateway,
            'google': GoogleGateway,
            'paypal': PaypalGateway,
            'paypal2': Paypal2Gateway,
            'paypal_adaptive': PaypalAPGateway,
            'paypal_express': PaypalExpressCheckoutGateway,
            'veritrans_air': VeritransAirGateway,
            'braintree': BraintreeGateway,
            'authorizenet': AuthorizeNetGateway,
            'stripe': StripeGateway
            }
        try:
            cls = gateways[name]
            return cls(self)
        except KeyError:
            raise HiiCartError("Unknown gateway: %s" % name)

    def save(self, *args, **kwargs):
        """Override to recalculate total and signal on state change."""
        self._recalc()
        if not self._cart_uuid:
            self._cart_uuid = str(uuid.uuid4())
        super(HiiCartBase, self).save(*args, **kwargs)
        # Signal sent after save in case someone queries database
        if self.state != self._old_state:
            self.cart_state_changed.send(sender=self.__class__.__name__, cart=self,
                                         old_state=self._old_state,
                                         new_state=self.state)
            self._old_state = self.state

    def set_state(self, newstate, validate=True):
        """Set state of the cart, optionally not validating the transition."""
        if newstate == self.state:
            return
        if validate and not self._is_valid_transition(self.state, newstate):
            raise HiiCartError("Invalid state transition %s -> %s" % (
                               self.state, newstate))
        self._cart_state = newstate
        self.save()

    def submit(self, gateway_name, collect_address=False, cart_settings_kwargs=None):
        """Submit this cart to a payment gateway."""
        gateway = self._get_gateway(gateway_name)
        self.gateway = gateway_name
        self.save()
        result = gateway.submit(collect_address, cart_settings_kwargs)
        if result and result.type is not "direct":
            self.set_state("SUBMITTED")
        return result

    def update_state(self):
        """
        Update cart state based on payments and lineitem expirations.

        Valid state transitions are listed in VALID_TRANSITIONS. This
        function contains the logic for when those various states are used.
        """
        newstate = None
        payments = self.payments.all()
        total_paid = sum([p.amount for p in payments if p.state == "PAID"])
        total_refund = abs(sum([p.amount for p in payments if p.state == "REFUND"]))
        # Subscriptions involve multiple payments, therefore diff may be < 0
        if self.total - total_paid <= 0:
            newstate = "COMPLETED"
        # If refunds exist determine if they represent a partial or full
        if total_refund > 0 and total_refund < total_paid:
            newstate = "PARTREFUND"
        elif total_refund > 0 and total_refund >= total_paid:
            newstate = "REFUND"
        # If all of the payments in the cart are PENDING, the cart should be PENDING
        if len(payments) and all([True if payment.state == "PENDING" else False for payment in payments]):
            newstate = "PENDING"
        # Account for recurring state changes
        if any([li.is_active for li in self.recurring_lineitems]):
            newstate = "RECURRING"
        elif len(self.recurring_lineitems) > 0:
            # Paid and then cancelled, but not expired
            if newstate in ("COMPLETED", "PARTREFUND", "REFUND") and not all([r.is_expired() for r in self.recurring_lineitems]):
                newstate = "PENDCANCEL"
            # Could be cancelled manually (is_active set to False)
            # Could be a re-subscription, but is now cancelled. Is not paid.
            # Could be expired
            elif newstate in ("COMPLETED", "PARTREFUND", "REFUND") or self.state == "RECURRING":
                newstate = "CANCELLED"
        # Validate transition then save
        if newstate and newstate != self.state and self._is_valid_transition(self.state, newstate):
            self._cart_state = newstate
            self.save()


# Stop CASCADE ON DELETE with User, but keep compatibility with django < 1.3
if django.VERSION[1] >= 3 and hiicart_settings["KEEP_ON_USER_DELETE"]:
    _user_delete_behavior = models.SET_NULL
else:
    _user_delete_behavior = None


class HiiCart(HiiCartBase):
    if _user_delete_behavior is not None:
        user = models.ForeignKey(User, on_delete=_user_delete_behavior, null=True, blank=True)
    else:
        user = models.ForeignKey(User, null=True, blank=True)


class LineItemBase(models.Model):
    """
    Abstract Base Class for a single line item in a purchase.

    An abstract base class is used here because of limitations in how
    inheritance in django works. If LineItem was created with a ForeignKey to
    cart and RecurringLineItem was subclassed, then cart.lineitems.all()
    would always return a list of LineItem, NOT a list of LineItem and
    RecurringLineItem. Therefore, we share common implementation details
    through the base class.
    http://stackoverflow.com/questions/313054/django-admin-interface-does-not-use-subclasss-unicode
    """
    _sub_total = models.DecimalField("Sub total", max_digits=18, decimal_places=10)
    _total = models.DecimalField("Total", max_digits=18, decimal_places=2, default=Decimal("0.00"))
    description = models.TextField("Description", blank=True)
    discount = models.DecimalField("Item discount", max_digits=18, decimal_places=10, default=Decimal("0.00"))
    name = models.CharField("Item", max_length=100)
    notes = generic.GenericRelation("Note")
    ordering = models.PositiveIntegerField("Ordering", default=0)
    quantity = models.PositiveIntegerField("Quantity")
    sku = models.CharField("SKU", max_length=255, default="1", db_index=True)
    digital_description = models.CharField("Digital Description", max_length=255, blank=True, null=True, default=None)

    class Meta:
        abstract = True
        ordering = ("ordering",)

    def __unicode__(self):
        return "%s - %d" % (self.name, self.total)

    def _recalc(self):
        """Recalculate totals"""
        self._sub_total = self.sub_total
        self._total = self.total

    def clone(self, newcart):
        """Clone this cart in the OPEN state."""
        dupe = copy.copy(self)
        # This method only works when id and pk have been cleared
        dupe.pk = None
        dupe.id = None
        dupe.cart = newcart
        dupe.save()
        return dupe

    def save(self, *args, **kwargs):
        """Override save to recalc before saving."""
        self._recalc()
        super(LineItemBase, self).save(*args, **kwargs)

    @property
    def sub_total(self):
        raise NotImplementedError()

    @property
    def total(self):
        raise NotImplementedError()


class OneTimeLineItemBase(LineItemBase):
    """Base class for line items that do not recur, for external apps to inherit"""

    unit_price = models.DecimalField("Unit price", max_digits=18, decimal_places=10)

    class Meta:
        abstract = True

    @property
    def sub_total(self):
        """Subtotal, calculated as price * quantity."""
        return self.quantity * self.unit_price

    @property
    def total(self):
        """Total, calculated as sub_total - discount."""
        return self.sub_total - self.discount


@HiiCart.register_lineitem_type()
class LineItem(OneTimeLineItemBase):
    """A single line item in a purchase."""
    cart = models.ForeignKey(HiiCart, verbose_name="Cart")


class RecurringLineItemBase(LineItemBase):
    """Base class for line items that recur, for external apps to inherit from"""

    duration = models.PositiveIntegerField("Duration", help_text="Length of each billing cycle", null=True, blank=True)
    duration_unit = models.CharField("Duration Unit", max_length=5, choices=SUBSCRIPTION_UNITS, default="DAY", null=False)
    is_active = models.BooleanField("Is Currently Subscribed", default=False, db_index=True)
    payment_token = models.CharField("Recurring Payment Token", max_length=256, null=True)
    recurring_price = models.DecimalField("Recurring Price", default=Decimal("0.00"), max_digits=18, decimal_places=2)
    recurring_shipping = models.DecimalField("Recurring Shipping Price", default=Decimal("0.00"), max_digits=18, decimal_places=2)
    recurring_times = models.PositiveIntegerField("Recurring Times", help_text="Number of payments which will occur at the regular rate.  (optional)", default=0)
    recurring_start = models.DateTimeField(null=True, blank=True)  # Allows delayed start to subscription.
    trial = models.BooleanField("Trial?", default=False)
    trial_price = models.DecimalField("Trial Price", default=Decimal("0.00"), max_digits=18, decimal_places=2)
    trial_length = models.PositiveIntegerField("Trial length", default=0)
    trial_times = models.PositiveIntegerField("Trial Times", help_text="Number of trial cycles", default=1)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        self.hiicart_settings = hiicart_settings
        super(RecurringLineItemBase, self).__init__(*args, **kwargs)

    @property
    def sub_total(self):
        """Subtotal, calculated as price * quantity."""
        return self.quantity * self.recurring_price

    @property
    def total(self):
        """Total, calculated as sub_total - discount + shipping."""
        return self.sub_total - self.discount + self.recurring_shipping

    def get_expiration(self):
        """Expiration/next billing date for item."""
        delta = self.expiration_delta
        payments = self.cart.payments.filter(
                state="PAID", amount__gt=0).order_by("-created")
        if not payments:
            if self.recurring_start:
                last_payment = self.recurring_start - delta
            else:
                return self.cart.created
        else:
            last_payment = payments[0].created
        return last_payment + delta

    @property
    def expiration_delta(self):
        delta = None
        if self.duration_unit == "DAY":
            delta = relativedelta(days=self.duration)
        elif self.duration_unit == "MONTH":
            delta = relativedelta(months=self.duration)
        return delta

    def is_expired(self, grace_period=None):
        """Get subscription expiration based on last payment optionally providing a grace period."""
        if grace_period:
            return timezone.now() > self.get_expiration() + grace_period
        elif self.hiicart_settings["EXPIRATION_GRACE_PERIOD"]:
            return timezone.now() > self.get_expiration() + self.hiicart_settings["EXPIRATION_GRACE_PERIOD"]


@HiiCart.register_lineitem_type(recurring=True)
class RecurringLineItem(RecurringLineItemBase):
    """
    Extra information needed for a recurring item, such as a subscription.

    To make a trial, put the trial price, tax, etc. into the parent LineItem,
    and mark this object trial=True, trial_length=xxx
    """
    cart = models.ForeignKey(HiiCart, verbose_name="Cart")


class PaymentMetaclass(models.base.ModelBase):
    # TODO: this `payment_state_changed` signal absolutely does not need to be
    # tacked onto the payment base classes as a weird meta attribute;  we should
    # define all signals sent by hiicart in a hiicart.signals module with
    # appropriate documentation
    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, PaymentBase)]
            attrs['payment_state_changed'] = Signal(providing_args=["payment", "new_state",
                                                                    "old_state"])
        except NameError:
            # This is PaymentBase
            parents = False
        new_class = super(PaymentMetaclass, cls).__new__(cls, name, bases, attrs)
        return new_class


class PaymentBase(models.Model):
    __metaclass__ = PaymentMetaclass

    amount = models.DecimalField("amount", max_digits=18, decimal_places=2)
    gateway = models.CharField("Payment Gateway", max_length=25, blank=True)
    notes = generic.GenericRelation("Note")
    state = models.CharField(max_length=16, choices=PAYMENT_STATES)
    created = models.DateTimeField("Created", auto_now_add=True)
    last_updated = models.DateTimeField("Last Updated", auto_now=True)
    transaction_id = models.CharField("Transaction ID", max_length=45, db_index=True, blank=True, null=True)

    class Meta:
        abstract = True
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __init__(self, *args, **kwargs):
        """Override in order to keep track of changes to state."""
        super(PaymentBase, self).__init__(*args, **kwargs)
        self._old_state = self.state

    def __unicode__(self):
        if self.id is not None:
            return u"#%i $%s %s %s" % (self.id, self.amount,
                                       self.state, self.created)
        else:
            return u"(unsaved) $%s %s" % (self.amount, self.state)

    def save(self, *args, **kwargs):
        super(PaymentBase, self).save(*args, **kwargs)
        logger.warn('Payment saved %s => %s for payment_id: %s' % (self._old_state, self.state, self.id))
        # Signal sent after save in case someone queries database
        if self.state != self._old_state:
            self.payment_state_changed.send(sender=self.__class__.__name__, payment=self,
                                            old_state=self._old_state,
                                            new_state=self.state)
            self._old_state = self.state


@HiiCartBase.set_payment_class
class Payment(PaymentBase):
    cart = models.ForeignKey(HiiCart, related_name="payments")


class Note(models.Model):
    """General note that can be attached to a cart, lineitem, or payment."""
    content_object = generic.GenericForeignKey()
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    text = models.TextField("Note")

    def __unicode__(self):
        return self.text


class PaymentResponse(models.Model):
    """Store the result of a payment attempt."""
    cart = models.ForeignKey(HiiCart, related_name="payment_results")
    response_code = models.PositiveIntegerField()
    response_text = models.TextField()
