import hiicart.gateway.amazon.urls
import hiicart.gateway.google.urls
import hiicart.gateway.paypal.urls
import hiicart.gateway.paypal2.urls
import hiicart.gateway.paypal_adaptive.urls
import hiicart.gateway.authorizenet.urls
import hiicart.gateway.paypal_express.urls
import hiicart.gateway.veritrans_air.urls

from django.conf.urls import patterns, include

urlpatterns = patterns('',
    (r'complete/?$',                'hiicart.views.complete'),
    (r'^amazon/',                   include(hiicart.gateway.amazon.urls)),
    (r'^google/',                   include(hiicart.gateway.google.urls)),
    (r'^paypal/',                   include(hiicart.gateway.paypal.urls)),
    (r'^paypal2/',                  include(hiicart.gateway.paypal2.urls)),
    (r'^paypal_adaptive/',          include(hiicart.gateway.paypal_adaptive.urls)),
    (r'^paypal_express/',           include(hiicart.gateway.paypal_express.urls)),
    (r'^veritrans_air/',            include(hiicart.gateway.veritrans_air.urls)),
    (r'^authorizenet/',             include(hiicart.gateway.authorizenet.urls)),
)
