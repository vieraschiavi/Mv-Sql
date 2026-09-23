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
const { spawnSync } = require("child_process");

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

  /** El compose RESUELTO por Docker, no el texto del archivo.
   *
   *  `docker compose config` no necesita demonio: parsea, valida el
   *  esquema y expande las variables. Eso es mucho más fuerte que un
   *  regex sobre el YAML crudo — un regex ve "${MVSQL_BIND:-127.0.0.1}"
   *  y se da por satisfecho sin saber a qué resuelve, y no se entera de
   *  un YAML mal indentado que reventaría recién en el servidor del
   *  cliente (comprobado: con el archivo roto a propósito, sale con 1).
   *
   *  Si no hay CLI de docker se cae al regex, que igual cubre lo básico. */
  function resolver(env = {}) {
    const r = spawnSync("docker", ["compose", "config", "--format", "json"],
      { cwd: path.join(RAIZ, "servidor"), encoding: "utf8",
        env: { ...process.env, ...env } });
    return r.status === 0 ? { ok: true, cfg: JSON.parse(r.stdout).services.mvsql }
                          : { ok: false, error: `${r.stdout || ""}${r.stderr || ""}` };
  }
  const hayDocker = spawnSync("docker", ["--version"], { encoding: "utf8" }).status === 0;
  const resuelto = hayDocker ? resolver() : { ok: false, error: "no hay CLI de docker" };

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
    if (resuelto.ok) {
      const vol = (resuelto.cfg.volumes || []).find((v) => v.target === "/datos");
      assert.ok(vol, "ningún volumen queda montado en /datos: el estado del " +
        "cliente se perdería al recrear el contenedor");
      assert.strictEqual(resuelto.cfg.environment.MVSQL_DATOS, "/datos");
      return;
    }
    assert.match(composeCodigo, /mvsql-datos:\/datos/,
      "el compose no monta el volumen en /datos");
  });

  await test("hay CLI de docker para resolver el compose (en CI es obligatorio)", () => {
    // Sin docker, los tests de abajo caen al regex o directamente se
    // saltean — o sea que el gate desaparece sin que nadie lo note. En una
    // máquina de desarrollo eso es aceptable; en CI es que alguien rompió
    // el runner, y tiene que doler. Mismo criterio que con makensis en
    // instalador-nsis.test.js.
    assert.ok(hayDocker || !process.env.CI,
      "no hay CLI de docker y esto es CI: los chequeos del compose quedaron " +
      "degradados a regex sin avisar. ubuntu-latest lo trae de fábrica, así " +
      "que si falta es que cambió la imagen del runner.");
  });

  await test("el compose es válido para Docker, no solo texto que matchea un regex", () => {
    if (!hayDocker) { console.log("      (sin CLI de docker: solo se validó por regex)"); return; }
    assert.ok(resuelto.ok,
      "`docker compose config` falló — el archivo no levanta en el servidor " +
      `del cliente:\n${resuelto.error}`);
  });

  console.log("\n== No queda expuesto sin que alguien lo decida ==");

  await test("el puerto se publica SOLO en 127.0.0.1 por defecto", () => {
    if (resuelto.ok) {
      // Lo que Docker VA A HACER, no lo que dice el YAML.
      assert.strictEqual(resuelto.cfg.ports[0].host_ip, "127.0.0.1",
        `el bind resuelve a ${resuelto.cfg.ports[0].host_ip}: el puerto queda ` +
        "abierto a toda la red del cliente sin que nadie lo haya pedido");
      return;
    }
    const linea = composeCodigo.split("\n").find((l) => /:8791"/.test(l));
    assert.ok(linea, "no se encontró el mapeo de puertos");
    assert.match(linea, /\$\{MVSQL_BIND:-127\.0\.0\.1\}/,
      `el default del bind no es 127.0.0.1 (${linea.trim()})`);
  });

  await test("con MVSQL_BIND definida pero VACÍA sigue cerrado", () => {
    // El caso que casi se cuela. En Docker Compose `${VAR:-def}` aplica el
    // default si VAR está sin definir O VACÍA; `${VAR-def}` (sin los dos
    // puntos) solo si está sin definir. Con la segunda forma y un
    // "MVSQL_BIND=" suelto en el .env —que es lo más natural de escribir
    // para decir "dejá el default"— host_ip queda vacío y Docker publica
    // en TODAS las interfaces. Medido: con `:-` da 127.0.0.1, sin los dos
    // puntos da None. No hay error, no hay aviso: la base del cliente
    // queda expuesta a su red y nadie se entera.
    if (!hayDocker) return;
    const r = resolver({ MVSQL_BIND: "" });
    assert.ok(r.ok, r.error);
    assert.strictEqual(r.cfg.ports[0].host_ip, "127.0.0.1",
      "con MVSQL_BIND vacía el bind quedó en " +
      `${JSON.stringify(r.cfg.ports[0].host_ip)}: usá \${MVSQL_BIND:-127.0.0.1} ` +
      "(con dos puntos), no ${MVSQL_BIND-127.0.0.1}");
  });

  await test("TODAS las variables del compose usan :- (no solo el bind)", () => {
    // La misma trampa aplica a cualquier otra variable que se agregue
    // después. Se chequea la forma, no un caso puntual, así que el próximo
    // ${ALGO-default} se frena acá aunque nadie escriba un test nuevo.
    const sinDosPuntos = [...composeCodigo.matchAll(/\$\{([A-Z_]+)([-?])/g)]
      .filter((m) => m[2] === "-")
      .map((m) => m[1]);
    assert.deepStrictEqual(sinDosPuntos, [],
      "estas variables usan ${VAR-default} en vez de ${VAR:-default}, así que " +
      "una definición vacía las deja sin default: " + sinDosPuntos.join(", "));
  });

  await test("MVSQL_BIND=0.0.0.0 SÍ abre a la red (la doc no miente)", () => {
    // docs/MODO_SERVIDOR.md le dice al cliente que con esa variable puede
    // exponerlo. Si la interpolación estuviera mal escrita, el default
    // ganaría siempre y la instrucción sería falsa — sin ningún error.
    if (!hayDocker) return;
    const r = resolver({ MVSQL_BIND: "0.0.0.0" });
    assert.ok(r.ok, r.error);
    assert.strictEqual(r.cfg.ports[0].host_ip, "0.0.0.0",
      "MVSQL_BIND no tiene efecto: la doc promete algo que no pasa");
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
    if (resuelto.ok) {
      assert.strictEqual(resuelto.cfg.read_only, true, "falta read_only: true");
      assert.ok((resuelto.cfg.security_opt || []).includes("no-new-privileges:true"),
        "falta no-new-privileges");
      assert.deepStrictEqual(resuelto.cfg.cap_drop, ["ALL"], "falta cap_drop: ALL");
      return;
    }
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
