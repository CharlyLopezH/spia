from django.db.models import Sum

from .models import MovimientoDia
from datetime import date
from django.db import transaction

from empleados.models import Empleado
from catalogos.models import CatDiasConcepto

from calendar import monthrange
from datetime import date as _date


def saldo_actual(empleado_id, concepto_id, periodo):
    """Devuelve el saldo disponible de un empleado para un concepto en un periodo."""
    resultado = MovimientoDia.objects.filter(
        fk_empleado_id=empleado_id,
        fk_concepto_id=concepto_id,
        periodo=periodo,
    ).aggregate(total=Sum('dias'))

    return resultado['total'] or 0


def desglose_saldo(empleado_id, concepto_id, periodo):
    """Devuelve un diccionario con el desglose por tipo de movimiento."""
    qs = MovimientoDia.objects.filter(
        fk_empleado_id=empleado_id,
        fk_concepto_id=concepto_id,
        periodo=periodo,
    ).values('tipo_movimiento').annotate(total=Sum('dias'))

    desglose = {
        'otorgado': 0,
        'acumulado': 0,
        'consumido': 0,
        'cancelado': 0,
        'ajustado': 0,
        'expirado': 0,
    }

    mapa = {
        'otorgamiento': 'otorgado',
        'acumulacion': 'acumulado',
        'consumo': 'consumido',
        'cancelacion': 'cancelado',
        'ajuste': 'ajustado',
        'expiracion': 'expirado',
    }

    for fila in qs:
        clave = mapa.get(fila['tipo_movimiento'])
        if clave:
            desglose[clave] = fila['total'] or 0

    desglose['disponible'] = sum(desglose.values())

    return desglose


def saldos_por_concepto(empleado_id, periodo):
    """Devuelve una lista con el saldo de cada concepto con movimientos."""
    qs = MovimientoDia.objects.filter(
        fk_empleado_id=empleado_id,
        periodo=periodo,
    ).values(
        'fk_concepto_id',
        'fk_concepto__clave',
        'fk_concepto__concepto',
    ).annotate(saldo=Sum('dias'))

    return [
        {
            'concepto_id': fila['fk_concepto_id'],
            'clave': fila['fk_concepto__clave'],
            'concepto': fila['fk_concepto__concepto'],
            'saldo': fila['saldo'] or 0,
        }
        for fila in qs
    ]


def kardex(empleado_id, concepto_id=None, periodo=None):
    """Devuelve los movimientos ordenados cronológicamente."""
    qs = MovimientoDia.objects.filter(fk_empleado_id=empleado_id)

    if concepto_id:
        qs = qs.filter(fk_concepto_id=concepto_id)
    if periodo:
        qs = qs.filter(periodo=periodo)

    return qs.select_related('fk_concepto').order_by('-fecha', 'id')


#Regresa los conceptos activos
def conceptos_otorgables():
    """
    Devuelve los conceptos activos que se otorgan al inicio del periodo,
    es decir, los que tienen dias_otorgamiento_default > 0.
    """
    return CatDiasConcepto.objects.filter(
        activo=True,
        dias_otorgamiento_default__gt=0,
    ).order_by('concepto')


def empleados_otorgables(empleado_id=None):
    """
    Devuelve los empleados activos a los que se les aplicará la carga.
    Si se pasa empleado_id, filtra por ese empleado.
    """
    qs = Empleado.objects.filter(estado='activo').order_by('apellidos', 'nombres')
    if empleado_id:
        qs = qs.filter(id=empleado_id)
    return qs


def preview_otorgamiento(periodo, empleado_id=None):
    """
    Calcula lo que haría el proceso sin escribir nada.
    Devuelve un diccionario con el resumen:
        {
            'periodo': 2026,
            'empleados': 34,
            'conceptos': 3,
            'movimientos_por_crear': 102,
            'movimientos_omitidos': 0,
            'total_dias': 986,
            'detalle_conceptos': [
                {'clave': 'CUM', 'concepto': 'Cumpleaños', 'dias': 1},
                ...
            ],
        }
    """
    empleados = empleados_otorgables(empleado_id)
    conceptos = list(conceptos_otorgables())

    # Contar cuántos movimientos se crearían vs. cuántos ya existen
    a_crear = 0
    omitidos = 0
    total_dias = 0

    for emp in empleados:
        for c in conceptos:
            existe = MovimientoDia.objects.filter(
                fk_empleado=emp,
                fk_concepto=c,
                periodo=periodo,
                tipo_movimiento='otorgamiento',
            ).exists()
            if existe:
                omitidos += 1
            else:
                a_crear += 1
                total_dias += c.dias_otorgamiento_default

    return {
        'periodo': periodo,
        'empleados': empleados.count(),
        'conceptos': len(conceptos),
        'movimientos_por_crear': a_crear,
        'movimientos_omitidos': omitidos,
        'total_dias': total_dias,
        'detalle_conceptos': [
            {
                'clave': c.clave,
                'concepto': c.concepto,
                'dias': c.dias_otorgamiento_default,
                'fundamento': c.fundamento or '',
            }
            for c in conceptos
        ],
    }


