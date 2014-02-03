#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from hiicart.gateway.paypal_express.gateway import PaypalExpressCheckoutGateway
from hiicart.gateway.paypal_express.ipn import PaypalExpressCheckoutIPN
from hiicart.gateway.paypal.views import _base_paypal_ipn_listener
from hiicart.utils import format_exceptions, cart_by_uuid
from hiicart.gateway.base import GatewayError


def _find_cart(request):
    request_data = request.GET
    uuid = request_data.get('cart') or request.session.get('hiicart_cart_uuid')
    cart = cart_by_uuid(uuid)
    if not cart:
        raise GatewayError("Paypal Express Checkout: Unknown transaction with cart uuid %s" % uuid)
    return cart


@never_cache
def get_details(request):
    token = request.GET.get('token', None)
    if not token:
        token = request.session.get('hiicart_paypal_express_token')
    cart = _find_cart(request)
    gateway = PaypalExpressCheckoutGateway(cart)
    result = gateway.get_details(token)
    request.session.update(result.session_args)

    return HttpResponseRedirect(result.url)


@never_cache
def finalize(request):
    token = request.GET.get('token', None)
    if not token:
        token = request.session.get('hiicart_paypal_express_token')
    payerid = request.GET.get('PayerID', None)
    if not payerid:
        payerid = request.session.get('hiicart_paypal_express_payerid')
    cart = _find_cart(request)
    gateway = PaypalExpressCheckoutGateway(cart)
    result = gateway.finalize(token, payerid)

    return HttpResponseRedirect(result.url)


@csrf_exempt
@format_exceptions
@never_cache
def ipn(request):
    return _base_paypal_ipn_listener(request, PaypalExpressCheckoutIPN)
