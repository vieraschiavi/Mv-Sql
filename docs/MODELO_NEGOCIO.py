"""
Modelo financiero MV SQL NLP — 3 escenarios × 1/3/6/12/18 meses, Uruguay.
Todos los supuestos explícitos y trazables. USD.
"""

# ── SUPUESTOS DE COSTO (datos verificados jul-2026) ─────────────────────
UYU_USD = 40.0                # tipo de cambio de referencia

# Estructura empresa (SAS bajo Literal E mientras la facturación lo permita)
SAS_ALTA = 3_000              # constitución + escribano (rango 35k-180k UYU)
SAS_MENSUAL = (23_500 + 44_000) / 2 / UYU_USD   # ~844 USD/mes contador+BPS+fijos
LITERAL_E_TOPE_ANUAL = 1_959_229 / UYU_USD      # ~48.981 USD/año

# Costos operativos del producto
INFRA_MES = 40                # Vercel Pro + dominio + correo
MP_COMISION = 0.062           # MercadoPago UY ~5,2% + IVA sobre comisión

# Costo de la IA cuando vendemos créditos (nosotros ponemos la key)
COSTO_IA_POR_CONSULTA = 0.004  # Haiku, ~6k tokens in / 800 out promedio

# Sueldos Uruguay (nominal + 13,5% aportes patronales ≈ costo empresa)
CARGA_PATRONAL = 1.135
SUELDO_IMPLEMENTADOR = 2_400 * CARGA_PATRONAL   # semi-senior
SUELDO_VENDEDOR = 1_600 * CARGA_PATRONAL
SUELDO_SOPORTE = 1_400 * CARGA_PATRONAL

# Publicidad
ADS_MES = 400                 # LinkedIn/Meta mínimo con señal útil en UY

# ── PRECIOS ─────────────────────────────────────────────────────────────
# ACTUAL (lo que está codeado hoy): pago único
P_UNICO = {"personal": 19, "profesional": 39, "empresa": 99}
# PROPUESTO: suscripción + servicios (lo que el plan de negocio ya recomendaba)
P_SUSC = {"personal": 15, "profesional": 29, "empresa": 79}
P_IMPLEMENTACION = 2_500      # proyecto de conexión a BD/ERP del cliente
P_SOPORTE_MES = 150           # mantenimiento post-implementación por cliente


def mes_a_mes(nombre, meses, nuevas_lic_mes, precio_lic, churn,
              implementaciones_mes, con_ads, empleados_desde=None,
              recurrente=True):
    """Devuelve lista de dicts con el P&L mes a mes."""
    filas = []
    licencias_activas = 0
    clientes_soporte = 0
    acumulado = 0.0

    for m in range(1, meses + 1):
        # ── Ingresos ──
        nuevas = nuevas_lic_mes(m)
        if recurrente:
            licencias_activas = licencias_activas * (1 - churn) + nuevas
            ing_lic = licencias_activas * precio_lic
        else:
            ing_lic = nuevas * precio_lic      # pago único: no se acumula

        impl = implementaciones_mes(m)
        ing_impl = impl * P_IMPLEMENTACION
        clientes_soporte += impl
        ing_soporte = clientes_soporte * P_SOPORTE_MES

        ingresos = ing_lic + ing_impl + ing_soporte

        # ── Costos ──
        c_mp = ingresos * MP_COMISION
        c_ia = licencias_activas * 30 * COSTO_IA_POR_CONSULTA if recurrente else 0
        c_infra = INFRA_MES
        c_estructura = SAS_MENSUAL + (SAS_ALTA if m == 1 else 0)
        c_ads = ADS_MES if con_ads else 0

        c_sueldos = 0
        if empleados_desde:
            for rol, (mes_alta, costo) in empleados_desde.items():
                if m >= mes_alta:
                    c_sueldos += costo

        costos = c_mp + c_ia + c_infra + c_estructura + c_ads + c_sueldos
        neto = ingresos - costos
        acumulado += neto

        filas.append(dict(mes=m, licencias=licencias_activas, impl=impl,
                          ingresos=ingresos, costos=costos, neto=neto,
                          acumulado=acumulado, sueldos=c_sueldos))
    return nombre, filas


