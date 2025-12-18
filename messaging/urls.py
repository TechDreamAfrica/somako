from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('thread/', views.message_thread, name='thread'),
    path('send/', views.send_message, name='send'),
]
