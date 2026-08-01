# ⚡ MV SQL NLP

🌎 Idiomas: [Español](README.md) · [English](README.en.md) · **Português**

**Seu banco de dados, no seu idioma.** Consulte qualquer banco SQL em linguagem
natural (espanhol, inglês ou português), sem saber uma linha de código. A IA gera
SQL profissional otimizado com CTEs, valida contra o seu esquema real, mostra o
**intervalo de confiança** de cada resposta e devolve tabelas, gráficos e
análises exportáveis para Excel, CSV, PDF e HTML.

## 📦 O que tem neste repositório

| Pasta | O que é |
|---|---|
| [`web/`](web/) | Landing comercial (estilo SaaS dark) pronta para a **Vercel** — 3 idiomas (ES/EN/PT), demo animada, preços com MercadoPago |
| [`desktop/`](desktop/) | **Programa de PC profissional** (Electron + React) com instalador NSIS `.exe` para Windows |
| [`app-python/`](app-python/) | **Versão autoinstalável** (`INICIAR_MVSQL.bat`): um duplo clique instala tudo e abre o app (Streamlit) |
| [`docs/`](docs/) | Plano de negócio e modelo financeiro, material de venda (roteiro de demo, proposta, one-pager) em 3 idiomas, checklist de implantação, integração MercadoPago |

## ✨ Funções principais

- 💬 **Linguagem natural → SQL** em ES/EN/PT, com JOINs corretos conforme as relações reais do esquema
- 🤖 **A IA que o cliente escolher**: Claude, GPT, **Copilot (Azure OpenAI)**, Gemini, Groq, Mistral, DeepSeek, Grok, **Ollama local (grátis)** ou qualquer endpoint compatível com OpenAI — com chave própria ou com créditos faturados por nós
- 🗄️ **Multibanco**: SQL Server, MySQL/MariaDB, PostgreSQL e SQLite — se adapta a qualquer esquema sem configuração
- 📄 **Modo Arquivo**: consulte um **CSV, Excel ou Parquet** sem ter banco de dados — carga rápida com cache
- 🔢 **Formato sob medida**: menu de casas decimais, separador de milhar, % e **moeda** (R$, US$, $U, AR$, €…) aplicado a tabelas, gráficos e análises
- 🧩 **Conector MCP**: `CONECTAR_CLAUDE_MCP.bat` liga o seu **Claude Desktop** direto ao seu banco (SQL Server/MySQL/PostgreSQL/SQLite) via MCP
- 🚀 **Otimização com CTE**: consultas estruturadas com `WITH … AS`, filtros antecipados, sem `SELECT *`; reotimizador de SQL existente
- 📐 **Intervalo de confiança** em cada resposta (ex.: 92% ±5), combinando autoavaliação do modelo, sinal do RAG e validação estrutural
- 🛡️ **Anti-alucinação**: o SQL é validado contra o catálogo real; se algo não existe, é rejeitado e corrigido sozinho (self-repair)
- 🔒 **Segurança**: conexão somente leitura, apenas `SELECT`/`WITH`; o RAG é local — os dados nunca saem da sua rede, só o esquema viaja
- 👥 **Equipe e permissões**: cada usuário entra com o seu PIN e vê **só as tabelas do seu papel** — a IA nem fica sabendo que as outras existem
- 🛡️ **Auditoria**: quem consultou o quê, quando, com qual SQL e com qual resultado — exportável para CSV para conformidade
- ⭐ **Consultas salvas** com nome + conversão em **stored procedures** de produção
- 📓 **Cadernos**: relatórios reutilizáveis que misturam Markdown, perguntas e SQL com **variáveis compartilhadas** (`{{mes}}`, `{{filial}}`) — rodam inteiros trocando um valor, e se exportam para Markdown
- 🕸️ **Diagrama de relações**: o mapa das suas tabelas e das chaves estrangeiras, mais as tabelas que ficaram soltas
- ⚙️ **Plano de execução interpretado**: por que uma consulta demora, em português, com a recomendação concreta
- 🔍 **Painel Explorar (EDA)**: mapa de correlações entre variáveis + **influência de variáveis** (Random Forest) para ver o que pesa sobre o quê — sobre o resultado ou sobre qualquer tabela inteira
- 📊 **Gráficos profissionais**: eixos com rótulos, valores formatados sem sobreposição, tipo automático conforme os dados ou à escolha (barras, barras horizontais, linha, área, pizza, dispersão, histograma) + análise em linguagem natural
- ⬇️ **Exportação** para Excel (com formatação), CSV, **JSON**, PDF e HTML
- 🔐 **Túnel SSH** opcional para bancos que não estão expostos à internet

## 🚀 Início rápido

**Versão autoinstalável (Windows, 2 minutos):** entre em `app-python/` e dê um
duplo clique em **`INICIAR_MVSQL.bat`**. Ele instala Python e as dependências,
gera um banco de demonstração e abre o app em `http://localhost:8791` (porta
fixa, para não conflitar com outros apps rodando no seu PC).

> ⚠️ Se você já tinha baixado uma cópia antiga do programa (por exemplo, do zip
> de exemplo original), baixe de novo — as versões antigas tinham um bug
> conhecido do pandas ao exibir colunas de data (`AssertionError` em
> `pd.to_datetime`), já corrigido aqui.

**App de desktop (desenvolvimento):**
```bash
cd desktop && npm install && npm run dev      # desenvolvimento
npm run dist                                   # instalador .exe (Windows)
```

**Web (Vercel):** importar o repositório na Vercel com *Root Directory* = `web/`
(é um site estático, sem build).

## ✅ Rodar os testes (em uma máquina limpa)

Só com `git` e `node` (18+) já dá para rodar os testes de `web/`; se também
houver `python3` no `PATH`, roda os testes do motor NL-para-SQL também
(`app-python/tests/` não precisa de nenhum pacote de `requirements.txt`, só
da biblioteca padrão):

```bash
git clone https://github.com/vieraschiavi/Mv-Sql.git
cd Mv-Sql
npm ci        # instala só as deps de web/ (jsonwebtoken, mercadopago, jszip…)
npm test      # descobre e roda TUDO: web/tests/*.test.js + app-python/tests/test_*.py
```

Sai com código de saída diferente de zero se algo falhar — é o mesmo que
`.github/workflows/tests.yml` roda a cada push. Para rodar um subconjunto:
`npm test -- --web` ou `npm test -- --python`.

## 💰 Modelo comercial

**O serviço é o negócio; o produto é o diferencial.**

| O quê | Preço | Como se cobra |
|---|---|---|
| **Implantação** no seu banco/ERP | US$ 2.500 (Express US$ 900) | pagamento único |
| Licença mensal | US$ 15 / 29 / 79 | assinatura (MercadoPago preapproval) |
| Suporte e manutenção | US$ 150/mês | assinatura |
| Créditos de IA embutidos | US$ 9 / 35 / 110 | pagamento único |

Teste completo de 7 dias sem cartão. Análise de mercado, concorrência e cenários
de rentabilidade em [`docs/PLAN_DE_NEGOCIO.md`](docs/PLAN_DE_NEGOCIO.md); modelo
financeiro executável em [`docs/MODELO_NEGOCIO.py`](docs/MODELO_NEGOCIO.py).
Checklist de entrada em produção em [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

Material de venda em português: [roteiro de demo](docs/VENTA_GUION_DEMO_PT.md) ·
[proposta](docs/VENTA_PROPUESTA_PT.md) · [one-pager](docs/VENTA_ONEPAGER_PT.md).
