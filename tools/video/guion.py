"""
guion.py — texto del video de demo, en los tres idiomas.
==================================================================
Un solo lugar para el guion: narración (lo que se escucha), rótulo
(lo que se lee en la banda inferior) y voz. Si hay que cambiar el
mensaje comercial, se cambia acá y se regenera el video.

Cada beat dura lo que dura su narración: por eso el video en inglés
y el de portugués no tienen la misma duración que el de castellano.
Eso es correcto — forzarlos a durar igual es lo que obliga a meter
silencios o a cortar frases.
==================================================================
"""

# Voz por idioma. Se eligieron tres voces masculinas con el mismo
# registro (cálida, cercana, profesional) para que los tres videos
# suenen a la misma marca. Mateo es rioplatense: es la que vende en
# Uruguay y no suena a locutor de aeropuerto.
VOCES = {
    "es": "es-UY-MateoNeural",
    "en": "en-US-AndrewMultilingualNeural",
    "pt": "pt-BR-AntonioNeural",
}

# Ritmo: edge-tts habla rápido por defecto para un video de producto.
RITMO = "-8%"

TITULO = {
    "es": "Tu base de datos, en tu idioma",
    "en": "Your database, in your own words",
    "pt": "Seu banco de dados, no seu idioma",
}

CIERRE = {
    "es": ("Probalo gratis 3 días", "mvsqlnlp.com"),
    "en": ("Try it free for 3 days", "mvsqlnlp.com"),
    "pt": ("Teste grátis por 3 dias", "mvsqlnlp.com"),
}

