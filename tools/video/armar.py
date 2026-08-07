"""
armar.py — arma el video de demo a partir de las capturas + el guion.
==================================================================
Formato vertical 1080x1920, mismo armado que el video de MV Kobra:
logo arriba (una sola vez por cuadro), titular, la captura dentro de
una ventana con borde, el rótulo abajo y los puntos de avance.

Cada beat dura lo que dura su narración, así nunca queda una frase
cortada ni un silencio largo.

    python tools/video/armar.py es /ruta/capturas web/assets/video/demo_es.mp4
==================================================================
"""

import asyncio
import os
import subprocess
import sys

import certifi
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guion import AIRE, CIERRE, GUION, RITMO, TITULO, VOCES  # noqa: E402

# edge-tts usa el bundle de certifi a secas; detrás del proxy hay que
# agregarle la CA o toda petición falla con SSL.
_CA = "/root/.ccr/ca-bundle.crt"
if os.path.exists(_CA):
    _bundle = open(certifi.where(), "rb").read()
    _extra = open(_CA, "rb").read()
    if _extra not in _bundle:
        with open(certifi.where(), "ab") as fh:
            fh.write(b"\n" + _extra)

import edge_tts  # noqa: E402

W, H = 1080, 1920
FPS = 25

# Paleta: la misma del sitio (que a su vez es la de Kobra).
FONDO_A, FONDO_B = (8, 21, 39), (5, 12, 24)
AMBAR = (242, 180, 65)
CELESTE = (56, 189, 248)
BLANCO = (255, 255, 255)
GRIS = (157, 176, 200)
TENUE = (108, 127, 153)
LINEA = (29, 49, 73)

F_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
F_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

FF = None


def ffmpeg():
    global FF
    if FF is None:
        try:
            import imageio_ffmpeg
            FF = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            FF = "ffmpeg"
    return FF


def fuente(ruta, tam):
    return ImageFont.truetype(ruta, tam)


def envolver(draw, texto, fnt, ancho_max):
    """Corta el texto en líneas que entren en ancho_max."""
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if draw.textlength(prueba, font=fnt) <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def fondo():
    """Degradado vertical + dos halos suaves, como el hero del sitio."""
    filas = np.linspace(0, 1, H)[:, None]
    base = (np.array(FONDO_A) * (1 - filas) + np.array(FONDO_B) * filas)
    img = np.repeat(base[:, None, :], W, axis=1)

    halo = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(halo)
    d.ellipse([W - 520, -320, W + 320, 520], fill=(48, 36, 13))     # ámbar arriba
    d.ellipse([-380, 260, 460, 1100], fill=(12, 34, 60))            # azul al costado
    halo = halo.filter(ImageFilter.GaussianBlur(160))

    mezcla = np.clip(img + np.asarray(halo, dtype=float), 0, 255).astype("uint8")
    return Image.fromarray(mezcla)


def rayo(d, x, y, alto, color):
    """El ⚡ de la marca, dibujado (no depende de fuentes con emoji)."""
    a = alto
    puntos = [(x + a * .55, y), (x + a * .12, y + a * .56), (x + a * .42, y + a * .56),
              (x + a * .22, y + a), (x + a * .78, y + a * .40),
              (x + a * .46, y + a * .40), (x + a * .70, y)]
    d.polygon(puntos, fill=color)


def marca(d, y=92):
    """Logo, una sola vez por cuadro y siempre en el mismo lugar."""
    f = fuente(F_BOLD, 40)
    txt_a, txt_b = "MV SQL ", "NLP"
    ancho = 34 + 16 + d.textlength(txt_a, font=f) + d.textlength(txt_b, font=f)
    x = (W - ancho) / 2
    rayo(d, x, y - 4, 44, AMBAR)
    x += 34 + 16
    d.text((x, y), txt_a, font=f, fill=BLANCO)
    x += d.textlength(txt_a, font=f)
    d.text((x, y), txt_b, font=f, fill=AMBAR)


def puntos(d, indice, total, y=1836):
    """Puntos de avance: se ve cuánto falta, como en el video de Kobra."""
    r, sep = 5, 26
    ancho = total * sep - (sep - 2 * r)
    x = (W - ancho) / 2
    for i in range(total):
        color = AMBAR if i == indice else LINEA
        d.ellipse([x, y - r, x + 2 * r, y + r], fill=color)
        x += sep


