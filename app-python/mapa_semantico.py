# © 2026 Martín Viera. Todos los derechos reservados.

"""
mapa_semantico.py — MV SQL NLP
==================================================================
El mapa semántico de CUALQUIER esquema, armado sólo con el catálogo
(nombres, tipos, PKs y FKs): sin IA, sin leer datos y sin que nadie lo
configure.

Qué contesta:
  - qué es cada columna: clave, fecha, medida, atributo o bandera;
  - cómo se dice cada tabla y columna en el idioma de la pregunta
    («FactSales» ≈ ventas / sales / vendas);
  - por dónde se unen las tablas: las FKs declaradas MÁS las que se
    deducen del nombre (cliente_id, id_cliente, ClienteId, CustomerKey,
    cod_cliente, nro_pedido…). En un lakehouse de Fabric o en un ERP viejo
    no hay ninguna FK declarada: sin esto la IA unía las tablas a ojo;
  - el camino de JOINs entre dos tablas que no se unen directo.

Lo usan tres partes del motor:
  - el RAG (motor.RecuperadorEsquema): tokens que separan snake/camel,
    sinónimos ES/EN/PT y las tablas vecinas por JOIN;
  - el prompt de generación (bloque «MAPA SEMÁNTICO»);
  - la confianza: ¿los JOIN del SQL siguen relaciones conocidas?

Se arma sobre el catálogo YA recortado por rol (equipo.tablas_visibles):
una tabla que el usuario no ve no aparece ni como vecina ni en un camino.

No importa nada del resto de la app a nivel de módulo (catalogo.py lo
importa a él); control_resultado se carga recién al revisar un SQL.
==================================================================
"""

import math
import re
import unicodedata
from collections import Counter, deque
from functools import lru_cache

# ──────────────────────────────────────────────────────────────
# 1) Palabras: separar nombres, normalizar y traducir
# ──────────────────────────────────────────────────────────────
_ANIO = re.compile(r"^(19|20)\d\d$")


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))


def partir(nombre):
    """Palabras de un nombre o una frase, en minúscula y sin tildes.

    'FactSalesAmount' → fact sales amount · 'cod_cliente' → cod cliente ·
    'CustomerID' → customer id · 'IDCliente' → id cliente · 'Ventas2024' → ventas 2024.
    """
    return list(_partir(str(nombre)))


@lru_cache(maxsize=65536)      # los nombres de columna se repiten mucho entre tablas
def _partir(nombre):
    s = sin_tildes(nombre)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", s)
    return tuple(t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t)


def raiz(palabra):
    """Singular aproximado ES/EN/PT. No es un lematizador: es CONSISTENTE.

    Lo que importa es que pregunta y esquema caigan en la misma forma:
    clientes/cliente → client, customers → customer, ciudades → ciudad,
    cidades/cidade → cidad, categories → category, paises/pais → pais.
    """
    t = palabra
    if len(t) <= 3 or t.isdigit():
        return t
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith("es") and len(t) > 4 and t[-3] not in "aeiou":
        t = t[:-2]
    elif t.endswith("s") and t[-2] not in "siu":
        t = t[:-1]
    if t.endswith("e") and len(t) > 3:
        t = t[:-1]
    return t


