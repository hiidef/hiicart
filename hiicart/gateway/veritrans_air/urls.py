import hiicart.gateway.veritrans_air.views

from django.conf.urls.defaults import *

urlpatterns = patterns('',  
    (r'ipn/?$',                                    'hiicart.gateway.veritrans_air.views.ipn'),
)