def fmt(x):
    """Formato MV: $ con separador de miles, sin decimales."""
    signo = "-" if x < 0 else ""
    return f"{signo}${abs(x):,.0f}".replace(",", ".")


def tabla(nombre, filas, hitos=(1, 3, 6, 12, 18)):
    print(f"\n{'='*78}\n{nombre}\n{'='*78}")
    print(f"{'Mes':>4} {'Lic.act':>8} {'Impl':>5} {'Ingresos':>12} "
          f"{'Costos':>12} {'Neto mes':>12} {'Acumulado':>13}")
    print("-" * 78)
    for f in filas:
        if f["mes"] in hitos:
            print(f"{f['mes']:>4} {f['licencias']:>8.0f} {f['impl']:>5.0f} "
                  f"{fmt(f['ingresos']):>12} {fmt(f['costos']):>12} "
                  f"{fmt(f['neto']):>12} {fmt(f['acumulado']):>13}")


# ════════════════════════════════════════════════════════════════════════
# ESCENARIO A — "Como está hoy": pago único, solo, sin ads
#   Supuesto optimista incluso: 8 ventas/mes desde el mes 2 (nadie vende
#   un software desconocido de US$39 en UY sin marca ni canal).
# ════════════════════════════════════════════════════════════════════════
A = mes_a_mes("ESCENARIO A · Producto solo, pago único US$39, sin ads (COMO ESTÁ HOY)",
              18,
              nuevas_lic_mes=lambda m: 0 if m == 1 else min(8, 2 + m),
              precio_lic=P_UNICO["profesional"], churn=0,
              implementaciones_mes=lambda m: 0,
              con_ads=False, recurrente=False)

# ════════════════════════════════════════════════════════════════════════
# ESCENARIO B — Base realista: suscripción + servicio de implementación
#   1 implementación/mes desde el mes 2, 2/mes desde el 7, 3/mes desde 13.
#   Licencias: crecimiento orgánico lento, churn 5%/mes.
# ════════════════════════════════════════════════════════════════════════
def impl_B(m):
    if m <= 1: return 0
    if m <= 6: return 1
    if m <= 12: return 2
    return 3

B = mes_a_mes("ESCENARIO B · BASE: suscripción US$29 + implementaciones, sin ads",
              18,
              nuevas_lic_mes=lambda m: 0 if m == 1 else min(6, m),
              precio_lic=P_SUSC["profesional"], churn=0.05,
              implementaciones_mes=impl_B,
              con_ads=False)

# ════════════════════════════════════════════════════════════════════════
# ESCENARIO C — Agresivo: con ads + contratación al escalar
#   Implementador desde mes 7, vendedor desde mes 13.
# ════════════════════════════════════════════════════════════════════════
def impl_C(m):
    if m <= 1: return 0
    if m <= 6: return 2
    if m <= 12: return 4      # entra el implementador
    return 6                  # + vendedor alimentando pipeline

C = mes_a_mes("ESCENARIO C · AGRESIVO: ads US$400/mes + equipo (impl. mes 7, vend. mes 13)",
              18,
              nuevas_lic_mes=lambda m: 0 if m == 1 else min(18, 2 * m),
              precio_lic=P_SUSC["profesional"], churn=0.05,
              implementaciones_mes=impl_C,
              con_ads=True,
              empleados_desde={"implementador": (7, SUELDO_IMPLEMENTADOR),
                               "vendedor": (13, SUELDO_VENDEDOR)})

for nombre, filas in (A, B, C):
    tabla(nombre, filas)

# ── Comparativa de rentabilidad neta acumulada ─────────────────────────
print(f"\n{'='*78}\nRENTABILIDAD NETA ACUMULADA (USD)\n{'='*78}")
print(f"{'Escenario':<12} {'Mes 1':>11} {'Mes 3':>11} {'Mes 6':>11} "
      f"{'Mes 12':>11} {'Mes 18':>11}")
