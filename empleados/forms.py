from django import forms
from .models import Empleado


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            'codigo',
            'nombres',
            'apellidos',
            'CURP',
            'foto',
        ]
        widgets = {
            'codigo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'No con el que checa',
            }),
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre(s)',
                'maxlength': 30,
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellidos',
                'maxlength': 50,
            }),
            'CURP': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CURP (18 caracteres)',
                'maxlength': 18,
                'style': 'text-transform: uppercase;',
            }),
            'foto': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),        
        }
        labels = {
            'codigo': 'Código',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'CURP': 'CURP',
            'foto': 'Foto',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo codigo y nombres son obligatorios
        self.fields['codigo'].required = True
        self.fields['nombres'].required = True

        # El resto opcionales
        self.fields['apellidos'].required = True
        self.fields['CURP'].required = False
        self.fields['foto'].required = False

        for name in [ 'CURP', 'foto']:
            self.fields[name].widget.attrs.pop('required', None)

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')

        qs = Empleado.objects.filter(codigo=codigo)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError('Ya existe un empleado con ese código.')

        return codigo

    def clean_CURP(self):
        curp = self.cleaned_data.get('CURP')
        if curp:
            curp = curp.strip().upper()
            if len(curp) != 18:
                raise forms.ValidationError('La CURP debe tener exactamente 18 caracteres.')
        return curp