import base
from hiicart.gateway.paypal_express.gateway import PaypalExpressCheckoutGateway

STORE_SETTINGS = {
        'API_USERNAME': 'sdk-three_api1.sdk.com',
        'API_PASSWORD': 'QFZCWN5HZM8VBG7Q',
        'API_SIGNATURE': 'A-IzJhZZjhg29XQ2qnhapuwxIDzyAZQ92FRP5dqBzVesOkzbdUONzmOU',
        'RETURN_URL': 'http://goodsietest.com/return_url',
        'CANCEL_URL': 'http://goodsietest.com/cancel_url',
        'FINALIZE_URL': 'http://goodsietest.com/finalize_url',
        'COMPLETE_URL': 'http://goodsietest.com/complete_url'
        }


class PaypalExpressCheckoutTestCase(base.HiiCartTestCase):
    """Paypal Express Checkout tests"""

    def test_submit(self):
        """Submit a cart to express checkout."""
        self.cart.hiicart_settings.update(STORE_SETTINGS)
        self.assertEquals(self.cart.state, "OPEN")
        result = self.cart.submit("paypal_express", False, {'request': None})
        self.assertEqual(result.type, "url")
        self.assertNotEqual(result.url, None)
        self.assertEqual(self.cart.state, "SUBMITTED")

    def test_submit_recurring(self):
        """Test submitting a cart with recurring items to express checkout"""
        self.cart.hiicart_settings.update(STORE_SETTINGS)
        self._add_recurring_item()
        self.assertEquals(self.cart.state, "OPEN")
        result = self.cart.submit("paypal_express", False, {'request': None})
        self.assertEqual(result.type, "url")
        self.assertEqual(self.cart.state, "SUBMITTED")

        token = result.session_args['hiicart_paypal_express_token']
        self.assertNotEqual(token, None)

    def test_update_cart_details(self):
        pp_params = {
            'PAYMENTREQUEST_0_SHIPTONAME': 'Dmitri Shostakovich',
            'PAYMENTREQUEST_0_SHIPTOSTREET': '321 Blast Off Lane',
            'PAYMENTREQUEST_0_SHIPTOSTREET2': 'Apt 456',
            'PAYMENTREQUEST_0_SHIPTOCITY': 'New Moscow',
            'PAYMENTREQUEST_0_SHIPTOSTATE': 'AK',
            'PAYMENTREQUEST_0_SHIPTOZIP': '90210',
            'PAYMENTREQUEST_0_SHIPTOCOUNTRYCODE': 'US'
        }

        self.cart.hiicart_settings.update(STORE_SETTINGS)
        gateway = PaypalExpressCheckoutGateway(self.cart)

        gateway._update_cart_details(pp_params)

        self.assertEqual(self.cart.ship_first_name, 'Dmitri')
        self.assertEqual(self.cart.ship_last_name, 'Shostakovich')
        self.assertEqual(self.cart.ship_street1, '321 Blast Off Lane')
        self.assertEqual(self.cart.ship_street2, 'Apt 456')
        self.assertEqual(self.cart.ship_city, 'New Moscow')
        self.assertEqual(self.cart.ship_state, 'AK')
        self.assertEqual(self.cart.ship_postal_code, '90210')
        self.assertEqual(self.cart.ship_country, 'US')