def ejecutar_otorgamiento(periodo, empleado_id=None, fecha=None, creado_por='sistema'):
    """
    Ejecuta la carga inicial: crea movimientos de 'otorgamiento' para todos
    los empleados activos × conceptos otorgables, si no existen ya.

    Devuelve un diccionario con el resultado:
        {
            'creados': N,
            'omitidos': M,
            'total_dias': X,
            'detalle': [...],   # lista de strings con cada movimiento creado
        }
    """
    if fecha is None:
        fecha = date(periodo, 1, 1)

    empleados = empleados_otorgables(empleado_id)
    conceptos = list(conceptos_otorgables())

    creados = 0
    omitidos = 0
    total_dias = 0
    detalle = []

    for emp in empleados:
        for c in conceptos:
            existe = MovimientoDia.objects.filter(
                fk_empleado=emp,
                fk_concepto=c,
                periodo=periodo,
                tipo_movimiento='otorgamiento',
            ).exists()

            if existe:
                omitidos += 1
                continue

            with transaction.atomic():
                MovimientoDia.objects.create(
                    fk_empleado=emp,
                    fk_concepto=c,
                    periodo=periodo,
                    fecha=fecha,
                    tipo_movimiento='otorgamiento',
                    dias=c.dias_otorgamiento_default,
                    descripcion=(
                        f'Otorgamiento inicial {periodo} — {c.concepto}'
                    ),
                    creado_por=creado_por,
                )

            creados += 1
            total_dias += c.dias_otorgamiento_default
            detalle.append(
                f"[{emp.codigo}] {emp.apellidos} {emp.nombres} → "
                f"{c.clave}: {c.dias_otorgamiento_default} día(s)"
            )

    return {
        'creados': creados,
        'omitidos': omitidos,
        'total_dias': total_dias,
        'detalle': detalle,
    }


def _concepto_por_clave(clave):
    """Devuelve un concepto del catálogo por su clave, o None si no existe."""
    return CatDiasConcepto.objects.filter(clave=clave, activo=True).first()


def preview_arrastre(periodo_anterior, periodo_actual):
    """
    Calcula qué saldos a favor del periodo anterior se arrastrarían al actual.

    Regla:
    - VAC (Vacaciones) no disfrutadas → se arrastran como VAP.
    - VAP (Vacaciones Pendientes) del periodo anterior que no se usaron → se
      arrastran como VAP.
    - Los demás conceptos (ECO, CUM, PER, etc.) no se arrastran: se pierden.

    Devuelve un diccionario:
        {
            'periodo_anterior': 2025,
            'periodo_actual': 2026,
            'vac': [{'empleado': <Empleado>, 'dias': 8}, ...],
            'vap': [{'empleado': <Empleado>, 'dias': 5}, ...],
            'total_vac': 68,
            'total_vap': 9,
            'empleados_vac': 12,
            'empleados_vap': 3,
            'movimientos_a_crear': 15,
            'dias_totales': 77,
        }
    """
    vac = _concepto_por_clave('VAC')
    vap = _concepto_por_clave('VAP')

    if not vac or not vap:
        return {
            'periodo_anterior': periodo_anterior,
            'periodo_actual': periodo_actual,
            'vac': [],
            'vap': [],
            'total_vac': 0,
            'total_vap': 0,
            'empleados_vac': 0,
            'empleados_vap': 0,
            'movimientos_a_crear': 0,
            'dias_totales': 0,
        }

    empleados = Empleado.objects.filter(estado='activo').order_by('apellidos', 'nombres')

    arrastres_vac = []
    arrastres_vap = []

    for emp in empleados:
        # Saldo de VAC del periodo anterior
        saldo_vac = saldo_actual(emp.id, vac.id, periodo_anterior)
        if saldo_vac > 0:
            arrastres_vac.append({'empleado': emp, 'dias': saldo_vac})

        # Saldo de VAP del periodo anterior
        saldo_vap = saldo_actual(emp.id, vap.id, periodo_anterior)
        if saldo_vap > 0:
            arrastres_vap.append({'empleado': emp, 'dias': saldo_vap})

    return {
        'periodo_anterior': periodo_anterior,
        'periodo_actual': periodo_actual,
        'vac': arrastres_vac,
        'vap': arrastres_vap,
        'total_vac': sum(a['dias'] for a in arrastres_vac),
        'total_vap': sum(a['dias'] for a in arrastres_vap),
        'empleados_vac': len(arrastres_vac),
        'empleados_vap': len(arrastres_vap),
        'movimientos_a_crear': len(arrastres_vac) + len(arrastres_vap),
        'dias_totales': sum(a['dias'] for a in arrastres_vac) + sum(a['dias'] for a in arrastres_vap),
    }


