import logging

from django.http import HttpResponseRedirect, HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from django.shortcuts import render_to_response
from hiicart.gateway.base import GatewayError
from hiicart.gateway.authorizenet.ipn import AuthorizeNetIPN
from hiicart.gateway.authorizenet.gateway import AuthorizeNetGateway
from hiicart.utils import format_exceptions, cart_by_uuid
from urllib import unquote_plus
from urlparse import parse_qs


log = logging.getLogger("hiicart.gateway.authorizenet")


def _find_cart(data):
    return cart_by_uuid(data['cart_id'])


@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    """
    Authorize.net Payment Notification
    """
    if request.method != "POST":
        return HttpResponse("Requests must be POSTed")
    data = request.POST.copy()
    # Authorize sends us info urlencoded as latin1
    # So, if we end up with the unicode char in our processed POST that means
    # "unknown char" (\ufffd), try to transcode from latin1
    parsed_raw = parse_qs(request.raw_post_data)
    for key, value in data.iteritems():
        if u'\ufffd' in value:
            try:
                data.update({key: unicode(unquote_plus(parsed_raw[key][-1]), 'latin1')})
            except:
                pass
    log.info("IPN Notification received from Authorize.net: %s" % data)
    try:
        log.info("IPN Notification received from Authorize.net (raw): %s" % request.raw_post_data)
    except:
        pass
    cart = _find_cart(data)
    if not cart:
        raise GatewayError('Authorize.net gateway: Unknown transaction')
    handler = AuthorizeNetIPN(cart)
    if not handler.confirm_ipn_data(data):
        log.error("Authorize.net IPN Confirmation Failed.")
        raise GatewayError("Authorize.net IPN Confirmation Failed.")
    handler.record_form_data(data)

    if data['x_response_code'] == '1':  # Approved
        handler.accept_payment(data)

    # Store payment result
    gateway = AuthorizeNetGateway(cart)
    gateway.set_response(data)

    # Return the user back to the store front
    response = render_to_response('gateway/authorizenet/ipn.html',
                                  {'return_url': data['return_url']})
    response['Location'] = data['return_url']
    return response
