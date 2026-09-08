/* © 2026 Martín Viera. Todos los derechos reservados. */

/** El modo servidor: lo que solo se rompe en la máquina del cliente.
 *
 * app-python/tests/test_modo_servidor.py prueba la parte ejecutable —
 * que el estado caiga en el volumen y en ningún otro lado. Eso se corre
 * de verdad y es el corazón del asunto.
 *
 * Este archivo cubre la otra mitad: el Dockerfile, el compose y el .sh.
 * Nada de eso se puede ejecutar en CI (no hay demonio Docker), pero cada
 * línea de acá corresponde a algo que, si está mal, falla RECIÉN en el
 * servidor de un cliente y con un consultor mirando:
 *
 *   - un COPY que falta → `docker compose exec ... preparar-propietario`
 *     tira ModuleNotFoundError y la instalación queda en trial
 *   - un puerto publicado en 0.0.0.0 por defecto → la base del cliente
 *     queda expuesta a toda su red interna sin que nadie lo haya decidido
 *   - la telemetría de Streamlit sin apagar → llamadas salientes desde
 *     una red corporativa que nadie pidió
 *   - un secreto en el compose → se filtra solo, porque un compose se
 *     commitea y se manda por chat
 */
const assert = require("assert");
const fs = require("fs");
const path = require("path");

let pasadas = 0, falladas = 0;
async function test(n, fn) {
  try { await fn(); console.log(`  ✓ ${n}`); pasadas++; }
  catch (e) { console.log(`  ✗ ${n}\n      ${e.message}`); falladas++; }
}

const RAIZ = path.join(__dirname, "..", "..");
const leer = (...p) => fs.readFileSync(path.join(RAIZ, ...p), "utf8");

/** Sin comentarios: en estos archivos casi todo lo que se busca está
 *  además EXPLICADO en un comentario arriba, así que un indexOf sobre el
 *  texto entero da verde aunque la línea real no esté. Ya pasó dos veces
 *  en este repo (licencia_owner.json, configurarCarpetaDatos). */