def _difuminar_bordes(cap, alto_fade=70):
    """Desvanece el borde superior e inferior de la captura.

    Una captura de pantalla siempre corta una fila de texto por la mitad.
    Con el degradado, el corte se lee como intencional en vez de como un
    descuido.
    """
    mascara = Image.new("L", cap.size, 255)
    d = ImageDraw.Draw(mascara)
    for i in range(alto_fade):
        v = int(255 * i / alto_fade)
        d.line([(0, i), (cap.width, i)], fill=v)
        d.line([(0, cap.height - 1 - i), (cap.width, cap.height - 1 - i)], fill=v)
    fondo_card = Image.new("RGB", cap.size, (15, 23, 42))
    return Image.composite(cap, fondo_card, mascara)


def tarjeta(img, captura, x, y, ancho_max, alto_max):
    """Pega la captura dentro de una ventana con barra y luces.

    Devuelve (alto_total, ancho_total) de la ventana dibujada.
    """
    barra = 34
    d = ImageDraw.Draw(img)

    escala = min(ancho_max / captura.width, (alto_max - barra) / captura.height)
    ancho = int(captura.width * escala)
    alto = int(captura.height * escala)
    cx = int(x + (ancho_max - ancho) / 2)

    d.rounded_rectangle([cx - 12, y, cx + ancho + 12, y + barra + alto + 12],
                        radius=18, fill=(15, 23, 42), outline=LINEA, width=2)
    for i, color in enumerate([(239, 111, 108), (247, 193, 91), (91, 201, 128)]):
        d.ellipse([cx + 4 + i * 20, y + 12, cx + 14 + i * 20, y + 22], fill=color)

    escalada = _difuminar_bordes(captura.resize((ancho, alto), Image.LANCZOS))
    img.paste(escalada, (cx, y + barra))
    return barra + alto + 12, ancho + 24