def ejecutar_arrastre(periodo_anterior, periodo_actual, creado_por='sistema'):
    """
    Crea los movimientos de arrastre de VAC y VAP no usados del periodo
    anterior hacia el actual, como asignaciones de VAP.

    Es idempotente: si ya existe un movimiento con la misma descripción,
    se omite.

    Devuelve un diccionario:
        {
            'creados': N,
            'omitidos': M,
            'dias_totales': X,
            'detalle': ['[396] VAC → VAP: 8 días', ...],
        }
    """
    preview = preview_arrastre(periodo_anterior, periodo_actual)
    vap = _concepto_por_clave('VAP')

    if not vap:
        return {
            'creados': 0, 'omitidos': 0, 'dias_totales': 0, 'detalle': [],
        }

    fecha = date(periodo_actual, 1, 1)

    creados = 0
    omitidos = 0
    dias_totales = 0
    detalle = []

    # --- Arrastre de VAC no usado ---
    for a in preview['vac']:
        emp = a['empleado']
        dias = a['dias']
        descripcion = (
            f"Arrastre de VAC {periodo_anterior} → VAP {periodo_actual}"
        )

        existe = MovimientoDia.objects.filter(
            fk_empleado=emp,
            fk_concepto=vap,
            periodo=periodo_actual,
            tipo_movimiento='asignacion',
            descripcion__startswith=f"Arrastre de VAC {periodo_anterior}",
        ).exists()

        if existe:
            omitidos += 1
            continue

        with transaction.atomic():
            MovimientoDia.objects.create(
                fk_empleado=emp,
                fk_concepto=vap,
                periodo=periodo_actual,
                fecha=fecha,
                tipo_movimiento='asignacion',
                dias=dias,
                descripcion=descripcion,
                creado_por=creado_por,
            )
        creados += 1
        dias_totales += dias
        detalle.append(
            f"[{emp.codigo}] {emp.apellidos} {emp.nombres} — "
            f"VAC {periodo_anterior} → VAP: {dias} días"
        )

    # --- Arrastre de VAP previo no usado ---
    for a in preview['vap']:
        emp = a['empleado']
        dias = a['dias']
        descripcion = (
            f"Arrastre de VAP {periodo_anterior} → VAP {periodo_actual}"
        )

        existe = MovimientoDia.objects.filter(
            fk_empleado=emp,
            fk_concepto=vap,
            periodo=periodo_actual,
            tipo_movimiento='asignacion',
            descripcion__startswith=f"Arrastre de VAP {periodo_anterior}",
        ).exists()

        if existe:
            omitidos += 1
            continue

        with transaction.atomic():
            MovimientoDia.objects.create(
                fk_empleado=emp,
                fk_concepto=vap,
                periodo=periodo_actual,
                fecha=fecha,
                tipo_movimiento='asignacion',
                dias=dias,
                descripcion=descripcion,
                creado_por=creado_por,
            )
        creados += 1
        dias_totales += dias
        detalle.append(
            f"[{emp.codigo}] {emp.apellidos} {emp.nombres} — "
            f"VAP {periodo_anterior} → VAP: {dias} días"
        )

    return {
        'creados': creados,
        'omitidos': omitidos,
        'dias_totales': dias_totales,
        'detalle': detalle,
    }

def consumos_del_mes(empleado_id, anio, mes):
    """
    Devuelve un diccionario {fecha: MovimientoDia} con el consumo de cada día
    del mes indicado.

    Como máximo hay un consumo por día (validado en el formulario de disponer).
    Si hubiera más de uno (por datos históricos), se queda con el primero.

    Ejemplo:
        {
            date(2026, 10, 13): <MovimientoDia ECO>,
            date(2026, 10, 14): <MovimientoDia ECO>,
            date(2026, 10, 20): <MovimientoDia PPR>,
        }
    """
    from calendar import monthrange

    fecha_inicio = date(anio, mes, 1)
    ultimo_dia = monthrange(anio, mes)[1]
    fecha_fin = date(anio, mes, ultimo_dia)

    qs = MovimientoDia.objects.filter(
        fk_empleado_id=empleado_id,
        tipo_movimiento='consumo',
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
    ).select_related('fk_concepto').order_by('fecha', 'id')

    # El diccionario se queda con el primero si hubiera duplicados
    consumos = {}
    for m in qs:
        if m.fecha not in consumos:
            consumos[m.fecha] = m

    return consumos