# (clave_de_captura, rótulo, narración)
# clave_de_captura None => tarjeta sin captura (intro / cierre).
GUION = {
    "es": [
        (None, "MV SQL NLP",
         "Tu base de datos ya tiene la respuesta. El problema es que solo dos "
         "personas en tu empresa saben cómo sacarla."),
        ("pregunta", "Preguntá como le preguntarías a un compañero",
         "Con MV SQL NLP escribís la pregunta en tu idioma. Sin código, sin SQL, "
         "sin esperar tres días a que Sistemas te la responda."),
        ("sql", "La IA escribe el SQL y te muestra cuánto confía",
         "La inteligencia artificial escribe el SQL, lo valida contra tu esquema "
         "real y te muestra el intervalo de confianza. Cuando no está segura, te "
         "lo dice."),
        ("tabla", "La respuesta completa, en segundos",
         "La respuesta llega en segundos, con el detalle completo, lista para "
         "exportar a Excel, CSV, JSON o PDF."),
        ("grafico", "El gráfico se arma solo, con tu moneda",
         "El gráfico se arma solo, con tu moneda y tus decimales. Valores "
         "legibles, ejes con etiquetas, nada superpuesto."),
        ("explorar", "Qué variables se mueven juntas",
         "En el panel Explorar ves el mapa de correlaciones: qué variables se "
         "mueven juntas y cuáles no tienen nada que ver."),
        ("influencia", "Y cuál pesa de verdad sobre cuál",
         "Y con SHAP ves cuánto pesa cada variable sobre la que te importa, y "
         "para qué lado: verde la sube, rojo la baja."),
        ("auditoria", "Quién consultó qué, con fecha y usuario",
         "Todo lo que se consulta queda registrado: quién preguntó qué, cuándo, "
         "y qué intentos se rechazaron. Exportable para auditoría."),
        ("permisos", "Cada uno ve solo sus tablas",
         "Y cada persona entra con su PIN y ve solamente las tablas de su rol. "
         "El de cobranzas no ve sueldos: la inteligencia artificial ni se entera "
         "de que esas tablas existen."),
        (None, "Tus datos nunca salen de tu red",
         "Tus datos nunca salen de tu red: a la inteligencia artificial solo "
         "viajan los nombres de las tablas. Probalo gratis tres días en "
         "mvsqlnlp.com."),
    ],
    "en": [
        (None, "MV SQL NLP",
         "Your database already has the answer. The problem is that only two "
         "people in your company know how to get it out."),
        ("pregunta", "Ask the way you'd ask a colleague",
         "With MV SQL NLP you just write the question in plain words. No code, "
         "no SQL, no waiting three days for IT to get back to you."),
        ("sql", "The AI writes the SQL — and tells you how sure it is",
         "The AI writes the SQL, validates it against your real schema and shows "
         "you the confidence interval. When it isn't sure, it says so."),
        ("tabla", "The full answer, in seconds",
         "The answer arrives in seconds, with the full detail, ready to export to "
         "Excel, CSV, JSON or PDF."),
        ("grafico", "The chart builds itself, in your currency",
         "The chart builds itself, in your currency and your decimals. Readable "
         "values, labelled axes, nothing overlapping."),
        ("explorar", "Which variables move together",
         "In the Explore panel you get the correlation map: which variables move "
         "together, and which have nothing to do with each other."),
        ("influencia", "And which one actually drives which",
         "And with SHAP you see how much each variable weighs on the one you care "
         "about, and in which direction: green pushes it up, red pulls it down."),
        ("auditoria", "Who queried what, with date and user",
         "Everything queried is logged: who asked what, when, and which attempts "
         "were rejected. Exportable for audit."),
        ("permisos", "Everyone sees only their own tables",
         "And each person logs in with their PIN and sees only the tables for "
         "their role. Collections doesn't see payroll — the AI never even learns "
         "those tables exist."),
        (None, "Your data never leaves your network",
         "Your data never leaves your network: only the table names travel to the "
         "AI. Try it free for three days at mvsqlnlp.com."),
    ],
    "pt": [
        (None, "MV SQL NLP",
         "Seu banco de dados já tem a resposta. O problema é que só duas pessoas "
         "na sua empresa sabem como tirá-la de lá."),
        ("pregunta", "Pergunte como perguntaria a um colega",
         "Com o MV SQL NLP você escreve a pergunta no seu idioma. Sem código, sem "
         "SQL, sem esperar três dias pela resposta da T I."),
        ("sql", "A IA escreve o SQL e mostra o quanto confia",
         "A inteligência artificial escreve o SQL, valida contra o seu esquema "
         "real e mostra o intervalo de confiança. Quando não está segura, ela "
         "avisa."),
        ("tabla", "A resposta completa, em segundos",
         "A resposta chega em segundos, com o detalhe completo, pronta para "
         "exportar para Excel, CSV, JSON ou PDF."),
        ("grafico", "O gráfico se monta sozinho, na sua moeda",
         "O gráfico se monta sozinho, com a sua moeda e as suas casas decimais. "
         "Valores legíveis, eixos com rótulos, nada sobreposto."),
        ("explorar", "Quais variáveis se movem juntas",
         "No painel Explorar você vê o mapa de correlações: quais variáveis se "
         "movem juntas e quais não têm nada a ver."),
        ("influencia", "E qual realmente pesa sobre qual",
         "E com SHAP você vê o quanto cada variável pesa sobre aquela que te "
         "importa, e para que lado: verde aumenta, vermelho reduz."),
        ("auditoria", "Quem consultou o quê, com data e usuário",
         "Tudo o que é consultado fica registrado: quem perguntou o quê, quando, "
         "e quais tentativas foram rejeitadas. Exportável para auditoria."),
        ("permisos", "Cada um vê só as suas tabelas",
         "E cada pessoa entra com o seu PIN e vê somente as tabelas do seu papel. "
         "Quem é da cobrança não vê a folha: a inteligência artificial nem fica "
         "sabendo que essas tabelas existem."),
        (None, "Seus dados nunca saem da sua rede",
         "Seus dados nunca saem da sua rede: para a inteligência artificial viajam "
         "apenas os nomes das tabelas. Teste grátis por três dias em "
         "mvsqlnlp.com."),
    ],
}
