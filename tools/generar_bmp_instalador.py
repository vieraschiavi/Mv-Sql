# © 2026 Martín Viera. Todos los derechos reservados.

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

# Mismo ícono que el favicon y el .ico de escritorio — fuente vectorial en
# web/assets/logo-mv.svg, acá se reusa el raster ya generado para no sumar
# una dependencia de rasterizado de SVG a este script.
ICONO = os.path.join(RAIZ, "desktop", "build", "icon.png")

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

# Ícono de marca, centrado arriba.
icono_s = 108
icono = Image.open(ICONO).convert("RGBA").resize((icono_s, icono_s), Image.LANCZOS)
img.paste(icono, ((W - icono_s) // 2, 40), icono)

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