#: Conceptos de negocio: etiqueta (es, en, pt) y las formas en que aparecen.
#: Una forma puede caer en dos conceptos («cobranza» es gestión y es pago).
CONCEPTOS = {
    "venta": (("ventas", "sales", "vendas"),
              "venta ventas vender vendido vendida vendidos vendidas vendimos vendio vendieron vende venden "
              "sale sales sell sells sold selling venda vendas vendeu venderam revenue revenues ingreso "
              "ingresos receita receitas facturacion faturamento ticket tickets"),
    "cliente": (("clientes", "customers", "clientes"),
                "cliente clientes customer customers client clients comprador compradores consumidor "
                "consumidores"),
    "producto": (("productos", "products", "produtos"),
                 "producto productos product products produto produtos articulo articulos artigo artigos "
                 "item items sku skus mercaderia mercadoria"),
    "fecha": (("fecha", "date", "data"),
              "fecha fechas date dates data datas dia dias day days diario daily mes meses month months "
              "monthly mensual mensuales mensal anio anios ano anos year years yearly anual trimestre "
              "trimestres quarter quarters trimestral semana semanas week weeks semanal weekly periodo "
              "periodos period periods calendario calendar "
              "enero febrero marzo abril mayo junio julio agosto septiembre setiembre octubre noviembre "
              "diciembre january february march april may june july august september october november "
              "december janeiro fevereiro marco maio junho julho setembro outubro novembro dezembro"),
    "monto": (("monto", "amount", "valor"),
              "monto montos importe importes amount amounts valor valores value values dinero money "
              "pesos dolares usd reais"),
    "cantidad": (("cantidad", "quantity", "quantidade"),
                 "cantidad cantidades quantity quantities qty quantidade quantidades unidades units volumen "
                 "volume piezas"),
    "factura": (("facturas", "invoices", "faturas"),
                "factura facturas facturado facturada facturados facturar facturacion invoice invoices "
                "invoiced billing fatura faturas faturado faturamento comprobante comprobantes"),
    "pago": (("pagos", "payments", "pagamentos"),
             "pago pagos pagado pagada pagados pagar payment payments paid pay pagamento pagamentos cobro "
             "cobros cobrado cobrada cobrados cobrar cobranza cobranzas collected recebido recebimento "
             "recebimentos recaudacion recaudado"),
    "cobranza": (("cobranza", "collections", "cobrança"),
                 "cobranza cobranzas collection collections cobranca gestion gestiones gestor gestores dunning"),
    "deuda": (("deuda", "debt", "dívida"),
              "deuda deudas debt debts divida dividas saldo saldos balance balances adeudado owed mora "
              "moroso morosos morosidad delinquency atraso atrasado inadimplencia inadimplente arrears"),
    "vencimiento": (("vencimiento", "due date", "vencimento"),
                    "vencimiento vencimientos vencido vencida vencidos vencidas vencer due overdue vencimento "
                    "vencimentos"),
    "cuota": (("cuotas", "installments", "parcelas"),
              "cuota cuotas installment installments instalment parcela parcelas"),
    "credito": (("créditos", "loans", "créditos"),
                "credito creditos credit credits loan loans prestamo prestamos emprestimo emprestimos "
                "financiacion otorgado otorgados otorgamiento granted concedido"),
    "sucursal": (("sucursal", "branch / store", "filial / loja"),
                 "sucursal sucursales branch branches filial filiales agencia agencias store stores tienda "
                 "tiendas loja lojas"),
    "pais": (("país", "country", "país"), "pais paises country countries nacion"),
    "ciudad": (("ciudad", "city", "cidade"),
               "ciudad ciudades city cities cidade cidades localidad localidades municipio town"),
    "provincia": (("provincia", "state / province", "estado / província"),
                  "provincia provincias province provinces state states"),
    "region": (("región / zona", "region / zone", "região / zona"),
               "region regiones regiao regioes zona zonas zone zones territorio territory"),
    "vendedor": (("vendedores", "salespeople", "vendedores"),
                 "vendedor vendedores vendedora seller sellers salesperson salespeople salesman salesmen rep "
                 "reps representante representantes"),
    "empleado": (("empleados", "employees", "funcionários"),
                 "empleado empleados employee employees funcionario funcionarios colaborador colaboradores "
                 "staff"),
    "proveedor": (("proveedores", "suppliers", "fornecedores"),
                  "proveedor proveedores supplier suppliers vendor vendors fornecedor fornecedores provider"),
    "stock": (("stock", "inventory", "estoque"),
              "stock stocks inventory inventories inventario inventarios estoque estoques existencia "
              "existencias"),
    "precio": (("precio", "price", "preço"), "precio precios price prices preco precos tarifa tarifas"),
    "costo": (("costo", "cost", "custo"), "costo costos coste costes cost costs custo custos"),
    "margen": (("margen", "margin", "margem"),
               "margen margenes margin margins margem margens ganancia ganancias profit profits lucro "
               "rentabilidad"),
    "pedido": (("pedidos", "orders", "pedidos"),
               "pedido pedidos order orders orden ordenes encomenda encomendas"),
    "detalle": (("detalle / líneas", "details / lines", "detalhe / itens"),
                "detalle detalles detail details linea lineas line lines renglon renglones detalhe"),
    "categoria": (("categoría / rubro", "category", "categoria"),
                  "categoria categorias category categories rubro rubros familia familias"),
    "marca": (("marca", "brand", "marca"), "marca marcas brand brands"),
    "segmento": (("segmento", "segment", "segmento"), "segmento segmentos segment segments segmentacion"),
    "descuento": (("descuento", "discount", "desconto"),
                  "descuento descuentos discount discounts desconto descontos bonificacion"),
    "envio": (("envío / flete", "shipping / freight", "envio / frete"),
              "envio envios shipping ship shipped shipment freight flete fletes frete despacho entrega "
              "entregas delivery"),
    "estado": (("estado", "status", "situação"), "estado estados status situacion situacao"),
    "tasa": (("tasa", "rate", "taxa"), "tasa tasas rate rates taxa taxas interes interest juros"),
    "empresa": (("empresa", "company", "empresa"), "empresa empresas company companies compania companhia"),
    "impuesto": (("impuesto", "tax", "imposto"), "impuesto impuestos tax taxes iva vat imposto impostos"),
    "canal": (("canal", "channel", "canal"), "canal canales channel channels"),
    "usuario": (("usuario", "user", "usuário"), "usuario usuarios user users login"),
}

