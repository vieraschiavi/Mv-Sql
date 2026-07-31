"""
generar_og_image.py — arma la imagen de vista previa (Open Graph).
==================================================================
Es la tarjeta que se ve cuando alguien comparte mvsqlnlp.com por
WhatsApp, LinkedIn, X o Slack. Sin ella, el link aparece como un
rectángulo gris sin imagen ni título: para un producto que se vende
por link compartido, es de lo más caro que puede faltar.

1200x630 es el tamaño que piden todas las plataformas.

    python3 tools/generar_og_image.py
==================================================================
"""
import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DESTINO = os.path.join(RAIZ, "web", "assets", "og-image.png")

W, H = 1200, 630

# Misma paleta que la landing (:root de web/index.html)
NAVY = (8, 21, 39)
HERO_A = (13, 36, 64)
AMBER = (242, 180, 65)
BLANCO = (234, 241, 251)
GRIS = (157, 176, 200)
LINEA = (29, 49, 73)

F_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
F_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def fuente(ruta, tam):
    try:
        return ImageFont.truetype(ruta, tam)
    except OSError:
        return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # Degradé vertical suave, del navy al azul del hero
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=(int(NAVY[0] + (HERO_A[0] - NAVY[0]) * t),
                     int(NAVY[1] + (HERO_A[1] - NAVY[1]) * t),
                     int(NAVY[2] + (HERO_A[2] - NAVY[2]) * t)))

    # Barra ámbar de la marca
    d.rectangle([0, 0, W, 8], fill=AMBER)

    margen = 84
    y = 128

    # El rayo va dibujado y no como emoji: Liberation Sans no tiene glifo
    # para ⚡ y salía un cuadrito vacío.
    bx, by, s = margen, y - 4, 52
    d.polygon([(bx + s * 0.55, by), (bx + s * 0.16, by + s * 0.56),
               (bx + s * 0.44, by + s * 0.56), (bx + s * 0.30, by + s),
               (bx + s * 0.72, by + s * 0.40), (bx + s * 0.44, by + s * 0.40),
               (bx + s * 0.62, by)], fill=AMBER)
    d.text((margen + 62, y), "MV SQL NLP", font=fuente(F_BOLD, 44), fill=AMBER)
    y += 96

    for linea in ["Tu base de datos,", "en tu idioma."]:
        d.text((margen, y), linea, font=fuente(F_BOLD, 76), fill=BLANCO)
        y += 88

    y += 26
    d.text((margen, y),
           "Preguntá en lenguaje natural. La IA escribe el SQL, lo valida",
           font=fuente(F_REG, 30), fill=GRIS)
    d.text((margen, y + 42),
           "contra tu esquema real y te devuelve tablas y gráficos.",
           font=fuente(F_REG, 30), fill=GRIS)

    # Chips de abajo, igual que los badges de la landing
    chips = ["SELECT-only", "CTEs optimizados", "Multi-IA", "ES · EN · PT"]
    cx, cy = margen, H - 108
    f_chip = fuente(F_REG, 24)
    for c in chips:
        ancho = int(d.textlength(c, font=f_chip)) + 40
        d.rounded_rectangle([cx, cy, cx + ancho, cy + 46], radius=23,
                            fill=None, outline=LINEA, width=2)
        d.text((cx + 20, cy + 10), c, font=f_chip, fill=GRIS)
        cx += ancho + 14

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    img.save(DESTINO, "PNG", optimize=True)
    kb = os.path.getsize(DESTINO) / 1024
    print(f"✓ {os.path.relpath(DESTINO, RAIZ)}  ({W}x{H}, {kb:.0f} KB)")


if __name__ == "__main__":
    main()
