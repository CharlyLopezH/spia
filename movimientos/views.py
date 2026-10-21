from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages

from empleados.models import Empleado
from catalogos.models import CatDiasConcepto

from .models import MovimientoDia
from .services import (
    saldo_actual,
    saldos_por_concepto,
    kardex,
    preview_otorgamiento,
    ejecutar_otorgamiento,
    preview_arrastre,
    ejecutar_arrastre,
    consumos_del_mes,
)

from .forms import DisponerDiasForm

from django.urls import reverse

from .services import (
    saldos_por_concepto,
    kardex,
    preview_otorgamiento,
    ejecutar_otorgamiento,
    preview_arrastre,
    ejecutar_arrastre,    
)

from .forms import (
    DisponerDiasForm,
    AsignacionDiscrecionalForm,
    RegistrarAcumulacionForm,
)

def kardex_index(request):
    """
    Pantalla de entrada: selector de empleado y periodo.
    """
    empleados = Empleado.objects.all().order_by('apellidos', 'nombres')
    periodo_actual = timezone.now().year
    periodos = _periodos_disponibles()

    return render(request, 'movimientos/kardex_index.html', {
        'empleados': empleados,
        'periodo_actual': periodo_actual,
        'periodos': periodos,
    })


def kardex_empleado(request, empleado_id, periodo=None):
    if periodo is None:
        periodo = timezone.now().year
    else:
        try:
            periodo = int(periodo)
        except (ValueError, TypeError):
            periodo = timezone.now().year

    empleado = get_object_or_404(Empleado, pk=empleado_id)

    # Conceptos a mostrar en las tarjetas: solo los que contabilizan
    conceptos_contables = CatDiasConcepto.objects.filter(
        activo=True,
        contabiliza=True,
    ).order_by('concepto')

    # Saldos reales por concepto (solo los que tienen movimientos)
    saldos_raw = saldos_por_concepto(empleado_id, periodo)
    saldos_por_id = {s['concepto_id']: s['saldo'] for s in saldos_raw}

    # Tarjetas: SOLO conceptos contabilizables
    tarjetas = []
    for c in conceptos_contables:
        tarjetas.append({
            'concepto': c,
            'saldo': saldos_por_id.get(c.id, 0),
            'tiene_movimientos': c.id in saldos_por_id,
        })

    # Movimientos: TODOS los del periodo (incluye eventuales)
    movimientos = kardex(empleado_id, periodo=periodo)

    # Total: solo suma los conceptos contabilizables
    total_disponible = sum(t['saldo'] for t in tarjetas)

    # Periodos para el selector
    periodos = _periodos_disponibles(empleado_id, incluir_actual=periodo)

    return render(request, 'movimientos/kardex.html', {
        'empleado': empleado,
        'periodo': periodo,
        'tarjetas': tarjetas,
        'movimientos': movimientos,
        'total_disponible': total_disponible,
        'periodos': periodos,
    })


def _periodos_disponibles(empleado_id=None, incluir_actual=None):
    """
    Devuelve una lista de periodos para el selector, ordenados descendente.
    Si se pasa empleado_id, incluye solo los periodos con movimientos de ese empleado
    más el periodo actual.
    """
    actual = timezone.now().year
    qs = MovimientoDia.objects.all()
    if empleado_id:
        qs = qs.filter(fk_empleado_id=empleado_id)

    periodos = set(qs.values_list('periodo', flat=True).distinct())
    periodos.add(actual)
    if incluir_actual:
        periodos.add(incluir_actual)

    return sorted(periodos, reverse=True)



def disponer_dias(request, empleado_id, concepto_id):
    """
    Pantalla para disponer días de una bolsa específica.

    El empleado y el concepto vienen por URL (desde el botón 'Disponer'
    en la tarjeta del kardex).

    Al enviar: crea N movimientos de consumo (uno por fecha).
    """
    empleado = get_object_or_404(Empleado, pk=empleado_id)
    concepto = get_object_or_404(CatDiasConcepto, pk=concepto_id)

    anio_actual = timezone.now().year
    saldo = saldo_actual(empleado.id, concepto.id, anio_actual)

    if request.method == 'POST':
        form = DisponerDiasForm(request.POST, empleado=empleado, concepto=concepto)
        if form.is_valid():
            movimientos = form.save(creado_por='rh')
            total = len(movimientos)

            messages.success(
                request,
                f'Se dispusieron {total} día(s) de {concepto.clave} para '
                f'{empleado.nombres} {empleado.apellidos}.'
            )
            return redirect(
                'movimientos:kardex_periodo',
                empleado_id=empleado.id,
                periodo=anio_actual,
            )
    else:
        form = DisponerDiasForm(empleado=empleado, concepto=concepto)

    # Verificar que el campo del formulario esté limpio
    return render(request, 'movimientos/disponer_dias.html', {
        'empleado': empleado,
        'concepto': concepto,
        'saldo': saldo,
        'anio_actual': anio_actual,
        'form': form,
    })