#: Conceptos vecinos: sólo del lado de la PREGUNTA y con medio peso. «Ventas»
#: en un Northwind vive en orders/order_details: sin esto, «sales by customer»
#: encontraba customers y nada más.
RELACIONADOS = {
    "venta": ("pedido", "factura"),
    "pedido": ("venta",),
    "factura": ("venta",),
    "cobranza": ("pago", "deuda"),
    "deuda": ("cuota", "vencimiento", "credito"),
    "margen": ("costo", "precio", "venta"),
    "vendedor": ("empleado",),
    "empleado": ("vendedor",),
}

_CONCEPTO_DE = {}
for _c, (_etq, _formas) in CONCEPTOS.items():
    for _f in _formas.split():
        _CONCEPTO_DE.setdefault(raiz(_f), set()).add(_c)

#: Palabras que no distinguen una tabla de otra (ni en la pregunta ni en el esquema).
STOP = set("""
de del la las el los lo un una unos unas y o u e a al en con sin por para que cual cuales cuanto cuanta
cuantos cuantas como cada se su sus mi mis es son fue fueron ser hay hizo hicieron tiene tienen entre sobre
desde hasta mas menos muy ya no si le les nos este esta estos estas ese esa esos esas total totales dame
mostrar muestra muestrame listar lista listado ver quiero necesito top mayor mayores menor menores mejor
mejores peor primeros ultimos ultimo ultima actual actuales promedio suma incluidos incluidas
the an of in on at by for to from with without and or per each what which who how many much is are was
were be been has have had do does did show list give me most least best worst first last average avg sum
count than vs all
os as um uma uns umas do da dos das na nos nas em com sem qual quais quanto quantos quanta quantas seu sua
seus suas ou foram sao muito maior media fizeram feitos feitas cada
fact dim tbl tb vw fct stg tmp dbo
""".split())

#: Prefijos de tabla que no son parte del nombre de la entidad.
_PREFIJOS_TABLA = {"fact", "dim", "tbl", "tb", "vw", "v", "f", "d", "t", "fct", "stg", "dw"}
#: Cola o cabeza de nombre que marca una clave: cliente_id, id_cliente, ClienteKey, cod_cliente…
_MARCA_CLAVE_FIN = {"id", "key", "sk", "fk", "cod", "code", "codigo", "nro", "num", "numero", "no"}
_MARCA_CLAVE_INICIO = {"id", "fk", "cod", "code", "codigo", "nro", "num", "numero", "key"}
#: Nombres de clave que no dicen a qué entidad apuntan: nunca se unen «por el nombre».
GENERICAS = {"id", "codigo", "code", "cod", "key", "nro", "numero", "num", "pk", "sk", "rowid"}


def conceptos(palabra):
    """Conceptos de negocio de una palabra ya normalizada (ver raiz)."""
    return _CONCEPTO_DE.get(raiz(palabra), set())


def analizar(texto, pregunta=False):
    """Bolsa de términos (Counter término → peso) para el TF-IDF.

    Cada palabra aporta su raíz, su concepto (§venta, §cliente…) y un prefijo
    de 6 letras («~segmen» une segmento/segment, «~catego» categoría/category).
    Un año (2024) aporta §fecha. En la pregunta se suman, con medio peso, los
    conceptos vecinos (RELACIONADOS).
    """
    bolsa = Counter()
    for crudo in partir(texto):
        if crudo in STOP or len(crudo) < 2:
            continue
        if crudo.isdigit():
            if _ANIO.match(crudo):
                bolsa[crudo] += 1
                bolsa["§fecha"] += 1
            continue
        r = raiz(crudo)
        bolsa[r] += 1
        if len(crudo) >= 6:
            bolsa["~" + crudo[:6]] += 0.5
        for c in _CONCEPTO_DE.get(r, ()):
            bolsa["§" + c] += 1
            if pregunta:
                for vecino in RELACIONADOS.get(c, ()):
                    bolsa["§" + vecino] += 0.5
    return bolsa