def cuadro(indice, total, titular, captura_path, pie=None, grande=False):
    """Un cuadro del video: logo, titular, captura y rótulo, apilados y
    centrados. Cada cosa tiene su franja: nunca se pisan entre sí."""
    img = fondo()
    d = ImageDraw.Draw(img)
    marca(d)

    ARRIBA, ABAJO = 230, 1780          # franja utilizable (logo arriba, puntos abajo)
    f_tit = fuente(F_BOLD, 76 if grande else 52)
    f_pie = fuente(F_REG, 40 if grande else 34)

    lineas = envolver(d, titular, f_tit, W - 130)[:3]
    alto_tit = len(lineas) * (f_tit.size + 14)

    cap = None
    if captura_path and os.path.exists(captura_path):
        cap = Image.open(captura_path).convert("RGB")

    lineas_pie = []
    if pie and not isinstance(pie, tuple):
        lineas_pie = envolver(d, pie, f_pie, W - 180)[:2]
    alto_pie = len(lineas_pie) * (f_pie.size + 10)

    # La ventana se lleva todo el espacio que sobra.
    hueco = ABAJO - ARRIBA - alto_tit - alto_pie - (70 if cap is not None else 0)
    y = ARRIBA
    if cap is None:
        y = ARRIBA + 180

    for ln in lineas:
        w = d.textlength(ln, font=f_tit)
        d.text(((W - w) / 2, y), ln, font=f_tit, fill=BLANCO)
        y += f_tit.size + 14

    if cap is not None:
        y += 40
        # La ventana suele quedar limitada por el ancho: se centra en el
        # hueco para que no quede todo el aire abajo.
        esc = min((W - 110) / cap.width, (hueco - 34) / cap.height)
        alto_previsto = 34 + int(cap.height * esc) + 12
        y += max(0, (hueco - alto_previsto) // 2)
        alto_card, _ = tarjeta(img, cap, 55, y, W - 110, hueco)
        y += alto_card + 34
    elif grande:
        sub, dominio = pie if isinstance(pie, tuple) else (pie or "", "")
        if sub:
            for ln in envolver(d, sub, f_pie, W - 200):
                w = d.textlength(ln, font=f_pie)
                d.text(((W - w) / 2, y + 40), ln, font=f_pie, fill=GRIS)
                y += f_pie.size + 12
        if dominio:
            f_dom = fuente(F_BOLD, 52)
            w = d.textlength(dominio, font=f_dom)
            d.text(((W - w) / 2, y + 110), dominio, font=f_dom, fill=AMBAR)

    for ln in lineas_pie:
        w = d.textlength(ln, font=f_pie)
        d.text(((W - w) / 2, y), ln, font=f_pie, fill=TENUE)
        y += f_pie.size + 10

    puntos(d, indice, total)
    return img


async def narrar(texto, voz, destino):
    com = edge_tts.Communicate(texto, voz, rate=RITMO)
    await com.save(destino)


def duracion(path):
    salida = subprocess.run(
        [ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    for linea in salida.splitlines():
        if "Duration:" in linea:
            h, m, s = linea.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"No pude leer la duración de {path}")


def main():
    idioma = sys.argv[1] if len(sys.argv) > 1 else "es"
    capturas = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/capturas_{idioma}"
    destino = sys.argv[3] if len(sys.argv) > 3 else f"web/assets/video/demo_{idioma}.mp4"

    trabajo = os.path.join("/tmp", f"mvsql_video_{idioma}")
    os.makedirs(trabajo, exist_ok=True)

    beats = GUION[idioma]
    total = len(beats)
    voz = VOCES[idioma]

    print(f"\n== Video {idioma.upper()} · {total} bloques · voz {voz} ==")

    audios, duraciones, imagenes = [], [], []
    for i, (clave, rotulo, texto) in enumerate(beats):
        mp3 = os.path.join(trabajo, f"voz{i:02d}.mp3")
        asyncio.run(narrar(texto, voz, mp3))
        d = duracion(mp3) + AIRE          # aire al final de cada frase
        audios.append(mp3)
        duraciones.append(d)

        if i == 0:
            img = cuadro(i, total, TITULO[idioma], None,
                         pie=(rotulo if rotulo != "MV SQL NLP" else "", ""), grande=True)
        elif i == total - 1:
            img = cuadro(i, total, rotulo, None, pie=CIERRE[idioma], grande=True)
        else:
            img = cuadro(i, total, rotulo, os.path.join(capturas, f"{clave}.png"))
        png = os.path.join(trabajo, f"cuadro{i:02d}.png")
        img.save(png)
        imagenes.append(png)
        print(f"  {i + 1:2}/{total}  {d:5.1f}s  {rotulo[:52]}")

    # 1) pista de audio. Cada narración se alarga con silencio hasta durar
    # exactamente lo que su cuadro (whole_dur=d, o sea narración + AIRE), y
    # recién ahí se pegan una detrás de otra. Hacerlo tramo por tramo, y no
    # con un apad al final, es lo que mantiene el audio pegado al video: si
    # se concatenaran los mp3 crudos, cada cuadro se adelantaría AIRE
    # segundos respecto de su narración y el desfasaje se acumularía.
    lista_a = os.path.join(trabajo, "audio.txt")
    audio_full = os.path.join(trabajo, "voz.m4a")
    tramos = []
    for i, (mp3, d) in enumerate(zip(audios, duraciones)):
        tramo = os.path.join(trabajo, f"tramo{i:02d}.m4a")
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", mp3, "-af",
                        f"apad=whole_dur={d:.3f},aresample=44100",
                        "-c:a", "aac", "-b:a", "128k", tramo], check=True)
        tramos.append(tramo)
    with open(lista_a, "w", encoding="utf-8") as fh:
        for tr in tramos:
            fh.write(f"file '{tr}'\n")
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", lista_a, "-c", "copy", audio_full], check=True)

    # 2) pista de video: cada cuadro dura lo que su narración
    lista_v = os.path.join(trabajo, "video.txt")
    with open(lista_v, "w", encoding="utf-8") as fh:
        for png, d in zip(imagenes, duraciones):
            fh.write(f"file '{png}'\nduration {d:.3f}\n")
        fh.write(f"file '{imagenes[-1]}'\n")

    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    subprocess.run([
        ffmpeg(), "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", lista_v,
        "-i", audio_full,
        "-vf", f"fps={FPS},format=yuv420p,scale={W}:{H}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "copy", "-shortest", "-movflags", "+faststart",
        destino], check=True)

    print(f"\n✓ {destino}  ({sum(duraciones):.0f}s)")


if __name__ == "__main__":
    main()
