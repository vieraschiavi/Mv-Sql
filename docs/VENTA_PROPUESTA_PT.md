# 📄 Proposta de implantação — modelo

Copiar, substituir o que está `[entre colchetes]` e mandar em PDF no mesmo dia
da demo.

🌎 Idiomas: [Español](VENTA_PROPUESTA.md) · [English](VENTA_PROPUESTA_EN.md) · **Português**

**O mais importante deste documento não é o preço: é a seção "O que NÃO
inclui".** É a única coisa que impede a implantação de virar desenvolvimento sob
medida de graça — o erro que, segundo o pre-mortem, queima três meses.

---

## Proposta — MV SQL NLP para [EMPRESA]

**Para:** [Nome e cargo]
**De:** Martín Viera — MV SQL NLP
**Data:** [data] · **Validade desta proposta:** 30 dias

### 1. O que conversamos

Na [EMPRESA], quando alguém precisa de um dado que não está num relatório fixo,
hoje pede para [a TI / o analista / você] e a resposta chega em **[X dias]**.
Isso gera dois custos: o tempo de quem prepara, e as decisões tomadas sem o dado
porque ele chegou tarde.

Você mencionou estas como as perguntas mais frequentes:

1. [pergunta 1, com as palavras dele]
2. [pergunta 2]
3. [pergunta 3]

### 2. O que vamos fazer

Deixar o MV SQL NLP funcionando sobre [o seu banco / o seu ERP], para que essas
perguntas — e as que surgirem — sejam respondidas em segundos, escritas em
português, pela pessoa que precisa delas.

| Etapa | O que inclui | Quando |
|---|---|---|
| **1. Levantamento** | Revisão do esquema, entrevista com quem conhece os dados, definição do vocabulário do negócio (o que significa exatamente "recebido", "ativo", "vencido" na [EMPRESA]) | Semana 1 |
| **2. Conexão** | Usuário somente leitura, instalação, teste com dados reais | Semana 1 |
| **3. Carga de consultas** | As [N] perguntas de negócio acordadas, salvas e conferidas contra os números que vocês já têm | Semana 2 |
| **4. Usuários e permissões** | Cadastro de [N] usuários com seus papéis: quem vê quais tabelas, quem exporta, quem audita | Semana 2 |
| **5. Treinamento** | Sessão de 90 minutos com a equipe + manual com os exemplos de vocês | Semana 2 |

**Prazo total: 2 semanas** a partir do acesso somente leitura.

### 3. O que NÃO inclui

Para não haver surpresa de nenhum lado:

- Desenvolvimento de software sob medida, módulos novos ou mudanças no programa.
- Migração, limpeza ou correção de dados existentes.
- Integrações com sistemas fora do banco acordado.
- Consultas de negócio além das [N] acordadas — cotadas à parte a [US$ X] cada
  uma, ou vocês mesmos cadastram (o programa foi feito para isso).
- Infraestrutura, licenças de banco de dados ou servidores.
- Suporte depois do mês de garantia (ver item 5).

### 4. Investimento

| Item | Valor |
|---|---|
| Implantação completa (etapas 1 a 5) | **US$ 2.500** |
| Licença Profissional — 3 meses | inclusa |
| **Total no início** | **US$ 2.500** |

Faturado 50% no começo e 50% contra entrega. Pagamento por Pix, transferência,
cartão ou MercadoPago. Preços acrescidos dos impostos aplicáveis.

### 5. Depois da implantação

- **Garantia:** 30 dias. Se algo do que foi entregue não funcionar como
  combinado, é corrigido sem custo.
- **Licença:** a partir do quarto mês, US$ [29/79] por mês.
- **Suporte e manutenção (opcional):** US$ 150 por mês — mudanças de esquema,
  consultas novas, prioridade de resposta em 24 horas úteis.

### 6. Compromissos

**Da minha parte:** todo o trabalho com conexão **somente leitura** — o programa
só executa `SELECT`, nunca altera nem apaga nada. Os dados da [EMPRESA] não saem
da sua rede: para a inteligência artificial viajam apenas os nomes de tabelas e
colunas, nunca as linhas. Confidencialidade total sobre tudo o que eu vir.

**Da sua parte:** um usuário somente leitura, uma pessoa de referência que
conheça os dados (umas 4 horas distribuídas nas duas semanas), e a validação dos
números no fechamento.

### 7. Para avançar

Responda este e-mail com um "vamos" e combinamos o começo. Se preferir começar
menor, existe a opção **Express (US$ 900)**: um único banco, esquema reduzido,
até 10 consultas, sem gestão de usuários.

Obrigado pelo tempo de hoje.

**Martín Viera**
vieraschiavi@gmail.com · mvsqlnlp.com

---

## Notas para você (apagar antes de enviar)

- **Nunca mande isso sem ter feito a demo.** Preço sem problema demonstrado
  sempre parece caro.
- **[N] consultas: coloque um número, nunca "as que precisarem".** Dez está bom
  para começar. É o limite que te protege.
- Se pedirem desconto: não baixe o preço, **tire escopo**. Menos consultas ou
  menos usuários. Baixar o preço ensina que o primeiro era inventado.
- Se pedirem para pagar tudo no final: 50/50 ou não tem projeto. A entrada não é
  pelo dinheiro, é o sinal de que o projeto é real.
- Guarde cada proposta enviada. Aos 7 dias sem resposta, um e-mail de uma linha:
  *"Seguimos ou deixamos para mais adiante?"*. Fecha mais que insistir.
- **Vendendo no Brasil:** o jurídico entra na conversa antes do financeiro. Abra
  pela LGPD (os dados não saem da rede) e pela auditoria; o preço só vira tema
  depois que a objeção de segurança estiver resolvida. E apresente o valor
  mensal equivalente antes do total em dólares.
