/**
 * Icono — el mismo set de trazo que usa la landing (web/index.html).
 *
 * Los emojis no los dibuja la app: los dibuja el sistema operativo. El
 * mismo 🗄️ es plano y gris en Windows y de colores en Mac, así que cada
 * título metía en la paleta un color que no es de la marca. Y este
 * producto se instala casi siempre en Windows, donde la fuente de emojis
 * es la más pobre de las tres.
 *
 * Grilla de 24, trazo 1.75, sin relleno y heredando currentColor, para
 * que el mismo icono sirva en la barra lateral oscura y en un botón
 * claro sin duplicar nada.
 */
const D = {
  bolt: <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" fill="currentColor" stroke="none" />,
  reloj: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  codigo: <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />,
  diana: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1.2" /></>,
  globo: <path d="M21 15a2 2 0 01-2 2H8l-4 4V5a2 2 0 012-2h13a2 2 0 012 2z" />,
  tabla: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 10v10" /></>,
  grafico: <><path d="M3 3v18h18" /><path d="M7 15v3M12 10v8M17 6v12" /></>,
  analisis: <><path d="M12 3v3M12 18v3M3 12h3M18 12h3" /><circle cx="12" cy="12" r="4" /><path d="M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /></>,
  bajar: <><path d="M12 3v13" /><path d="M7 12l5 5 5-5" /><path d="M4 21h16" /></>,
  estrella: <path d="M12 3l2.6 5.6 6 .8-4.4 4.2 1.1 6-5.3-2.9L6.7 19.6l1.1-6L3.4 9.4l6-.8L12 3z" />,
  bloques: <><rect x="3" y="14" width="8" height="7" rx="1" /><rect x="13" y="14" width="8" height="7" rx="1" /><rect x="8" y="4" width="8" height="7" rx="1" /></>,
  acelerar: <><path d="M3 12a9 9 0 0118 0" /><path d="M12 12l4-3" /><path d="M3 12h2M19 12h2" /></>,
  cpu: <><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" /></>,
  enchufe: <><path d="M9 2v6M15 2v6" /><path d="M6 8h12v3a6 6 0 01-12 0V8z" /><path d="M12 17v5" /></>,
  base: <><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 5v6c0 1.7-4 3-9 3s-9-1.3-9-3V5" /><path d="M21 11v6c0 1.7-4 3-9 3s-9-1.3-9-3v-6" /></>,
  enlace: <><path d="M10 13a5 5 0 007.5.5l3-3A5 5 0 0013.5 3.5l-1.7 1.7" /><path d="M14 11a5 5 0 00-7.5-.5l-3 3A5 5 0 0010.5 20.5l1.7-1.7" /></>,
  libro: <><path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" /></>,
  chincheta: <><path d="M12 17v5" /><path d="M9 3h6l-1 6 4 3v2H6v-2l4-3-1-6z" /></>,
  play: <path d="M6 4l14 8-14 8V4z" fill="currentColor" stroke="none" />,
  tacho: <><path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15" /><path d="M10 11v6M14 11v6" /></>,
  refrescar: <><path d="M3 12a9 9 0 0115-6.7L21 8" /><path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 01-15 6.7L3 16" /><path d="M3 21v-5h5" /></>,
};

export default function Icono({ n, size = 16, style }) {
  const d = D[n];
  if (!d) return null;
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={{ flex: "none", verticalAlign: "-.18em", ...style }}
    >
      {d}
    </svg>
  );
}
