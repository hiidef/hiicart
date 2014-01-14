#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Paypal Views"""

import logging
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from hiicart.gateway.base import GatewayError
from hiicart.gateway.paypal.ipn import PaypalIPN
from hiicart.utils import format_exceptions, cart_by_uuid, format_data
from urllib import unquote_plus
from urlparse import parse_qs


logger = logging.getLogger("hiicart.gateway.paypal")


def _find_cart(data):
    # invoice may have a suffix due to retries
    invoice = data.get('invoice') or data.get('item_number') or data.get('rp_invoice_id')
    if not invoice:
        logger.warn("No invoice # in data, aborting IPN")
        return None
    return cart_by_uuid(invoice[:36])


def _base_paypal_ipn_listener(request, ipn_class):
    """
    PayPal IPN (Instant Payment Notification)
    Shared between Paypal and Paypal Express Checkout

    Confirms that payment has been completed and marks invoice as paid.
    Adapted from IPN cgi script provided at:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/456361
    """
    if request.method != "POST":
        logger.error("IPN Request not POSTed")
        return HttpResponseBadRequest("Requests must be POSTed")

    data = request.POST.copy()
    logger.info("IPN Received:\n%s" % format_data(data))
    # Verify the data with Paypal
    cart = _find_cart(data)
    if not cart:
        logger.error("paypal gateway: Unknown transaction: %s" % data)
        return HttpResponse()
    handler = ipn_class(cart)
    if not handler.confirm_ipn_data(request.raw_post_data):
        logger.error("Paypal IPN Confirmation Failed.")
        raise GatewayError("Paypal IPN Confirmation Failed.")
    # Paypal defaults to cp1252, because it hates you
    # So, if we end up with the unicode char that means
    # "unknown char" (\ufffd), try to transcode from cp1252
    parsed_raw = parse_qs(request.raw_post_data)
    for key, value in data.iteritems():
        if u'\ufffd' in value:
            try:
                data.update({key: unicode(unquote_plus(parsed_raw[key][-1]), 'cp1252')})
            except:
                # Fallback to shift-jis if cp1252 fails
                try:
                    data.update({key: unicode(unquote_plus(parsed_raw[key][-1]), 'shift-jis')})
                except:
                    pass
    txn_type = data.get("txn_type", "")
    status = data.get("payment_status", "unknown")
    if txn_type == "subscr_cancel" or txn_type == "subscr_eot":
        handler.cancel_subscription(data)
    elif txn_type == "subscr_signup":
        handler.activate_subscription(data)
    elif status == "Completed":
        handler.accept_payment(data)
    elif status == "Refunded":
        handler.payment_refunded(data)
    elif status == "Pending":
        if hasattr(handler, "payment_pending"):
            handler.payment_pending(data)
        else:
            logger.info("Unknown IPN type or status. Type: %s\tStatus: %s\nHandler: %r" %
                 (txn_type, status, handler))
    else:
        logger.info("Unknown IPN type or status. Type: %s\tStatus: %s" %
                 (txn_type, status))
    return HttpResponse()


@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    return _base_paypal_ipn_listener(request, PaypalIPN)
