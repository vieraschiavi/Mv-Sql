# 📄 Implementation proposal — template

Copy it, replace everything `[in brackets]` and send it as a PDF the same day as
the demo.

🌎 Languages: [Español](VENTA_PROPUESTA.md) · **English** · [Português](VENTA_PROPUESTA_PT.md)

**The most important part of this document is not the price: it's the "What it
does NOT include" section.** It is the only thing standing between an
implementation and three months of free custom development — the mistake the
pre-mortem flagged as the most expensive one.

---

## Proposal — MV SQL NLP for [COMPANY]

**To:** [Name and title]
**From:** Martín Viera — MV SQL NLP
**Date:** [date] · **This proposal is valid for:** 30 days

### 1. What we discussed

At [COMPANY], when someone needs a number that isn't in a standard report, they
ask [IT / the analyst / you] and the answer arrives in **[X days]**. That creates
two costs: the time of whoever prepares it, and the decisions taken without the
number because it arrived too late.

You mentioned these as the most frequent questions:

1. [question 1, in their words]
2. [question 2]
3. [question 3]

### 2. What we're going to do

Leave MV SQL NLP running on [your database / your ERP], so those questions — and
whatever comes up next — are answered in seconds, written in plain language, by
the person who needs the answer.

| Stage | What it covers | When |
|---|---|---|
| **1. Discovery** | Schema review, interview with whoever knows the data, definition of the business vocabulary (what exactly "collected", "active", "overdue" mean at [COMPANY]) | Week 1 |
| **2. Connection** | Read-only user, installation, test against real data | Week 1 |
| **3. Query loading** | The [N] agreed business questions, saved and reconciled against the numbers you already have | Week 2 |
| **4. Users and permissions** | Setup of [N] users with their roles: who sees which tables, who exports, who audits | Week 2 |
| **5. Training** | A 90-minute session with the team + a manual using your own examples | Week 2 |

**Total timeline: 2 weeks** from the moment we have read-only access.

### 3. What it does NOT include

So there are no surprises on either side:

- Custom software development, new modules or changes to the program.
- Migration, cleanup or correction of existing data.
- Integrations with systems outside the agreed database.
- Additional business queries beyond the [N] agreed — quoted separately at
  [US$ X] each, or you load them yourselves (the program is built for that).
- Infrastructure, database licences or servers.
- Support after the warranty month (see section 5).

### 4. Investment

| Item | Amount |
|---|---|
| Full implementation (stages 1 to 5) | **US$ 2,500** |
| Professional licence — 3 months | included |
| **Total at kickoff** | **US$ 2,500** |

Invoiced 50% at the start and 50% on delivery. Payment by bank transfer or card.
Prices exclude any applicable taxes.

### 5. After the implementation

- **Warranty:** 30 days. If anything delivered doesn't work as agreed, it gets
  fixed at no cost.
- **Licence:** from the fourth month, US$ [29/79] per month.
- **Support and maintenance (optional):** US$ 150 per month — schema changes, new
  queries, 24 business-hour response priority.

### 6. Commitments

**On my side:** all work over a **read-only** connection — the program only runs
`SELECT`, it never modifies or deletes anything. [COMPANY]'s data does not leave
your network: only table and column names travel to the AI, never the rows. Full
confidentiality over everything I see.

**On your side:** a read-only user, one point of contact who knows the data
(about 4 hours spread over the two weeks), and sign-off on the numbers at the end.

### 7. To move forward

Reply to this email with a "go" and we'll schedule the kickoff. If you'd rather
start smaller, there's the **Express option (US$ 900)**: a single database, a
narrow schema, up to 10 queries, no user management.

Thank you for your time today.

**Martín Viera**
vieraschiavi@gmail.com · mvsqlnlp.com

---

## Notes for you (delete before sending)

- **Never send this without having done the demo.** A price without a
  demonstrated problem always looks expensive.
- **[N] queries: put a number in, never "as many as they need".** Ten is a fine
  starting point. That limit is what protects you.
- If they ask for a discount: don't cut the price, **cut the scope**. Fewer
  queries or fewer users. Cutting the price teaches them the first one was made up.
- If they ask to pay everything at the end: 50/50 or there's no project. The
  deposit isn't about the money, it's the signal that the project is real.
- Keep every proposal you send. After 7 days with no reply, a one-line email:
  *"Are we moving ahead or parking this for later?"*. It closes more than chasing does.
- **Selling outside Latin America:** lead with data residency and the audit
  trail, not with "ask in your own language". In an English-speaking market that
  last one is assumed, and it makes the pitch sound smaller than it is.
