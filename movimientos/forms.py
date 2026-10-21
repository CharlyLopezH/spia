from django import forms
from django.utils import timezone

from empleados.models import Empleado
from catalogos.models import CatDiasConcepto

from .models import MovimientoDia
from .services import saldo_actual


MESES_CHOICES = [
    (1, 'Enero'),
    (2, 'Febrero'),
    (3, 'Marzo'),
    (4, 'Abril'),
    (5, 'Mayo'),
    (6, 'Junio'),
    (7, 'Julio'),
    (8, 'Agosto'),
    (9, 'Septiembre'),
    (10, 'Octubre'),
    (11, 'Noviembre'),
]


class DisponerDiasForm(forms.Form):
    """
    Formulario para disponer días de una bolsa específica.

    El empleado y el concepto vienen por parámetro (desde la URL).
    El usuario captura una lista de fechas (una por línea) y el sistema
    crea un movimiento de tipo 'consumo' con dias = -1 por cada fecha.

    Validaciones:
    - Las fechas no pueden ser sábado ni domingo.
    - No pueden repetirse dentro de la misma captura.
    - La suma de días no puede exceder el saldo disponible.
    - No puede haber un consumo previo en la misma fecha para el mismo empleado/concepto.
    """
    fechas_texto = forms.CharField(
        label='Fechas a disponer (una por línea)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '2026-10-06\n2026-10-07\n2026-10-08',
        }),
    )
    motivo = forms.CharField(
        label='Motivo',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ej. Permiso autorizado por RH — Folio 12345',
        }),
    )

    def __init__(self, *args, **kwargs):
        # El empleado y el concepto vienen desde la vista (por URL)
        self.empleado = kwargs.pop('empleado', None)
        self.concepto = kwargs.pop('concepto', None)
        super().__init__(*args, **kwargs)

    def clean_fechas_texto(self):
        """
        Parsea el textarea y devuelve una lista de objetos date validados.
        """
        from datetime import datetime

        texto = self.cleaned_data.get('fechas_texto', '')
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]

        if not lineas:
            raise forms.ValidationError('Debes capturar al menos una fecha.')

        fechas = []
        errores = []
        dias_semana = ['lunes', 'martes', 'miércoles', 'jueves',
                       'viernes', 'sábado', 'domingo']

        for i, linea in enumerate(lineas, start=1):
            # Parseo
            try:
                fecha = datetime.strptime(linea, '%Y-%m-%d').date()
            except ValueError:
                errores.append(f'Línea {i}: "{linea}" no es una fecha válida (usa AAAA-MM-DD).')
                continue

            # No sábado ni domingo
            if fecha.weekday() in (5, 6):
                errores.append(
                    f'Línea {i}: {linea} ({dias_semana[fecha.weekday()]}) no es día hábil.'
                )
                continue

            # No duplicada en la lista
            if fecha in fechas:
                errores.append(f'Línea {i}: {linea} está repetida.')
                continue

            fechas.append(fecha)

        if errores:
            raise forms.ValidationError(errores)

        return fechas

    def clean(self):
        """
        Validación cruzada: saldo suficiente y no duplicados con consumos previos.
        """
        cleaned_data = super().clean()
        fechas = cleaned_data.get('fechas_texto')

        if not (self.empleado and self.concepto and fechas):
            return cleaned_data

        # Validar saldo por cada periodo afectado
        from collections import defaultdict
        fechas_por_anio = defaultdict(list)
        for f in fechas:
            fechas_por_anio[f.year].append(f)

        for anio, fechas_anio in fechas_por_anio.items():
            saldo = saldo_actual(self.empleado.id, self.concepto.id, anio)
            if len(fechas_anio) > saldo:
                self.add_error(
                    'fechas_texto',
                    f'Saldo insuficiente de {self.concepto.clave} en {anio}: '
                    f'disponible {saldo}, solicitado {len(fechas_anio)}.'
                )
        # Validar duplicados con consumos previos (de cualquier concepto)
        # Un empleado no puede tener dos ausencias el mismo día.
        duplicadas = []
        for fecha in fechas:
            existe = MovimientoDia.objects.filter(
                fk_empleado=self.empleado,
                tipo_movimiento='consumo',
                fecha=fecha,
            ).exists()
            if existe:
                duplicadas.append(fecha.strftime('%Y-%m-%d'))

        if duplicadas:
            self.add_error(
                'fechas_texto',
                f'El empleado ya tiene un consumo registrado en estas fechas: '
                f'{", ".join(duplicadas)}.'
            )
        return cleaned_data

    def save(self, creado_por=None):
        """
        Crea un MovimientoDia de tipo 'consumo' por cada fecha capturada.
        Devuelve la lista de movimientos creados.
        """
        fechas = self.cleaned_data['fechas_texto']
        motivo = self.cleaned_data.get('motivo', '').strip()
        descripcion = motivo or 'Disposición registrada manualmente'

        movimientos = []
        for fecha in fechas:
            mov = MovimientoDia.objects.create(
                fk_empleado=self.empleado,
                fk_concepto=self.concepto,
                periodo=fecha.year,
                fecha=fecha,
                tipo_movimiento='consumo',
                dias=-1,
                descripcion=descripcion,
                creado_por=creado_por or 'rh',
            )
            movimientos.append(mov)

        return movimientos
    