print("-" * 78)
for etiqueta, (nombre, filas) in zip("ABC", (A, B, C)):
    acum = {f["mes"]: f["acumulado"] for f in filas}
    print(f"{etiqueta:<12} " + " ".join(f"{fmt(acum[h]):>11}" for h in (1, 3, 6, 12, 18)))

# ── Punto de equilibrio y sueldo propio ────────────────────────────────
print(f"\n{'='*78}\nPUNTO DE EQUILIBRIO Y RETIRO PROPIO\n{'='*78}")
for etiqueta, (nombre, filas) in zip("ABC", (A, B, C)):
    breakeven = next((f["mes"] for f in filas if f["neto"] > 0), None)
    acum_pos = next((f["mes"] for f in filas if f["acumulado"] > 0), None)
    ult = filas[-1]
    print(f"{etiqueta}: primer mes con neto>0: {breakeven or 'NUNCA'} · "
          f"acumulado>0: {acum_pos or 'NUNCA'} · "
          f"neto mes 18: {fmt(ult['neto'])}/mes")

# ── Cuánto hace falta para vivir del producto SOLO ─────────────────────
print(f"\n{'='*78}\n¿CUÁNTAS VENTAS PARA UN SUELDO DE US$3.000 NETO/MES?\n{'='*78}")
objetivo = 3_000
fijos = SAS_MENSUAL + INFRA_MES
for nombre_p, precio in P_UNICO.items():
    n = (objetivo + fijos) / (precio * (1 - MP_COMISION))
    print(f"Pago único {nombre_p:<12} US${precio:>3}: {n:>6.0f} ventas CADA MES, para siempre")
for nombre_p, precio in P_SUSC.items():
    n = (objetivo + fijos) / (precio * (1 - MP_COMISION))
    print(f"Suscripción {nombre_p:<11} US${precio:>3}: {n:>6.0f} clientes ACTIVOS (se acumulan)")
n_impl = (objetivo + fijos) / (P_IMPLEMENTACION * (1 - MP_COMISION))
print(f"Implementación      US${P_IMPLEMENTACION}: {n_impl:>6.1f} proyectos por mes")

# ── Mercado direccionable ──────────────────────────────────────────────
print(f"\n{'='*78}\nMERCADO DIRECCIONABLE URUGUAY (embudo)\n{'='*78}")
empresas_uy = 207_182          # INE, Q1 2026
pct_no_micro = 0.10            # ~90% son unipersonales/micro sin BD real
con_bd_erp = 0.55              # de las no-micro, las que tienen ERP/BD consultable
dolor_real = 0.20              # que además tengan a alguien pidiendo reportes seguido
alcanzables = 0.30             # a las que realísticamente puedo llegar solo

tam = empresas_uy * pct_no_micro
sam = tam * con_bd_erp
som_dolor = sam * dolor_real
som = som_dolor * alcanzables
print(f"Empresas activas UY (INE Q1-2026):      {empresas_uy:>8,.0f}".replace(",", "."))
print(f"  × no-micro (10%)                       {tam:>8,.0f}".replace(",", "."))
print(f"  × con ERP/BD consultable (55%)         {sam:>8,.0f}".replace(",", "."))
print(f"  × con dolor real de reportes (20%)     {som_dolor:>8,.0f}".replace(",", "."))
print(f"  × alcanzables por mí solo (30%)        {som:>8,.0f}".replace(",", "."))
print(f"\nCon 2% de conversión sobre {som:,.0f} alcanzables = {som*0.02:,.0f} clientes posibles."
      .replace(",", "."))
print(f"A US$39 pago único eso es {fmt(som*0.02*39)} TOTAL — de una sola vez, no por mes.")
print(f"A US${P_IMPLEMENTACION} de implementación eso es {fmt(som*0.02*P_IMPLEMENTACION)} de pipeline.")
