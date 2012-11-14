HiiCart - Django Shopping Cart
===============================

A simple shopping cart implementation with support for PayPal,
Google Checkout, Amazon Payments, Authorize.net, and Braintree.


Installation and Setup
----------------------

Installation is as easy as installing with `easy_install` or `pip` and
adding the appropriate settings for the gateways you want to use.  Please see
the documentation in hiicart/settings.py for more details about the settings
available.

Once set up, create LineItem and HiiCart objects to submit payments:

    def foo():
        cart = HiiCart.objects.create() 
        LineItem.objects.create(
            cart=cart, description="foo", name="bar",
            quantity=1, sku="12345", thankyou="thanks!",
            unit_price=9.99)
        return cart.submit("google")

This returns an object containing the redirect URL for you user.

Logging
--------

Older versions of HiiCart used to have logging configurable through the
`HIICART_SETTINGS` object's `LOG` and `LOG_LEVEL` keys.  This has been removed
in favor of using [Django's built-in logging configuration](https://docs.djangoproject.com/en/dev/topics/logging/#an-example)
or manual configuration of the "hiicart" logger elsewhere in application code.

To maintain the same configuration as old versions of HiiCart, use something
similar to the following in your `settings.py`:

```python
LOGGING = {
    ...
    "formatters": {
        ...
        "hiicart": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
        },
    },
    "handlers": {
        ...
        "hiicart": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": ...,
            "formatter": "hiicart",
            "maxBytes": 5242880,
            "backupCount": 10,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        ...
        "hiicart": {
            "handlers": ["hiicart"],
            "level": "DEBUG",
        },
    },
}
```

HiiCart will aggressively log events and IPN requests to this log in at the INFO
level and errors at the ERROR level.

Testing
-------

HiiCart is testable via Django's test runner.  To run the tests, simply run

```
python manage.py test hiicart
```

Some tests might not run without valid gateway configuration, which you can
add to a `local_settings.py` file if running the tests from a hiicart checkout
or to your regular settings if running from your django project.

Example App
-----------

An example app is included that shows very generally how to get everything set
up and working. Right now it really needs a lot of work, but is functional for
the most basic case.
