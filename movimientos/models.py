from django.db import models


class MovimientoDia(models.Model):
    TIPO_CHOICES = [
        ('otorgamiento', 'Otorgamiento'),
        ('acumulacion', 'Acumulación'),
        ('consumo', 'Consumo'),
        ('cancelacion', 'Cancelación'),
        ('ajuste', 'Ajuste'),
        ('expiracion', 'Expiración'),
    ]

    fk_empleado = models.ForeignKey(
        'empleados.Empleado',
        on_delete=models.PROTECT,
        related_name='movimientos_dias',
        db_column='fk_empleado',
        db_constraint=False,
        verbose_name='Empleado',
    )
    fk_concepto = models.ForeignKey(
        'catalogos.CatDiasConcepto',
        on_delete=models.PROTECT,
        related_name='movimientos_dias',
        db_column='fk_concepto',
        db_constraint=False,
        verbose_name='Concepto',
    )
    fk_solicitud = models.IntegerField(
        'Solicitud', null=True, blank=True, db_index=True,
        help_text='ID de la solicitud que generó este movimiento (si aplica).'
    )

    periodo = models.IntegerField(
        'Periodo', db_index=True,
        help_text='Año al que aplica el movimiento. Ej. 2026.'
    )
    fecha = models.DateField('Fecha del movimiento')
    tipo_movimiento = models.CharField(
        'Tipo de movimiento', max_length=20, choices=TIPO_CHOICES
    )
    dias = models.IntegerField(        
        help_text='Positivo = entrada, negativo = salida.'
    )
    descripcion = models.TextField('Descripción', blank=True, null=True)
    creado_por = models.CharField(
        'Creado por', max_length=100, blank=True, null=True
    )
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'movimientos_dias'
        verbose_name = 'Movimiento de día'
        verbose_name_plural = 'Kardex de días'
        ordering = ['-fecha', '-id']
        indexes = [
            models.Index(
                fields=['fk_empleado', 'fk_concepto', 'periodo'],
                name='idx_kardex_emp_con_per',
            ),
            models.Index(fields=['fecha'], name='idx_kardex_fecha'),
            models.Index(
                fields=['tipo_movimiento'], name='idx_kardex_tipo'
            ),
            models.Index(fields=['fk_solicitud'], name='idx_kardex_solicitud'),
        ]

    def __str__(self):
        signo = '+' if self.dias >= 0 else ''
        return (
            f"{self.fecha} - {self.fk_concepto.clave} "
            f"{signo}{self.dias} ({self.get_tipo_movimiento_display()})"
        )

    @property
    def es_entrada(self):
        return self.dias > 0

    @property
    def es_salida(self):
        return self.dias < 0