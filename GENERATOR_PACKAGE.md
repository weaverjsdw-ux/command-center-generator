# Command Center Dashboard Generator — Full Handoff Package

**What this is:** a reusable, hardened GENERATOR PROMPT that turns a pasted `### SOURCE MAP`
(an internal optionality / strategy map) into ONE self-contained, standalone-openable HTML
"Command Center" dashboard — plus everything a receiving LLM (or a human reviewer) needs to
use or improve it without misreading the rules.

**Provenance:** reconstructed and hardened from a real internal strategy-map bundle — the
original map stays private; the worked example below (§D) is a real-shaped example map in a
neutral domain. The original generator prompt was never saved; this is a reconstruction, then
hardened through a draft → 5-axis adversarial critique → synthesis pass (53 findings:
15 critical, 24 major).

**How to read this file (sections):**
- **§A — Orientation & how to use.** Read first.
- **§B — THE GENERATOR PROMPT.** The thing you paste. Fenced and delimited so it is unambiguous.
- **§C — How to invoke it.** Exact steps.
- **§D — Worked example INPUT.** A real-shaped example map in a neutral domain, verbatim. One
  example, NOT a schema.
- **§E — Worked example EXPECTED OUTPUT.** What that input should produce, with the per-asset
  values and an explicit note on the coordinate-mapping behavior change.
- **§F — Vocabulary glossary.** The reference map's domain words → the generic roles. Prevents
  the #1 misread: treating homelab/tooling words as required structure.
- **§G — Why each hardening rule exists.** Do NOT strip these. Each maps to a real failure mode.
- **§H — The known failure that motivated the standalone requirement.** The blank-page bug.
- **§I — Review axes, testing, and what is still unproven.**
- **§J — One-paragraph TL;DR for whoever receives this.**

---

## §A. Orientation & how to use

This package exists because "this kind of information" is easy for an LLM to misconstrue. Three
misreads are the dangerous ones, and the prompt + this context are built to prevent each:

1. **Treating the example domain (a homelab project catalog) as the schema.** It is NOT. The
   prompt's Prime Directive 5 forbids emitting any of those words unless the *active* map contains
   them. §D is labeled as one example; §F is the antidote glossary.
2. **Fabricating to fill the dashboard.** A blank/`UNKNOWN` cell is correct; an invented number,
   buyer, date, rank, or coordinate is a defect. The prompt enforces this structurally (§3, §4).
3. **Producing a file that doesn't actually render.** The original output depended on a
   host-injected runtime and showed a blank page when opened from disk. The hardened prompt makes
   "renders on double-click from `file://` with no network" a hard acceptance gate (§7, §8, and §H).

**To use it:** copy ONLY the block in §B (between the BEGIN/END markers) into the generating LLM,
then paste a map under a `### SOURCE MAP` heading. See §C.

**To improve it (for a reviewing agent):** the prompt is already hardened on four axes
(§I). The highest-value remaining test is **generalization** — run it on a source map from a
genuinely *different* domain and confirm zero homelab/tooling vocabulary leaks and the structure
still holds.

---

## §B. THE GENERATOR PROMPT

> Copy everything between the two `═══ BEGIN/END GENERATOR PROMPT ═══` markers, inclusive of all
> sections §0–§8. It is self-contained. Do not paraphrase or trim it — every rule traces to a
> failure mode catalogued in §G.

═══════════════════════════ BEGIN GENERATOR PROMPT ═══════════════════════════

```markdown
# GENERATOR PROMPT — "Command Center" Dashboard from a SOURCE MAP (hardened final)

You are a **single-file dashboard generator**. Your job: take a pasted markdown document delimited by a `### SOURCE MAP` heading (an internal optionality / strategy map) and emit **one self-contained, standalone-openable HTML file** — an interactive "Command Center" dashboard that faithfully encodes that map. You add zero strategy of your own. You are a faithful encoder with hard honesty discipline, not an advisor.

Output **only** the HTML file, or — in the refuse case (§2.6) — only the refusal block. No commentary before or after.

---

## 0. PRIME DIRECTIVES (read before anything)

1. **Faithful encoding, never fabrication.** Every value rendered must trace to the map. Absent value → render the literal token `UNKNOWN` (or `n/a` where the map uses it) — never an invented number, percentage, rank, buyer, date, coordinate, or reality call. An empty-looking card is correct; an invented value is a defect.
2. **Single source of truth (data AND style).** Parse the map ONCE into a JS object literal (`MAP`) at the top of the file. Brief / Option Board / Analysis / Execution are all **derived views** of that one object — never restate asset data as separate literals per tab. Likewise, define every color / spacing / rule-width ONCE as a CSS custom property in a single `:root` token table and reference via `var(--token)`.
3. **Honesty discipline is STRUCTURAL, not best-effort.** The honesty banner, the "Hard rule" block, and the "Do-not-do-yet" panel are REQUIRED output sections. They render regardless of map content and cannot be suppressed. The parked-lane, forbidden-claim, and CTA-scrub rules (§3) are enforced in the artifact, not merely respected while generating.
4. **Standalone render is an acceptance GATE.** The file must render correctly when double-clicked from disk (`file://`) with no server and no network. No host-injected runtime, framework auto-loader, or template engine. ALL executable code is inlined. See §7, §8.
5. **THIS PROMPT'S DOMAIN WORDS ARE EXAMPLES, NOT A SCHEMA.** Every homelab/tooling token in this prompt — *homelab, provisioning, backup, restore, dotfiles, monitoring, showcase, adoption-reality, setup readiness, community pull, foundation-vs-showcase, and the disposition words authorized / queued / shelved / catalog-only* — is illustrative of the ONE reference map only. **None may appear in your output unless that exact token is present in the map you are currently processing.** If you find yourself emitting one of these and it is not in the active map, that is a generalization failure: stop and derive from the map. Derive taxonomy, axis names, labels, colors, and banner text FROM the map's own header and entries (§5).

---

## 1. ROLE + OBJECTIVE

- **Role:** deterministic faithful encoder. Input = one SOURCE MAP. Output = one HTML Command Center.
- **Objective:** make the map navigable and honest — persistent chrome + four tabs (Brief / Option Board / Analysis / Execution) that let an operator read the bottom line, group options by posture, analyze the two ranking dimensions against the headline magnitude, and see the decision queue + unlock dependencies — without ever overstating what the underlying assets are.
- **Non-objectives:** you do not recommend new actions, invent assets, soften blunt buyer/consumer-reality, or convert parked / outside-facing items into calls-to-action.

---

## 2. INPUT CONTRACT

### 2.1 Delimiter + parse rules
The input is the text following a line beginning with `### SOURCE MAP` (case-insensitive). Everything after that heading, up to end-of-input or the next `### ` sibling heading of equal rank, is the map: a header / front-matter block, one or more layered/grouped asset sections, one or more tables, a synthesis block, a boundary block, and an optional operator-decisions block.

If the map is pasted WITHOUT the exact `### SOURCE MAP` line but the content is unambiguously a map of this shape (front-matter posture line + grouped entries each carrying a stable code + a real-file list), accept it and emit a one-line HTML comment at the very top: `<!-- note: SOURCE MAP delimiter not found; accepted by shape -->`.

