# ANZ Data Platform Phase 1 — Initial Design & Architecture Assessment

## Core Design Premise

The fundamental architectural shift in this initiative is not about delivering individual reports — it is about establishing a **certified silver layer** (the Fabric Sales Revenue Dataset) as the single source of truth for all downstream reporting. This distinction matters because it changes where complexity lives: business logic is resolved once, centrally, rather than being re-implemented per report.

---

## Key Design Principles

### 1. Centralize Business Logic, Not Reports

The current state is fragmented Tableau reports with duplicated revenue logic. The architectural response is to move all critical logic — billing day standardization, FX handling, AOP/Outlook/Prior Year comparisons, revenue calculations — into a single governed layer. Power BI reports become thin consumers of certified data, not owners of business rules.

This is the correct inversion. The complexity cost is paid once, in the pipeline, not multiplied across every report.

### 2. Silver Layer as Decoupling Mechanism

The Fabric dataset acts as a decoupling boundary between:
- **Upstream complexity** — raw source data from ERP/transactional systems with inconsistent grain, timing, and logic
- **Downstream agility** — Power BI reports that can be built, iterated, or retired without touching transformation logic

This is what enables agile report delivery. Once the silver layer is stable, adding a new view (e.g., Account Manager Dashboard, CathLab) is a reporting concern, not a data engineering concern.

### 3. Governance at the Layer Boundary

The governance model is architecturally sound: Finance defines and signs off on logic; the Data & AI team implements it centrally; local redefinition is explicitly prohibited. This enforces that the silver layer is the authority — not individual report authors or regional teams. Without this, the fragmentation problem re-emerges at the Fabric layer.

### 4. Separation of Reporting Surface from Data Model

Phase 1 scope consistently distinguishes between the dataset and reporting views:
- Account Manager Dashboard is scoped as "revenue views" — a projection of the dataset, not a new dataset
- Business Overview is "revenue layer" — same source
- CathLab Dashboard is "revenue component" — same source

This naming convention signals the right mental model: reports are views over a model, not independent pipelines.

### 5. Incremental Domain Expansion Built In

The roadmap shows Phase 2 (Margin) and Phase 3 (Operations) building on the same foundation, not creating parallel stacks. This only works if the silver layer is designed with extensibility in mind — clean grain, consistent keys, documented logic — rather than being scoped narrowly to Phase 1 revenue fields alone.

---

## Architecture Risks Worth Flagging

- **Silver layer scope creep**: If the dataset is designed only for current revenue reports, extending to margin (Phase 2) may require structural changes. The model should anticipate future domain joins (cost, inventory) even if not populated yet.
- **Logic governance enforcement**: The "no local redefinition" principle is stated but not mechanically enforced. Access controls and dataset certification in Fabric need to back this up operationally.
- **Dual-run validation gap**: Parallel running Tableau and Power BI validates outputs but not logic parity at the transformation level. A reconciliation framework (not just visual report comparison) should be defined before cutover.

---

## Summary

The architecture is correct in its orientation. The Certified Sales Revenue Dataset in Fabric is not a reporting tool — it is an infrastructure layer. Its value is proportional to how cleanly it separates "what the data means" from "how it is displayed." Phase 1 success should be measured less by report count and more by whether the silver layer can independently answer: is this number right, and who signed off on that definition?
