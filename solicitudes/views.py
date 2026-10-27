from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.urls import reverse

from movimientos.models import MovimientoDia
from movimientos.services import saldo_actual

from .models import Solicitud
from .forms import SolicitudForm, SolicitudDetalleFormSet


def crear_solicitud(request):
    """
    Vista para crear una nueva solicitud con sus detalles.
    """
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        formset = SolicitudDetalleFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            solicitud = form.save(commit=False)
            solicitud.save()

            formset.instance = solicitud
            formset.save()

            messages.success(request, f'Solicitud {solicitud.folio} creada correctamente.')
            return redirect('solicitudes:lista')
    else:
        form = SolicitudForm()
        formset = SolicitudDetalleFormSet()

    return render(request, 'solicitudes/form.html', {
        'form': form,
        'formset': formset,
        'accion': 'Crear solicitud',
    })


def lista_solicitudes(request):
    """
    Lista de solicitudes (Fase C la embellece).
    """
    return render(request, 'solicitudes/lista.html', {
        'solicitudes': Solicitud.objects.all().order_by('-fecha_solicitud')
    })

def detalle_solicitud(request, pk):
    """
    Muestra el detalle de una solicitud y permite gestionarla.
    """
    solicitud = get_object_or_404(Solicitud, pk=pk)
    
    return render(request, 'solicitudes/detalle.html', {
        'solicitud': solicitud,
    })

@transaction.atomic
def aprobar_solicitud(request, pk):
    """
    Cambia el estado de la solicitud a 'aprobada'.
    Solo acepta peticiones POST por seguridad.
    """
    solicitud = get_object_or_404(Solicitud, pk=pk)

    if request.method == 'POST':
        if solicitud.estado == 'pendiente':
            solicitud.estado = 'aprobada'
            # Aquí podríamos registrar quién lo aprobó si tuviéramos login
            solicitud.aprobado_por = 'RH (Admin)' 
            solicitud.fecha_aprobacion = timezone.now()
            solicitud.save()
            messages.success(request, f'La solicitud {solicitud.folio} ha sido aprobada.')
        else:
            messages.error(request, 'Esta solicitud no se puede aprobar en su estado actual.')

    return redirect('solicitudes:detalle', pk=solicitud.pk)


@transaction.atomic
def aplicar_solicitud(request, pk):
    """
    Aplica la solicitud: descuenta los días del kardex generando movimientos de consumo.
    """
    solicitud = get_object_or_404(Solicitud, pk=pk)

    if request.method == 'POST':
        if solicitud.estado != 'aprobada':
            messages.error(request, 'Solo se pueden aplicar solicitudes aprobadas.')
            return redirect('solicitudes:detalle', pk=solicitud.pk)

        # 1. Validar que haya saldo suficiente para TODOS los detalles antes de aplicar
        # Agrupamos los días requeridos por concepto para validar de forma consolidada
        dias_requeridos = {}
        for det in solicitud.detalles.all():
            dias_requeridos[det.fk_concepto] = dias_requeridos.get(det.fk_concepto, 0) + det.dias

        errores = []
        for concepto, total_dias in dias_requeridos.items():
            saldo = saldo_actual(solicitud.fk_empleado.id, concepto.id, solicitud.fecha_solicitud.year)
            if saldo < total_dias:
                errores.append(f"Saldo insuficiente de {concepto.clave}: disponible {saldo}, solicitado {total_dias}.")

        if errores:
            # Si hay errores, abortamos la transacción y avisamos
            for error in errores:
                messages.error(request, error)
            return redirect('solicitudes:detalle', pk=solicitud.pk)

        # 2. Si todo está bien, generamos los movimientos en el Kardex
        for det in solicitud.detalles.all():
            MovimientoDia.objects.create(
                fk_empleado=solicitud.fk_empleado,
                fk_concepto=det.fk_concepto,
                periodo=det.fecha.year,
                fecha=det.fecha,
                tipo_movimiento='consumo',
                dias=-det.dias, # Negativo porque es una salida
                descripcion=f"Solicitud {solicitud.folio}",
                creado_por=solicitud.aprobado_por or 'RH'
            )

        # 3. Cambiamos el estado de la solicitud
        solicitud.estado = 'aplicada'
        solicitud.aplicado_por = 'RH (Admin)'
        solicitud.fecha_aplicacion = timezone.now()
        solicitud.save()

        messages.success(request, f'La solicitud {solicitud.folio} se ha aplicado al kardex correctamente.')

    return redirect('solicitudes:detalle', pk=solicitud.pk)


@transaction.atomic
def cancelar_solicitud(request, pk):
    """
    Cancela una solicitud aplicada y devuelve los días al kardex.
    """
    solicitud = get_object_or_404(Solicitud, pk=pk)

    if request.method == 'POST':
        if solicitud.estado != 'aplicada':
            messages.error(request, 'Solo se pueden cancelar solicitudes que ya fueron aplicadas.')
            return redirect('solicitudes:detalle', pk=solicitud.pk)

        # 1. Devolver los días (generar movimientos de cancelación)
        for det in solicitud.detalles.all():
            MovimientoDia.objects.create(
                fk_empleado=solicitud.fk_empleado,
                fk_concepto=det.fk_concepto,
                periodo=det.fecha.year,
                fecha=det.fecha,
                tipo_movimiento='cancelacion',
                dias=det.dias, # Positivo porque devolvemos el día
                descripcion=f"Cancelación de solicitud {solicitud.folio}",
                creado_por='RH (Admin)'
            )

        # 2. Cambiar estado
        solicitud.estado = 'cancelada'
        solicitud.save()

        messages.success(request, f'La solicitud {solicitud.folio} ha sido cancelada y los días devueltos al kardex.')

    return redirect('solicitudes:detalle', pk=solicitud.pk)