def carga_inicial(request):
    """
    Pantalla para ejecutar la carga inicial del periodo.

    Procesos:
    1. Otorgamientos por derecho (ECO, CUM, VAC, etc.).
    2. Arrastre de vacaciones no disfrutadas del periodo anterior (VAC → VAP).

    GET:  muestra el formulario con los conceptos y el preview del arrastre.
    POST: ejecuta ambos procesos.
    """
    periodo_actual = timezone.now().year

    if request.method == 'POST':
        periodo = request.POST.get('periodo', periodo_actual)
        try:
            periodo = int(periodo)
        except (ValueError, TypeError):
            periodo = periodo_actual

        periodo_anterior = periodo - 1

        # Verificar confirmación
        confirmado = request.POST.get('confirmar') == 'on'
        if not confirmado:
            messages.error(
                request,
                'Debes marcar la casilla de confirmación para ejecutar la carga.'
            )
            return redirect('movimientos:carga_inicial')

        # ¿Se debe aplicar arrastre?
        aplicar_arrastre = request.POST.get('aplicar_arrastre') == 'on'

        # --- Proceso 1: Otorgamientos ---
        resultado_otorg = ejecutar_otorgamiento(
            periodo=periodo,
            creado_por='admin_web',
        )

        # --- Proceso 2: Arrastre (si se pidió) ---
        resultado_arrastre = None
        if aplicar_arrastre:
            resultado_arrastre = ejecutar_arrastre(
                periodo_anterior=periodo_anterior,
                periodo_actual=periodo,
                creado_por='admin_web',
            )

        # --- Mensaje de resultado ---
        total_creados = resultado_otorg['creados']
        total_omitidos = resultado_otorg['omitidos']
        total_dias = resultado_otorg['total_dias']

        if resultado_arrastre:
            total_creados += resultado_arrastre['creados']
            total_omitidos += resultado_arrastre['omitidos']
            total_dias += resultado_arrastre['dias_totales']

        if total_creados == 0 and total_omitidos > 0:
            messages.warning(
                request,
                f'No se crearon movimientos nuevos. '
                f'{total_omitidos} ya existían (la carga del periodo {periodo} '
                f'ya se había ejecutado antes).'
            )
        else:
            mensaje = (
                f'Carga inicial ejecutada para el periodo {periodo}: '
                f'{resultado_otorg["creados"]} otorgamientos'
            )
            if resultado_arrastre:
                mensaje += (
                    f' + {resultado_arrastre["creados"]} arrastres'
                )
            mensaje += (
                f' creados. '
                f'{total_omitidos} omitidos. '
                f'{total_dias} días otorgados en total.'
            )
            messages.success(request, mensaje)

        # Redirigir al resultado
        return redirect(f"{reverse('movimientos:carga_inicial')}?periodo={periodo}")

    # --- GET ---
    periodo_str = request.GET.get('periodo', periodo_actual)
    try:
        periodo = int(periodo_str)
    except (ValueError, TypeError):
        periodo = periodo_actual

    periodo_anterior = periodo - 1

    preview_otorg = preview_otorgamiento(periodo)
    preview_arrast = preview_arrastre(periodo_anterior, periodo)

    return render(request, 'movimientos/carga_inicial.html', {
        'periodo': periodo,
        'periodo_anterior': periodo_anterior,
        'periodo_actual': periodo_actual,
        'preview': preview_otorg,
        'arrastre': preview_arrast,
    })

def asignacion_discrecional(request):
    """
    Pantalla para asignar días a un empleado de forma discrecional.

    Crea un movimiento de tipo 'asignacion' con signo positivo.
    Sin validación de saldo: la asignación suma, no consume.
    """
    if request.method == 'POST':
        form = AsignacionDiscrecionalForm(request.POST)
        if form.is_valid():
            movimiento = form.save(creado_por='rh')
            messages.success(
                request,
                f'Se asignaron {movimiento.dias} día(s) de '
                f'{movimiento.fk_concepto.clave} a '
                f'{movimiento.fk_empleado.nombres} {movimiento.fk_empleado.apellidos}.'
            )
            return redirect(
                'movimientos:kardex_periodo',
                empleado_id=movimiento.fk_empleado_id,
                periodo=movimiento.periodo,
            )
    else:
        form = AsignacionDiscrecionalForm()

    return render(request, 'movimientos/asignacion_discrecional.html', {
        'form': form,
        'accion': 'Asignación discrecional',
    })
