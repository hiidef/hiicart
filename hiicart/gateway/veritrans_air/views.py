#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

import logging
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from hiicart.gateway.base import GatewayError
from hiicart.gateway.veritrans_air.ipn import VeritransAirIPN
from hiicart.utils import format_exceptions, cart_by_id, format_data
from urllib import unquote_plus
from urlparse import parse_qs


logger = logging.getLogger("hiicart.gateway.veritrans_air")


def _find_cart(data):
    # invoice may have a suffix due to retries
    order = data.get('orderId')
    if not order:
        logger.warn("No orderId # in data, aborting IPN")
        return None
    return cart_by_id(order)


@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    """
    Veritrans Air IPN

    Confirms that payment has been completed and marks invoice as paid.
    """
    if request.method != "POST":
        logger.error("IPN Request not POSTed")
        return HttpResponse("ERR")

    data = request.POST.copy()
    logger.info("IPN Received:\n%s" % format_data(data))
    cart = _find_cart(data)
    if not cart:
        logger.error("veritrans air gateway: Unknown transaction: %s" % data)
        return HttpResponse("ERR")
    handler = VeritransAirIPN(cart)
    # Verify the data with Veritrans
    if not handler.confirm_ipn_data(data):
        logger.error("Veritrans Air IPN Confirmation Failed.")
        return HttpResponse("ERR")

    status = data["mStatus"]
    result_code = data["vResultCode"]
    msg = data["mErrMsg"]

    if status == 'success':
        handler.accept_payment(data)
    elif status == 'pending':
        handler.payment_pending(data)

    return HttpResponse("OK")
