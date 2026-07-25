# 🚀 Puesta en producción — checklist

Todo lo que hay que configurar antes de cobrarle a un cliente. Sin esto, o no
cobrás, o cobrás y no podés entregar, o entregás y perdés plata.

## 1. Variables de entorno en Vercel

`Project → Settings → Environment Variables`. Todas en **Production**.

| Variable | Para qué | Si falta |
|---|---|---|
| `MP_ACCESS_TOKEN` | Cobrar por MercadoPago (token de **producción**, no de prueba) | No se puede cobrar nada |
| `LICENSE_SECRET` | Firmar las licencias de descarga. Cadena aleatoria larga, **nunca** la compartas | Nadie puede descargar lo que compró |
| `OWNER_TOKEN` | Entrar al panel del dueño en `/owner` | El panel responde 503 (cerrado, que es lo correcto) |
| `ANTHROPIC_API_KEY` | La IA del plan "créditos embebidos" | El plan de créditos no funciona |
| `KV_REST_API_URL` + `KV_REST_API_TOKEN` | Contador de créditos | **El plan de créditos se rechaza** (a propósito, ver abajo) |

Para generar `LICENSE_SECRET` y `OWNER_TOKEN`:

```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

## 2. Vercel KV — obligatorio antes de vender créditos

`Project → Storage → Create Database → KV`, y conectalo al proyecto. Las dos
variables `KV_*` se agregan solas.

**Por qué no es opcional:** el proxy de IA descuenta un crédito por consulta
usando KV. Sin KV no hay contador, y sin contador una licencia de 100 créditos
(US$ 9) puede consumir tu API key de Anthropic sin límite.

Por eso `/api/ai-proxy` **falla cerrado**: sin KV responde 503 y no llama a la
IA. El cliente ve un mensaje que le sugiere usar su propia API key. Es
deliberado: se corta el servicio, nunca la billetera.

> Los planes de **suscripción** e **implementación** funcionan sin KV — el
> cliente pone su propia clave de IA. Solo el plan de créditos lo necesita.

## 3. MercadoPago

1. Credenciales de **producción** en <https://www.mercadopago.com.uy/developers/panel>.
2. Webhook apuntando a `https://TU-DOMINIO/api/webhook`, evento `payment`.
3. **Suscripciones habilitadas** en la cuenta: los planes mensuales usan
   `preapproval`, que es un producto distinto del checkout común. Si la cuenta
   no lo tiene habilitado, `/api/create-subscription` devuelve error de
   MercadoPago — pedilo por soporte antes de publicar precios mensuales.

## 4. Release en GitHub (el .exe y el .zip)

La web enlaza a `releases/latest`. Si no hay Release publicado, esos botones
llevan a una página vacía.

`Actions → "Build MV SQL NLP releases" → Run workflow` (rama `main`).
Compila el instalador de Windows en un runner Windows real y sube el zip
autoinstalable al mismo Release.

> Este paso lo tiene que disparar una persona: la integración de Claude no
> tiene permiso de `workflow_dispatch` (responde 403).

## 5. Probar de punta a punta antes de publicitar

```bash
cd web && npm test        # 36 pruebas, deben pasar todas
```

Y una compra real con tarjeta propia, del monto más barato:

1. Comprar el pack de 100 créditos (US$ 9).
2. Verificar que llega a `/gracias` y que la descarga funciona.
3. Abrir el zip y confirmar que trae `licencia_mvsql.json`.
4. Abrir la app, elegir "MV SQL Créditos" y hacer una consulta.
5. Entrar a `/owner` con el `OWNER_TOKEN` y confirmar que la venta aparece.

Si los 5 pasos dan, el negocio está operativo.

## 6. Qué mirar la primera semana

- `/owner` — ventas, ticket promedio y tasa de aprobación de pagos.
- Vercel → Logs — errores 500 en `/api/*`.
- Consumo en <https://console.anthropic.com> — si sube sin ventas de créditos,
  algo anda mal.