class AsignacionDiscrecionalForm(forms.Form):
    """
    Formulario para asignar días a un empleado de forma discrecional.

    Genera un movimiento de tipo 'asignacion' con signo POSITIVO.
    No valida saldo: la asignación suma, no consume.
    Solo valida que los días sean mayores a 0.
    """
    fk_empleado = forms.ModelChoiceField(
        queryset=Empleado.objects.filter(estado='activo').order_by('apellidos', 'nombres'),
        label='Empleado',
        empty_label='— Selecciona un empleado —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fk_concepto = forms.ModelChoiceField(
        queryset=CatDiasConcepto.objects.filter(
            activo=True,
            contabiliza=True,
            dias_otorgamiento_default=0,
            es_por_evento=False,
        ).order_by('concepto'),
        label='Concepto',
        empty_label='— Selecciona un concepto —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fecha = forms.DateField(
        label='Fecha de la asignación',
        initial=timezone.now,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    dias = forms.IntegerField(
        label='Días a asignar',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. 15',
            'min': 1,
        }),
    )
    motivo = forms.CharField(
        label='Motivo',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Ej. Saldo pendiente de años anteriores, acuerdo con dirección, etc.',
        }),
    )

    def __init__(self, *args, **kwargs):
        self.periodo = kwargs.pop('periodo', timezone.now().year)
        super().__init__(*args, **kwargs)

    def save(self, creado_por=None):
        """
        Crea el MovimientoDia de tipo 'asignacion' con signo positivo.
        """
        empleado = self.cleaned_data['fk_empleado']
        concepto = self.cleaned_data['fk_concepto']
        fecha = self.cleaned_data['fecha']
        dias = self.cleaned_data['dias']
        motivo = self.cleaned_data.get('motivo', '').strip()

        descripcion = motivo or 'Asignación discrecional'
        descripcion = f"{descripcion} ({fecha.isoformat()})"

        return MovimientoDia.objects.create(
            fk_empleado=empleado,
            fk_concepto=concepto,
            periodo=self.periodo,
            fecha=fecha,
            tipo_movimiento='asignacion',
            dias=dias,   # positivo
            descripcion=descripcion,
            creado_por=creado_por or 'rh',
        )


