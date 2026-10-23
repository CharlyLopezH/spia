from django.db import models


class CatDiasConcepto(models.Model):
    """
    Catálogo primario de conceptos de permiso (días otorgables por concepto).
    Ejemplos: Vacaciones, Días económicos, Puntualidad, Incapacidad IMSS, etc.
    """
    clave = models.CharField(
        'Clave', max_length=20, unique=True,
        help_text='Código corto para referenciar el concepto. Ej. VAC, ECO, PUN.'
    )
    concepto = models.CharField(
        'Concepto', max_length=200,
        help_text='Nombre del permiso.'
    )
    fundamento = models.TextField(
        'Fundamento', blank=True, null=True,
        help_text='Fundamento legal o normativo que sustenta este concepto.'
    )
    derecho = models.CharField(
        'Derecho', max_length=100, blank=True, null=True,
        help_text='Días o derecho que otorga el reglamento. Ej. "8 días", "Hasta 15 días con autorización".'
    )
    dias_otorgamiento_default = models.IntegerField(
        'Días de otorgamiento por defecto', default=0,
        help_text='Días que se asignan automáticamente al inicio de cada periodo. Si es 0, no se otorga.'
    )

    max_dias_por_periodo = models.IntegerField(
        'Máximo de días por periodo', null=True, blank=True,
        help_text='Límite total que se puede solicitar de este concepto en el año. '
                  'Dejar vacío para no aplicar límite.'
    )

    contabiliza = models.BooleanField(
    'Contabiliza saldo', default=True,
    help_text='Si se marca, el concepto maneja saldo acumulable y aparece '
              'en las tarjetas del kardex. Si no, es eventual (duelo, '
              'enfermedad) y solo se registra en el historial.'
    )

    es_por_evento = models.BooleanField(
    'Se obtiene por evento',
    default=False,
    help_text='Si se marca, este concepto se gana por eventos periódicos como la puntualidad perfecta '
              '(ej. puntualidad mensual) y se registra con el formulario '
              '"Registrar Puntualidad Perfecta".'
    )    



    color_badge = models.CharField(
        'Color del badge', max_length=20, default='secondary',
        help_text='Color para mostrar en las tarjetas del kardex.'
    )
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        managed = True
        db_table = 'cat_dias_conceptos'
        verbose_name = 'Día por concepto'
        verbose_name_plural = 'Días por concepto'
        ordering = ['concepto']

    def __str__(self):
        return f"{self.clave} - {self.concepto}"