# ──────────────────────────────────────────────────────────────
# 2) TF-IDF propio (biblioteca estándar: corre igual sin sklearn)
# ──────────────────────────────────────────────────────────────
def _tf(peso):
    return 1.0 + math.log(peso) if peso >= 1 else peso


class IndiceTfidf:
    """TF-IDF con tf sublineal e idf suavizado, sobre bolsas ya analizadas."""

    def __init__(self, bolsas):
        n = len(bolsas)
        df = Counter()
        for b in bolsas:
            df.update(set(b))
        self.idf = {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}
        self.vectores = [self._vector(b) for b in bolsas]

    def _vector(self, bolsa):
        v = {t: _tf(w) * self.idf[t] for t, w in bolsa.items() if t in self.idf and w > 0}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norma for t, x in v.items()}

    def similitudes(self, bolsa):
        q = self._vector(bolsa)
        return [sum(w * d.get(t, 0.0) for t, w in q.items()) for d in self.vectores]


#: Lo fijo de cada ficha («TABLA:», «Cantidad de filas», tipos, «NOT NULL»…):
#: no distingue una tabla de otra y en el TF-IDF viejo pesaba más que los nombres.
_PLANTILLA = re.compile(
    r"TABLA:|Cantidad de filas:[^\n]*|Columnas:|Relaciones \(JOINs\):|NOT NULL|\[PK\]|"
    r"\((?:[A-Za-z ]+)(?:\(\d+(?:,\s*\d+)?\))?\)|valores ejemplo:")


def texto_indice(tabla, info):
    """Lo que el RAG indexa de una tabla: el nombre (×3) y sus columnas."""
    return " ".join([tabla] * 3 + [c["columna"] for c in info.get("columnas", [])])


def texto_valores(info, tope=15):
    """Valores de ejemplo (sólo para el índice local: nunca viajan desde acá)."""
    return " ".join(str(v) for vals in (info.get("muestras") or {}).values() for v in list(vals)[:tope])


def bolsa_de_ficha(ficha):
    """Bolsa de términos de una ficha: nombres a peso pleno, valores de ejemplo a 0,3."""
    if "indice" not in ficha:          # ficha armada a mano (tests, versiones viejas)
        return analizar(_PLANTILLA.sub(" ", ficha.get("texto", "")))
    bolsa = analizar(ficha["indice"])
    for t, w in analizar(ficha.get("indice_valores", "")).items():
        bolsa[t] += 0.3 * w
    return bolsa


def elegir_tablas(nombres, sims, padres, k=4, corte=0.35, extra=3, max_saltos=3, tope_extra=4):
    """Índices de las tablas a mandar al prompt, en orden de relevancia.

    padres: {tabla: [tablas a las que apunta]} (el lado N:1 de cada relación).

    1) k adaptativo: entran las k mejores y hasta `extra` más si están cerca
       de la mejor (≥ corte × la mejor). Nunca menos de max(k, 3), como antes.
    2) Puentes: si dos tablas elegidas no se unen directo, entran las del
       camino de JOINs entre ellas (pagos → cuotas → créditos → sucursales).
       Sin esto la IA tenía las dos puntas y ninguna forma de unirlas.
       Primero los pares más relevantes; en total, nunca más de
       max(k, 3) + tope_extra tablas (un esquema muy conectado no puede
       llenar el prompt de puentes).
    """
    n = len(nombres)
    orden = sorted(range(n), key=lambda i: (-sims[i], i))
    base = min(max(k, 3), n)
    if n <= base or not orden or sims[orden[0]] <= 0:
        return orden[:base] if n > base else orden
    top = sims[orden[0]]
    elegidas = [i for i in orden[:k + extra] if sims[i] >= corte * top]
    for i in orden:
        if len(elegidas) >= base:
            break
        if i not in elegidas:
            elegidas.append(i)
    tope = base + tope_extra
    pos = {nombres[i]: i for i in range(n)}
    hijos = _hijos(padres)
    fuertes = [i for i in elegidas if sims[i] >= corte * top]
    pares = sorted(((a, b) for x, a in enumerate(fuertes) for b in fuertes[x + 1:]),
                   key=lambda par: -(sims[par[0]] + sims[par[1]]))
    salida = list(elegidas)
    for a, b in pares:
        if len(salida) >= tope:
            break
        camino = camino_tablas(padres, nombres[a], nombres[b], max_saltos, hijos=hijos) or []
        nuevas = [pos[t] for t in camino[1:-1] if t in pos and pos[t] not in salida]
        if nuevas and len(salida) + len(nuevas) <= tope:
            salida += nuevas
    return salida


