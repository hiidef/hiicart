#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Hiicart Utils"""

import logging
import traceback
from pprint import pformat
from django.http import HttpResponse, QueryDict
from hiicart.models import CART_TYPES

logger = logging.getLogger("hiicart")

def call_func(name, *args, **kwargs):
    """Call a function when all you have is the [str] name and arguments."""
    parts = name.split('.')
    module = __import__(".".join(parts[:-1]), fromlist=[parts[-1]])
    return getattr(module, parts[-1])(*args, **kwargs)


def format_exceptions(method):
    """
    Format exceptions into HttpResponse

    Useful in particular for Google Checkout's integration console.
    The default django error page is displayed as raw html, making
    debugging difficult.
    """
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except:
            fmt = traceback.format_exc()
            logger.error("Exception encountered: %s" % fmt)
            response = HttpResponse(fmt)
            response.status_code=500  # Definitely _not_ a 200 resposne
            return response
    return wrapper


def format_data(data):
    """Return data (request.GET or request.POST) as a formatted string for
    use in logging or recording exceptional request/responses."""
    format = lambda x: pformat(x, indent=4)
    try:
        if isinstance(data, QueryDict):
            if hasattr(data, "dict"):
                return format(data.dict())
            return format(dict(data.items()))
        return format(data)
    except:
        return str(data)


def cart_by_id(id):
    for Cart in CART_TYPES:
        try:
            return Cart.objects.get(pk=id)
        except Cart.DoesNotExist:
            pass


def cart_by_uuid(uuid):
    for Cart in CART_TYPES:
        try:
            return Cart.objects.get(_cart_uuid=uuid)
        except Cart.DoesNotExist:
            pass


def cart_by_email(email):
    for Cart in CART_TYPES:
        try:
            return Cart.objects.get(bill_email=email)
        except Cart.DoesNotExist:
            pass
    for Cart in CART_TYPES:
        try:
            return Cart.objects.get(ship_email=email)
        except Cart.DoesNotExist:
            pass
