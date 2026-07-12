// MV SQL NLP — catálogo de productos comprables (pago único → descarga)
// mode "own_ai": el cliente trae su propia API key de IA (más barato).
// mode "credits": el zip descargado trae una licencia con créditos embebidos
//                 que consumen nuestra IA a través de /api/ai-proxy — no
//                 requiere que el cliente configure nada.
const PRODUCTS = {
  "personal:own_ai":     { title: "MV SQL NLP — Plan Personal (IA propia)",      price: 19  },
  "profesional:own_ai":  { title: "MV SQL NLP — Plan Profesional (IA propia)",   price: 39  },
  "empresa:own_ai":      { title: "MV SQL NLP — Plan Empresa (IA propia)",       price: 99  },
  "personal:credits":    { title: "MV SQL NLP — 100 créditos IA embebidos",      price: 9   },
  "profesional:credits": { title: "MV SQL NLP — 500 créditos IA embebidos",      price: 35  },
  "empresa:credits":     { title: "MV SQL NLP — 2000 créditos IA embebidos",     price: 110 },
};

module.exports = { PRODUCTS };
