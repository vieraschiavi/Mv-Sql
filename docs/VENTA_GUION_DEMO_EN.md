# 🎯 Demo script — 20 minutes

For the meeting with a data, collections or admin manager. This is not a product
demo: it's a demo of **their** problem.

🌎 Languages: [Español](VENTA_GUION_DEMO.md) · **English** · [Português](VENTA_GUION_DEMO_PT.md)

**Golden rule:** if by minute 5 you are not showing **their** database, the
meeting is already lost. The `cartera_demo.db` demo is plan B, never plan A.

---

## Before the meeting (30 minutes of prep)

Email them two days ahead:

> "So the demo is about your data and not a generic example, I only need two
> things: a **read-only** user on the database (or on a copy), and the 3
> questions you get asked most that are hardest to answer today. With that I
> show up with everything already working."

If they give you access: connect, read the schema and **prepare 2 correct
answers in advance**. Never improvise the first query in front of the client.

If they don't give you access (the usual on a first meeting): ask for **the 3
questions** anyway, plus an Excel export from their system. File mode gives you
a real demo all the same.

---

## Minute by minute

### 0–2 · The problem, in their words
Don't open the program yet.

> "Before I show you anything: when you need a number that isn't in a standard
> report, how do you get it today? Who do you ask, and how long does it take?"

Let them talk. Write down the number they say (three days, a week, "it
depends"). **That number justifies your price for the rest of the meeting.**

### 2–5 · Their question, answered live
Open the program already connected to their database. Type **the question they
emailed you**, word for word.

While it generates, narrate what's happening:

> "Notice I didn't send your data to any AI: I only described the names of your
> tables. The rows never leave your network."

Show the result. Then shut up and let them look at it.

### 5–8 · Why they can trust it
This is where the sale is won or lost. The buyer's real fear is *"what if the
number is wrong and I take it into a board meeting?"*.

1. **The SQL in plain sight** — "You can hand this to your technical team to review."
2. **The validation** — "If the AI invents a column that doesn't exist, the query
   is rejected and fixes itself. It won't hand you a made-up number."
3. **The confidence interval** — "When it isn't sure, it tells you. ChatGPT
   doesn't do that."

> "How would *you* verify this number is right?" — and then do it with them, right there.

### 8–12 · The second question (the one they don't dare ask)
> "Now you ask a question. The one you normally wouldn't request because it's not
> worth bothering IT about."

**This is the moment that sells.** When they see they can ask anything at zero
cost, their face changes. If it comes back wrong, even better: show how it gets
corrected and how the query is saved so it comes out right every time.

### 12–16 · What ChatGPT can't give them
Show **Team and permissions** and **Audit trail**:

> "You can hand this to your whole team without worrying. Each person only sees
> their own tables — collections doesn't see payroll. And everything anyone
> queries is logged right here, with date and user, exportable for audit."

If it's a lender, an accounting firm or anything regulated, **this alone
justifies the price**. It's the one thing they cannot replicate with a ChatGPT
subscription.

### 16–20 · The close
Don't ask "so, what did you think?". Ask:

> "What would have to happen for this to be running in your team next month?"

Listen for the real objection (budget, IT, "I have to run it by…"), and close
with the concrete next step:

> "I'll send you the proposal today with fixed scope and a fixed price. If it
> works for you, implementation takes 2 weeks and we start whenever you say."

---

## Common objections and how to answer

| They say | What they're thinking | Answer |
|---|---|---|
| "I can do this with ChatGPT" | Doesn't see the differentiator | "Try it: upload an Excel and ask for collections by branch. Now do it with 40 million rows, without your data leaving your network, and with a record of who ran it. That's the difference." |
| "What if the AI gets it wrong?" | Afraid of looking bad | "It does get things wrong, yes. That's why the SQL is in plain sight and validated against your schema, and why every answer carries its confidence interval. I'm not asking you to trust it — I'm asking you to verify it." |
| "I need to talk to IT" | Needs an internal ally | "Perfect, bring them to the next one. This takes work off IT's plate: they stop being the request queue. And the connection is read-only — they'll appreciate that." |
| "It's expensive" | Hasn't tied the price to their current cost | "How many hours a month does your team spend building reports by hand? At [their number] hours, this pays for itself in [X] months. After that it's profit every month." |
| "Send me some info and I'll look at it" | Nothing moved for them | "I'll send it. Can I ask you one last thing? What would I have had to show you today for this to be a priority?" — that answer is worth more than the sale. |

---

## After the meeting (same day, not the next)

Short email:

> Subject: **The query we ran today + proposal**
>
> [Name], here's the SQL for the query we ran, so your team can review it
> whenever they want. Attached is the proposal with the closed scope and the
> fixed price we discussed.
>
> At your disposal.

Attach the real SQL you generated together. **It's the proof that the meeting
was about their business and not about a product.**

---

## Note for English-speaking markets

Outside Latin America the "ask in your own language" angle lands weaker — most
buyers already assume an AI understands English. Lead instead with the two
arguments that stay strong everywhere:

1. **The data never leaves the network** (the compliance officer's argument).
2. **Permissions plus audit trail** (the reason a general-purpose chatbot cannot
   be given to the whole team).

Keep the confidence interval as the closer: no competing tool shows it.