def _hijos(padres):
    hijos = {}
    for t, ps in padres.items():
        for p in ps:
            hijos.setdefault(p, []).append(t)
    return hijos


def camino_tablas(padres, a, b, max_saltos=3, hijos=None):
    """Tablas del camino de JOINs más corto de a hasta b (incluidas), o None.

    Sólo caminos con forma de VALLE: primero se baja (de una tabla a las que
    la referencian: clientes → pedidos → líneas) y después se sube (de una
    tabla a las que referencia: líneas → productos → categorías). Subir y
    volver a bajar —facturas → vendedores ← ventas mensuales— cruza dos
    tablas de hechos por una dimensión y multiplica filas: no es un camino.
    """
    if a == b:
        return [a]
    hijos = _hijos(padres) if hijos is None else hijos
    # Estado: (tabla, ya_subio). Bajando se puede seguir bajando o empezar a subir.
    previo = {(a, False): None}
    cola = deque([(a, False, 0)])
    while cola:
        actual, subio, saltos = cola.popleft()
        if saltos >= max_saltos:
            continue
        pasos = [(p, True) for p in padres.get(actual, ())]
        if not subio:
            pasos += [(h, False) for h in hijos.get(actual, ())]
        for v, sube in pasos:
            estado = (v, sube)
            if v == actual or estado in previo:
                continue
            previo[estado] = (actual, subio)
            if v == b:
                camino, e = [], estado
                while e is not None:
                    camino.append(e[0])
                    e = previo[e]
                return camino[::-1]
            cola.append((v, sube, saltos + 1))
    return None


# ──────────────────────────────────────────────────────────────
# 3) Roles de columna
# ──────────────────────────────────────────────────────────────
_TOKENS_FECHA = {"fecha", "fec", "date", "data", "dt", "datetime", "timestamp", "periodo", "period", "dia", "day",
                 "mes", "month", "anio", "ano", "year", "quarter", "trimestre", "semana", "week", "hora",
                 "time", "update", "updated", "created", "modified"}
_TOKENS_BANDERA = {"es", "is", "has", "tiene", "flag", "activo", "activa", "active", "anulado", "anulada",
                   "deleted", "borrado", "pagada", "pagado", "discontinued", "habilitado", "enabled", "baja"}


def _es_numerico(tipo):
    return "INTERVAL" not in tipo and bool(re.search(
        r"INT|REAL|FLOAT|DOUBLE|DEC|NUMERIC|NUMBER|MONEY|CURRENCY", tipo))


def _es_texto(tipo):
    return bool(re.search(r"CHAR|TEXT|CLOB|STRING", tipo))


def entidad_de_columna(columna):
    """A qué entidad apunta una columna clave, o None: cod_cliente → ('cliente',)."""
    toks = partir(columna)
    if len(toks) >= 2 and toks[-1] in _MARCA_CLAVE_FIN:
        return tuple(toks[:-1])
    if len(toks) >= 2 and toks[0] in _MARCA_CLAVE_INICIO:
        return tuple(toks[1:])
    return None


def rol_columna(col):
    """'clave', 'fecha', 'bandera', 'medida', 'atributo' u 'otro' (por nombre y tipo, sin datos)."""
    nombre, tipo = col["columna"], str(col.get("tipo") or "").upper()
    toks = partir(nombre)
    if col.get("pk") or entidad_de_columna(nombre) or (toks and toks[-1] in GENERICAS and len(toks) == 1):
        return "clave"
    if "DATE" in tipo or "TIME" in tipo or any(t in _TOKENS_FECHA for t in toks) or (toks and toks[-1] == "at"):
        return "fecha"
    if tipo in ("BIT", "BOOL", "BOOLEAN") or (toks and toks[0] in _TOKENS_BANDERA and
                                              (_es_numerico(tipo) or not tipo)):
        return "bandera"
    if _es_numerico(tipo):
        return "medida"
    if _es_texto(tipo) or not tipo:
        return "atributo"
    return "otro"


# ──────────────────────────────────────────────────────────────
# 4) El mapa: roles, sinónimos y relaciones (declaradas + deducidas)
# ──────────────────────────────────────────────────────────────
def _entidad_de_tabla(tabla):
    toks = partir(str(tabla).split(".")[-1])
    while len(toks) > 1 and toks[0] in _PREFIJOS_TABLA:
        toks = toks[1:]
    return tuple(raiz(t) for t in toks)


