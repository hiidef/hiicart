from django.conf.urls import patterns

urlpatterns = patterns('',
    (r'cbui/?$', 'hiicart.gateway.amazon.views.cbui'),
    (r'ipn/?$', 'hiicart.gateway.amazon.views.ipn'),
)