def registrar_acumulacion(request):
    """
    Pantalla para registrar la acumulación de días ganados por un evento
    periódico (típicamente puntualidad perfecta mensual).

    Crea un movimiento de tipo 'acumulacion' con signo positivo.
    El memo es obligatorio.
    """
    if request.method == 'POST':
        form = RegistrarAcumulacionForm(request.POST)
        if form.is_valid():
            movimiento = form.save(creado_por='rh')
            messages.success(
                request,
                f'Se acumularon {movimiento.dias} día(s) de '
                f'{movimiento.fk_concepto.clave} a '
                f'{movimiento.fk_empleado.nombres} {movimiento.fk_empleado.apellidos} '
                f'para el periodo {movimiento.periodo}.'
            )
            return redirect(
                'movimientos:kardex_periodo',
                empleado_id=movimiento.fk_empleado_id,
                periodo=movimiento.periodo,
            )
    else:
        form = RegistrarAcumulacionForm()

    return render(request, 'movimientos/registrar_acumulacion.html', {
        'form': form,
        'accion': 'Asignación de Puntualidad Perfecta ganada',
    })

def registrar_acumulacion(request):
    """
    Pantalla para registrar la acumulación de días ganados por un evento
    periódico (típicamente puntualidad perfecta mensual).

    Crea un movimiento de tipo 'acumulacion' con signo positivo.
    El memo es obligatorio.

    Si viene un empleado_id por GET, lo precarga en el formulario.
    """
    empleado_id = request.GET.get('empleado_id')

    if request.method == 'POST':
        form = RegistrarAcumulacionForm(request.POST)
        if form.is_valid():
            movimiento = form.save(creado_por='rh')
            messages.success(
                request,
                f'Se acumularon {movimiento.dias} día(s) de '
                f'{movimiento.fk_concepto.clave} a '
                f'{movimiento.fk_empleado.nombres} {movimiento.fk_empleado.apellidos} '
                f'para el periodo {movimiento.periodo}.'
            )
            return redirect(
                'movimientos:kardex_periodo',
                empleado_id=movimiento.fk_empleado_id,
                periodo=movimiento.periodo,
            )
    else:
        # Si viene empleado_id por GET, inicializar el campo
        initial = {}
        if empleado_id:
            initial['fk_empleado'] = empleado_id
        form = RegistrarAcumulacionForm(initial=initial)

    return render(request, 'movimientos/registrar_acumulacion.html', {
        'form': form,
        'accion': 'Registro de Puntualidad en el Periodo',
    })

import calendar
from datetime import date, timedelta


def calendario_empleado(request, empleado_id, anio=None, mes=None):
    """
    Muestra un calendario mensual con los consumos de un empleado.

    Navegable mes a mes, pero limitado al año del periodo (año actual).
    Arranca en el mes actual si no se especifica.
    """
    empleado = get_object_or_404(Empleado, pk=empleado_id)

    # Año del periodo (año actual por ahora)
    periodo_activo = timezone.now().year
    anio = periodo_activo if anio is None else int(anio)

    # Forzar el año al periodo activo (no se puede navegar fuera del periodo)
    if anio != periodo_activo:
        return redirect('movimientos:calendario_empleado', empleado_id=empleado.id)

    # Mes actual por defecto
    mes = timezone.now().month if mes is None else int(mes)

    # Forzar el mes al rango válido (1-12)
    if mes < 1:
        mes = 1
    elif mes > 12:
        mes = 12

    # Obtener los consumos del mes
    consumos = consumos_del_mes(empleado_id, anio, mes)

    # Construir el grid del calendario
    # calendar.Calendar(firstweekday=0) → lunes=0
    cal = calendar.Calendar(firstweekday=0)
    semanas = cal.monthdayscalendar(anio, mes)

    # Convertir el grid de números a un grid con fechas y consumos
    # monthdayscalendar devuelve listas de 7 números; 0 = día de otro mes
    grid = []
    for semana in semanas:
        fila = []
        for dia in semana:
            if dia == 0:
                # Día de otro mes
                fila.append({'fecha': None, 'consumo': None})
            else:
                fecha = date(anio, mes, dia)
                fila.append({
                    'fecha': fecha,
                    'consumo': consumos.get(fecha),
                })
        grid.append(fila)

    # Nombres del mes
    MESES_ES = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
    }
    mes_nombre = MESES_ES[mes]

    # Mes anterior y siguiente (con límites del periodo)
    mes_anterior = mes - 1 if mes > 1 else None
    mes_siguiente = mes + 1 if mes < 12 else None

    # Hoy (para resaltar el día actual)
    hoy = timezone.now().date() if anio == timezone.now().year else None

    return render(request, 'movimientos/calendario.html', {
        'empleado': empleado,
        'anio': anio,
        'mes': mes,
        'mes_nombre': mes_nombre,
        'grid': grid,
        'mes_anterior': mes_anterior,
        'mes_siguiente': mes_siguiente,
        'hoy': hoy,
        'periodo_activo': periodo_activo,
    })