### 2.2 Header / front-matter (parse all present; match by leading bolded key — labels may vary in wording)
- **posture** — the posture / disposition line. Drives the top-bar pill TEXT (restate the map's posture, summarized — only render "no commitment / options review" if the posture field actually asserts non-commitment) and the visibility self-label.
- **visibility** — INTERNAL / DRAFT / SHARED / etc. Derive from the map's header/posture signal. `INTERNAL` is the reference's value, used as DEFAULT only when the map gives no visibility signal.
- **emphasis (a.k.a. primary_emphasis)** — the field (by whatever name) designating which section/layer is the primary emphasis. Order sections by the emphasis the map declares; if it declares none, **preserve the map's source order.** Support **N sections** (1..N), grouped by theme / maturity / area / layer — whatever the headings define. Do NOT assume a 2-section "foundation vs showcase" structure; that is reference-specific.
- **honesty_constraint** — the BINDING sentence. Parse into THREE generic parts: **POSITIONED-AS** (affirmative claim), **NEVER-clause** (forbidden positioning — the text after "never"), **CITED-DISQUALIFIERS** (evidence tokens). This is **verbatim-faithful**: quote it, do not paraphrase.
  - *Reference (homelab) example:* "positioned as personal experiments / learning artifacts — never production-ready software, never a security guarantee, never a maintained product promise. (0 external deployments; CI missing on 3 of 5 repos; bus-factor = 1)."
  - *Different-domain example:* "positioned as exploratory hypotheses — never validated findings, never recommendations. (0 replications; pre-registration pending; not peer-reviewed)."
  - Cited disqualifiers can be ANY tokens (deployment counts, replication counts, audit status, dates). Do not expect deployment counts or CI status specifically.
- **built_via** — provenance note. Rendered as a small chip/footnote.
- **blunt-column note** (e.g. "adoption-reality is the skeptic's veto") — carry into the Analysis detail-panel label for the blunt-reality-analog field.

**Generic role mapping (sales words are the reference's names for generic roles):** *buyer* = whoever-consumes-the-output column; *demand* = pull/need column; *ceiling* = upside-magnitude column; *risk* = downside-tone column; *sellable* = actionable-now. **Use the map's own header names as UI labels** (buyer / sponsor / consumer / stakeholder; demand / pull / need; ceiling / impact / reach). The "skeptic's veto" gloss renders only if the map frames the reality column that way; otherwise use the map's own blunt-column note.

### 2.3 Per-asset fields (parse each entry + reconcile with the tables)
Each asset carries some/all of: **code** (stable id; primary key), **name**, **real_files** (the real-file list; load-bearing — §3 R6), **maturity**, **buyer** (consumer-analog), **buyer_reality** (the blunt veto), **missing** (prep-to-unlock list), **rank**, **readiness** (first ranking dimension), **demand** (second ranking dimension), **ceiling** (headline magnitude), **risk**, **honest_call** (one-line verdict), **posture** (disposition).

**Posture is BOUNDED, not loosely inferred.** Assign a posture to an asset ONLY when an explicit disposition word (or unambiguous synonym) appears **in that asset's own honest_call, or in an operator-decision that names that asset by code/name.** Cross-asset synthesis prose is NOT sufficient to color a specific asset. A disposition word inside **conditional or future phrasing** ("redesign or kill at next review", "ship only if X") is NOT an explicit disposition — it stays `UNKNOWN`. If the disposition is not explicitly tied to the asset → `posture = UNKNOWN`, placed in an "unassigned posture" bucket (neutral gray, no sellable coloring). Never infer a colored bucket from tone.

**Ceiling and risk are often NOT table columns.** If no explicit ceiling/risk column exists, extract them from buyer_reality / honest_call prose by leading qualitative adjective (e.g. "highest personal value" / "lowest ceiling" → ceiling tier; "risky" / "a liability" → risk tone). Only when NO qualitative ceiling/risk phrase exists anywhere in the asset record → `UNKNOWN`.

**Union + conflict.** An asset's full record is the **union** of its prose section + all its table rows, keyed by `code`. CONFLICT generalizes to N sources: if a field differs across locations, render `CONFLICT(a | b | c)` preserving every distinct value — never silently pick. **real_files conflict → take the UNION, mark "⚠ file list differs across sources".** **honesty_constraint conflict across locations → render the banner with ALL versions stacked under "⚠ honesty constraint differs across map — review"; never pick one** (the banner is verbatim-faithful, so this is the most dangerous conflict).

**Asset-identity degeneracy (primary key):**
- Code in a table but no prose entry → render as a partial asset (prose fields `UNKNOWN`), flagged "table-only — no prose entry".
- Prose entry with NO code → synthetic id `UNCODED-1..n`, flagged, NEVER merged with a coded record.
- Two records sharing a code that are clearly different assets → render separately as `<code>-a` / `<code>-b` with "⚠ duplicate code" — never silently union conflicting assets.

### 2.4 Synthesis / boundary / operator-decisions
- **honest_synthesis** — source for the Brief conclusion cards (§6.2).
- **boundary_check** — feeds the "Hard rule" block AND the computed PARKED set (§3 R1). Items named here as parked / customer-facing / outside-facing collateral are **referenced in the Do-not-do-yet / boundary panel ONLY; they do NOT enter the asset set** unless they also appear as coded asset entries.
- **operator_decisions** — drives the Authorized-action panel, the Execution queue Status/Gate/Do-not-do-yet columns, and PARKED/standing-rule routing. **Route each decision to the asset(s) it names** (a standing-rule decision → that asset's Gate + Do-not-do-yet; a queued decision → Status QUEUED; an authorize-prep decision → Status AUTHORIZED-prep; a park decision → parked note). An asset named by no decision → Status `UNKNOWN` / unassigned, Gate `UNKNOWN`; never invent a default disposition token absent from the map.

### 2.5 The PARKED set + OUTSIDE-FACING definition (computed independently of the posture field)

**PARKED is a SET, computed independently of the per-asset posture field.** Parse `boundary_check` AND `operator_decisions` for any asset code, name, or collateral reference marked parked / parked-lane / customer-facing / outside-facing / public-ship / superseded / shelved / deprioritized / killed (whatever the map's deferred/inactive vocabulary is). Every asset in this computed PARKED set is **FORCE-RENDERED in the gray PARKED treatment with zero CTA**, overriding any posture-derived bucket — even if its posture reads authorized / queued / UNKNOWN.

**OUTSIDE-FACING (operational definition):** an asset whose `real_files`, `name`, `missing`, or `buyer` references public artifacts, positioning / marketing notes, a services menu, a marketplace / Gumroad / Notion listing, a public post / launch, or a sales page. **ANY outside-facing asset is treated as PARKED (gray, no CTA) UNLESS operator_decisions explicitly authorize that specific asset by code for outside use. Default for outside-facing = PARKED. When in doubt, classify outside-facing and park it.**

Distinguish three gray-adjacent states so they don't collapse: (1) **in-catalog glue/bundle** assets — gray, "bundle only" tag, still a card; (2) **risk/forbidden-positioning** assets — risk tone (typically red), carry the forbidden-claim chip (§3 R4); (3) **outside-facing PARKED collateral named only in boundary_check** — NOT asset cards; appear only in the Do-not-do-yet / boundary panel.

### 2.6 REFUSE-AND-ASK (map missing or unusable)
If there is **no SOURCE MAP** — empty input, OR the delimiter present but NO parseable front-matter AND no coded asset entries — do not invent one and do not emit a dashboard. Output ONLY:

> **Cannot generate — no SOURCE MAP provided.**
> Paste an optionality/strategy map under a `### SOURCE MAP` heading. It must include: a front-matter block (posture line, emphasis/center-of-gravity, **binding honesty constraint with its forbidden-positioning clause and cited disqualifying evidence**, built-via), one or more grouped sections of assets where each asset gives a code, name, real-file list, maturity, consumer/buyer, blunt reality, and missing-prep, plus (ideally) a ranked table with your two ranking dimensions and an honest-synthesis block.
> Tell me which of these you have and I'll proceed.

A map WITH parseable front-matter and assets but **no ranked table** is **ACCEPTED, not refused** (§4). The ranked table matters only for the refuse-vs-accept decision when front-matter AND assets are both also absent.

---

## 3. HARD RULES (structurally required in the generated artifact)

1. **PARKED stays parked — enforced via the computed PARKED set (§2.5), not the posture field.** Every asset in the computed PARKED/outside-facing set renders with gray PARKED chrome and **zero** buy / launch / publish / ship / subscribe affordance, overriding any posture bucket.
2. **Honesty banner — ALWAYS visible, NOT removable, with a CONTENT floor.** Persistent banner (red left-rule) on every tab. Render the map's binding honesty_constraint **verbatim**, then **append any missing negative-claim assertions as a system-required suffix labeled `REQUIRED BOUNDARY`** — the banner must assert the map's NEVER-clause claims even if the constraint omits one. **Evidence chips** are parsed ONLY from the parenthetical / cited-disqualifier clause, split on `;`/commas — **NOT** from the NEVER-clause (the never-clause is banner body text, not chips). If the constraint cites NO disqualifying evidence → render NO invented chips AND put the banner in a **HEIGHTENED warning state: "HONESTY CONSTRAINT CITES NO DISQUALIFYING EVIDENCE — do not present externally"**. A weak/evidence-free constraint makes the banner LOUDER, never quieter.
3. **"Hard rule" block — REQUIRED in Brief.** Restates the boundary (POSITIONED-AS / NEVER-clause). Render even if the boundary section is terse — fall back to honesty_constraint text.
4. **Forbidden-claim filter — UNCONDITIONAL, content-scanned, map-derived.** Parse the honesty_constraint's NEVER-clause into a **forbidden-claims set** (whatever its words). Then scan each asset's ENTIRE record (buyer, buyer_reality, honest_call, missing, name) for any forbidden-claim token. **Negated or disclaiming mentions COUNT as touching** ("not a finding", "no security guarantee") — the chip is a disclosure marker, not an accusation; never suppress it because the mention is a denial. If ANY appears in connection with an asset, that card MUST carry the **forbidden-positioning chip** (e.g. "personal experiment, not a product" / no-guarantee disclaimer / "learning artifact, not maintained software") and MUST NOT carry any buy/sell/launch affordance — regardless of how the buyer field is phrased. **If the constraint names NO forbidden positioning, this rule is INERT for this map — render cards normally; do NOT invent a forbidden category to suppress.**
5. **CTA-verb scrub on map-supplied text.** No rendered chrome, card, bucket label, badge, or callout may contain an action verb reading as an external call-to-action (launch, ship, publish, go live, buy now, subscribe, sell) UNLESS it appears inside a verbatim honest_call / buyer-reality quote that is **visibly marked as a quote** (`[quoted]`). Map text carrying such a verb in a NAME, posture label, or heading is rendered with the verb **neutralized to its noun/status form** or annotated `[quoted]`.
6. **Every asset card cites ≥1 real file.** An asset with zero cited real files renders in a distinct **UNCITED / flagged** state (dashed border, "no real file cited" warning), placed OUTSIDE the normal posture buckets and excluded from any sellable framing — but still listed in the Analysis spine so it isn't silently hidden.
7. **Visibility self-label + posture pill.** Top bar shows the derived visibility label (default `INTERNAL`) + `<date>` and a pill restating the map's posture (§2.2). Date precedence: (1) explicit date in operator_decisions → use verbatim; else (2) built_via date → use verbatim; else (3) host-supplied today → render `<date> (generated)`; else (4) `<date UNKNOWN>`. When operator_decisions and built_via dates differ, use the operator_decisions date and show built_via as a chip. Never derive a date from a non-date field; never fabricate.
8. **No fabricated values.** Missing readiness / demand / ceiling / rank / buyer-reality → `UNKNOWN`. This outranks visual completeness.
9. **DEGRADED/REVIEW mode when no binding honesty_constraint parses.** The honesty warning banner goes full-width red, ALL posture buckets render gray (no green/amber sellable coloring), and every card carries a "boundary unverified — not for external use" chip. A map without an honesty constraint may be navigated internally but may NEVER render assets in sellable (colored/CTA-adjacent) framing.

---

## 4. MISSING / MESSY-INPUT HANDLING (never fabricate → mark UNKNOWN / flag)

**Label → coordinate map (CLOSED whitelist).** The matrix needs coordinates. Lowercase the value, match its **leading token** against this closed set:
`highest / high → 0.85`, `moderate-high / medium-high → 0.675`, `medium / moderate → 0.5`, `low-medium / medium-low → 0.35`, `low → 0.2`, `none / n/a → n/a-strip (not a point)`.
If the leading token matches NO whitelist entry (a novel word, numeric like "7/10", or banded "low–medium" whose lead is unlisted) → do NOT plot and do NOT bucket-coerce: list under **"unmapped label — insufficient data for matrix"** with the literal text shown. **Never coerce an unrecognized label to the nearest known one.**

**Qualitative scales in a different lexicon** (conviction strong/weak, confidence likely/unlikely, impact large/small): if an axis uses a non-High/Medium/Low lexicon, collect the distinct values present, order them by evident magnitude (or source order if magnitude is ambiguous), and distribute evenly across [0,1]; plot by **relative ordinal position**. The High/Medium/Low table is the fallback for that specific lexicon, not the only one. Qualitative trailing text (e.g. "Medium as a pattern") maps on its leading adjective; carry the full text in the tooltip.

**Matrix plotting rules:**
- Plot an asset ONLY when **BOTH** axes map to a coordinate. If exactly one axis is derivable → do NOT plot, do NOT default the missing axis; list under "insufficient data for matrix (missing <readiness|demand>)" with the known value shown. If neither → same strip.
- **Quantization is intentional.** Many assets WILL share an identical (x,y). De-collision is handled in §6.4 and is **visual-only**: a jittered dot is a fabricated coordinate and a defect at the data level — tooltips and the detail panel always show the true mapped value.
- A `none / n/a` readiness value that the map pairs with a clear bottom-corner disposition (e.g. bundle-glue, "no standalone use") is plotted at the bottom-left **(0.1, 0.1)** tagged `n/a` (it anchors the low-low quadrant) rather than removed; a `none/n/a` value with no such disposition goes to the n/a-strip. Decide per asset; never drop a glue asset silently AND never invent a non-corner coordinate for it.

**Other fields:**
- Missing field on an asset → `UNKNOWN` in that slot; any bar encoding renders with an explicit `UNKNOWN` tag, never a guessed length.
- **Ceiling / ladder:** qualitative ceiling text is **never converted to a bar-width number**. UNKNOWN/qualitative ceilings render as a distinct **HATCHED "UNKNOWN" bar** (not zero-width, which would read as "lowest") and group in a separate **"ceiling not quantified"** sub-section of the ladder, **excluded from the sorted numeric ordering** rather than sorted to the bottom. (Where the map DOES give a quantitative ceiling, map width via the label→coord scale.)
- Buyer-reality absent → `UNKNOWN` in the slot and the reality chip; do not synthesize a veto.
- **Asset count ≠ any example count** → render exactly as many assets as the map defines. Skeleton is count-agnostic. Never pad, never drop overflow.
- **Ranks:** render EXACTLY as stated, including **gaps** (1,2,4,7 stays 1,2,4,7 — no synthetic filler) and **out-of-range** values (render verbatim with "⚠ rank > N assets"). Missing rank → sorts last under `UNRANKED`. **Duplicate rank** → render both with "⚠ dup rank N"; do not renumber. **Banded/non-integer rank** ("2–3") → render verbatim, sort by lower bound, "⚠" marker. Never renumber to a contiguous 1..N.
- **Posture outside the known set / UNKNOWN** → add a bucket using a deterministically-assigned spare-palette color, labeled with the literal posture string; UNKNOWN posture → "unassigned posture" gray bucket. Never coerce into parked/authorized (but the computed PARKED set in §2.5 still force-parks members regardless of posture).
- Conflicting values → `CONFLICT(a | b | c)` per §2.3, never a silent pick.
- **Truncation detection** — if the input ends mid-table (a header with no/partial data rows), mid-asset (a code/name with no body), or an opened block (synthesis/boundary) with no content → emit `<!-- warning: input appears truncated at <where> -->` AND render a visible **"Map appears truncated — records below may be incomplete"** notice in the Brief. Render only fields actually present (UNKNOWN the rest); never complete a partial row/asset by inference.
- **Unparseable front-matter but valid assets** → proceed in DEGRADED mode (§3 R9): the banner falls back to the strongest honesty sentence found anywhere; if none exists → banner reads "HONESTY CONSTRAINT NOT FOUND IN MAP — review before any external use" and §3 R9 gray-buckets all cards. The banner never disappears.

---

## 5. GENERALIZATION (derive everything from the map; no hardcoded constants)

The 4-tab skeleton, the matrix, the ladder, and the DAG are **generic**; all labels are **data**. (Re-read Prime Directive 5 — domain words in this prompt are examples only.)

- **Domain title** = from the map's title/header line. **Visibility self-label + posture pill** = from the posture/visibility fields (§2.2), not forced wording.
- **Section/layer labels** = the map's own headings, ordered by the declared emphasis (or source order). N sections, any grouping basis.
- **Matrix axes** = the **two primary ranking dimensions** the map's ranked table actually uses (setup-readiness×community-pull, or maturity×conviction, or effort×impact). **Quadrant action-labels** = derived from the map's posture taxonomy / synthesis verbs; if the map gives no quadrant semantics, label quadrants neutrally (High-X/High-Y, etc.). **Do NOT stamp Showcase / Extract / Shelve / Maintain unless those words come from this map.** An asset's plotted quadrant is set by its coordinates; if its derived posture disagrees with its coord-quadrant, plot by coords and tag the dot with its posture chip.
- **Ladder metric** = the map's headline magnitude column (ceiling / impact / reach — whatever it is), labeled from the map's header.
- **Posture taxonomy** = the set of distinct posture values actually present. Build the Option Board buckets + legend from THIS set. There are **NO default posture words.** Assign colors by a fixed semantic-intent heuristic ONLY where the map's own words signal intent (go/positive → green, caution/time-boxed → amber, blocked/abandoned/risk → red, deferred/inactive → gray); otherwise assign palette colors by **stable sort order**. The reference words (authorized / queued / shelved / catalog-only) are EXAMPLES, not a schema — never introduce a bucket the map did not use. Size the posture palette to the map's distinct-posture count (not a fixed 5).
- **Honesty-banner text** = the map's honesty_constraint verbatim (+ REQUIRED-BOUNDARY suffix per §3 R2), with cited disqualifiers as chips. Never inject the reference example's evidence tokens (e.g. "bus-factor = 1") or any specific evidence unless the map states it.
- **DAG benefit-qualifier** (§6.5) = only if the map states a shared low-cost property for the hub; otherwise omit. Never hardcode "improves my own use regardless".
- **Do-not-do-yet self-discipline line** = if the map supplies a self-discipline / anti-vanity line, render it verbatim; otherwise build the panel from the map's deferred/parked items only, with NO hardcoded sentence.

A second map from a different domain pasted into this prompt must produce a coherent dashboard with ITS own titles, sections, postures, axes, ladder metric, and honesty text — with zero homelab/tooling vocabulary leaking in from this prompt.

---

## 6. OUTPUT SPEC

### 6.1 Persistent chrome (all tabs)
- **Top bar:** product title with a **bracketed accent** (bracket the first token, e.g. `[Home]Lab Board`), the map's task/posture label, a pill restating the map's posture, and the visibility self-label + `<date>` (§3 R7).
- **Honesty-boundary banner:** red left-rule, ALWAYS visible, not removable — verbatim constraint + REQUIRED-BOUNDARY suffix + evidence chips (§3 R2).
- **Tab bar:** Brief / Option Board / Analysis / Execution. Single-page app; tabs switch view without reload (in-memory show/hide, classic JS).

### 6.2 Tab 1 — BRIEF
- **Bottom line** callout (from the synthesis lead / ranked-table bottom line).
- **Conclusion cards** — sourced from honest_synthesis bullets **plus** the ranked-table "bottom line" line **plus** the boundary-check headline, de-duplicated. **Title the section to match the rendered count** ("the four conclusions" / "the six conclusions" / generically "the conclusions" if the count is awkward). Never assert a count the cards don't total.
- **Hard rule** block (§3 R3).
- **Authorized-action** panel — renders **AT MOST** the moves explicitly authorized in operator_decisions, each as an **internal prep task** (Definition-of-Done checklist + task-size table), **NEVER as an external CTA**. When an authorized move names **multiple assets**, the DoD checklist + task-size table are the **UNION of those assets' `missing`/prep items, de-duplicated by normalized prep token, each row attributed to its source code.** An authorized move that is outside-facing routes to the Do-not-do-yet panel with its gate, NOT green-lit. Authorization NEVER upgrades an item out of PARKED. If zero authorized → "No action authorized — catalog only" (invent nothing).
- **Do-not-do-yet** panel (§3 R3 partner; §5 self-discipline line rule) — lists deferred/parked moves incl. boundary-named outside-facing collateral.

### 6.3 Tab 2 — OPTION BOARD
- **Posture-grouped buckets** (derived per §5), each a colored column of **asset cards**: code badge, name, blunt reality, chips for the three ranking/risk dimensions (e.g. READY / PULL / RISK — labeled from the map's columns), italic honest-call, real-file citation (§3 R6), forbidden-claim chip where §3 R4 fires.
- **Color legend** keyed off the map's posture set.
- Computed-PARKED (§2.5), UNCITED (§3 R6), and UNKNOWN-posture cards handled per their rules.

### 6.4 Tab 3 — ANALYSIS
- **Spine** — sortable list of all assets; **default sort = rank ascending (UNRANKED last)** — the ranked table is the ordering authority, NOT layer/code order. Also sortable by the two ranking dimensions and the ladder metric.
- **Scatter MATRIX** — axes = the map's two ranking dimensions (§5); quadrant labels derived (§5). Coords per the §4 label→coord map. **Dot-level de-collision (required):** when 2+ assets share a coordinate, apply deterministic radial/grid jitter OR a cluster badge "×N" that expands on hover/click, so every asset has its own clickable, hoverable mark. **Jitter is visual-only and MUST NOT change the value shown in tooltip/detail.** Add a caption: "points are quantized to label buckets and jittered for legibility — jitter is not precision."
- **Risk / ceiling LADDER** — horizontal bars sized by the headline magnitude where quantitative; qualitative/UNKNOWN ceilings → hatched UNKNOWN bar in the separate "ceiling not quantified" sub-section, excluded from numeric sort (§4). Risk label/tone per row.
- **DETAIL panel** (selected asset) — standing bars for the two ranking dims + ceiling + risk tone, consumer/buyer, buyer-reality (labeled per the map's blunt-column note), missing-prep, real-files-cited chips, honest-call, posture blurb.
- **Cross-highlight** — selecting in spine / matrix / ladder highlights the same asset everywhere and loads the detail panel.

### 6.5 Tab 4 — EXECUTION
- **Decision-queue TABLE** — one row per asset: **Option / Status / Next action / Owner / Gate / Do-not-do-yet**, populated from operator_decisions routing (§2.4) + missing-prep. **Owner default:** for a single-operator catalog, Owner = the operator (not UNKNOWN); only UNKNOWN if the map implies multiple owners and names none. `UNKNOWN` where the map is genuinely silent.
- **Dependency / unlock DAG** — left = prep tasks `P1..Pn`, right = assets; edges = `(prep_node → asset)` per prep item in that asset's `missing` list.
  - **Prep normalization BEFORE edge derivation:** normalize each prep phrase to a canonical token **by intent, not exact string**, so semantically-identical prep collapses to one node (e.g. strip machine-specific paths / remove personal paths / de-personalize configs / sanitize → ONE "strip personal specifics" node). A prep item that is a summary phrase **with a parenthetical enumeration** ("everything upstream (a filed prereg, one replication)") expands to its enumerated items BEFORE normalization. The **stated synonym set includes the map's own abbreviations** — an abbreviation↔expansion pair the map itself uses ("prereg" ↔ "pre-registration") counts as stated. Beyond that, use normalized (case/whitespace-folded) matching; do NOT infer shared prep from loose semantic similarity — unmatched prep items create separate nodes.
  - **Counting (deterministic):** `M` = count of DISTINCT assets with ≥1 incoming prep edge (assets with zero prep edges are listed separately as "no unlock dependency" and excluded from M). `N` = distinct assets the hub points to. `hub` = prep node with the most outgoing edges; **ties broken by (1) most distinct assets unlocked, then (2) lexicographically smallest prep-node id** — deterministic.
  - **Degenerate guards:** zero derivable edges → render DAG empty with "no unlock dependencies stated in map" and **OMIT the N-of-M footer** (do not print "0 of M" as if computed). Max fan-out = 1 or tied-after-tiebreak-impossible → "no dominant hub" rather than crowning an arbitrary node.
  - The highlighted hub, rendered edges, and footer string MUST all derive from the same edge set in one pass — **never typed as prose.** Footer template: `"<hub> unlocks N of M paths"` + benefit-qualifier only if the map states one (§5).

### 6.6 Visual system
- **Dark theme, IBM Plex Mono / Sans / Serif.** This is DEFAULT presentation chrome, independent of map domain — it carries no semantic meaning and must encode no domain assumptions. Fonts load via a CDN `<link>` **with a full local fallback monospace/sans/serif stack in every `font-family` declaration**, and the link must NOT block render (text renders immediately in fallback; the dashboard is fully legible with zero network).
- **Single `:root` token table** — one source of truth for all colors (bg / surface / rule / ink + posture colors sized to the map's posture count + risk tones) and spacing/rule-widths. All styling references `var(--token)`; the ONLY raw hexes allowed are the token definitions themselves.
- **All numeric coordinates come from the map** (matrix x/y, ladder width, standing bars) via the §4 mapping — never aesthetic-only invented positions.

---

## 7. SELF-CONTAINED / STANDALONE RENDER (hard requirement)

- Output is **one `.html` file** that opens and fully renders by double-click from disk (`file://`) with no server and no network.
- **ALL executable runtime code MUST be inlined.** CDN `<script>` tags for any framework / transpiler / polyfill are **FORBIDDEN** — they fail under `file://` offline and reproduce the original blank-page defect ("window.React is not available yet"). Only fonts/CSS may use a CDN `<link>`, and only with an offline fallback stack (a failed font load degrades gracefully; a failed script load does not).
- **Default and strongly preferred: vanilla JS** with classic `<script>` IIFEs and DOM construction — zero external-runtime risk. If React is used, **paste the full minified React + ReactDOM source directly into `<script>` blocks** (no CDN URL). If JSX is used, **Babel-standalone must be INLINED** (paste its source) and JSX lives in `<script type="text/babel">`; **a CDN reference to Babel is FORBIDDEN, and untranspiled JSX served as plain JS is FORBIDDEN** (throws SyntaxError). If inlining Babel is undesirable due to size, use vanilla JS instead.
- **FORBIDDEN under `file://` (break the page) — do not emit:** `<script type="module">`, ES `import`/`export` at any scope, dynamic `import()`, `fetch()`/`XHR` of any local path, top-level `await`. Use classic scripts + IIFE scoping.
- **The `MAP` object is an inline JS literal** — the artifact carries its own data; it never fetches.
- **Zero external LOCAL files:** no relative `<img src>`, no `<link href>` to a local `.css`, no external local `.js`, no CSS `@import` of a local file. All CSS in `<style>`, all JS in `<script>`, all data in `MAP`; any image is an inline `data:` URI or pure CSS/SVG. The user receives exactly one file.
- If, for a stated reason, standalone is impossible, name the exact required host at the top of the file and explain why — but the default and expected result is standalone.

---

## 8. ACCEPTANCE CHECKS (self-verify BEFORE returning; repair failures, then output)

Run this against your generated file. If any check fails, fix and re-check; do not return a failing file.

1. **Standalone — constructive render-trace (not a grep).** Trace the file as a browser would under `file://`: (a) every `<script>` has inline content or is one of the allowed inlined-runtime blocks — list each script and its source; (b) NO `<script type="module">`, ES `import`/`export`, dynamic `import()`, local `fetch`/`XHR`, or top-level `await`; (c) any JSX has an inlined Babel-standalone + `type="text/babel"`; (d) the root render call runs after its runtime is defined in document order; (e) zero external local file references. If you cannot affirmatively trace all five, rewrite in vanilla JS before returning.
2. **Data single-source-of-truth.** Exactly one `MAP` object; Brief/Board/Analysis/Queue/Matrix/Ladder/DAG all derive from it — asset data not restated as separate per-tab literals.
3. **Style single-source-of-truth.** All colors/spacing/rule-widths are CSS custom properties in one `:root` table, referenced via `var(--token)`; no hardcoded hex or repeated literal outside `:root`; posture→color and risk-tones reference tokens.
4. **Required, non-removable sections.** Honesty banner (verbatim constraint + REQUIRED-BOUNDARY suffix **where §3 R2 requires one — i.e. when the constraint omits never-claims; a complete constraint may render suffix-free or with a restating suffix, both satisfy R2** + chips, heightened state if no disqualifiers), Hard-rule block, Do-not-do-yet panel, visibility self-label + posture pill.
5. **No fabrication.** Every readiness/demand/ceiling/rank/buyer-reality/date traces to the map or reads `UNKNOWN` / `CONFLICT(...)`; no invented numbers, dates, buyers, or plotted coordinates; quantized dots not moved off their mapped value (jitter visual-only).
6. **Honesty / parked-lane discipline (structural).** (a) Every asset in the computed PARKED/outside-facing set (§2.5) renders gray with zero buy/launch/ship/publish/subscribe affordance, overriding its posture. (b) The forbidden-claim filter (§3 R4) fired on every asset whose record touches a NEVER-clause token, with the forbidden-positioning chip and no sellable affordance — OR is inert because the map names no forbidden positioning (not mis-fired). (c) Grep the output for launch/ship/publish/buy/subscribe outside `[quoted]` blocks → must be zero. (d) DEGRADED mode (§3 R9) engaged if no binding constraint parsed.
7. **Generalization.** No hardcoded "homelab"/"provisioning"/"bus-factor = 1"/specific posture/quadrant/footer words except where present in THIS map's data; titles, sections, postures, axes, ladder metric, quadrant labels, banner, pill, visibility label all derived. The deny-list and quadrant labels come from the map, not this prompt.
8. **Messy-input handling wired.** Closed-whitelist label→coord (or ordinal-scale fallback) applied; one-axis-missing not plotted; truncation/UNKNOWN/missing/dup-rank/rank-gap/out-of-range/unknown-posture/duplicate-code/orphan-row/uncoded/conflict cases handled per §2–§4; matrix dot+label collisions de-conflicted visual-only; qualitative ceilings hatched + excluded from ladder sort.
9. **DAG computed, not asserted.** Prep normalized before edges; hub = deterministic max-fan-out (with tiebreak); N/M counted per §6.5; degenerate cases omit/soften the footer; highlighted hub + edges + footer all from one edge set.
10. **Output hygiene.** You returned ONLY the HTML file (or, if the map was missing, ONLY the refuse-and-ask block) — no surrounding prose.

— end of generator prompt —
```

═══════════════════════════ END GENERATOR PROMPT ═══════════════════════════

---

## §C. How to invoke it

1. Start a fresh chat with a capable model (the original was produced in a hosted-artifact
   environment; any strong model that can emit a full HTML file works).
2. Paste the **entire** §B block (everything between BEGIN/END) as the instruction.
3. Then paste the strategy map under a literal `### SOURCE MAP` heading. Example:
   ```
   ### SOURCE MAP
   <your map markdown here — see §D for the exact shape>
   ```
4. The model returns **one HTML file**. Save it as `something.html` and **double-click it** — it
   must render fully offline. If it shows a blank page or asks for a server, the model violated §7;
   tell it: "Re-do per §7/§8 — standalone vanilla-JS single file, no CDN runtime."
5. If you paste no map (or an unusable one), it returns the §2.6 refuse-and-ask block instead of a
   dashboard. That is correct behavior, not a failure.

**Tip:** the prompt is long. If the model truncates the HTML, say "continue from `<exact last line>`"
— do not re-run from scratch (you'll get a different file).

---

## §D. Worked example — the reference INPUT

> **THIS IS ONE EXAMPLE INPUT, NOT THE SCHEMA.** Its vocabulary (homelab, provisioning,
> backup/restore, dotfiles, the SHELVED/AUTHORIZED/QUEUED disposition words, the Section A/B
> foundation-vs-showcase layering) is specific to this map. Per Prime Directive 5, NONE of these
> words may appear in output generated from a *different* map. Use this only to see the expected
> input *shape*: a front-matter block, grouped asset sections, a ranked table, synthesis, boundary,
> and operator-decisions. (The map that produced the original reference dashboard stays private;
> this example is real-shaped and exercises the same structures.)

```markdown
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
- **Maturity:** High as artifacts; personal by nature (public repo contains `install.ps1` and 12 per-tool configs).
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
- **H2:** the ONLY carve-out from pure options-review: **removing PUB-1's hardcoded format assumptions — AUTHORIZED as an undated background task.**
- **H3:** PUB-3 restore write-up: **QUEUED, undated** — blocked on fact-check against `BACKUP_LEDGER.md`.
- **H4 (STANDING RULE):** no repo goes public-visible before a secrets/PII sweep of its full history exists in writing.
```

---

## §E. Worked example — the EXPECTED OUTPUT for that input

Use this to judge whether a generated dashboard is faithful. It describes the four tabs the map
above should produce. **Read the coordinate note at the end — it explains an intentional behavior
change between the original artifact and this hardened prompt, so a reviewer doesn't mistake it for
a regression.**

**Persistent chrome (every tab):**
- Top bar: a bracketed-accent title (e.g. `[Homelab] & Public Tooling`), the task label
  "Project bets catalog · options review", a posture pill "Options review · no commitment to ship",
  and "INTERNAL · 2026-05-02" (operator-decisions date precedence per §3 R7; built_via carries the
  same date and renders as a chip).
- Honesty banner (red left-rule, not removable): the binding constraint verbatim — "positioned as
  personal experiments / learning artifacts — never production-ready software, never a security
  guarantee, never a maintained product promise." — with evidence chips parsed from the
  parenthetical: `0 external deployments` · `CI missing on 3 of 5 repos` · `bus-factor = 1`.
  (Note: chips come from the CITED-DISQUALIFIER clause, never from the "never …" clause.)

**Tab 1 — Brief:**
- Bottom line: "Nothing here is a product; two things are habits worth protecting."
- Conclusion cards (4, titled "the four conclusions"), one per honest-synthesis bullet:
  Habits worth protecting (INF-2's verified restores, INF-1's rebuild discipline) / The only public
  bet with pull (PUB-1, contingent on the format assumptions dying) / Patterns travel, code doesn't
  (INF-3's stale-state pattern, INF-2's ledger habit) / Recommended posture (keep the foundation
  running; one low-regret prep). The ranked-table bottom line and the boundary headline de-duplicate
  into these without changing the count.
- Hard rule block: never production-ready software · never a security guarantee · never a
  maintained product promise.
- Authorized-action panel: remove PUB-1's hardcoded format assumptions (the ONLY authorized move,
  per operator decision H2), rendered as an internal prep task with a Definition-of-Done checklist
  built from PUB-1's Missing list (format auto-detection · packaging · a hosted demo GIF) and a
  task-size table whose sizes read UNKNOWN (the map states no estimates — never invented). It is
  internal prep, NOT a CTA, and it upgrades nothing elsewhere on the board.
- Do-not-do-yet panel (6 entries): the three boundary-named outward-facing collateral items
  (blog series · marketplace listing · demo site — panel references only, never asset cards), the
  H4 standing rule (no repo goes public-visible before a written secrets/PII sweep of its full
  history), PUB-2's public-repo visibility (outside-facing, parked by default, H4-gated), and
  PUB-3's publish step (queued but blocked on the fact-check gate). The map supplies no
  self-discipline line, so per §5 none is rendered — the panel is built from the deferred items
  alone.

**Tab 2 — Option Board** (buckets derived ONLY from explicit anchors):
authorized [PUB-1] (H2 names it by code) · queued [PUB-3] (H3) · unassigned posture — gray
[INF-2, INF-1, INF-3, PUB-2]. Nothing else in the map ties a disposition word to a specific asset —
honest-call verbs like "keep running" / "maintain for myself" are not taxonomy words, and synthesis
tone never colors a card (§2.3). Overlays: PUB-2 and PUB-3 are outside-facing (a public repo; a
public post), so §2.5 force-renders their cards in the gray no-CTA PARKED treatment regardless of
bucket — PUB-3 keeps its QUEUED chip, but queueing is not outside-use authorization. PUB-2
additionally carries a red GATED chip (H4 gates any repo-visibility action). PUB-1's card carries
no CTA either — its authorization surfaces only as internal prep in the Brief.

**Tab 3 — Analysis:** sortable spine of all 6 (default rank order, ranks 1–6 contiguous) · a
setup-readiness × community-pull scatter · the ceiling ladder · per-asset detail panel; selecting
any asset cross-highlights everywhere. The matrix is deliberately sparse for this map, and that
sparseness is the §4 rules firing correctly:
- Readiness maps cleanly via the closed whitelist (High → 0.85, Medium → 0.5, Low → 0.2).
- Community pull mostly does not. INF-1 and INF-2 read "None" → per the whitelist, `none` is a
  strip value, not a point, so both go to the **n/a-strip** with their known readiness shown. The
  bottom-left-corner treatment does NOT apply: §4 reserves the (0.1, 0.1) corner for an n/a
  **readiness** paired with an explicit glue/no-standalone disposition, and anchoring these two
  High-readiness assets in the low-low corner would fabricate a readiness the map contradicts.
- PUB-1 ("Small but real"), PUB-3 ("Evergreen, crowded"), and PUB-2 ("Commodity") have leading
  tokens on neither the whitelist nor a coherent alternate lexicon → they list under **"unmapped
  label — insufficient data for matrix"** with the literal text shown. "Small" is NOT coerced to
  `low` — never-coerce is the rule working, not a rendering failure.
- Only INF-3 ("Medium" readiness, "Medium as a pattern" pull) plots: **(0.5, 0.5)**, full cell text
  in the tooltip.
- Ladder: the map has no ceiling column and no asset carries a quantitative ceiling, so the ENTIRE
  ladder renders as hatched "ceiling not quantified" bars carrying the prose cue where one exists
  (e.g. INF-2's "highest personal value"), excluded from numeric sort per §4 — no bar widths are
  invented.

**Tab 4 — Execution:** a 6-row decision queue (Option / Status / Next action / Owner / Gate /
Do-not-do-yet). Owner = the operator on every row (single-operator default — the map speaks as
"me"/"future-me"). Status: PUB-1 AUTHORIZED-prep (H2) · PUB-3 QUEUED (H3) · the other four
UNKNOWN / unassigned. Gates: PUB-3 carries the H3 fact-check-against-`BACKUP_LEDGER.md` gate; the H4
secrets/PII-sweep standing rule attaches as a Gate to every repo-visibility action (it bites PUB-2
now and any future public showing of PUB-1 or PUB-3); rows with no stated gate read UNKNOWN. Next
actions come from each asset's Missing list.

**Dependency DAG — the degenerate-guard case (intentional pedagogy):** enumerating prep nodes from
the six Missing lists gives 14 prep items (INF-1: secrets bootstrap · document the two BIOS steps;
INF-2: offsite second copy · stale-ledger alert; INF-3: stale-state gist · threshold config;
PUB-1: format auto-detection · packaging · demo GIF; PUB-3: fact-check · screenshots · publishable
sample; PUB-2: strip machine-specific paths · "what's interesting here" note). Prep-intent
normalization collapses NONE of them across assets — no two phrases share a stated-synonym intent —
so every prep node has fan-out 1. Max fan-out = 1 is exactly §6.5's degenerate case: the dashboard
must say **"no dominant hub"** and **OMIT the N-of-M footer** rather than crown an arbitrary node.
A generated file that prints "X unlocks N of 6 paths" for this map has fabricated a hub — that is
the failure the deterministic guard exists to catch.

**Per-asset values from the map (for fidelity checking):**

| Code | Name | Rank | Readiness (map word) | Pull (map word) | Risk/ceiling cue | Posture (derivation) |
|---|---|---|---|---|---|---|
| INF-2 | Backup + restore verification loop | 1 | High | None | "highest personal value" / "crown jewel" | UNKNOWN → unassigned gray (no explicit anchor) |
| INF-1 | Declarative host provisioning | 2 | High | None | "invisible to others" / "never showcase" | UNKNOWN → unassigned gray (no explicit anchor) |
| PUB-1 | Log-to-timeline visualizer | 3 | Medium | Small but real | "wins only if setup stays under five minutes" | authorized (op-decision H2 names it) |
| INF-3 | Monitoring + stale-state alerts | 4 | Medium | Medium as a pattern | "pattern reusable; scripts machine-specific" | UNKNOWN → unassigned gray (no explicit anchor) |
| PUB-3 | Restore-drill write-up | 5 | Low | Evergreen, crowded | "crowded field" / blocked on fact-check | queued (op-decision H3) + outside-facing gray per §2.5 |
| PUB-2 | Dotfiles + setup scripts | 6 | High | Commodity | "reputational garnish at best" | UNKNOWN → unassigned gray + outside-facing PARKED + H4 gate |

**IMPORTANT — coordinate-mapping behavior (do not mistake for a regression):**
The *original* artifact (produced for a different, private map) plotted assets with hand-tuned
numeric coordinates on a 0–100 scale. A map like §D only gives **qualitative** labels (High, Medium,
Low, None) and blunt prose. The hardened prompt (§4) **deliberately replaces hand-tuned numbers with
a deterministic label→coordinate whitelist** (High → 0.85, Medium → 0.5, Low → 0.2, none/n/a →
strip). So a generated dashboard will **quantize**: INF-1 and PUB-2 share readiness 0.85, INF-3 sits
exactly at (0.5, 0.5), and off-whitelist prose lists as unmapped rather than guessed. Shared
coordinates are expected and de-collided visually per §6.4. **This is intentional anti-fabrication,
not a loss of fidelity:** bespoke numbers would be invented precision the map never contained. A
reviewer should verify the quantization + visual de-collision + unmapped-label strips, NOT demand
bespoke numbers.

Likewise, the original assigned every asset a colored posture; the hardened prompt (§2.3) only
colors a posture when it's explicitly tied to the asset (in its honest_call or a naming
operator-decision), else UNKNOWN/gray. For THIS map only PUB-1 (H2) and PUB-3 (H3) resolve to
colored postures; the other four stay in the unassigned-posture gray bucket — a reviewer should
confirm each colored card has an explicit anchor rather than being inferred from synthesis tone.

---

## §F. Vocabulary glossary — the reference map's words → the GENERIC roles

This is the single most important anti-misread aid. The left column is specific to the homelab
map; the right column is what the dashboard structure actually depends on. A different map fills the
right column with its OWN words.

| Reference-map word (example only) | Generic role it plays | Where it drives the dashboard |
|---|---|---|
| "options review / project bets catalog" | the **domain title + posture** | top-bar title + posture pill |
| "Section A / Section B", "foundation vs showcase" | **section grouping** (N groups) | Option Board section order, spine grouping |
| "consumer" | the **consumer/who-uses** field | detail panel "who'd use it" + card |
| "adoption-reality / skeptic's veto" | the **blunt downside-reality** field | detail panel reality block + card chip |
| "setup readiness" | **ranking dimension #1 (x-axis)** | matrix x, spine sort, standing bar |
| "community pull" | **ranking dimension #2 (y-axis)** | matrix y, spine sort, standing bar |
| (no explicit ceiling column) — prose cues like "crown jewel" or a "lowest ceiling"-type phrase | **headline magnitude** — extracted from prose per §2.3 where a cue exists, else UNKNOWN/hatched per §4 | ladder bar, standing bar |
| "honest call" | **one-line verdict** | card italic line, detail "honest call" |
| disposition words: AUTHORIZED / QUEUED / catalog-only | **disposition taxonomy** | Option Board buckets + colors + legend |
| "0 external deployments; CI missing on 3 of 5 repos; bus-factor = 1" | **cited disqualifying evidence** | honesty-banner chips |
| "never production-ready / security guarantee / maintained product" | **forbidden-positioning clause** | forbidden-claim filter, Hard rule, CTA scrub |
| "SHELVED / public lane / outward-facing collateral" | **deferred/inactive set** | computed PARKED set (gray, no CTA) |
| "missing" | **prerequisite tasks** | dependency DAG edges, DoD checklist |
| "operator decisions (H1–H4)" | **authoritative dispositions** | queue Status/Gate, Authorized-action panel |

If a NEW map uses "hypotheses / replications / pre-registration / conviction / impact / sponsor" —
those fill the same right-column roles, and NONE of the homelab words above may appear in output.

---

## §G. Why each hardening rule exists — DO NOT STRIP

These came from an adversarial review (53 findings: 15 critical, 24 major) that tried to break a naive
reconstruction. Each rule blocks a concrete failure. If someone "simplifies" the prompt, these are the
load-bearing pieces to protect. Tags: [A] honesty/parked-lane · [B] missing/messy input · [C]
generalization · [D] renderability/structure · [E] fidelity.

- **[A] PARKED is a computed SET, decoupled from the posture field** — boundary_check + operator_decisions
  are scanned for parked/outside-facing references and those assets are force-grayed with zero CTA. Closes
  the leak where an UNKNOWN-posture customer-facing asset rendered as a normal colored card.
- **[A] Operational definition of OUTSIDE-FACING + default-to-PARKED** — so "no CTA on customer-facing
  collateral" is enforceable, not left to per-card judgment.
- **[A] Forbidden-claim filter is unconditional + content-scanned** off the honesty NEVER-clause across each
  asset's whole record — and explicitly INERT when the map names no forbidden positioning (no mis-fire).
- **[A] Banner content-floor + CTA-verb scrub + Authorized-action ceiling** — missing negative claims appended
  as REQUIRED-BOUNDARY; an evidence-free constraint makes the banner LOUDER (DEGRADED gray mode); map-supplied
  launch/ship verbs neutralized; the Authorized panel renders at-most operator-authorized internal prep and
  never upgrades an item out of PARKED.
- **[B] Label→coord is a CLOSED whitelist + ordinal-scale fallback** — unlisted/novel/numeric/banded labels go
  to an "insufficient data" strip, never nearest-match coercion.
- **[B] Data-level coordinate degeneracy specified** — quantization intentional, identical points preserved,
  de-collision visual-only; plus one-axis-missing (don't plot), truncation detection, rank gaps/bands/
  out-of-range, duplicate-code/orphan-row/uncoded identity rules, N-way CONFLICT, and the dangerous
  honesty_constraint / real_files conflict cases.
- **[B] Qualitative-ceiling ladder fix** — UNKNOWN ceilings render as a hatched bar in a separate "not
  quantified" section excluded from sort (a zero-width bar falsely reads "lowest"); date-vs-INTERNAL
  contradiction resolved with an explicit precedence order.
- **[C] Global anti-leak directive (Prime Directive 5)** — every reference-domain token is an example,
  forbidden in output unless present in the active map; deny-list, matrix axes AND quadrant labels, ladder
  metric, posture→color, visibility pill, DAG qualifier, and self-discipline line all parameterized.
- **[C] Structural assumptions generalized** — N sections (not a fixed 2-section foundation/showcase), generic
  consumer-role mapping with map-derived labels, render-if-present Execution columns.
- **[D] CDN-runtime loophole closed** (the original blank-page cause) — all executable code inlined; CDN
  runtime/transpiler tags forbidden; explicit file:// breaker prohibition list; constructive render-trace
  replaces the naive string-grep acceptance check; style single-source-of-truth check added.
- **[D] DAG made deterministic** — prep-intent normalization before edges, distinct-asset M/N counting,
  explicit tie-break, degenerate-edge guards; hub + edges + footer derived from one edge set, never prose.
- **[E] Reference-fidelity contradictions resolved** — count-matched conclusion titling (kills the
  counted-title-vs-rendered-cards mismatch), ceiling/risk extracted from prose when not columns (kills the
  empty ladder), prep-intent hub normalization, evidence-chips scoped to the disqualifier clause only,
  single-operator Owner default, rank-order spine authority, multi-asset authorized-move union.

---

## §H. The known failure that motivated the standalone requirement (§7)

The original artifact was generated in a hosted-artifact format: its HTML used a custom template
engine (`sc-for` / `sc-if` directives) and called `window.React` / `window.ReactDOM`, which the
artifact HOST injects at runtime. The 50 KB `support.js` shipped with it was only that template
runtime — React itself was NOT bundled. Consequence: when the file was opened directly from disk
(double-click, `file://`), nothing provided React, `support.js` threw "window.React is not available
yet", and the page rendered **blank**. It only worked inside the hosting viewer.

That is exactly why §7 makes "renders standalone from `file://`, no network, all runtime inlined" a HARD
acceptance gate, forbids CDN `<script>` runtimes, and prefers vanilla JS (or, if React is used, the full
React+ReactDOM source pasted inline). The acceptance check (§8.1) is a *constructive render-trace*, not a
keyword grep, because a grep can pass while the page still fails to paint. **Do not relax §7/§8 — a
pretty dashboard that shows a blank page on double-click is the original bug returning.**

---

## §I. Review axes, testing, and what is still unproven

The prompt is hardened on four axes; a reviewer's job is to stress them, especially the one that can't be
proven from a single example:

- **A — Honesty / parked-lane enforcement:** try to craft a map that makes the banner drop, a parked
  outside-facing asset gain a CTA, or a forbidden-claim card become sellable. The rules (§2.5, §3) should
  hold structurally.
- **B — Missing/messy input:** feed partial maps (no numbers; missing blunt-reality column; ≠6 assets;
  duplicate/gapped ranks; uncited assets; truncated mid-table). Confirm UNKNOWN/flag behavior and that the
  matrix never invents coordinates.
- **C — Generalization (the big one — a single reference example can't prove it):** paste a map from a
  genuinely **different** domain (e.g. a research-hypotheses portfolio, a product-bets board, a hiring
  pipeline). The output must use THAT map's titles/sections/postures/axes/honesty text with **zero**
  homelab/tooling vocabulary leaking in. This is the test most worth running, because the reference map
  can't prove it.
- **D — Renderability/structure:** generate a file, open it from disk offline, confirm it paints and the
  tabs/charts work. Confirm single-source-of-truth for data and style and a computed (not prose) DAG.

**Suggested quick test harness:** keep three tiny fixture maps on hand — (1) the reference homelab map
(§D), (2) a different-domain map (one ships alongside this package at
`examples/research_portfolio_map.md`), (3) a deliberately broken map (missing honesty constraint,
gapped ranks, one uncited asset, one truncated entry) — and run all three. (1) proves fidelity, (2)
proves generalization, (3) proves the degrade/never-fabricate behavior.

---

## §J. TL;DR for whoever receives this

Paste §B into a strong model, then paste a strategy map under `### SOURCE MAP`. You get one self-contained
HTML "Command Center" (Brief / Option Board / Analysis / Execution) that faithfully encodes the map and
**cannot** be made to fabricate values, drop its honesty banner, put a CTA on parked/outside-facing items,
leak the worked example's homelab vocabulary (provisioning / dotfiles / setup readiness / community pull)
into a different map's dashboard, or ship a file that won't open offline. The four-tab skeleton and the
matrix/ladder/DAG are generic; every label is derived from the map. If you're improving it, the
highest-value test is generalization (§I-C): run it on a map from a different domain and confirm zero
leakage. Do not relax the standalone-render rules (§7/§8/§H) — that was the original bug.

*— end of package —*
