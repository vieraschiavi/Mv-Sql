# 💳 Integración de MercadoPago — MV SQL NLP

Cómo cobrar suscripciones y créditos desde la web (Vercel) con MercadoPago,
y cómo activar las licencias en la app.

## Modelo de cobro

| Producto | Mecanismo MP | Nota |
|---|---|---|
| Planes Personal / Profesional / Empresa (US$ 15 / 29 / 79 mes) | **Suscripciones (preapproval)** | Débito automático mensual en moneda local |
| Paquetes de créditos 100 / 500 / 2000 (US$ 9 / 35 / 110) | **Checkout Pro (preference)** | Pago único; acreditar créditos al aprobarse |
| Prueba 3 días | Sin pago | Licencia trial emitida al registrarse (email) |

Comisión de MercadoPago (Argentina, dinero disponible al instante): ~6,3 % + IVA
por transacción (verificar la tarifa vigente en el panel). Considerarla en el precio.

## Arquitectura mínima (sin servidor propio)

La web es estática en Vercel; los endpoints de pago van como
**Vercel Serverless Functions** (`web/api/*.js`):

```
web/api/crear-preferencia.js   → crea preference de Checkout Pro (créditos)
web/api/crear-suscripcion.js   → crea preapproval (planes mensuales)
web/api/webhook.js             → recibe notificaciones IPN/webhook de MP
```

Variables de entorno en Vercel: `MP_ACCESS_TOKEN` (producción) y
`MP_WEBHOOK_SECRET`.

### Ejemplo: crear preferencia de créditos

```js
// web/api/crear-preferencia.js
import { MercadoPagoConfig, Preference } from "mercadopago";

const mp = new MercadoPagoConfig({ accessToken: process.env.MP_ACCESS_TOKEN });

const PAQUETES = {
  cred100:  { title: "MV SQL NLP — 100 créditos",  unit_price: 9 },
  cred500:  { title: "MV SQL NLP — 500 créditos",  unit_price: 35 },
  cred2000: { title: "MV SQL NLP — 2000 créditos", unit_price: 110 },
};

export default async function handler(req, res) {
  const { paquete, email } = req.body;
  const item = PAQUETES[paquete];
  if (!item) return res.status(400).json({ error: "paquete inválido" });

  const pref = await new Preference(mp).create({ body: {
    items: [{ ...item, quantity: 1, currency_id: "USD" }],
    payer: { email },
    back_urls: {
      success: "https://mvsqlnlp.com/gracias",
      failure: "https://mvsqlnlp.com/pago-fallido",
    },
    auto_return: "approved",
    external_reference: `${paquete}:${email}`,
    notification_url: "https://mvsqlnlp.com/api/webhook",
  }});
  res.json({ init_point: pref.init_point });
}
```

### Webhook → emisión de licencia

Al recibir `payment.approved`:
1. Verificar el pago con la API de MP (`GET /v1/payments/{id}`) — nunca confiar
   solo en el webhook.
2. Generar una **clave de licencia** firmada (JWT con email, plan, vencimiento,
   créditos) y enviarla por email.
3. La app de escritorio valida la licencia offline (firma) y descuenta créditos
   localmente, sincronizando cuando hay conexión.

## Facturación de créditos de IA

El plan con créditos usa **nuestra** API key (server-side proxy):
- Un endpoint `web/api/consulta-ia.js` recibe la petición de la app con la
  licencia, valida créditos restantes, llama al proveedor elegido y descuenta 1 crédito.
- Ventaja: el cliente no necesita API key y facturamos todo junto (el margen de
  crédito cubre el costo de la IA — ver PLAN_DE_NEGOCIO.md).

## Checklist para salir a producción

- [ ] Cuenta MercadoPago verificada (vendedor) + credenciales de producción
- [ ] Alta de suscripciones (preapproval) aprobada por MP
- [ ] Webhook con verificación de firma (`x-signature`)
- [ ] Emails transaccionales (licencia, recibo) — Resend/SendGrid gratis hasta 100/día
- [ ] Página de términos y política de privacidad (links del footer)
- [ ] Precios en moneda local: MP convierte USD→ARS/UYU automáticamente, pero
      conviene publicar precio local fijo por país para evitar sorpresas
