#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Paypal2 Gateway"""

# TODO: why is there one of these.

import logging
import urllib
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from hiicart.gateway.base import GatewayError
from hiicart.gateway.paypal2 import api
from hiicart.gateway.paypal2.ipn import Paypal2IPN
from hiicart.utils import format_exceptions, cart_by_uuid, format_data


logger = logging.getLogger("hiicart.gateway.paypal_adaptive")


def _find_cart(data):
    # invoice may have a suffix due to retries
    if 'invoice' in data:
        invoice = data['invoice']
    elif 'rp_invoice_id' in data:
        invoice = data['invoice']
    else:
        invoice = data['item_number']
    if not invoice:
        logger.warn("No invoice # in data, aborting IPN")
        return None
    return cart_by_uuid(invoice[:36])


# TODO: Move all the functions from ipn.py here. There's no real reason
#       for it to be in a separate file. It creates confusion when you
#       have an api.py and ipn.py. The same should happen in the other
#       gateways.


@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    """Instant Payment Notification ipn.

    There is currently not working documentation on Paypal's site
    for IPNs from the Adaptive Payments API.  This has been created using
    test messages from AP and knowledge from the web payments API."""
    if request.method != "POST":
        logger.error("IPN Request not POSTed")
        return HttpResponseBadRequest("Requests must be POSTed")
    data = request.POST
    logger.info("IPN Received:\n%s" % format_data(data))
    # Verify the data with Paypal
    cart = _find_cart(data)
    ipn = Paypal2IPN(cart)
    if not ipn.confirm_ipn_data(request.raw_post_data):
        logger.error("Paypal IPN Confirmation Failed.")
        raise GatewayError("Paypal IPN Confirmation Failed.")
    if "txn_type" in data: # Inidividual Tranasction IPN
        if data["txn_type"] == "cart":
            ipn.accept_payment(data)
        elif data["txn_type"] == "recurring_payment_profile_created":
            ipn.recurring_payment_profile_created(data)
        elif data["txn_type"] == "recurring_payment":
            ipn.accept_recurring_payment(data)
        elif data["txn_type"] == "recurring_payment_profile_cancel":
            ipn.recurring_payment_profile_cancelled(data)
        else:
            logger.info("Unknown txn_type: %s" % data["txn_type"])
    else: #dunno
        logger.error("transaction_type not in IPN data.")
        raise GatewayError("transaction_type not in IPN.")
    return HttpResponse()


@csrf_view_exempt
@format_exceptions
@never_cache
def authorized(request):
    if "token" not in request.GET:
        raise Http404
    # I don't know if this actually works
    cart = _find_cart(request.GET)
    ipn = Paypal2IPN(cart)
    info = api.get_express_details(request.GET["token"], ipn.settings)
    params = request.GET.copy()
    params["cart"] = info["INVNUM"]
    url = "%s?%s" % (ipn.settings["RECEIPT_URL"], urllib.urlencode(params))
    return HttpResponseRedirect(url)


@csrf_view_exempt
@format_exceptions
@never_cache
def do_pay(request):
    if "token" not in request.POST or "PayerID" not in request.POST \
        or "cart" not in request.POST:
            raise GatewayError("Incorrect values POSTed to do_buy")
    cart = cart_by_uuid(request.POST["cart"])
    ipn = Paypal2IPN(cart)
    if len(cart.one_time_lineitems) > 0:
        api.do_express_payment(request.POST["token"], request.POST["PayerID"],
                               cart, ipn.settings)
    if len(cart.recurring_lineitems) > 0:
        api.create_recurring_profile(request.POST["token"],
                                     request.POST["PayerID"],
                                     cart, ipn.settings)
    # TODO: Redirect to HiiCart complete URL
    return HttpResponseRedirect("/")
