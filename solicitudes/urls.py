from django.urls import path
from django.http import HttpResponse
from . import views

app_name = 'solicitudes'

urlpatterns = [
    path('', views.lista_solicitudes, name='lista'),
    path('crear/', views.crear_solicitud, name='crear'),
    path('<int:pk>/', views.detalle_solicitud, name='detalle'),
    
    # Nuevas rutas de acción
    path('<int:pk>/aprobar/', views.aprobar_solicitud, name='aprobar'),
    path('<int:pk>/aplicar/', views.aplicar_solicitud, name='aplicar'),
    path('<int:pk>/cancelar/', views.cancelar_solicitud, name='cancelar'),
]