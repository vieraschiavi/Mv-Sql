# 📄 Propuesta de implementación — plantilla

Copiar, reemplazar lo que está `[entre corchetes]` y mandar como PDF el mismo día
de la demo.

**Lo más importante de este documento no es el precio: es la sección "Qué NO
incluye".** Es lo único que impide que la implementación se convierta en
desarrollo a medida gratis — el error que, según el pre-mortem, quema tres meses.

---

## Propuesta — MV SQL NLP para [EMPRESA]

**Para:** [Nombre y cargo]
**De:** Martín Viera — MV SQL NLP
**Fecha:** [fecha] · **Validez de esta propuesta:** 30 días

### 1. Lo que conversamos

En [EMPRESA], cuando alguien necesita un dato que no está en un reporte fijo,
hoy se lo pide a [Sistemas / el analista / vos] y la respuesta llega en
**[X días]**. Eso genera dos costos: el tiempo de quien lo prepara, y las
decisiones que se toman sin el dato porque llegó tarde.

Me mencionaste estas preguntas como las más frecuentes:

1. [pregunta 1, con sus palabras]
2. [pregunta 2]
3. [pregunta 3]

### 2. Qué vamos a hacer

Dejar MV SQL NLP funcionando sobre [su base / su ERP], para que esas preguntas
—y las que surjan— se respondan en segundos, escribiéndolas en español, por la
persona que las necesita.

| Etapa | Qué incluye | Cuándo |
|---|---|---|
| **1. Relevamiento** | Revisión del esquema, entrevista con quien conoce los datos, definición del vocabulario del negocio (qué significa exactamente "cobrado", "activo", "vencido" en [EMPRESA]) | Semana 1 |
| **2. Conexión** | Usuario de solo lectura, instalación, prueba con datos reales | Semana 1 |
| **3. Carga de consultas** | Las [N] preguntas de negocio acordadas, guardadas y verificadas contra los números que ustedes ya tienen | Semana 2 |
| **4. Usuarios y permisos** | Alta de [N] usuarios con sus roles: quién ve qué tablas, quién exporta, quién audita | Semana 2 |
| **5. Capacitación** | Sesión de 90 minutos con el equipo + manual con sus propios ejemplos | Semana 2 |

**Plazo total: 2 semanas** desde que tenemos el acceso de solo lectura.

### 3. Qué NO incluye

Para que no haya sorpresas de ningún lado:

- Desarrollo de software a medida, módulos nuevos o cambios en el programa.
- Migración, limpieza o corrección de datos existentes.
- Integraciones con sistemas fuera de la base acordada.
- Consultas de negocio adicionales por encima de las [N] acordadas —
  se cotizan aparte a [US$ X] cada una, o las cargan ustedes mismos (el
  programa está hecho para eso).
- Infraestructura, licencias de base de datos o servidores.
- Soporte posterior al mes de garantía (ver punto 5).

### 4. Inversión

| Concepto | Importe |
|---|---|
| Implementación completa (etapas 1 a 5) | **US$ 2.500** |
| Licencia Profesional — 3 meses | incluida |
| **Total al inicio** | **US$ 2.500** |

Se factura 50% al comenzar y 50% contra entrega. Pago por transferencia o
MercadoPago. Precios más IVA si corresponde.

### 5. Después de la implementación

- **Garantía:** 30 días. Si algo de lo entregado no funciona como acordamos, se
  corrige sin costo.
- **Licencia:** a partir del cuarto mes, US$ [29/79] por mes.
- **Soporte y mantenimiento (opcional):** US$ 150 por mes — cambios de esquema,
  consultas nuevas, prioridad de respuesta en 24 horas hábiles.

### 6. Compromisos

**De mi parte:** todo el trabajo con conexión de **solo lectura** — el programa
solo ejecuta SELECT, nunca modifica ni borra nada. Los datos de [EMPRESA] no
salen de su red: a la inteligencia artificial solo viajan los nombres de tablas
y columnas, nunca las filas. Confidencialidad total sobre lo que vea.

**De su parte:** un usuario de solo lectura, una persona de referencia que
conozca los datos (unas 4 horas repartidas en las dos semanas), y la validación
de los números al cierre.

### 7. Para avanzar

Respondé este mail con un "vamos" y coordinamos el arranque. Si preferís empezar
más chico, existe la opción **Express (US$ 900)**: una sola base, esquema
acotado, hasta 10 consultas, sin gestión de usuarios.

Gracias por el tiempo de hoy.

**Martín Viera**
vieraschiavi@gmail.com · mvsqlnlp.com

---

## Notas para vos (borrar antes de enviar)

- **Nunca mandes esto sin haber hecho la demo.** El precio sin el problema
  demostrado siempre parece caro.
- **[N] consultas: poné un número, nunca "las que necesiten".** Diez está bien
  para empezar. Es el límite que te protege.
- Si piden descuento: no bajes el precio, **sacá alcance**. Menos consultas o
  menos usuarios. Bajar el precio enseña que el primero era inventado.
- Si piden pagar todo al final: 50/50 o no hay proyecto. El anticipo no es por
  la plata, es la señal de que el proyecto es real.
- Guardá cada propuesta enviada. A los 7 días sin respuesta, un mail de una
  línea: *"¿Seguimos o lo dejamos para más adelante?"*. Cierra más que insistir.
