from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'ipn/?$', 'hiicart.gateway.authorizenet.views.ipn'),
)
