# 🎯 Roteiro de demo — 20 minutos

Para a reunião com um gerente de dados, cobrança ou administração. Não é uma
demo de produto: é uma demo do problema **dele**.

🌎 Idiomas: [Español](VENTA_GUION_DEMO.md) · [English](VENTA_GUION_DEMO_EN.md) · **Português**

**Regra de ouro:** se no minuto 5 você não está mostrando o banco de dados
**dele**, a reunião já foi perdida. A demo com `cartera_demo.db` é o plano B,
nunca o A.

---

## Antes da reunião (30 minutos de preparo)

Peça por e-mail, dois dias antes:

> "Para que a demo seja sobre os seus dados e não sobre um exemplo genérico,
> preciso só de duas coisas: um usuário de **somente leitura** no banco (ou numa
> cópia), e as 3 perguntas que mais te pedem e que hoje são difíceis de
> responder. Com isso eu chego com tudo funcionando."

Se derem acesso: conecte, olhe o esquema e **prepare 2 respostas corretas de
antemão**. Nunca improvise a primeira consulta na frente do cliente.

Se não derem acesso (o mais comum na primeira vez): peça mesmo assim **as 3
perguntas** e um Excel exportado do sistema deles. Com o modo Arquivo você tem
uma demo real do mesmo jeito.

---

## Minuto a minuto

### 0–2 · O problema, com as palavras dele
Não abra o programa ainda.

> "Antes de te mostrar qualquer coisa: quando você precisa de um número que não
> está num relatório fixo, como consegue hoje? Para quem você pede e quanto tempo demora?"

Deixe falar. Anote o número que ele disser (três dias, uma semana, "depende").
**Esse número justifica o seu preço pelo resto da reunião.**

### 2–5 · A pergunta dele, respondida ao vivo
Abra o programa já conectado ao banco dele. Escreva **a pergunta que ele mandou
por e-mail**, literal.

Enquanto gera, narre o que está acontecendo:

> "Repare que eu não mandei os seus dados para nenhuma IA: só descrevi os nomes
> das suas tabelas. As linhas nunca saem da sua rede."

Mostre o resultado. Cale a boca e deixe ele olhar.

### 5–8 · Por que ele pode confiar
É aqui que a venda se ganha ou se perde. O medo real do comprador é *"e se o
número estiver errado e eu levar isso para uma reunião de diretoria?"*.

1. **O SQL à vista** — "Você pode entregar isso para a sua equipe técnica revisar."
2. **A validação** — "Se a IA inventa uma coluna que não existe, a consulta é
   rejeitada e se corrige sozinha. Ela não te devolve um número inventado."
3. **O intervalo de confiança** — "Quando não está segura, ela avisa. Isso o
   ChatGPT não faz."

> "Como *você* verificaria se este número está certo?" — e faça isso junto com ele, na hora.

### 8–12 · A segunda pergunta (a que ele não se atreve a pedir)
> "Agora faça você a pergunta. Aquela que normalmente você não pediria porque não
> vale a pena incomodar a TI."

**Este é o momento que vende.** Quando ele vê que pode perguntar qualquer coisa
sem custo, a cara muda. Se der errado, melhor ainda: mostre como se corrige e
como a consulta fica salva para sair certa sempre.

### 12–16 · O que o ChatGPT não pode dar
Mostre **Equipe e permissões** e **Auditoria**:

> "Isso você pode dar para a sua equipe sem medo. Cada pessoa vê só as tabelas
> dela — quem é da cobrança não vê a folha de pagamento. E tudo que cada um
> consulta fica registrado aqui, com data e usuário, exportável para auditoria."

Se for uma financeira, um escritório contábil ou algo regulado, **só isso já
justifica o preço**. É a única coisa que não dá para replicar com uma assinatura
do ChatGPT.

### 16–20 · O fechamento
Não pergunte "o que você achou?". Pergunte:

> "O que precisaria acontecer para isso estar rodando na sua equipe no mês que vem?"

Escute a objeção real (orçamento, TI, "tenho que falar com…"), e feche com o
passo concreto:

> "Te mando hoje a proposta com escopo fechado e preço fixo. Se servir, a
> implantação leva 2 semanas e a gente começa quando você disser."

---

## Objeções frequentes e o que responder

| Ele diz | O que está pensando | Resposta |
|---|---|---|
| "Isso eu faço com ChatGPT" | Não vê o diferencial | "Testa: sobe um Excel e pede o recebido por filial. Agora faz isso com 40 milhões de linhas, sem tirar os dados da sua rede, e com registro de quem consultou. A diferença está aí." |
| "E se a IA errar?" | Medo de passar vergonha | "Erra, sim. Por isso o SQL fica à vista e validado contra o seu esquema, e por isso cada resposta traz o intervalo de confiança. Não te peço para confiar: te peço para verificar." |
| "Tenho que falar com a TI" | Precisa de um aliado interno | "Perfeito, traz ele na próxima. Da TI isso tira trabalho: eles deixam de ser a fila de pedidos. E a conexão é somente leitura, eles vão agradecer." |
| "É caro" | Não ligou o preço ao custo atual | "Quantas horas por mês a sua equipe gasta montando relatório na mão? A [número dele] horas, isso se paga em [X] meses. Depois é lucro todo mês." |
| "Me manda material que eu vejo" | Nada mexeu com ele | "Mando sim. Posso fazer uma última pergunta? O que eu teria que ter te mostrado hoje para isso virar prioridade?" — a resposta vale mais que a venda. |

---

## Depois da reunião (no mesmo dia, não no outro)

E-mail curto:

> Assunto: **A consulta que vimos hoje + proposta**
>
> [Nome], te deixo o SQL da consulta que rodamos, para a sua equipe revisar
> quando quiser. Segue em anexo a proposta com o escopo fechado e o preço fixo
> que conversamos.
>
> Fico à disposição.

Anexe o SQL real que vocês geraram juntos. **É a prova de que a reunião foi
sobre o negócio dele e não sobre um produto.**

---

## Nota para o mercado brasileiro

Três ajustes que mudam a conversa no Brasil:

1. **LGPD é o argumento de abertura**, não o de fechamento. "Os dados não saem da
   sua rede" resolve sozinho a objeção do jurídico — que no Brasil aparece antes
   da objeção de preço.
2. **Permissão + auditoria** é o que permite entregar a ferramenta para o time
   inteiro. Um chatbot genérico não passa por comitê de segurança.
3. **Cobrança em real:** o preço em US$ 2.500 assusta na primeira leitura.
   Apresente o valor mensal equivalente e o parcelamento antes do total.
