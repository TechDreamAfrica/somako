"""
Payment URLs
"""
from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('initiate/', views.initiate_payment, name='initiate'),
    path('callback/', views.payment_callback, name='callback'),
    path('success/<uuid:payment_id>/', views.payment_success, name='payment_success'),
    path('failed/<uuid:payment_id>/', views.payment_failed, name='payment_failed'),
    path('history/', views.payment_history, name='history'),
    path('webhook/', views.paystack_webhook, name='webhook'),
    path('verify/<str:reference>/', views.verify_payment, name='verify'),
]