class RegistrarAcumulacionForm(forms.Form):
    """
    Formulario para registrar la acumulación de un día (o varios) que el
    empleado se ganó por un evento periódico (típicamente puntualidad
    perfecta mensual).

    Genera un movimiento de tipo 'acumulacion' con signo POSITIVO.
    El memo es obligatorio porque es el respaldo documental del evento.
    """
    fk_empleado = forms.ModelChoiceField(
        queryset=Empleado.objects.filter(estado='activo').order_by('apellidos', 'nombres'),
        label='Empleado',
        empty_label='— Selecciona un empleado —',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fk_concepto = forms.ModelChoiceField(
        queryset=CatDiasConcepto.objects.filter(
            activo=True,
            contabiliza=True,
            es_por_evento=True,
        ).order_by('concepto'),
        label='Concepto',
        empty_label='— Selecciona un concepto —',
        initial=lambda: CatDiasConcepto.objects.filter(
        activo=True, es_por_evento=True
        ).first(),
        widget=forms.Select(attrs={'class': 'form-select'}),        
    )
    periodo = forms.IntegerField(
        label='Periodo',
        initial=timezone.now().year,
        widget=forms.NumberInput(attrs={
            'class': 'form-control bg-light',
            'min': 2000,
            'max': 2100,
            'readonly': True,
            'tabindex': '-1',
            'style': 'pointer-events: none; user-select: none;',            
            
        }),
    )
    mes = forms.ChoiceField(
        label='Mes del periodo',
        choices=MESES_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    dias = forms.IntegerField(
        label='Días ganados',
        min_value=1,
        max_value=1,        
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'readonly':True,
            'placeholder': '1 para PPR',
        }),
    )
    memo = forms.CharField(
        label='Memo / Referencia',
        required=True,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Memo generado por RRHH para notificación de premio por puntualidad',
        }),
    )


    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('fk_empleado')
        concepto = cleaned_data.get('fk_concepto')
        periodo = cleaned_data.get('periodo')
        mes = cleaned_data.get('mes')

        if empleado and concepto and periodo and mes:
            from datetime import date
            fecha = date(periodo, int(mes), 1)
            nombre_mes = dict(MESES_CHOICES)[int(mes)]

            # 1. Validar duplicado por (empleado, concepto, periodo, mes)
            ya_existe = MovimientoDia.objects.filter(
                fk_empleado=empleado,
                fk_concepto=concepto,
                periodo=periodo,
                tipo_movimiento='acumulacion',
                fecha=fecha,
            ).exists()

            if ya_existe:
                self.add_error(
                    'mes',
                    f'Ya se asignó {concepto.clave} para {nombre_mes} {periodo} '
                    f'a este empleado.'
                )
                return cleaned_data

            # 2. Validar tope máximo (11 acumulaciones por año)
            ya_otorgados = MovimientoDia.objects.filter(
                fk_empleado=empleado,
                fk_concepto=concepto,
                periodo=periodo,
                tipo_movimiento='acumulacion',
            ).count()

            if ya_otorgados >= 11:
                self.add_error(
                    'mes',
                    f'Este empleado ya alcanzó el máximo de 11 acumulaciones '
                    f'de {concepto.clave} en el periodo {periodo}.'
                )

        return cleaned_data

    def save(self, creado_por=None):
        empleado = self.cleaned_data['fk_empleado']
        concepto = self.cleaned_data['fk_concepto']
        periodo = self.cleaned_data['periodo']
        mes = int(self.cleaned_data['mes'])
        dias = self.cleaned_data['dias']
        memo = self.cleaned_data['memo'].strip()

        # Fecha = primer día del mes seleccionado
        from datetime import date
        fecha = date(periodo, mes, 1)

        # Descripción con el nombre del mes y el memo
        nombre_mes = dict(MESES_CHOICES)[mes]
        descripcion = f"Puntualidad {nombre_mes} {periodo} — Memo {memo}"

        return MovimientoDia.objects.create(
            fk_empleado=empleado,
            fk_concepto=concepto,
            periodo=periodo,
            fecha=fecha,
            tipo_movimiento='acumulacion',
            dias=dias,
            descripcion=descripcion,
            creado_por=creado_por or 'rh',
        )