def _etiquetas(palabras, maximo=3):
    """«ventas | sales | vendas» por cada concepto de negocio de las palabras."""
    salida = []
    for p in palabras:
        for c in sorted(conceptos(p)):
            etq = " | ".join(dict.fromkeys(CONCEPTOS[c][0]))
            if etq not in salida:
                salida.append(etq)
    return salida[:maximo]


def construir_mapa(catalogo):
    """Mapa semántico del catálogo: {"tablas", "relaciones", "vecinas", "padres"}.

    vecinas: con quién se une cada tabla (sin sentido); padres: a qué tablas
    apunta (el lado «uno» de cada relación N:1).

    relaciones: [{tabla_origen, columna_origen, tabla_destino, columna_destino,
    origen: "declarada"|"deducida", regla}] — las mismas claves que las FKs del
    catálogo, así el diagrama de relaciones las dibuja sin traducir nada.
    """
    tablas = catalogo.get("tablas", {}) or {}
    cols = {t: [c["columna"] for c in (info.get("columnas") or [])] for t, info in tablas.items()}
    pk_unica = {}
    for t, info in tablas.items():
        pks = [c["columna"] for c in (info.get("columnas") or []) if c.get("pk")]
        pk_unica[t] = pks[0] if len(pks) == 1 else None
    entidad = {t: _entidad_de_tabla(t) for t in tablas}

    relaciones, vistas = [], set()

    def sumar(to, co, td, cd, origen, regla):
        clave = (to.lower(), co.lower(), td.lower(), cd.lower())
        if clave in vistas or (clave[2], clave[3], clave[0], clave[1]) in vistas:
            return
        vistas.add(clave)
        relaciones.append({"tabla_origen": to, "columna_origen": co, "tabla_destino": td,
                           "columna_destino": cd, "origen": origen, "regla": regla})

    # Declaradas (también las que sumó sumar_contexto desde el modelo de origen).
    # Se aceptan las claves viejas «tabla»/«columna».
    for fk in catalogo.get("fks", []) or []:
        to = fk.get("tabla_origen") or fk.get("tabla")
        co = fk.get("columna_origen") or fk.get("columna")
        td, cd = fk.get("tabla_destino"), fk.get("columna_destino")
        if to in tablas and td in tablas and co:
            cd = cd or pk_unica.get(td)       # SQLite: «REFERENCES clientes» sin columna = su PK
            if cd:
                sumar(to, co, td, cd, "declarada", "fk")
    cubiertas = {(r["tabla_origen"].lower(), r["columna_origen"].lower()) for r in relaciones}

    def columna_destino(d, c, x):
        mismas = [col for col in cols[d] if col.lower() == c.lower()]
        if mismas:
            return mismas[0]
        if pk_unica[d]:
            return pk_unica[d]
        for col in cols[d]:
            ent = entidad_de_columna(col)
            if ent and tuple(raiz(p) for p in ent) == x:
                return col
        genericas = [col for col in cols[d] if col.lower() in GENERICAS]
        return genericas[0] if len(genericas) == 1 else None

    # Índices: con cientos de tablas, recorrerlas todas por cada columna clave
    # tardaba segundos.
    por_entidad, por_sufijo, por_concepto = {}, {}, {}
    for t, ent in entidad.items():
        por_entidad.setdefault(ent, []).append(t)
        for k in range(1, len(ent)):
            por_sufijo.setdefault(ent[-k:], []).append(t)
        if len(ent) == 1:
            for c in conceptos(ent[0]):
                por_concepto.setdefault(c, []).append(t)
    duenas_de = {}
    for t, pk in pk_unica.items():
        if pk:
            duenas_de.setdefault(pk.lower(), []).append(t)

    def tablas_para(x, excluir):
        candidatas = list(por_entidad.get(x, [])) + list(por_sufijo.get(x, []))
        if len(x) == 1:
            for c in sorted(conceptos(x[0])):
                candidatas += por_concepto.get(c, [])
        return [t for t in dict.fromkeys(candidatas) if t != excluir]

    # Deducidas por el nombre de la columna.
    for t in tablas:
        for c in cols[t]:
            if (t.lower(), c.lower()) in cubiertas or c == pk_unica[t]:
                continue
            ent = entidad_de_columna(c)
            hecho = False
            if ent:
                x = tuple(raiz(p) for p in ent)
                for d in tablas_para(x, t):
                    cd = columna_destino(d, c, x)
                    if cd:
                        sumar(t, c, d, cd, "deducida", "nombre")
                        hecho = True
                        break
            if hecho or c.lower() in GENERICAS:
                continue
            # La misma columna es la PK (única) de otra tabla: CUIT, SKU, legajo…
            duenas = [d for d in duenas_de.get(c.lower(), []) if d != t]
            if len(duenas) == 1:
                sumar(t, c, duenas[0], pk_unica[duenas[0]], "deducida", "misma_columna")

    vecinas = {t: {} for t in tablas}           # dicts ordenados: sin repetidos y sin buscar en listas
    padres = {t: {} for t in tablas}
    for r in relaciones:
        a, b = r["tabla_origen"], r["tabla_destino"]
        if a != b:
            vecinas[a][b] = vecinas[b][a] = padres[a][b] = True
    vecinas = {t: list(v) for t, v in vecinas.items()}
    padres = {t: list(v) for t, v in padres.items()}

    n_salientes = Counter(r["tabla_origen"] for r in relaciones if r["tabla_origen"] != r["tabla_destino"])
    n_entrantes = Counter(r["tabla_destino"] for r in relaciones if r["tabla_origen"] != r["tabla_destino"])
    info_tablas = {}
    for t, info in tablas.items():
        salientes, entrantes = n_salientes[t], n_entrantes[t]
        por_rol = {"clave": [], "fecha": [], "medida": [], "atributo": [], "bandera": [], "otro": []}
        columnas = {}
        for col in info.get("columnas") or []:
            rol = rol_columna(col)
            por_rol[rol].append(col["columna"])
            columnas[col["columna"]] = {"rol": rol, "sinonimos": _etiquetas(partir(col["columna"]), 1)}
        if salientes >= 2 and por_rol["medida"]:
            rol_t = "hechos"
        elif entrantes and not salientes:
            rol_t = "maestro"
        elif salientes:
            rol_t = "detalle"
        else:
            rol_t = "suelta"
        info_tablas[t] = {"rol": rol_t, "sinonimos": _etiquetas(entidad[t]), "columnas": columnas,
                          "claves": por_rol["clave"], "fechas": por_rol["fecha"], "medidas": por_rol["medida"],
                          "atributos": por_rol["atributo"], "banderas": por_rol["bandera"]}

    return {"tablas": info_tablas, "relaciones": relaciones, "vecinas": vecinas, "padres": padres}


