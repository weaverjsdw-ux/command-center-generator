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
- **H2:** the ONLY carve-out from pure options-review: **removing PUB-1's hardcoded format assumptions — AUTHORIZED as an undated background task.** Everything else stays catalog-only.
- **H3:** PUB-3 restore write-up: **QUEUED, undated** — blocked on fact-check against `BACKUP_LEDGER.md`.
- **H4 (STANDING RULE):** no repo goes public-visible before a secrets/PII sweep of its full history exists in writing.
