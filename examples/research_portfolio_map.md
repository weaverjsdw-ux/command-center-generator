# Cognition Side-Lab — Hypotheses Portfolio (INTERNAL — quarterly triage)

**Posture:** Triage catalog — what each hypothesis is, who'd build on it, what's missing, ranked by evidence maturity. **No commitment to publish or pursue.** Private; curiosity-first; no submission deadline.
**Primary emphasis:** the memory-effects cluster is the lab's center; the tooling experiments exist to serve it (ranked second).
**Honesty constraint (binding, every entry):** positioned as exploratory hypotheses — **never validated findings, never recommendations, never a causal claim.** There is no external validation (0 replications; pre-registration pending on all active lines; nothing peer-reviewed). Outward-facing material (preprints, talk proposals, blog explainers) stays **PARKED** in the outreach lane.
**Built via:** quarterly lab notebook review (2026-06-30), self-directed.

> **The "evidence-reality" column is deliberately blunt** — enthusiasm ≠ evidence. A hypothesis can be beloved and still rest on n=12. Read that column as the reviewer's veto.

---

## Cluster A — Memory effects (center)

### MEM-1 — Spacing-interval saturation curve
- **Asset (real):** `notebooks/spacing_curve.ipynb`, `data/sessions_2026H1.csv` (n=214 self-trials), `prereg/DRAFT_spacing.md`.
- **Maturity:** Medium (pilot data collected; pre-registration drafted, unfiled).
- **Consumer:** future-me designing the confirmatory study; possibly a collaborator.
- **Evidence-reality (blunt):** **Suggestive, self-sampled, underpowered.** The curve shape is pretty; n=214 from one subject proves nothing. Worth a real pre-registered run, worthless to share before that.
- **Missing:** file the pre-registration; a second subject; power analysis.

### MEM-2 — Interference from same-day topic switching
- **Asset (real):** `notebooks/interference.ipynb`, tagging schema in `codebook.md`.
- **Maturity:** Low (exploratory scatter only).
- **Consumer:** the lab's own study queue.
- **Evidence-reality (blunt):** **A hunch with a plot.** Confounded with time-of-day; the codebook tags were applied retroactively. Kill or redesign.
- **Missing:** prospective tagging; a confound plan.

### MEM-3 — Retrieval-practice logging harness
- **Asset (real):** `harness/quiz_runner.py`, `harness/README.md`, 6 months of run logs.
- **Maturity:** High (runs daily; logs are consistent).
- **Consumer:** every study in Cluster A depends on it.
- **Evidence-reality (blunt):** **Solid infrastructure, not a finding.** It measures reliably; it concludes nothing. Its value is that other work can trust the data layer.
- **Missing:** export format documentation; a data dictionary.

## Cluster B — Tooling experiments (support)

### TOOL-1 — Notebook-to-prereg template pipeline
- **Asset (real):** `tools/prereg_from_notebook.py`, `templates/prereg.md`.
- **Maturity:** Medium (works on 2 of 3 notebook styles).
- **Consumer:** me at pre-registration time; conceivably other self-experimenters.
- **Evidence-reality (blunt):** **Useful to one person so far.** The third notebook style breaks it; nobody else has run it.
- **Missing:** fix style-3 parsing; one outside user.

### TOOL-2 — Blinded self-scoring protocol
- **Asset (real):** `protocols/blind_scoring.md`, scorer script `tools/blind_score.py`.
- **Maturity:** Medium (used in the H1 pilot).
- **Consumer:** any self-experiment where the experimenter is also the rater.
- **Evidence-reality (blunt):** **The most defensible thing in the lab.** Self-rating bias is the obvious attack on everything here; this protocol is the only structural answer on hand.
- **Missing:** an audit of unblinding leaks; a worked example write-up.

### TOOL-3 — Talk-proposal draft ("Self-experiments that survive review")
- **Asset (real):** `drafts/talk_proposal.md` (900 words).
- **Maturity:** Low (draft; claims outrun the data).
- **Consumer:** a methods-community audience, eventually.
- **Evidence-reality (blunt):** **Premature by its own abstract.** It promises conclusions the portfolio explicitly does not have.
- **Missing:** everything upstream (a filed prereg, one replication); honest reframing.

---

## Evidence maturity × build-on-it pull — ranked (the catalog's bottom line)

| Rank | Item | Evidence maturity | Build-on-it pull | Honest call |
|---|---|---|---|---|
| 1 | MEM-3 Logging harness | High | High (everything depends on it) | Keep running; document the data layer |
| 2 | TOOL-2 Blinded scoring | Medium | High (defends the whole lab) | Audit for leaks, then write the worked example |
| 3 | MEM-1 Spacing curve | Medium | Medium | File the prereg before touching more data |
| 4 | TOOL-1 Prereg pipeline | Medium | Low | Fix style-3 only if MEM-1 files |
| 5 | MEM-2 Interference | Low | Low | Redesign or kill at next triage |
| 6 | TOOL-3 Talk proposal | Low | n/a | Parked by its own honesty problem |

## Honest synthesis
- **Nothing here is a finding; two things are load-bearing infrastructure** (MEM-3's harness, TOOL-2's blinding protocol).
- **The only externally interesting artifact is TOOL-2**, and only as a worked method write-up — not as a claim about memory.
- **The portfolio's real risk is narrative drift:** the talk draft (TOOL-3) shows the pull to present exploration as results; the honesty constraint exists because of it.
- **Recommended posture:** infrastructure first; the one low-regret prep is **the TOOL-2 unblinding-leak audit**, since every future study inherits its credibility.

## Boundary check
Internal triage only. No outreach material produced (preprints, talk proposals, explainers remain PARKED). Every hypothesis cites a real file. No validated-finding or causal claim anywhere. Nothing submitted.

## Operator decisions on this portfolio (2026-06-30)
- **R1:** evidence-reality calls stand as written.
- **R2:** the ONLY carve-out from pure triage: **the TOOL-2 unblinding-leak audit — AUTHORIZED as an undated background task.** Everything else stays catalog-only.
- **R3:** MEM-1 pre-registration filing: **QUEUED, undated** — blocked on the power analysis.
- **R4 (STANDING RULE):** no outward-facing draft (TOOL-3 included) advances before at least one pre-registered result exists.
