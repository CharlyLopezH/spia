from django.urls import path
from . import views

app_name = 'empleados'

urlpatterns = [
    path('', views.lista_empleados, name='lista'),
    path('crear/', views.crear_empleado, name='crear'),
    path('<int:pk>/editar/', views.editar_empleado, name='editar'),
    path('<int:pk>/eliminar/', views.eliminar_empleado, name='eliminar'),
]