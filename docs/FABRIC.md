# © 2026 Martín Viera. Todos los derechos reservados.

# Conectar MV SQL NLP a Microsoft Fabric

## Qué es, en una línea

Fabric no es un motor nuevo: el **SQL analytics endpoint** de un Lakehouse y el
de un Warehouse hablan TDS —el mismo protocolo que SQL Server— en el 1433. Así
que el motor, el dialecto T-SQL, el validador anti-alucinación y la barrera de
solo lectura funcionan tal cual.

Lo único distinto es **cómo se entra**: Fabric no acepta usuario y contraseña de
SQL. Solo Entra ID (el ex Azure AD). Eso es lo que se agregó.

---

## Requisitos

| | |
|---|---|
| Driver del sistema | **ODBC Driver 18 for SQL Server** ([descarga de Microsoft](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)) |
| Paquete Python | `pip install pyodbc` |

El 17 no sirve para el modo automático: no soporta `ActiveDirectoryDefault`. Si
ves un error de autenticación al conectar, lo primero a revisar es la versión
del driver.

---

## El servidor: de dónde se copia

En el portal de Fabric, sobre el **Lakehouse** o el **Warehouse**:

> Settings → **SQL analytics endpoint** → **SQL connection string**

Queda algo así:

```
abc123def456.datawarehouse.fabric.microsoft.com
```

Ese string va en el campo "SQL connection string del endpoint". El campo
"Lakehouse o Warehouse" es el **nombre** del ítem, no el workspace.

---

## Los tres modos de entrar, y cuándo usar cada uno

### 1 · Con mi cuenta (interactivo)

Abre el navegador, resolvés MFA ahí y listo. **No se guarda ningún secreto en
ningún lado.**

Es el modo para trabajar desde tu laptop. Si la empresa tiene MFA obligatorio
—y Adium seguro lo tiene— este es el único que funciona sin pedirle nada a
nadie.

### 2 · Service principal

Para un **agente, un job o cualquier cosa desatendida**: no hay una persona
frente a la pantalla para aprobar el login.

- **Usuario** = Application (client) ID del app registration
- **Password** = el secreto de ese app registration

Lo que hay que pedirle a quien administre el tenant:

1. Un **app registration** en Entra ID, con un client secret.
2. Que en el **workspace de Fabric** se agregue ese service principal con rol
   **Viewer** (alcanza: el producto solo lee).
3. Que esté habilitado *Service principals can use Fabric APIs* en la
   configuración del tenant — suele estar apagado por defecto y es el paso que
   más veces frena esto.

### 3 · Automática

El driver encuentra la identidad solo. Sirve adentro de un **notebook de
Fabric**, en una VM de Azure con managed identity, o en cualquier máquina con
`az login` hecho. Sin credenciales de ningún tipo.

---

## Seguridad de la conexión

Dos cosas que la cadena hace siempre y no son configurables:

- **`Encrypt=yes`.** Fabric va por internet; sin cifrar, las consultas y los
  datos viajan en claro.
- **Nunca `TrustServerCertificate=yes`.** Contra el SQL Server interno de una
  empresa eso se usa porque esos servidores tienen certificados autofirmados.
  Fabric tiene un certificado público de verdad, así que aceptarle cualquiera
  solo habilitaría a un intermediario a hacerse pasar por Microsoft. Es la
  diferencia entre "cifrado" y "cifrado con alguien que sabés quién es".

Y la de siempre: **el producto solo ejecuta `SELECT` y `WITH`**. Acá eso no es
redundante — el endpoint de un Lakehouse es de solo lectura por diseño, pero un
**Warehouse de Fabric sí acepta escrituras**. Contra un Warehouse, la barrera
del producto es la única que queda.

---

## Qué funciona distinto que contra SQL Server

Dos cosas del catálogo, y las dos degradan sin romper nada:

| | SQL Server | Fabric | Consecuencia |
|---|---|---|---|
| **Cantidad de filas** | sale de `sys.partitions`, gratis | no existe: las tablas son archivos Delta/Parquet | queda en blanco |
| **Claves foráneas** | declaradas y aplicadas | el Lakehouse no tiene; el Warehouse solo las admite `NOT ENFORCED` | los joins se infieren por nombre de columna |

Sobre el tamaño: **no se cae a un `COUNT(*)` por tabla.** Contra un lakehouse
eso serían N consultas pesadas cada vez que alguien conecta. Preferimos no
saber el tamaño antes que colgar la app para averiguarlo — y, sobre todo,
preferimos dejarlo en blanco antes que reportar 0, que le diría a la IA que la
tabla está vacía.

Sobre los joins: el catálogo ya deduce relaciones por nombre de columna cuando
no hay FKs declaradas. Es peor que tenerlas, pero es exactamente para esto que
esa inferencia existe. Si el Warehouse las declara —aunque sea
`NOT ENFORCED`— se leen y se usan.

---

## Lo que todavía no está probado

**La conexión no se probó contra un tenant de Fabric real.** No tengo uno.

Lo que sí está probado, y con tests que corren en cada push:

- La cadena de conexión que se arma para cada uno de los tres modos.
- Que siempre cifre y que nunca acepte cualquier certificado.
- Que el modo service principal sin credenciales corte con un mensaje que dice
  qué poner, en vez de fallar al conectar.
- Que el catálogo salga completo aunque falten `sys.partitions` y las FKs, con
  el tamaño en blanco y no en 0.
- Que contra un SQL Server normal no se haya perdido nada.

La primera conexión real es el paso que falta, y es de dos minutos: driver 18,
`pip install pyodbc`, el string del portal y el modo "Con mi cuenta".

---

## Lo que sigue, si Adium lo adopta

Este conector es la puerta de entrada. Con eso resuelto, lo que se abre:

- **Notebooks de Fabric**: el producto corre en modo servidor adentro del
  tenant (ver [MODO_SERVIDOR.md](MODO_SERVIDOR.md)), con autenticación
  automática y sin que ningún dato salga de la infraestructura de ellos.
- **Agentes**: el modo service principal es justamente el que necesita un
  agente para consultar la base sin una persona aprobando cada login.
- **Proveedor de IA**: el producto ya soporta Claude, GPT y Ollama local. Si
  Anthropic todavía no está habilitado en el tenant, se puede arrancar con lo
  que sí esté y cambiar el proveedor después sin tocar nada más — es un
  desplegable en la pantalla de conexión.
