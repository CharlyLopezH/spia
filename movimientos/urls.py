from django.urls import path
from . import views

app_name = 'movimientos'

urlpatterns = [
    path('kardex/', views.kardex_index, name='kardex_index'),
    path('kardex/<int:empleado_id>/', views.kardex_empleado, name='kardex'),
    path('kardex/<int:empleado_id>/<int:periodo>/',
         views.kardex_empleado, name='kardex_periodo'),
    path('disponer/<int:empleado_id>/<int:concepto_id>/',
         views.disponer_dias, name='disponer_dias'),    path('carga-inicial/', views.carga_inicial, name='carga_inicial'),
    path('carga-inicial/', views.carga_inicial, name='carga_inicial'),         
    path('asignacion-discrecional/', views.asignacion_discrecional,name='asignacion_discrecional'),
    path('registrar-acumulacion/', views.registrar_acumulacion,name='registrar_acumulacion'),
    # Calendario
    path('calendario/<int:empleado_id>/', views.calendario_empleado,
         name='calendario_empleado'),
    path('calendario/<int:empleado_id>/<int:anio>/<int:mes>/',
         views.calendario_empleado, name='calendario_empleado_mes'),    
]