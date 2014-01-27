#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import  # Fix conflicting stripe module names
import logging

import json
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from hiicart.utils import format_exceptions, format_data


logger = logging.getLogger("hiicart.gateway.stripe")


@csrf_exempt
@format_exceptions
@never_cache
def ipn(request):
    """
    Stripe Webhook Handler
    """
    if request.method != "POST":
        logger.error("IPN Request not POSTed")
        return HttpResponseBadRequest("Requests must be POSTed")

    data = json.loads(request.raw_post_data)
    logger.info("IPN Received:\n%s" % format_data(data))

    # Charges are handled synchronously, so no need to do anything with webhook
    # data at this time. Eventually, we will want to listen to the following events
    # that aren't triggered by a UI action:
    #   charge.disputed
    #   charge.refunded
    #   invoice.payment_succeeded (for subscriptions)
    #   invoice.payment_failed (for subscriptions)

    return HttpResponse()
