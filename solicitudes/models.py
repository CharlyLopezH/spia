from django.db import models
from django.utils import timezone

from empleados.models import Empleado
from catalogos.models import CatDiasConcepto


class Solicitud(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de aprobación'),
        ('aprobada', 'Aprobada (Lista para aplicar)'),
        ('aplicada', 'Aplicada (Días descontados)'),
        ('cancelada', 'Cancelada'),
    ]

    id = models.BigAutoField(primary_key=True) # Pk    

    folio = models.CharField(
        'Folio / Memo', max_length=50, unique=True,
        help_text='Número de oficio o folio interno de la solicitud.'
    )
    fk_empleado = models.ForeignKey(
        Empleado, on_delete=models.PROTECT,
        verbose_name='Empleado'
    )
    fecha_solicitud = models.DateField(
        'Fecha de solicitud', default=timezone.now
    )
    motivo = models.TextField(
        'Motivo', blank=True, null=True
    )
    estado = models.CharField(
        'Estado', max_length=20, choices=ESTADO_CHOICES, default='pendiente'
    )

    # Auditoría de aprobación
    aprobado_por = models.CharField(
        'Aprobado por', max_length=100, blank=True, null=True
    )
    fecha_aprobacion = models.DateTimeField(
        'Fecha de aprobación', blank=True, null=True
    )

    # Auditoría de aplicación
    aplicado_por = models.CharField(
        'Aplicado por', max_length=100, blank=True, null=True
    )
    fecha_aplicacion = models.DateTimeField(
        'Fecha de aplicación', blank=True, null=True
    )

    class Meta:
        verbose_name = 'Solicitud'
        verbose_name_plural = 'Solicitudes'
        ordering = ['-fecha_solicitud', '-id']

    def __str__(self):
        return f"Solicitud {self.folio} — {self.fk_empleado.nombres} {self.fk_empleado.apellidos} ({self.estado})"

    @property
    def dias_totales(self):
        """Suma los días de todos los detalles."""
        return sum(det.dias for det in self.detalles.all())


class SolicitudDetalle(models.Model):

    id = models.BigAutoField(primary_key=True) # <-- Pk

    fk_solicitud = models.ForeignKey(
        Solicitud, on_delete=models.CASCADE,
        related_name='detalles', verbose_name='Solicitud'
    )
    fk_concepto = models.ForeignKey(
        CatDiasConcepto, on_delete=models.PROTECT,
        verbose_name='Concepto'
    )
    fecha = models.DateField(
        'Fecha a disponer'
    )
    dias = models.IntegerField(
        'Días', default=1,
        help_text='Cantidad de días a descontar en esta fecha.'
    )
    nota = models.CharField(
        'Nota', max_length=200, blank=True, null=True
    )

    class Meta:
        verbose_name = 'Detalle de solicitud'
        verbose_name_plural = 'Detalles de solicitud'
        ordering = ['fecha']
        # Evitar que en la misma solicitud se repita el mismo día
        constraints = [
            models.UniqueConstraint(
                fields=['fk_solicitud', 'fecha'],
                name='unique_solicitud_fecha'
            )
        ]

    def __str__(self):
        return f"{self.fk_concepto.clave} — {self.fecha} ({self.dias} días)"