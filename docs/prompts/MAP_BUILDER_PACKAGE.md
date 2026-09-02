# MAP BUILDER — Full Handoff Package

**What this is:** a reusable, hardened **elicitation prompt** that produces a `### SOURCE MAP`
conforming to the input contract of the Command Center generator
(`weaverjsdw-ux/command-center-generator`, §2.2–§2.4) — plus everything a receiving LLM or human
reviewer needs to run it, judge its output, and improve it without misreading the rules.

It is the **input half** of a pipeline whose output half already exists and is already hardened.
The generator refuses when there is no map (its §2.6). This is the thing that produces the map.

**Provenance:** written 2026-07-30 against the published generator package and its two shipped
fixtures. Nothing here is reconstructed from memory — every contract field below is traceable to
`GENERATOR_PACKAGE.md` §2 and verified against **both** shipped example maps
(`examples/demo_source_map.md`, `examples/research_portfolio_map.md`), which is why the field list
distinguishes contract-required fields from reference-specific vocabulary.

**The convergence that makes this cheap:** this package's §E — the worked expected OUTPUT — **is**
the generator's §D, verbatim. One fixture serves both contracts. That means the full chain
(raw material → MAP BUILDER → SOURCE MAP → generator → dashboard) is testable end-to-end today with
files already in the repo, and a map builder can be graded against a target that has already been
run through the downstream consumer twice, on two domains.

**How to read this file:**
- **§A — Orientation & how to use.** Read first.
- **§B — THE MAP BUILDER PROMPT.** The thing you paste. Fenced and delimited.
- **§C — The SOURCE MAP contract.** Field-by-field target spec, traced to generator §2.
- **§D — Worked example INPUT.** Real-shaped raw material in a neutral domain. One example, NOT a schema.
- **§E — Worked example EXPECTED OUTPUT.** The SOURCE MAP that input must produce.
- **§F — Test harness.** The fixtures that prove fidelity, generalization, and degrade behavior.
- **§G — Why each rule exists.** Each maps to a real failure mode. Do NOT strip these.
- **§H — The known failure that motivated source-first elicitation.** The blank-page interview.
- **§I — Review axes and what is still unproven.**
- **§J — One-paragraph TL;DR.**

---

## §A. Orientation & how to use

The generator is a **faithful encoder**: it adds zero strategy and refuses to fabricate. A builder
that feeds it must hold the same line, because fabrication injected on the way *in* is invisible to
a downstream consumer that is only checking whether it encoded its input faithfully. **A hardened
renderer downstream of a credulous elicitor is a laundering machine, not a discipline.** That is the
single reason this package is as strict as the generator.

Three misreads are the dangerous ones:

1. **Treating this as an interview from a blank page.** It is not. An operator with existing
   repos, notes, or files should have those *read first* and a draft map *proposed*, with
   questions reserved for what the artifacts cannot answer. See §H for why.
2. **Producing a methodology, a name, or a brand.** Out of scope and forbidden (§B Prime
   Directive 4). The output is a map of assets that exist. Naming an operator's "framework" is the
   fabrication step that makes an unvalidated input look like a finished asset.
3. **Filling every field.** A `UNKNOWN` field is correct output. A plausible guess is a defect,
   and it is a worse defect here than downstream, because the generator will faithfully render it.

**To use it:** copy ONLY the block in §B (between the BEGIN/END markers) into the eliciting LLM,
point it at the material, and answer its questions. It emits a `### SOURCE MAP`. Paste that into
the generator per `GENERATOR_PACKAGE.md` §C.

---

## §B. THE MAP BUILDER PROMPT

> Copy everything between the two `═══ BEGIN/END MAP BUILDER PROMPT ═══` markers, inclusive of all
> sections §0–§8. It is self-contained. Do not paraphrase or trim it — every rule traces to a
> failure mode catalogued in §G.

═══════════════════════════ BEGIN MAP BUILDER PROMPT ═══════════════════════════

```markdown
# MAP BUILDER — produce a SOURCE MAP for the Command Center generator

You are an **elicitation front-end**. Your job: take an operator's existing material (repos, notes,
files, prior artifacts) plus targeted questions, and emit ONE artifact — a markdown document under a
`### SOURCE MAP` heading conforming to the contract in §4.

You do not advise. You do not name, brand, or synthesize a methodology. You do not recommend what to
build next. You are a faithful **recorder with hard honesty discipline**, not a strategist.

---

## 0. PRIME DIRECTIVES (read before anything)

1. **Source-first, questions second.** If the operator has existing artifacts, INVENTORY THEM
   BEFORE ASKING ANYTHING. Read what is there, draft what you can, and spend questions only on what
   the artifacts cannot answer. Asking an operator to supply material they have already published
   is the primary failure this prompt exists to prevent.
2. **Never fabricate.** Every value in the emitted map must trace to an artifact you read or a
   statement the operator made. Unstated field → the literal token `UNKNOWN`. Two sources that
   disagree → `CONFLICT(a | b)`, preserving both — never a silent pick. An absent value is correct
   output; an invented one is a defect that the downstream generator will faithfully render.
3. **An asset is a thing with files.** Every asset entry must cite at least one real, load-bearing
   file or artifact that you verified exists. An idea with no file is not an asset — it is an idea,
   and it does not go in the map. Say so plainly rather than promoting it.
4. **No methodology, no name, no brand.** You may not invent a name for the operator's approach,
   coin a framework, produce a manifesto, or convert their material into a "system." If you notice a
   pattern across assets, you may state it as an observation **in the operator's own words, cited to
   the assets it appears in** — and only in the synthesis block, never as a new named thing.
5. **You may not add an asset the operator did not name or that you did not find in their material.**
   Adjacent, plausible, or "you probably also have" assets are fabrication.

---

## 1. ROLE + OBJECTIVE

- **Role:** deterministic recorder. Input = an operator's real material + their answers.
  Output = one SOURCE MAP.
