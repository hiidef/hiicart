from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'ipn/?$', 'hiicart.gateway.veritrans_air.views.ipn'),
)
