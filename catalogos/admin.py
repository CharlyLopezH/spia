from django.contrib import admin
from .models import CatDiasConcepto


@admin.register(CatDiasConcepto)
class CatDiasConceptoAdmin(admin.ModelAdmin):
    list_display = ['clave', 'concepto','contabiliza','es_por_evento', 'derecho', 'activo']
    list_filter = ['contabiliza', 'es_por_evento', 'activo']
    search_fields = ['clave', 'concepto', 'fundamento', 'derecho']
    list_editable = ['contabiliza', 'es_por_evento', 'activo']
    ordering = ['concepto']