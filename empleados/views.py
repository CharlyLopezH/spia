from django.contrib import messages
from django.shortcuts import redirect, render
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Empleado
from .forms import EmpleadoForm


def lista_empleados(request):
    query = request.GET.get('q', '').strip()

    # Selector de registros por página: solo acepta 10, 15, 25, 50
    try:
        per_page = int(request.GET.get('per_page', 10))
        if per_page not in [10, 15, 25, 50]:
            per_page = 10
    except (ValueError, TypeError):
        per_page = 10

    qs = Empleado.objects.all()

    if query:
        qs = qs.filter(
            Q(codigo__icontains=query) |
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(CURP__icontains=query)
        )

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))
    

    return render(request, 'empleados/lista.html', {
        'page_obj': page_obj,
        'query': query,
        'per_page': per_page,
        'per_page_options': [10, 15, 25, 50],
    })

# Create your views here.
def crear_empleado(request):
    if request.method == 'POST':
        form = EmpleadoForm(request.POST,request.FILES)
        if form.is_valid():
            form.save()
            return redirect('empleados:lista')
    else:
        form = EmpleadoForm()

    return render(request, 'empleados/form.html', {
        'form': form,
        'accion': 'Agregar',
    })


def editar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == 'POST':
        form = EmpleadoForm(request.POST, request.FILES, instance=empleado)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empleado actualizado correctamente.')
            return redirect('empleados:lista')
    else:
        form = EmpleadoForm(instance=empleado)

    return render(request, 'empleados/form.html', {
        'form': form,
        'accion': 'Editar',
        'empleado': empleado,
    })


def eliminar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk) # type: ignore

    if request.method == 'POST':
        empleado.delete()
        messages.success(request, 'Empleado eliminado.')
        return redirect('empleados:lista')

    return render(request, 'empleados/confirmar_eliminar.html', {
        'empleado': empleado,
    })