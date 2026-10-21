from django.contrib import admin
from .models import MovimientoDia


@admin.register(MovimientoDia)
class MovimientoDiaAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'fecha', 'fk_empleado', 'fk_concepto',
        'tipo_movimiento', 'dias', 'periodo', 'fk_solicitud',
    ]
    list_filter = ['tipo_movimiento', 'periodo', 'fk_concepto', 'fecha']
    search_fields = [
        'fk_empleado__nombres', 'fk_empleado__apellidos',
        'fk_empleado__codigo', 'descripcion', 'creado_por',
    ]
    date_hierarchy = 'fecha'
    readonly_fields = ['creado_en']
    ordering = ['-fecha', '-id']
    list_select_related = ['fk_empleado', 'fk_concepto']

    fieldsets = (
        ('Identificación', {
            'fields': ('fk_empleado', 'fk_concepto', 'periodo', 'fecha')
        }),
        ('Movimiento', {
            'fields': ('tipo_movimiento', 'dias', 'descripcion')
        }),
        ('Trazabilidad', {
            'fields': ('fk_solicitud', 'creado_por', 'creado_en')
        }),
    )