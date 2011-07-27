from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_view_exempt
from django.http import HttpResponseRedirect
from hiicart.gateway.paypal_express.gateway import PaypalExpressCheckoutGateway
from hiicart.gateway.paypal_express.ipn import PaypalExpressCheckoutIPN
from hiicart.gateway.paypal.views import _base_paypal_ipn_listener
from hiicart.utils import format_exceptions, cart_by_uuid

def _find_cart(request_data):
    uuid = request_data["cart"]
    return cart_by_uuid(uuid)

@never_cache
def get_details(request):
    token = request.session.get('hiicart_paypal_express_token')
    # If token wasn't saved in the session, Paypal may have passed it as a query param
    if not token:
        token = request.GET['token']
    cart = _find_cart(request.GET)
    if cart:
        gateway = PaypalExpressCheckoutGateway(cart)

        result = gateway.get_details(token)
        
        request.session.update(result.session_args)

    return HttpResponseRedirect(result.url)

@never_cache
def finalize(request):
    token = request.session.get('hiicart_paypal_express_token')
    payerid = request.session.get('hiicart_paypal_express_payerid')
    cart = _find_cart(request.GET)
    if cart:
        gateway = PaypalExpressCheckoutGateway(cart)

        result = gateway.finalize(token, payerid)

    return HttpResponseRedirect(result.url)


@csrf_view_exempt
@format_exceptions
@never_cache
def ipn(request):
    return _base_paypal_ipn(request, PaypalExpressCheckoutIPN)
