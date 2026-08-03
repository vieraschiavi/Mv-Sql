"""
generar_bmp_instalador.py — imagen lateral del asistente de instalación.
==================================================================
Es el panel azul de la izquierda en las páginas de Bienvenida y
Finalizar del instalador NSIS (el look "asistente moderno de Windows",
como VS Code o cualquier instalador profesional). Sin ella, NSIS pone
su imagen gris genérica y el instalador se ve de 2005.

MUI2 exige BMP de Windows de 164x314 en 24 bits — un PNG o un BMP de
32 bits se ve negro o directamente no carga, y falla en silencio.

    python3 tools/generar_bmp_instalador.py

Regenera installer/lateral.bmp (que sí se commitea: makensis lo
necesita en CI y no corre Python).
==================================================================
"""
import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DESTINO = os.path.join(RAIZ, "installer", "lateral.bmp")

# Tamaño exacto que exige MUI_WELCOMEFINISHPAGE_BITMAP.
W, H = 164, 314

# Misma paleta que la landing y la og-image (:root de web/index.html).
NAVY = (8, 21, 39)
HERO_A = (13, 36, 64)
AMBER = (242, 180, 65)
BLANCO = (234, 241, 251)

F_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def fuente(tam):
    try:
        return ImageFont.truetype(F_BOLD, tam)
    except OSError:
        return ImageFont.load_default()


img = Image.new("RGB", (W, H), NAVY)
d = ImageDraw.Draw(img)

# Degradado vertical suave, como el hero de la landing.
for y in range(H):
    t = y / H
    r = int(HERO_A[0] + (NAVY[0] - HERO_A[0]) * t)
    g = int(HERO_A[1] + (NAVY[1] - HERO_A[1]) * t)
    b = int(HERO_A[2] + (NAVY[2] - HERO_A[2]) * t)
    d.line([(0, y), (W, y)], fill=(r, g, b))

# Monograma "MV" en una caja redondeada, arriba (como el icono de la
# captura de referencia, pero con la marca propia).
caja_w, caja_h = 84, 84
cx = (W - caja_w) // 2
cy = 38
d.rounded_rectangle([cx, cy, cx + caja_w, cy + caja_h], radius=16,
                    fill=NAVY, outline=AMBER, width=3)
f_mv = fuente(34)
bb = d.textbbox((0, 0), "MV", font=f_mv)
d.text((cx + (caja_w - (bb[2] - bb[0])) // 2 - bb[0],
        cy + (caja_h - (bb[3] - bb[1])) // 2 - bb[1]),
       "MV", font=f_mv, fill=AMBER)

# Rayo (⚡) dibujado como polígono — Liberation Sans no tiene el glifo,
# mismo truco que en generar_og_image.py. Centrado, grande, en ámbar.
ry, esc = 168, 1.0
rx = W // 2
rayo = [(rx + int(dx * esc), ry + int(dy * esc)) for dx, dy in
        [(8, -46), (-22, 8), (-4, 8), (-8, 46), (22, -8), (4, -8)]]
d.polygon(rayo, fill=AMBER)

# Marca al pie.
f_nom = fuente(19)
texto = "MV SQL NLP"
bb = d.textbbox((0, 0), texto, font=f_nom)
d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], 252), texto, font=f_nom, fill=BLANCO)
f_sub = fuente(11)
sub = "mvsqlnlp.com"
bb = d.textbbox((0, 0), sub, font=f_sub)
d.text(((W - (bb[2] - bb[0])) // 2 - bb[0], 280), sub, font=f_sub,
       fill=(157, 176, 200))

# BMP de 24 bits sí o sí: "RGB" en Pillow escribe BI_RGB de 24bpp, que
# es lo único que MUI2 carga sin sorpresas.
img.save(DESTINO, format="BMP")
print(f"✓ {os.path.relpath(DESTINO, RAIZ)}  {W}x{H}, "
      f"{os.path.getsize(DESTINO) / 1024:.0f} KB")
