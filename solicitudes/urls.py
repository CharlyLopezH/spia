from django.urls import path
from django.http import HttpResponse
from . import views

app_name = 'solicitudes'

def en_construccion(request):
    return HttpResponse("Módulo de solicitudes en construcción (Fase B).")

urlpatterns = [
    path('', en_construccion, name='lista'),
    path('', views.lista_solicitudes, name='lista'),
    path('crear/', views.crear_solicitud, name='crear'),
]