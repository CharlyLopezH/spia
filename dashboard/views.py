from datetime import date

from django.shortcuts import render
from django.utils import timezone

from empleados.models import Empleado
from movimientos.models import MovimientoDia
from solicitudes.models import Solicitud


def inicio(request):
    """
    Dashboard principal de SPIA.

    Muestra:
    - Indicadores: empleados activos, movimientos del mes, solicitudes pendientes.
    - Últimos 10 movimientos registrados.
    - Accesos rápidos a las acciones más comunes.
    """
    hoy = timezone.now().date()

    # Indicadores
    total_empleados_activos = Empleado.objects.filter(estado='activo').count()
    movimientos_del_mes = MovimientoDia.objects.filter(
        fecha__year=hoy.year,
        fecha__month=hoy.month,
    ).count()
    solicitudes_pendientes = Solicitud.objects.filter(estado='pendiente').count()

    # Últimos movimientos (orden del modelo: -fecha, -id)
    ultimos_movimientos = (
        MovimientoDia.objects
        .select_related('fk_empleado', 'fk_concepto')
        .order_by('-fecha', '-id')[:10]
    )

    return render(request, 'dashboard/inicio.html', {
        'hoy': hoy,
        'total_empleados_activos': total_empleados_activos,
        'movimientos_del_mes': movimientos_del_mes,
        'solicitudes_pendientes': solicitudes_pendientes,
        'ultimos_movimientos': ultimos_movimientos,
    })