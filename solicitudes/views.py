from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

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