def _norm(nombre):
    return str(nombre or "").split(".")[-1].strip().strip('[]"`').lower()


def relacion_entre(mapa, tabla_a, col_a, tabla_b, col_b):
    """La relación del mapa que une esas dos columnas (en cualquier sentido), o None."""
    a, ca, b, cb = _norm(tabla_a), _norm(col_a), _norm(tabla_b), _norm(col_b)
    for r in mapa.get("relaciones", []):
        par = (_norm(r["tabla_origen"]), _norm(r["columna_origen"]),
               _norm(r["tabla_destino"]), _norm(r["columna_destino"]))
        if par == (a, ca, b, cb) or par == (b, cb, a, ca):
            return r
    return None


def revisar_joins(sql, mapa):
    """¿Los JOIN ... ON del SQL siguen relaciones del mapa?

    Devuelve (fraccion, fuera): fraccion = JOIN verificables que siguen una
    relación conocida / JOIN verificables (None si no hay ninguno: una sola
    tabla, o sólo uniones contra CTEs/subconsultas); fuera = los que no, en
    texto («a.x = b.y»). Un JOIN con clave compuesta cuenta si TODAS sus
    columnas siguen relaciones.
    """
    from control_resultado import joins_del_sql   # tarde: evita catalogo → mapa → control → conectores → catalogo
    total, buenos, fuera = 0, 0, []
    for j in joins_del_sql(sql or ""):
        if not j.get("verificable"):
            continue
        total += 1
        pares = list(zip(j["col_base"], j["col_unida"]))
        if pares and all(relacion_entre(mapa, j["base"], cb, j["unida"], cu) for cb, cu in pares):
            buenos += 1
        else:
            fuera.append(" AND ".join(f"{j['base']}.{cb} = {j['unida']}.{cu}" for cb, cu in pares))
    return (buenos / total if total else None), fuera


def joins_validos(sql, mapa):
    """Fracción de los JOIN del SQL que siguen una relación del mapa (None si no hay JOIN verificable)."""
    return revisar_joins(sql, mapa)[0]


