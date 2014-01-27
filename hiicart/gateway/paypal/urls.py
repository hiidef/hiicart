from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'ipn/?$', 'hiicart.gateway.paypal.views.ipn'),
)