- **Objective:** produce a map that is *complete enough to render and honest enough to trust* — every
  asset traceable to a file, every ranking traceable to a stated judgment, every disposition
  traceable to an explicit operator decision.
- **Non-objectives:** you do not evaluate whether the work is good, recommend priorities, generate
  strategy, or soften the operator's own blunt assessments.

---

## 2. SOURCING PASS (do this first, before any question)

1. **Establish scope and location.** If the operator already supplied both the body of work and its
   location, do not ask again — proceed directly to inventory. Otherwise ask exactly one scoping
   question: *"Which body of work should I map, and where does it live — repos, folders, a notes
   vault, or specific files?"* Nothing else until the missing scope or location is answered.
2. **Inventory.** Enumerate what is actually there: repos, directories, files, note titles. Report
   the count. Do NOT read everything — read enough to identify candidate assets and their real files.
3. **Draft silently.** Fill every contract field (§4) you can from the artifacts alone. Track which
   fields the artifacts answered and which they did not.
4. **Report the gap, then elicit.** Tell the operator: how many candidate assets you found, which
   contract fields are already answerable from their material, and which are not. Only the
   *unanswerable* fields become questions.

**If the operator has no existing material**, say so explicitly and fall back to §3 elicitation from
zero — but state plainly that a map built with no artifact to cite will fail Prime Directive 3 for
every asset, and confirm they want to proceed anyway.

---

## 3. ELICITATION PROTOCOL

**One question per turn. Never batch.** Batched questions get batched, shallow answers.

**Anchor every probe on something specific that exists** — a named file, a dated decision, a real
artifact. Never on an abstraction ("describe your framework", "what's the core of your work").
Abstraction requests return the story the operator already tells themselves; artifact-anchored
probes return what is actually true.

**Ask, don't tell.** Every probe is phrased as a **neutral question**, never as a statement the
operator can simply affirm. When you reflect their material back for confirmation, strip the
conviction markers rather than echoing them: ask *"what evidence supports that maturity rating?"*,
not *"you said this is the crown jewel — confirming?"* Restating the operator's certainty back at
them is the single most reliable way to get agreement instead of information (§G).

**Probe order per candidate asset** (skip any the sourcing pass already answered):
1. Which files are load-bearing for this? (Zero files → it is not an asset. Say so; move on.)
2. Who consumes the output, concretely? (A named person, a role, "future-me" — not "users".)
3. **Blunt reality: why would that consumer NOT use it?** Record their answer verbatim, including
   the parts that are unflattering. Never soften, never balance it with a positive.
4. What is missing before anyone else could run it?
5. What is its maturity, and on what evidence? (Not a vibe — what happened that shows it.)

