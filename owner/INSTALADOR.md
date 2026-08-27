# © 2026 Martín Viera. Todos los derechos reservados.

# Versión propietario — instalador completo, sin trial

Esta carpeta es para **probar el producto exactamente como lo recibe un cliente
que pagó la versión full**, sin límite de 7 días y sin tener que comprar nada.

No es una variante recortada ni una demo: es el mismo build que el del cliente,
con una licencia de plan `propietario` embebida que vence en 2099. Todo lo que
paga un cliente de Empresa está habilitado — stored procedures, optimizador de
CTE, los 5 puestos de equipo, exportación, auditoría.

## Cuál bajar

Hay dos productos y cada uno tiene su instalador de propietario.

| | Qué es | Requisitos | De dónde sale |
|---|---|---|---|
| **`MV-SQL-NLP-App-Setup-OWNER.exe`** | App de escritorio (Electron). **Autocontenida: no precisa nada instalado.** | Ninguno | Asset del último Release |
| **`MV-SQL-NLP-Setup-OWNER.exe`** | Producto Python/Streamlit (el del `.zip`) | Necesita Python en la PC — el instalador arma el resto solo (entorno virtual, dependencias, base demo) | `owner/instalador/` de este repo |

Si querés simplemente abrir y probar, andá al de **Electron**: doble clic e
instala, nada más. El de Python sirve para probar el otro producto de la suite.

## Dónde está el de Electron

En el **Release** de la última versión, junto al instalador de clientes:

```
https://github.com/vieraschiavi/Mv-Sql/releases/latest
```

Lo sube `.github/workflows/build-desktop.yml` en cada versión nueva.

### Por qué está en el Release y no commiteado acá

Pesa cerca de 90 MB. Un binario de ese tamaño commiteado queda en el historial
de git **para siempre** y en cada versión se suma otro: a los diez releases el
repositorio pesa un giga y cada `git clone` se lo baja entero. Un asset de
Release da lo mismo a un clic, siempre en la versión actual, sin ese costo.

## La guarda que lo protege

El paso que publica ese asset está condicionado a `github.event.repository.private`.

En un repositorio **público** cualquiera baja un asset de Release sin siquiera
loguearse, y este `.exe` abre sin trial y con licencia hasta 2099: publicarlo
ahí sería regalar el producto que se está vendiendo. Con esa condición el paso
directamente no corre si el repositorio no es privado — no depende de que
alguien se acuerde.

Si el repositorio vuelve a ser público, el instalador del propietario deja de
publicarse solo, y el resumen de la corrida explica por qué. Sigue quedando como
artefacto `mvsql-app-owner` en la pestaña Actions, que exige acceso al
repositorio.

## Alternativa sin instalar nada nuevo

Si ya tenés el producto **de cliente** instalado y no querés instalar otro, está
el conversor: instalás lo normal y un script le escribe la licencia de por vida
donde haya quedado. Ver `owner/README.md`.

## Qué NO hacer

- No subir ninguno de estos `.exe` a un Release de un repositorio público.
- No commitear `desktop/licencia_owner.json` ni `paquete/mvsql-nlp-app-OWNER.zip`
  (están en `.gitignore`): si la licencia del propietario entrara al repo,
  cualquier build —incluida la de clientes— saldría con acceso hasta 2099.
- No repartir estos instaladores: no vencen nunca.