const sinComentarios = (txt) =>
  txt.split("\n").filter((l) => !/^\s*#/.test(l)).join("\n");

(async () => {
  const DOCKERFILE = leer("servidor", "Dockerfile");
  const COMPOSE = leer("servidor", "docker-compose.yml");
  const SH = leer("servidor", "arrancar-sin-docker.sh");
  const IGNORE = leer(".dockerignore");
  const dfCodigo = sinComentarios(DOCKERFILE);
  const composeCodigo = sinComentarios(COMPOSE);

  console.log("\n== La imagen se lleva lo que necesita ==");

  await test("copia el preparador de propietario Y su dependencia", () => {
    // Sin el segundo COPY, el primero igual entra y todo "parece bien":
    // el error aparece cuando alguien corre el script en el servidor del
    // cliente y se come un ModuleNotFoundError sobre generar_conversor_owner.
    assert.match(dfCodigo, /COPY\s+servidor\/preparar-propietario\.py\s+\/app\//,
      "falta el COPY de servidor/preparar-propietario.py");
    assert.match(dfCodigo, /COPY\s+tools\/generar_conversor_owner\.py\s+\/app\/tools\//,
      "el preparador importa LICENCIA de generar_conversor_owner y ese archivo " +
      "no entra a la imagen: el script explota al correrlo");
  });

  await test("tools/ no está excluida del contexto (si no, ese COPY falla)", () => {
    const excluyeTools = IGNORE.split("\n")
      .filter((l) => !/^\s*#/.test(l))
      .some((l) => /^tools\/\s*$/.test(l.trim()));
    const reincluye = /^!tools\/generar_conversor_owner\.py\s*$/m.test(IGNORE);
    assert.ok(!excluyeTools || reincluye,
      ".dockerignore excluye tools/ entera y no re-incluye " +
      "generar_conversor_owner.py: el build falla en el COPY");
  });

  await test("el estado va a /datos, que es el volumen — no a /app, que se pisa", () => {
    assert.match(dfCodigo, /ENV\s+MVSQL_DATOS=\/datos/,
      "sin MVSQL_DATOS la app escribe en /app, que se reemplaza entero en " +
      "cada build: el cliente pierde equipo, auditoría y licencia al actualizar");
    assert.match(composeCodigo, /mvsql-datos:\/datos/,
      "el compose no monta el volumen en /datos");
  });

  console.log("\n== No queda expuesto sin que alguien lo decida ==");

  await test("el puerto se publica SOLO en 127.0.0.1 por defecto", () => {
    const linea = composeCodigo.split("\n").find((l) => /:8791"/.test(l));
    assert.ok(linea, "no se encontró el mapeo de puertos");
    assert.match(linea, /\$\{MVSQL_BIND:-127\.0\.0\.1\}/,
      `el default del bind no es 127.0.0.1 (${linea.trim()}): así el puerto ` +
      "queda abierto a toda la red del cliente sin que nadie lo haya pedido");
  });

  await test("el .sh también arranca en 127.0.0.1 salvo que le digan lo contrario", () => {
    assert.match(SH, /BIND="\$\{MVSQL_BIND:-127\.0\.0\.1\}"/,
      "el camino sin Docker tiene que tener el MISMO default seguro que el compose");
  });

  await test("la telemetría de Streamlit está apagada en LOS DOS caminos", () => {
    // Streamlit por defecto manda estadísticas de uso afuera. En la red de
    // un cliente, eso es tráfico saliente que nadie autorizó — y es lo
    // primero que salta en una auditoría de seguridad.
    for (const [nombre, txt] of [["Dockerfile", dfCodigo], ["arrancar-sin-docker.sh", SH]]) {
      assert.match(txt, /gatherUsageStats=false/,
        `${nombre} no apaga browser.gatherUsageStats`);
    }
  });

  console.log("\n== Contención del contenedor ==");

  await test("no corre como root", () => {
    assert.match(dfCodigo, /^USER\s+mvsql\s*$/m,
      "el contenedor corre como root dentro de la red del cliente");
  });

  await test("sistema de archivos de solo lectura y sin privilegios nuevos", () => {
    assert.match(composeCodigo, /read_only:\s*true/, "falta read_only: true");
    assert.match(composeCodigo, /no-new-privileges:true/, "falta no-new-privileges");
    assert.match(composeCodigo, /cap_drop:\s*\n\s*-\s*ALL/, "falta cap_drop: ALL");
  });

  await test("el healthcheck mira /_stcore/health, no la portada", () => {
    // La portada de Streamlit devuelve 200 aunque el script haya reventado:
    // un healthcheck contra "/" reporta sano un contenedor roto.
    assert.match(dfCodigo, /_stcore\/health/,
      "el healthcheck no usa el endpoint real de salud de Streamlit");
  });

  console.log("\n== Ni un secreto en archivos que se comparten ==");

  await test("el compose no trae credenciales de ninguna base", () => {
    // Un docker-compose.yml se commitea, se copia a otro cliente y se manda
    // por chat. Las credenciales van por la pantalla de conexión y quedan
    // en el volumen.
    const sospechosas = composeCodigo.split("\n").filter((l) =>
      /(PASSWORD|PASSWD|SECRET|API_?KEY|TOKEN)\s*[:=]\s*\S/i.test(l) &&
      !/\$\{/.test(l));
    assert.deepStrictEqual(sospechosas, [],
      "hay algo que parece un secreto literal: " + sospechosas.join(" | "));
  });

  await test(".dockerignore deja afuera .env, licencias y datos de clientes", () => {
    for (const patron of [".env", "licencia_owner.json",
                          "app-python/licencia_mvsql.json", "app-python/auditoria.db"]) {
      assert.ok(IGNORE.split("\n").some((l) => l.trim() === patron),
        `.dockerignore no excluye ${patron}: puede terminar en una capa de la imagen`);
    }
  });

  console.log("\n== Está documentado y enlazado ==");

  await test("docs/MODO_SERVIDOR.md existe y dice el límite honesto", () => {
    const doc = leer("docs", "MODO_SERVIDOR.md");
    assert.ok(doc.length > 2000, "la doc quedó demasiado corta para servir de algo");
    assert.match(doc, /docker compose down -v/,
      "no explica cómo borrar los datos del cliente al terminar, que es el punto");
    assert.match(doc, /Ollama/,
      "no menciona la salida a internet de la IA ni la alternativa local: " +
      "es la primera pregunta del área de seguridad del cliente");
  });

  await test("FORMAS_DE_INSTALAR.md manda al modo servidor", () => {
    // Quien busca cómo instalar entra por ahí. Si el modo servidor no está
    // enlazado, no existe para nadie.
    const formas = leer("docs", "FORMAS_DE_INSTALAR.md");
    assert.match(formas, /MODO_SERVIDOR\.md/,
      "FORMAS_DE_INSTALAR.md no menciona docs/MODO_SERVIDOR.md");
  });

  console.log(`\n  ${pasadas} pasadas · ${falladas} falladas\n`);
  process.exit(falladas ? 1 : 0);
})();
