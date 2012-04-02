__version__ = '0.3.7'


def validate_gateway(gateway):
    """Test that a gateway is correctly set up.
    Returns True if successful, or an error message."""
    from hiicart.gateway.base import GatewayError
    from hiicart.gateway.amazon.gateway import AmazonGateway
    from hiicart.gateway.google.gateway import GoogleGateway
    from hiicart.gateway.paypal.gateway import PaypalGateway
    from hiicart.gateway.paypal2.gateway import Paypal2Gateway
    from hiicart.gateway.paypal_adaptive.gateway import PaypalAPGateway
    from hiicart.gateway.braintree.gateway import BraintreeGateway
    from hiicart.gateway.authorizenet.gateway import AuthorizeNetGateway
    from hiicart.gateway.paypal_express.gateway import PaypalExpressCheckoutGateway
    gateways = {
        'amazon': AmazonGateway,
        'google': GoogleGateway,
        'paypal': PaypalGateway,
        'paypal2': Paypal2Gateway,
        'paypal_adaptive': PaypalAPGateway,
        'paypal_express': PaypalExpressCheckoutGateway,
        'braintree': BraintreeGateway,
        'authorizenet': AuthorizeNetGateway
        }
    try:
        cls = gateways[gateway]
        obj = cls()
        return obj._is_valid() or "Authentication Error"
    except GatewayError, err:
        return err.message

