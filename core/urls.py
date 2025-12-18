from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('downloads/', views.downloads, name='downloads'),
    path('download/apk/', views.download_apk, name='download_apk'),
]
