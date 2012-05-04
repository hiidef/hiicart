import logging

from celery.decorators import task

from hiicart.models import HiiCart
from hiicart.gateway.braintree.ipn import BraintreeIPN

log = logging.getLogger('hiicart.gateway.braintree.tasks')


@task
def update_payment_status(hiicart_id, transaction_id, tries=0, cart_class=HiiCart):
    """Check the payment status of a Braintree transaction."""
    hiicart = cart_class.objects.get(pk=hiicart_id)
    handler = BraintreeIPN(hiicart)
    done = handler.update_order_status(transaction_id)
    # Reschedule the failed payment to run in 4 hours
    if not done:
        # After 18 tries (72 hours) we will void and fail the payment
        if tries >= 18:
            handler.void_order(transaction_id)
        else:
            tries = tries + 1
            update_payment_status.apply_async(args=[hiicart_id,
                                                    transaction_id,
                                                    tries,
                                                    cart_class],
                                              countdown=14400)
