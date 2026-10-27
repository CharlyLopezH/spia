from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from empleados.models import Empleado
from catalogos.models import CatDiasConcepto

from .models import Solicitud, SolicitudDetalle

from django.forms.models import BaseInlineFormSet

class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['folio', 'fk_empleado', 'fecha_solicitud', 'motivo']
        widgets = {
            'folio': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. RH-2026-001'}),
            'fk_empleado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_solicitud': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fk_empleado'].queryset = Empleado.objects.filter(estado='activo').order_by('apellidos', 'nombres')


class SolicitudDetalleForm(forms.ModelForm):
    class Meta:
        model = SolicitudDetalle
        fields = ['fk_concepto', 'fecha', 'dias', 'nota']
        widgets = {
            'fk_concepto': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'fecha': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'dias': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 1}),
            'nota': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fk_concepto'].queryset = CatDiasConcepto.objects.filter(activo=True).order_by('concepto')

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        
        # Solo validamos fin de semana a nivel de fila
        if fecha and fecha.weekday() in (5, 6):
            self.add_error('fecha', 'No se permiten sábados ni domingos.')            
        return cleaned_data

class BaseSolicitudDetalleFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        # Diccionario para sumar los días solicitados por concepto
        dias_por_concepto = {}

        for form in self.forms:
            # Ignorar formularios vacíos o marcados para eliminar
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue

            concepto = form.cleaned_data.get('fk_concepto')
            dias = form.cleaned_data.get('dias', 0)

            if concepto:
                if concepto.id not in dias_por_concepto:
                    dias_por_concepto[concepto.id] = {
                        'clave': concepto.clave,
                        'dias': 0,
                        'max': concepto.max_dias_por_periodo
                    }
                dias_por_concepto[concepto.id]['dias'] += dias

        # Validar contra la regla del catálogo
        for c_id, datos in dias_por_concepto.items():
            if datos['max'] is not None and datos['dias'] > datos['max']:
                raise forms.ValidationError(
                    f"Error en la solicitud: Estás solicitando {datos['dias']} día(s) de {datos['clave']}, "
                    f"pero el máximo permitido por periodo es {datos['max']}."
                )    


SolicitudDetalleFormSet = inlineformset_factory(
    Solicitud, 
    SolicitudDetalle,
    form=SolicitudDetalleForm,
    extra=1,
    can_delete=True
)