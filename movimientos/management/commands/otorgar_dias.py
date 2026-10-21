from datetime import date

from django.core.management.base import BaseCommand
from django.utils import timezone

from movimientos.services import (
    preview_otorgamiento,
    ejecutar_otorgamiento,
)


class Command(BaseCommand):
    help = (
        'Otorga los días iniciales por concepto a los empleados activos, '
        'leyendo el valor dias_otorgamiento_default del catálogo. '
        'Es idempotente: si un empleado ya tiene otorgamiento del concepto '
        'en el periodo, se omite.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--periodo', type=int, default=timezone.now().year,
            help='Año al que aplica el otorgamiento (default: año actual).'
        )
        parser.add_argument(
            '--empleado', type=int,
            help='ID de un empleado específico. Si se omite, aplica a todos los activos.'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra lo que haría, sin escribir en la base de datos.'
        )
        parser.add_argument(
            '--fecha', type=str,
            help='Fecha del movimiento en formato YYYY-MM-DD (default: 1 de enero del periodo).'
        )

    def handle(self, *args, **options):
        periodo = options['periodo']
        empleado_id = options.get('empleado')
        dry_run = options['dry_run']
        fecha_str = options.get('fecha')

        # Determinar la fecha
        if fecha_str:
            try:
                fecha = date.fromisoformat(fecha_str)
            except ValueError:
                self.stderr.write(self.style.ERROR(
                    f'Fecha inválida: {fecha_str}. Usa formato YYYY-MM-DD.'
                ))
                return
        else:
            fecha = date(periodo, 1, 1)

        # Preview para encabezado del reporte
        preview = preview_otorgamiento(periodo, empleado_id=empleado_id)

        if preview['empleados'] == 0:
            self.stderr.write(self.style.ERROR(
                'No hay empleados activos que procesar.'
            ))
            return

        if preview['conceptos'] == 0:
            self.stderr.write(self.style.WARNING(
                'No hay conceptos activos con dias_otorgamiento_default > 0.'
            ))
            return

        # Encabezado
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nOtorgamiento de días — Periodo {periodo}'
        ))
        self.stdout.write(f'  Fecha del movimiento: {fecha}')
        self.stdout.write(f'  Empleados a procesar: {preview["empleados"]}')
        self.stdout.write(f'  Conceptos a otorgar: {preview["conceptos"]}')
        self.stdout.write(f'  Movimientos por crear: {preview["movimientos_por_crear"]}')
        self.stdout.write(f'  Movimientos omitidos (ya existían): {preview["movimientos_omitidos"]}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n  Modo DRY-RUN: no se escribirá nada.\n'
            ))
            # Mostrar detalle de conceptos
            for c in preview['detalle_conceptos']:
                self.stdout.write(
                    f'  - {c["clave"]}: {c["dias"]} día(s) — {c["concepto"]}'
                )
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                f'[DRY-RUN] Se crearían {preview["movimientos_por_crear"]} movimientos, '
                f'{preview["movimientos_omitidos"]} se omitirían. '
                f'Total de días: {preview["total_dias"]}.'
            ))
            return

        # Ejecución real
        self.stdout.write('')
        resultado = ejecutar_otorgamiento(
            periodo=periodo,
            empleado_id=empleado_id,
            fecha=fecha,
            creado_por='sistema',
        )

        # Detalle de cada movimiento creado
        for linea in resultado['detalle']:
            self.stdout.write(f'  + {linea}')

        # Resumen final (con plurales correctos)
        creados = resultado['creados']
        omitidos = resultado['omitidos']
        msg_creados = f'{creados} movimiento' + (' creado' if creados == 1 else 's creados')
        msg_omitidos = f'{omitidos} omitido' + ('' if omitidos == 1 else 's')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'✓ {msg_creados}, {msg_omitidos} (ya existían). '
            f'Total de días otorgados: {resultado["total_dias"]}.'
        ))