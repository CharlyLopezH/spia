from django.contrib import admin
from .models import Solicitud, SolicitudDetalle


class SolicitudDetalleInline(admin.TabularInline):
    model = SolicitudDetalle
    extra = 1
    fields = ['fk_concepto', 'fecha', 'dias', 'nota']


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ['folio', 'fk_empleado', 'fecha_solicitud', 'estado', 'dias_totales']
    list_filter = ['estado', 'fecha_solicitud']
    search_fields = ['folio', 'fk_empleado__nombres', 'fk_empleado__apellidos']
    readonly_fields = ['fecha_aprobacion', 'fecha_aplicacion']
    inlines = [SolicitudDetalleInline]
    ordering = ['-fecha_solicitud']