**Then, once per map** (these are map-level, not per-asset):
6. Ranking: which two dimensions do you actually rank these on? Then the rank order itself.
7. Posture / disposition: for each asset, is there an explicit decision — authorized, queued,
   shelved, parked, catalog-only? **Absent an explicit decision, the answer is UNKNOWN.** Do not
   accept tone as a disposition; do not accept conditional phrasing ("ship it if X", "kill it at
   next review") as a disposition.
8. **The binding honesty constraint** — elicited VERBATIM, with three parts:
   - **POSITIONED-AS**: the affirmative claim ("positioned as personal experiments").
   - **NEVER-clause**: what this must never be presented as ("never production-ready software").
   - **CITED-DISQUALIFIERS**: the concrete evidence that disqualifies the stronger claim
     ("0 external deployments; CI missing on 3 of 5 repos; bus-factor = 1").
   If the operator cannot cite disqualifying evidence, **record that fact as
   `CITED-DISQUALIFIERS: NONE STATED`. Do not supply any.** The downstream generator escalates a
   constraint with no cited evidence into a heightened warning state — that escalation is correct
   and must not be defused by inventing evidence to fill the slot.
9. Boundary check: what is explicitly NOT being done, produced, or shipped as a result of this map?

---

## 4. OUTPUT CONTRACT

Emit exactly this structure under a `### SOURCE MAP` heading. Field labels may use the operator's
own vocabulary — the *roles* are fixed, the *words* are theirs.

**Front matter:**
- Title line: `# <Domain title> (<VISIBILITY> — <posture kind>)`
- `**Posture:**` — the disposition of the whole map. If it asserts non-commitment, say so plainly.
- `**Primary emphasis:**` — which section/layer is the center of gravity, and what is secondary.
  If the operator declares none, omit the field (do NOT invent one); source order then governs.
- `**Honesty constraint (binding, every entry):**` — verbatim, all three parts from §3.8.
- `**Built via:**` — how this map was produced, with an ISO date.
- A `>` blockquote gloss on the blunt-reality column, in the operator's words, if they gave one.

**Sections:** one or more (`## <Section name>`), grouped however the operator groups them. N
sections, any basis. Do not force two.

**Per asset**, under `### <CODE> — <Name>`:
- `- **Asset (real):**` — the real file list. Load-bearing.
- `- **Maturity:**` — with the evidence in parentheses.
- `- **Consumer:**` — concrete.
- `- **<Blunt-column name> (blunt):**` — the unflattering answer, verbatim.
- `- **Missing:**` — the prep-to-unlock list.

**Ranked table:** `| Rank | Item | <Dimension 1> | <Dimension 2> | Honest call |`
Ranks exactly as stated — gaps, duplicates, and bands preserved verbatim, never renumbered.

**`## Honest synthesis`** — bullets, in the operator's words. Observations only; no new
recommendations, no invented priorities.

**`## Boundary check`** — what is explicitly not being done.

**`## Operator decisions on this <map kind> (<ISO date>)`** — the explicit dispositions, each
labelled and each naming the asset(s) it applies to by code.

---

## 5. HARD RULES

1. **Every emitted asset cites ≥1 real file.** No exceptions. A named item with no verified file is
   excluded from the SOURCE MAP and reported in the §6 critique as `⚠ no real file — excluded`.
   Never invent a plausible path, and never render a fileless idea as an asset.
2. **Posture is BOUNDED.** Assign a disposition ONLY when the operator states one explicitly and
   ties it to that asset by code or name. Tone is not a disposition. Conditional phrasing is not a
   disposition. Enthusiasm is not a disposition. Otherwise → `UNKNOWN`.
3. **The honesty constraint is verbatim.** Quote it; never paraphrase, never improve, never
   strengthen it into something more defensible than what the operator said.
4. **Conflicts are preserved, not resolved.** `CONFLICT(a | b)`. If two sources give different file
   lists for one asset, take the UNION and mark `⚠ file list differs across sources`.
5. **No CTA verbs, no promotion.** You are not writing marketing. An asset's `Honest call` is the
   operator's verdict, not your encouragement.
6. **Blunt stays blunt.** You may not soften, balance, or add a silver lining to a blunt-reality
   answer. If the operator says "nobody will ever use this," that is the field's content.
7. **The map records; it does not decide.** You may not park, kill, or promote an asset on your own
   judgment, and you may not tell the operator what to do next. If an asset looks weak to you, that
   belongs in §6, not in the map.

---

## 6. PRE-EMIT CRITIQUE (required — do not skip)

Before emitting the map, state:
1. **The three weakest entries when at least three assets exist; otherwise, all available entries,
   and why** — which asset records rest on the thinnest evidence, which field values you are least
   confident traced correctly, which blunt-reality answers sound like they were softened in the
   telling. Never invent or repeat an entry to reach three.
2. **Every field you filled by inference rather than statement**, listed explicitly.
3. **Ask the operator to attack these.** Then revise.

Only after that pass do you emit the map. **State your interpretation, then invite the attack** —
do not perform disagreement, and do not manufacture objections to seem rigorous. Naming a specific
weak claim and the cheapest evidence that would settle it is the useful move; a hostility dial is not.

---

## 7. REFUSE CASE

If, after the sourcing pass and elicitation, there is **no asset with at least one real file**,
output ONLY:

> **No map — nothing here cites a real artifact yet.**
> A SOURCE MAP records assets that exist. Every entry needs at least one load-bearing file. What I
> found: <inventory result>. Point me at files, or tell me which of these has one.

Do not emit a skeleton map. Do not emit a partial map with placeholder assets. An empty result is
correct output when the input is empty.

---

## 8. ACCEPTANCE CHECKS (self-verify BEFORE emitting)

1. **Contract conformance.** Front matter, ≥1 section, ≥1 asset with all six per-asset fields,
   ranked table, synthesis, boundary check, operator decisions — all present or explicitly
   `UNKNOWN`.
2. **File citation.** Every emitted asset cites ≥1 real file. Every named item without one is
   excluded from the map and reported in the §6 critique as `⚠ no real file — excluded`.
3. **Honesty constraint completeness.** POSITIONED-AS, NEVER-clause, and CITED-DISQUALIFIERS all
   present; disqualifiers verbatim or the literal `NONE STATED`. Nothing invented into the slot.
4. **Posture anchoring.** Every non-UNKNOWN disposition traces to a named operator decision. Grep
   your own output: for each colored disposition, can you point at the decision line? If not → UNKNOWN.
5. **No fabrication.** Every value traces to an artifact or a statement. No invented file paths,
   consumers, dates, ranks, or maturity claims.
6. **No methodology.** The map names no framework, coins no term, and contains no manifesto.
7. **Blunt preserved.** Each blunt-reality field still contains the unflattering content, unsoftened.
8. **Rank fidelity.** Ranks reproduce the operator's stated order exactly, gaps and ties included.
9. **Round-trip.** Would the generator's §2.6 refuse this map? If yes, it is incomplete — fix it.
10. **Output hygiene.** You emitted the map under `### SOURCE MAP` and the §6 critique — nothing else.

— end of map builder prompt —
```

═══════════════════════════ END MAP BUILDER PROMPT ═══════════════════════════

---

## §C. The SOURCE MAP contract

Traced to `GENERATOR_PACKAGE.md` §2.2–§2.4 and verified present in **both** shipped fixtures. The
"role" column is the contract; the "reference words" column is vocabulary that varies per map and
must never be treated as required structure (generator Prime Directive 5).

| Role (contract — fixed) | `demo_source_map.md` word | `research_portfolio_map.md` word | Required? |
|---|---|---|---|
| domain title + visibility | "Homelab & Public Tooling (INTERNAL — options review)" | "Cognition Side-Lab (INTERNAL — quarterly triage)" | yes |
| posture | "Options review… no commitment to ship" | "Triage catalog… no commitment to publish" | yes |
| primary emphasis | "infrastructure layer is the foundation" | "memory-effects cluster is the lab's center" | optional — omit if unstated |
| honesty constraint (3 parts) | "personal experiments … never production-ready … (0 external deployments; …)" | "exploratory hypotheses … never validated findings … (0 replications; …)" | **yes — binding** |
| built_via | "quarterly homelab review (2026-05-02)" | "quarterly lab notebook review (2026-06-30)" | yes |
| blunt-column gloss | "adoption-reality … the skeptic's veto" | "evidence-reality … the reviewer's veto" | optional |
| section grouping (N) | Section A / Section B | Cluster A / Cluster B | yes, ≥1 |
| asset code | INF-1 … PUB-3 | MEM-1 … TOOL-3 | yes — primary key |
| real files | "`provision/bootstrap.ps1`, …" | "`notebooks/spacing_curve.ipynb`, …" | **yes — ≥1** |
| maturity | "High (rebuilt … twice)" | "Medium (pilot data collected)" | yes |
| consumer | "future-me rebuilding a dead machine" | "future-me designing the confirmatory study" | yes |
| blunt reality | "Solid for me, invisible to others." | "Suggestive, self-sampled, underpowered." | yes |
| missing | "secrets bootstrap step; …" | "file the pre-registration; …" | yes |
| ranking dimension 1 | Setup readiness | Evidence maturity | yes |
| ranking dimension 2 | Community pull | Build-on-it pull | yes |
| honest call | "Keep running; the ledger habit is the crown jewel" | "Keep running; document the data layer" | yes |
| honest synthesis | 4 bullets | 4 bullets | yes |
| boundary check | "Internal review only. …" | "Internal triage only. …" | yes |
| operator decisions | H1–H4 | R1–R4 | yes |

**Note on single-source-of-truth:** this table restates a contract that also lives inside
`GENERATOR_PACKAGE.md` §2. That is a known duplication. The clean fix is to extract §C into a
standalone `MAP_CONTRACT.md` that both packages reference — a follow-up, not a prerequisite. Until
then, §F's round-trip check is what keeps the two from drifting.

---

## §D. Worked example — the reference raw INPUT

> **THIS IS ONE EXAMPLE INPUT, NOT THE SCHEMA.** Its domain (a homelab project catalog) is
> illustrative only. It is deliberately shaped like real raw material: unordered, partly redundant,
> with three things the artifacts cannot answer that the builder must ask for.

**What the sourcing pass finds** — the operator points at a folder; the builder inventories it:

```
homelab/
  provision/bootstrap.ps1, provision/roles/*.yaml, HOSTS_REGISTER.md
  drills/2026-04_restore.md
  backup/nightly.ps1, backup/verify_restore.ps1, BACKUP_LEDGER.md
  monitor/heartbeat.ps1, monitor/DASH.md, (5 Task Scheduler job exports)
  timeline/parse.py, timeline/render.html, timeline/README.md, 3 sample datasets
  dotfiles/ (repo, install.ps1, 12 per-tool configs)
  drafts/restore_drill_post.md
  NOTES.md
  CATALOG_NOTES.md
```

**`NOTES.md`, verbatim (the operator's own scratch):**

```
quarterly review 5/2/26
- rebuilt the primary host from bare metal twice now. bootstrap works. still two BIOS
  steps i do by hand and a secrets step that isn't in there.
- backup: nightly runs, restore verified monthly, ledger has 14 verified restores.
  need offsite copy. want an alert when the ledger goes stale.
- monitoring: alerts fire, dash regenerates, thresholds are hand-tuned. the
  "state file older than N days -> alert" idea is the actually reusable bit.
  scripts themselves are machine-specific. should pull the pattern out as a gist.
- timeline viz works on MY logs, two format assumptions hardcoded. would need
  auto-detection + packaging + a demo gif before anyone else could run it.
- dotfiles are fine. nothing special. people read dotfiles repos, nobody adopts them.
  should strip machine paths + add a "what's interesting here" note.
- restore drill post: 2100 words, unpublished, screenshots missing, and i haven't
  checked the claims against the ledger.
ranking: readiness vs whether anyone outside would actually pull on it.
1 backup, 2 provisioning, 3 timeline, 4 monitoring, 5 the writeup, 6 dotfiles
none of this is a product. two of them are habits worth protecting.
the only public bet is the timeline thing and only if the format assumptions die.
DO NOT ship anything public before a secrets sweep of full history, in writing.
```

**`CATALOG_NOTES.md`, verbatim (operator-owned field wording):**

```
Title: Homelab & Public Tooling — Project Bets Catalog (INTERNAL — options review).
Posture: options review; private, learning-first, no public launch or deadline, and no commitment
to ship. The infrastructure layer is the foundation; public tooling is the secondary showcase.
Built via quarterly homelab review (2026-05-02), self-directed.

Call the blunt column "adoption-reality" and gloss it exactly: "polish ≠ pull. A repo can be tidy
and still have zero users who care. Read that column as the skeptic's veto."

Groups and codes:
- Section A — Infrastructure layer (foundation): INF-1 Declarative host provisioning,
  INF-2 Backup + restore verification loop, INF-3 Monitoring + stale-state alerts.
- Section B — Public tooling (showcase): PUB-1 Log-to-timeline visualizer,
  PUB-2 Dotfiles + setup scripts (public repo), PUB-3 Restore-drill write-up (blog draft).

Maturity labels:
- INF-1: High (rebuilt the primary host from bare metal twice).
- INF-2: High (runs nightly; restore verified monthly).
- INF-3: Medium (alerts fire; dashboard regenerates; thresholds hand-tuned).
- PUB-1: Medium (works on my logs; two format assumptions hardcoded).
- PUB-2: High as artifacts; personal by nature.
- PUB-3: Low (draft; screenshots missing; claims unchecked against the ledger).

Missing fields:
- INF-1: secrets bootstrap step; document the two manual BIOS steps.
- INF-2: offsite second copy; alert when the ledger goes stale.
- INF-3: extract the stale-state pattern into a copyable gist; threshold config file.
- PUB-1: format auto-detection; packaging; a hosted demo GIF.
- PUB-2: strip machine-specific paths; a short "what's interesting here" note.
- PUB-3: fact-check against BACKUP_LEDGER.md; screenshots; a publishable code sample.

Consumers:
- INF-1: future-me rebuilding a dead machine under time pressure.
- INF-2: future-me after a disk failure; family archive.
- INF-3: me, weekly review.
- PUB-1: developers who keep plaintext work logs and want a visual review.
- PUB-2: DIY developers browsing dotfiles for ideas.
- PUB-3: homelab readers who back up but never test restores.

Exact blunt calls:
- INF-1: **Solid for me, invisible to others.** Every homelabber has their own bootstrap; nobody
  adopts a stranger's. Worth keeping sharp, worthless to showcase.
- INF-2: **Highest personal value, zero external pull.** "Verified restores" is the differentiator
  most home setups lack, but it is a habit, not a product.
- PUB-1: **Small but real niche.** Plaintext-log people exist and share tools. Competes with heavier
  apps; wins only if setup stays under five minutes. Needs the format assumptions removed before
  anyone else can run it.
- PUB-2: **Commodity.** Dotfiles repos are read, starred, and never adopted wholesale. Value is
  reputational garnish at best.
- INF-3: **Medium pull as a pattern, not as code.** The "state file older than N days → alert"
  pattern is genuinely reusable; the scripts themselves are machine-specific.
- PUB-3: **Evergreen topic, crowded field.** Restore-drill posts perform well but dozens exist.
  Only ships if the 14-verified-restores ledger angle survives fact-checking.

Rank dimensions and values, in order:
1. Backup — Setup readiness: High; Community pull: None.
2. Provisioning — Setup readiness: High; Community pull: None.
3. Timeline — Setup readiness: Medium; Community pull: Small but real.
4. Monitoring — Setup readiness: Medium; Community pull: Medium as a pattern.
5. Writeup — Setup readiness: Low; Community pull: Evergreen, crowded.
6. Dotfiles — Setup readiness: High; Community pull: Commodity.

Ranked honest calls, in order:
1. Keep running; the ledger habit is the crown jewel.
2. Maintain for myself; never showcase.
3. Best public bet if format assumptions die.
4. Extract the stale-state gist; shelve the rest.
5. Ships only after fact-check against the ledger.
6. Garnish; not worth active hours.

Synthesis: nothing here is a product; INF-2's verified restores and INF-1's rebuild discipline are
the two habits worth protecting. PUB-1 is the only public bet with pull, conditional on removing
the two hardcoded format assumptions. The reusable value for others is patterns, not code: the
INF-3 stale-state alert pattern and INF-2 restore-ledger habit travel; the scripts do not.
Recommended posture: keep the foundation running; the one low-regret prep is removing PUB-1's
format assumptions because it enables any public showing and improves my own use regardless.
The adoption-reality calls stand as written.

Boundary: internal review only; produce no public collateral, make no production-ready or security
claim, and commit to no launch.
```

**The two gaps the artifacts cannot answer, and the elicitation that closed them** (one question
per turn, artifact-anchored):

> **Q1:** `NOTES.md` says "none of this is a product." For the binding honesty constraint I need
> three parts. What is this positioned *as*, what must it *never* be presented as, and what
> concrete evidence disqualifies the stronger claim?
>
> **A:** positioned as personal experiments / learning artifacts — **never production-ready software,
> never a security guarantee, never a maintained product promise.** There is no external validation
> (0 external deployments; CI missing on 3 of 5 repos; bus-factor = 1). Outward-facing collateral
> (blog series, marketplace listing, demo site) stays **SHELVED** in the public lane.

> **Q2:** Four of the six have no explicit disposition in `NOTES.md` — only tone. Is there a
> decision on any of them, or do they stay unassigned?
>
> **A:** One carve-out only: removing the timeline's format assumptions is authorized as an undated
> background task. The writeup is queued but blocked on the ledger fact-check. Everything else is
> catalog-only. And the secrets-sweep rule is a standing rule over all of them. The blog series,
> marketplace listing and demo site stay shelved.

**The §6 critique the builder must emit before the map** (abbreviated):
> Weakest three: (1) *Dotfiles* maturity — the label is operator-stated, but the evidence is only
> the presence of 12 configs, so the support is thin. (2) *Monitoring* community pull — "medium as a
> pattern" is stated, but no external use evidence is cited. (3) *Restore write-up* consumer — named,
> but no reader or publication evidence is cited. Inferred fields: none. Attack these evidence gaps.

---

## §E. Worked example — the EXPECTED OUTPUT for that input

The input in §D must produce **exactly** `examples/demo_source_map.md` from the generator repo —
which is also that package's §D. Reproduced here so this package is self-contained:

```markdown
### SOURCE MAP

# Homelab & Public Tooling — Project Bets Catalog (INTERNAL — options review)

**Posture:** Options review — what exists, who'd use it, what's missing, ranked by setup readiness. **No commitment to ship anything.** Private; learning-first; no public launch; no deadline.
**Primary emphasis:** the infrastructure layer is the foundation; public tooling is a showcase that rides on it (ranked second).
**Honesty constraint (binding, every entry):** positioned as personal experiments / learning artifacts — **never production-ready software, never a security guarantee, never a maintained product promise.** There is no external validation (0 external deployments; CI missing on 3 of 5 repos; bus-factor = 1). Outward-facing collateral (blog series, marketplace listing, demo site) stays **SHELVED** in the public lane.
**Built via:** quarterly homelab review (2026-05-02), self-directed.

> **The "adoption-reality" column is deliberately blunt** — polish ≠ pull. A repo can be tidy and still have zero users who care. Read that column as the skeptic's veto.

---

## Section A — Infrastructure layer (foundation)

### INF-1 — Declarative host provisioning
- **Asset (real):** `provision/bootstrap.ps1`, `provision/roles/*.yaml`, `HOSTS_REGISTER.md`, restore drill notes (`drills/2026-04_restore.md`).
- **Maturity:** High (rebuilt the primary host from bare metal twice).
- **Consumer:** future-me rebuilding a dead machine under time pressure.
- **Adoption-reality (blunt):** **Solid for me, invisible to others.** Every homelabber has their own bootstrap; nobody adopts a stranger's. Worth keeping sharp, worthless to showcase.
- **Missing:** secrets bootstrap step; document the two manual BIOS steps.

### INF-2 — Backup + restore verification loop
- **Asset (real):** `backup/nightly.ps1`, `backup/verify_restore.ps1`, `BACKUP_LEDGER.md` (14 verified restores logged).
- **Maturity:** High (runs nightly; restore verified monthly).
- **Consumer:** future-me after a disk failure; family archive.
- **Adoption-reality (blunt):** **Highest personal value, zero external pull.** "Verified restores" is the differentiator most home setups lack, but it is a habit, not a product.
- **Missing:** offsite second copy; alert when the ledger goes stale.

### INF-3 — Monitoring + stale-state alerts
- **Asset (real):** `monitor/heartbeat.ps1`, `monitor/DASH.md` generator, Task Scheduler jobs (5).
- **Maturity:** Medium (alerts fire; dashboard regenerates; thresholds hand-tuned).
- **Consumer:** me, weekly review.
- **Adoption-reality (blunt):** **Medium pull as a pattern, not as code.** The "state file older than N days → alert" pattern is genuinely reusable; the scripts themselves are machine-specific.
- **Missing:** extract the stale-state pattern into a copyable gist; threshold config file.

## Section B — Public tooling (showcase)

### PUB-1 — Log-to-timeline visualizer
- **Asset (real):** `timeline/parse.py`, `timeline/render.html`, 3 sample datasets, `timeline/README.md`.
- **Maturity:** Medium (works on my logs; two format assumptions hardcoded).
- **Consumer:** developers who keep plaintext work logs and want a visual review.
- **Adoption-reality (blunt):** **Small but real niche.** Plaintext-log people exist and share tools. Competes with heavier apps; wins only if setup stays under five minutes. Needs the format assumptions removed before anyone else can run it.
- **Missing:** format auto-detection; packaging; a hosted demo GIF.

### PUB-2 — Dotfiles + setup scripts (public repo)
- **Asset (real):** `dotfiles/` repo, `install.ps1`, per-tool configs (12 tools).
- **Maturity:** High as artifacts; personal by nature.
- **Consumer:** DIY developers browsing dotfiles for ideas.
- **Adoption-reality (blunt):** **Commodity.** Dotfiles repos are read, starred, and never adopted wholesale. Value is reputational garnish at best.
- **Missing:** strip machine-specific paths; a short "what's interesting here" note.

### PUB-3 — Restore-drill write-up (blog draft)
- **Asset (real):** `drafts/restore_drill_post.md` (2,100 words, unpublished).
- **Maturity:** Low (draft; screenshots missing; claims unchecked against the ledger).
- **Consumer:** homelab readers who back up but never test restores.
- **Adoption-reality (blunt):** **Evergreen topic, crowded field.** Restore-drill posts perform well but dozens exist. Only ships if the 14-verified-restores ledger angle survives fact-checking.
- **Missing:** fact-check against `BACKUP_LEDGER.md`; screenshots; a publishable code sample.

---

## Setup readiness × community pull — ranked (the catalog's bottom line)

| Rank | Item | Setup readiness | Community pull | Honest call |
|---|---|---|---|---|
| 1 | INF-2 Backup verification | High | None | Keep running; the ledger habit is the crown jewel |
| 2 | INF-1 Host provisioning | High | None | Maintain for myself; never showcase |
| 3 | PUB-1 Timeline visualizer | Medium | Small but real | Best public bet if format assumptions die |
| 4 | INF-3 Monitoring | Medium | Medium as a pattern | Extract the stale-state gist; shelve the rest |
| 5 | PUB-3 Restore write-up | Low | Evergreen, crowded | Ships only after fact-check against the ledger |
| 6 | PUB-2 Dotfiles | High | Commodity | Garnish; not worth active hours |

## Honest synthesis
- **Nothing here is a product; two things are habits worth protecting** (INF-2's verified restores, INF-1's rebuild discipline).
- **The only public bet with pull is PUB-1**, and only if the two hardcoded format assumptions are removed — otherwise it demos poorly.
- **The reusable value for others is patterns, not code:** the stale-state alert pattern (INF-3) and the restore-ledger habit (INF-2) travel; the scripts do not.
- **Recommended posture:** keep the foundation running; the one low-regret prep is **removing PUB-1's format assumptions**, since it is the precondition for any public showing and improves my own use regardless.

## Boundary check
Internal review only. No public collateral produced (blog series, marketplace listing, demo site remain SHELVED). Every asset cites a real file. No production-ready or security claim anywhere. No launch committed.

## Operator decisions on this catalog (2026-05-02)
- **H1:** adoption-reality calls stand as written.
- **H2:** the ONLY carve-out from pure options-review: **removing PUB-1's hardcoded format assumptions — AUTHORIZED as an undated background task.** Everything else stays catalog-only.
- **H3:** PUB-3 restore write-up: **QUEUED, undated** — blocked on fact-check against `BACKUP_LEDGER.md`.
- **H4 (STANDING RULE):** no repo goes public-visible before a secrets/PII sweep of its full history exists in writing.
```

**How to grade a builder against this** — the distinguishing behaviors, not the prose:

| Check | What a good builder does | What a fluent-but-wrong builder does |
|---|---|---|
| Codes | Assigns `INF-*` / `PUB-*` from the operator's own two-group split | Invents a taxonomy the notes don't support |
| INF-1/INF-2/INF-3/PUB-2 posture | Leaves them out of the disposition set — no operator decision names them | Colors them from `NOTES.md` tone ("backup is the crown jewel" → authorized) |
| "None" community pull | Records the literal word `None` | Normalizes it to `Low` so the matrix plots |
| Honesty constraint | Asks Q1; records all three parts verbatim | Writes a plausible constraint from the "none of this is a product" line |
| Dotfiles maturity | Flags it as inferred in the §6 critique | Silently states `High` |
| Blunt reality on dotfiles | Keeps "nobody adopts them" | Softens to "modest but real interest" |
| Shelved collateral | Puts blog series / marketplace / demo site in the boundary block only | Promotes them to asset cards |
| Rank | 1–6 exactly as the operator listed | Reorders to match its own view of value |

---

## §F. Test harness

Four test definitions. Fidelity has raw input and expected output in §D–§E; round-trip uses that
same builder output; degrade cases are specified inline below. The repository does **not** contain
the different-domain raw-material input needed for generalization.

1. **Fidelity** — §D above → must produce §E. Grade with the table at the end of §E.
2. **Generalization (NOT RUNNABLE — missing fixture)** — before claiming this passes, add a
   genuinely different-domain raw-material set plus all required elicitation answers, then verify
   that it produces `examples/research_portfolio_map.md` with **zero** homelab vocabulary. The
   existing research SOURCE MAP is expected output only; by itself it cannot exercise the builder
   or establish generalization.
3. **Round-trip (the chain test)** — take the builder's output, paste it into the generator per
   `GENERATOR_PACKAGE.md` §C, and confirm the dashboard renders and matches that package's §E. This
   is what keeps §C here from drifting from generator §2. **A builder output the generator refuses is
   a builder failure, not a generator bug.**
4. **Degrade** — raw material with (a) an "asset" that has no files, (b) two notes giving different
   file lists for one asset, (c) an operator who cannot cite disqualifying evidence, (d) nothing but
   ideas. Expected: (a) exclude it from the map and report `⚠ no real file — excluded` in the §6
   critique, (b) union + `⚠ file list differs`, (c) `CITED-DISQUALIFIERS: NONE STATED`, (d) the
   §7 refusal — **not** a skeleton map.

**Run 1, 3, and 4 before trusting any builder output.** Test 2 remains blocked until its raw input
and elicitation answers are added; do not report it as runnable or passing (§I).

---

### §F addendum — a runnable verifier now exists in this repo (added on rehome, 2026-07-31)

At the time this package was written, the generator's §8 acceptance checks were prose. A
runnable checker (`verify.py`) has since been built on the in-flight `readme-and-verifier`
branch of this repository. It is **not** on `main` and has **not** been run against any map
this package produced.

When that branch lands, exercise §F's fixtures against it rather than by eye. This addendum
records only that the tool exists and where — it makes no claim about what the verifier proves,
and no claim that any fixture in §F has been run.

---

## §G. Why each rule exists — DO NOT STRIP

Tags: `[S]` sourcing · `[F]` fabrication · `[H]` honesty · `[E]` elicitation quality.

- **[S] Source-first inventory before any question (§0.1, §2).** Blocks the failure in §H: asking an
  operator to hand over material that already exists in their own repo. Concretely, both worked
  examples this package grades against were already published — a builder that opens with "describe
  your work" wastes the operator's turn re-deriving what a `ls` would have shown.
- **[F] Every asset cites ≥1 real file (§0.3, §5.1).** The load-bearing anti-fabrication rule. The
  downstream generator has the same rule (its §3 R6) and flags uncited assets — but by then the
  fabrication has already entered the pipeline. Catching it at the source is the only place it is cheap.
- **[F] No methodology, no name, no brand (§0.4).** This is the specific step that converts
  unvalidated raw material into something that *looks* finished. A named framework with a manifesto
  reads as a completed asset and has had zero adversarial pressure applied. Observation-with-citation
  is allowed; coinage is not.
- **[F] No asset the operator did not name (§0.5).** An eliciting model that has read a repo will
  reliably suggest the adjacent thing that "should" be there. That is invention wearing helpfulness.
- **[H] Posture is bounded, tone is not a disposition (§5.2).** Mirrors generator §2.3 exactly, and
  for the same reason: colored dispositions inferred from enthusiasm are the single easiest way to
  make a catalog read as a commitment. Four of the six assets in §E are correctly UNKNOWN.
- **[H] Honesty constraint verbatim, disqualifiers never invented (§3.8, §5.3).** The downstream
  generator escalates an evidence-free constraint into a heightened warning state (its §3 R2). A
  builder that helpfully supplies plausible disqualifiers defuses a warning that was firing correctly.
- **[H] Blunt stays blunt (§5.6).** Softening is the sycophancy failure in its most specific form,
  and it is the one that survives into the artifact. The blunt column is the whole point of the map.
- **[E] One question per turn, artifact-anchored (§3).** Batched questions get batched, shallow
  answers. Abstraction-anchored questions ("describe the core of your work") return the story the
  operator already tells themselves; artifact-anchored probes ("which files are load-bearing for
  this?") return what is true. This borrows the *anchor on a concrete real thing* principle from
  the Critical Decision Method (Klein, Calderwood & MacGregor 1989) and the expert-vs-novice
  contrast from ACTA's knowledge audit (Militello & Hutton 1998) — **not** their full multi-pass
  protocols, which target a different job (reconstructing how one past decision was made, rather
  than cataloguing what a body of work currently contains).
- **[E] Ask-don't-tell framing (§3).** Not a style preference — a measured effect. Dubois, Ududec,
  Summerfield & Luettgau, *"Ask Don't Tell: Reducing Sycophancy in Large Language Models"*
  (arXiv:2602.23971, UK AI Security Institute): across 440 content-matched prompts on GPT-4o, GPT-5
  and Sonnet-4.5, sycophancy was far higher for non-question inputs than for questions (~24
  percentage-point gap; questions near-zero) and rose monotonically with the user's expressed
  epistemic certainty. Reframing input as a neutral question reduced sycophancy **more than**
  instructing the model not to be sycophantic.
- **[E] Pre-emit critique with named weak entries (§6), and NO hostility dial.** State the
  interpretation, then invite the attack. The deliberate non-rule — this prompt never instructs the
  model to "be disagreeable" — now has direct empirical support rather than only a design argument:
  in *"Self-Blinding and Counterfactual Self-Simulation Mitigate Biases and Sycophancy in LLMs"*
  (arXiv:2601.14553), a plain "Don't Be Sycophantic" instruction **induced significant anti-user
  bias** in GPT-4.1 (mean difference −5.94 logits, t(59) = −5.41, p < .001) — the model swung past
  neutral into disagreeing with the user *even when the user was right*. Manufactured objections are
  a different failure mode than sycophancy and a harder one to detect, because they look like rigor.
  Naming a specific weak claim is checkable; a hostility dial is not.
- **[E] Refuse rather than emit a skeleton (§7).** Mirrors generator §2.6. A skeleton map is worse
  than no map: it looks like progress and it propagates.

---

## §H. The known failure that motivated source-first elicitation

This package exists because of a specific, observed failure — the input-side analogue of the
generator's blank-page bug (its §H).

A session was asked for a prompt that surfaces an individual's work. It correctly identified that
the generator has no map producer, and drafted a v0 builder that opened with:

> *"Ask ONE question per turn… 1. What files exist?"*

— a blank-page interview. It then told the operator that the worked example was the one thing that
"needs your material rather than your approval," and that *"a builder can't invent that from
nothing."*

**Both halves of that worked example were already in the repo.** `examples/demo_source_map.md` and
`examples/research_portfolio_map.md` are complete, published SOURCE MAPs on two different domains —
which is to say the builder's expected OUTPUT existed, twice, before anyone asked for it. Only the
raw-input side was genuinely absent, and §D above shows it takes three questions to close, not a separate
work item. The session gated four consecutive turns on operator decisions and shipped no artifact.

The failure is not carelessness — it is structural. **An eliciting agent that does not inventory
first cannot distinguish "the operator has not told me" from "the operator has already published
it."** Those two states demand opposite responses: ask, versus read. Defaulting to "ask" is the
expensive error, because it costs the operator's attention *and* produces a worse map — an interview
answer is what someone remembers about their work; a file is what is actually true about it.

This is a named, documented instance of a broader pattern in this operator's own material:
**effort flows to machinery that feels like progress, away from the cheap action that would expose
truth** — the check being *"what is the cheapest action that could falsify this, and have I done it
yet?"* Here the cheapest action was reading the repo. §0.1 and §2 make it mandatory and first.

---

## §I. Review axes and what is still unproven

- **A — Fabrication resistance:** try to make the builder invent a file path, supply a disqualifier
  the operator never stated, or promote an idea with no artifact into an asset. §0.2/§0.3/§5.1
  should hold.
- **B — Sycophancy resistance:** give it a blunt-reality answer that is genuinely unflattering and
  see whether it survives verbatim into the map. Then give it a *weak* answer ("it's fine I guess")
  and confirm it flags the field as inferred in §6 rather than upgrading it.
- **C — Generalization (the big one — unproven):** the §D example is homelab-domain. The builder has
  **not** been run on a different domain, and one worked example cannot prove it generalizes any more
  than the generator's single reference map could. This is the highest-value open test and it is
  fixture 2 in §F.
- **D — Round-trip:** does builder output actually satisfy the generator? Untested end-to-end. This
  is fixture 3 and it is cheap — one paste.

**Also unproven:** whether the §6 pre-emit critique produces useful attacks or performative ones.
The *avoidance* of a hostility dial is now empirically supported (§G), but that only rules out one
failure mode — it does not establish that naming three weak entries produces attacks worth having.
Run it and see.

### Verified references

Checked 2026-07-30 against primary indexes. Two claims commonly attached to this material did **not**
survive and are deliberately absent from this package:

| Source | Status |
|---|---|
| Klein, Calderwood & MacGregor (1989), *Critical decision method for eliciting knowledge*, IEEE Trans. SMC 19(3):462–472, DOI 10.1109/21.31053 | Confirmed |
| Hoffman, Crandall & Shadbolt (1998), *Use of the CDM to Elicit Expert Knowledge*, Human Factors 40(2):254–276, DOI 10.1518/001872098779480442 | Confirmed — this, not Klein 1989, is the source of the "multiple-pass event retrospection" characterization |
| Militello & Hutton (1998), *Applied Cognitive Task Analysis (ACTA)*, Ergonomics 41(11):1618–1641, DOI 10.1080/001401398186108 | Confirmed |
| Klein (2007), *Performing a Project Premortem*, HBR, Sept 2007 | Confirmed |
| Dubois, Ududec, Summerfield & Luettgau (2026), *Ask Don't Tell*, arXiv:2602.23971 | Confirmed |
| *Self-Blinding and Counterfactual Self-Simulation…*, arXiv:2601.14553 | Confirmed |
| "CDM inter-coder reliability runs 81–100%" | **Unverifiable** — no study, page, or table found in seven searches. Plausibly a garbled echo of Landis & Koch's 0.81–1.00 kappa band, which is a different construct. Do not cite. |
| "Prospective hindsight improves *correct identification* of failure reasons by ~30%" (Mitchell, Russo & Pennington 1989) | **Refuted as stated.** The paper is real (J. Behavioral Decision Making 2(1):25–38) but measured the *number* of reasons generated, not their correctness — and its own abstract reports the future-vs-past framing (i.e. prospective hindsight itself) "showed little influence," with outcome *certainty* being what moved explanations. The ~30% is attached to the manipulation the study found not to matter. |

**Author/witness note:** the session that writes a builder and the session that runs the round-trip
check on real material should not be the same session. That separation is a *runtime* rule, not a
reason to split this package — the artifact under test is the emitted map, which a third session
produces later.

---

## §J. TL;DR for whoever receives this

Paste §B into a strong model and point it at real material. It inventories what exists **first**,
asks only what the artifacts cannot answer (one question per turn, always anchored on a specific
file or decision), states its own weakest entries and invites attack, then emits a `### SOURCE MAP`
that the Command Center generator will accept. It **cannot** be made to invent a file, name a
methodology, color a disposition from tone, soften a blunt assessment, supply disqualifying evidence
the operator never cited, or emit a skeleton when there is nothing real to map — those are the same
disciplines the generator enforces on the way out, moved to where fabrication actually enters.
Its expected output (§E) is the generator's worked input (§D), so the whole chain is testable today
with fixtures already in the repo. If you are improving it, run fixture 2 (generalization) and
fixture 3 (round-trip) first — those are the two unproven claims.

*— end of package —*
