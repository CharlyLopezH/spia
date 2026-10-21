from django.db import models

class Empleado(models.Model):
    id = models.AutoField(primary_key=True)
    codigo = models.IntegerField()
    nombres = models.CharField(max_length=30)
    apellidos = models.CharField(max_length=50)
    fk_adscripcion = models.IntegerField(null=True, blank=True)
    fk_puesto = models.IntegerField(null=True, blank=True)
    CURP = models.CharField(max_length=18, null=True, blank=True)
    foto = models.ImageField(upload_to='fotos/', null=True, blank=True)
    estado = models.CharField('Estado', max_length=20, default='activo',
                              choices=[('activo', 'Activo'),
                                       ('inactivo', 'Inactivo'),],
)
    class Meta:
        managed = False
        db_table = 'empleados'
        ordering = ['codigo']
    def __str__(self):
        return f"{self.codigo} - {self.apellidos} {self.nombres}"
    @property
    def nombre_completo(self):
        return f"{self.apellidos}, {self.nombres}"