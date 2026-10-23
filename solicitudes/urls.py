from django.urls import path
from django.http import HttpResponse
from . import views

app_name = 'solicitudes'

urlpatterns = [
    path('', views.lista_solicitudes, name='lista'),
    path('crear/', views.crear_solicitud, name='crear'),
    path('<int:pk>/', views.detalle_solicitud, name='detalle'),
]