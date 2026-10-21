from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from empleados.models import Empleado
from catalogos.models import CatDiasConcepto

from .models import Solicitud, SolicitudDetalle


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
        
        if fecha and fecha.weekday() in (5, 6):
            self.add_error('fecha', 'No se permiten sábados ni domingos.')
            
        return cleaned_data


SolicitudDetalleFormSet = inlineformset_factory(
    Solicitud, 
    SolicitudDetalle,
    form=SolicitudDetalleForm,
    extra=1,
    can_delete=True
)