# ──────────────────────────────────────────────────────────────
# 5) El bloque del prompt
# ──────────────────────────────────────────────────────────────
_RESERVADAS = set("""
order group user table select from where key index desc asc by values check column default primary
references limit offset union join left right full inner outer cross on as case when then else end and
or not null like in is between exists all any distinct top percent having into insert update delete create
drop alter grant revoke transaction schema database procedure function view trigger constraint foreign
unique set
""".split())


def requiere_comillas(nombre):
    """Un nombre que hay que citar en el SQL: con espacios/símbolos o palabra reservada."""
    n = str(nombre)
    return not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", n) or n.lower() in _RESERVADAS


def _cita(nombre):
    return '"' + str(nombre).replace('"', '""') + '"' if requiere_comillas(nombre) else str(nombre)


def _linea_join(r):
    nota = "" if r["origen"] == "declarada" else "  (deducida por el nombre)"
    return (f"- {_cita(r['tabla_origen'])}.{_cita(r['columna_origen'])} = "
            f"{_cita(r['tabla_destino'])}.{_cita(r['columna_destino'])}{nota}")


def bloque_prompt(mapa, tablas=None, privado=False, max_columnas=12, max_joins=30, max_caminos=10):
    """El mapa como texto para el prompt de generación ('' si no aporta nada).

    tablas: las que van al prompt (las recuperadas). Sólo se nombran ésas y,
    en los caminos, las del medio (que el mapa ya tiene recortadas por rol).
    privado: versión mínima — JOINs, caminos y nombres a citar. Nunca lleva
    valores de ejemplo (el mapa no los tiene: se arma sin leer datos).
    """
    info = mapa.get("tablas", {})
    sel = [t for t in (tablas if tablas is not None else list(info)) if t in info]
    sel = list(dict.fromkeys(sel))
    if not sel:
        return ""
    lineas = ["MAPA SEMÁNTICO: roles, sinónimos y JOINs válidos (deducido de nombres, tipos y claves del "
              "esquema; no usa datos)."]
    if not privado:
        lineas.append("Tablas:")
        for t in sel:
            it = info[t]
            partes = [f"- {_cita(t)} [{it['rol']}]"]
            if it["sinonimos"]:
                partes.append("≈ " + "; ".join(it["sinonimos"]))
            for etiqueta, clave in (("medidas", "medidas"), ("fechas", "fechas"), ("atributos", "atributos"),
                                    ("banderas", "banderas"), ("claves", "claves")):
                cols = it[clave][:max_columnas]
                if cols:
                    nombres = []
                    for c in cols:
                        sin = it["columnas"].get(c, {}).get("sinonimos") or []
                        nombres.append(_cita(c) + (f" ({sin[0]})" if sin and clave != "claves" else ""))
                    partes.append(f"{etiqueta}: " + ", ".join(nombres))
            lineas.append(" · ".join(partes))
    conj = set(sel)
    directas = [r for r in mapa.get("relaciones", []) if r["tabla_origen"] in conj and r["tabla_destino"] in conj]
    if directas:
        lineas.append("JOINs válidos (uní estas tablas SOLO por estas columnas):")
        lineas += [_linea_join(r) for r in directas[:max_joins]]
    vecinas, padres = mapa.get("vecinas", {}), mapa.get("padres", {})
    hijos = _hijos(padres)
    caminos = []
    for i, a in enumerate(sel):
        for b in sel[i + 1:]:
            if b in vecinas.get(a, ()) or len(caminos) >= max_caminos:
                continue
            camino = camino_tablas(padres, a, b, 3, hijos=hijos)
            if not camino or len(camino) < 3:
                continue
            pasos = []
            for x, y in zip(camino, camino[1:]):
                r = next((r for r in mapa["relaciones"] if {r["tabla_origen"], r["tabla_destino"]} == {x, y}), None)
                if r:
                    pasos.append(_linea_join(r)[2:].replace("  (deducida por el nombre)", ""))
            caminos.append(f"- {_cita(a)} → {_cita(b)}: " + " ; ".join(pasos))
    if caminos:
        lineas.append("Caminos entre tablas que no se unen directo:")
        lineas += caminos
    citar = [t for t in sel if requiere_comillas(t)]
    citar += [f"{t}.{c}" for t in sel for c in info[t]["columnas"] if requiere_comillas(c)]
    if citar:
        lineas.append("Nombres que van citados (\"…\"; [..] en SQL Server, `..` en MySQL): " + ", ".join(citar))
    if len(lineas) == 1:
        return ""
    return "\n".join(lineas)
