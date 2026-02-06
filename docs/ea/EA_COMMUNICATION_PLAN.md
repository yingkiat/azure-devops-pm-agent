# EA Communication & Rollout Plan

## Part 1: Rollout Strategy

### Value Proposition

Three capabilities that change how EA works:

1. **AI Ingestion** - Any content (documents, slides, spreadsheets, whiteboard photos) becomes structured CMDB data. No manual data entry.
2. **Automated EA Artifacts** - Roadmap diagrams and detailed draw.io views generated directly from the CMDB. Regenerable on demand.
3. **Portal** - Catalogue, elements, and diagrams linked together in one browsable interface. The single reference point.

### Rollout Philosophy: Output First, Input Second

**The mistake:** Sitting down with domain leads to refine the application catalogue. It's necessary work, but as a first impression it feels like data hygiene overhead. You burn political capital before demonstrating value.

**The approach:** Lead with a finished artifact built from messy existing data. Let the gaps in the output create pull for the refinement work.

```
Wrong sequence:  Ask for data → Clean data → Build artifacts → Show value
Right sequence:  Build artifacts from messy data → Show value with gaps visible → Gaps create pull → Refinement happens naturally
```

### Layer 1: IT Director (Week 1)

**Goal:** Get endorsement and air cover. Don't ask for anything.

**Preparation (before the meeting):**
- Ingest everything available: CMDB exports, Confluence pages, spreadsheets, slide decks
- Run full discovery through the tool - accept imperfect data
- Generate a portfolio-level landscape view: applications by domain, lifecycle status, rough roadmap
- Identify and count the gaps explicitly (no owner, unknown lifecycle, missing integrations)

**The meeting:**
- Present "here's what our landscape looks like based on existing data"
- The gaps are the hook: "We have 140 applications but 30 have no owner and 20 have unknown lifecycle status"
- The director sees the value of the complete picture AND the cost of incomplete data
- Ask for one thing: his endorsement for domain leads to fill the gaps

**Outcome:** The director pushes refinement to his leads because *he* wants the picture complete. The work request comes from above, not from you sideways.

### Layer 2: Domain Leads (Weeks 2-4)

**Goal:** Refine each domain's landscape through expert correction, not data entry.

**Preparation (before each lead session):**
- Pre-populate their domain view from ingested data
- Generate their domain diagram: their systems, integrations, lifecycle positions
- Identify specific gaps and questions for their domain
- Prepare a printed/shared version they can mark up

**Session structure (45-60 min per domain lead):**

| Phase | Duration | Activity |
|-------|----------|----------|
| **Show** | 10 min | Present their domain diagram. "Here's what we have for your area." |
| **Correct** | 20 min | "What's wrong with this picture?" They'll immediately spot retired systems, missing platforms, wrong integrations. Capture every correction. |
| **Position** | 10 min | For systems they confirm exist, ask: "Where is this going? Staying as-is (H1), changing soon (H2), or part of the target state (H3)?" |
| **Dependencies** | 5 min | "What outside your domain does your stuff depend on? What depends on you?" |
| **Gaps** | 5 min | "What's missing entirely? What systems did we not capture?" |

**Critical technique: Correction, not creation.** People naturally engage when correcting something that's wrong about their area. "That system retired last year" and "you're missing our new platform" come out effortlessly. The same information extracted via a blank spreadsheet would take three follow-up emails.

**After each session (same day):**
- Apply corrections to the model
- Regenerate their domain diagram with fixes
- Send it back: "Here's the updated view with your corrections"
- This speed builds credibility - traditional EA would take weeks to update models

**After all domain sessions:**
- Cross-reference dependencies between domains
- Identify conflicts (Domain A says system X is strategic, Domain B says it's sunsetting)
- Generate updated portfolio view for director with coverage metrics

### Layer 3: Broader IT (Month 2+)

**Goal:** Architecture literacy and shared reference point. Only after landscape is credible (~80% coverage).

**Rollout sequence:**
1. Portal goes live as the reference point for application information
2. Roadmap diagrams become the shared language in architecture review boards
3. New project proposals reference the landscape ("where does this fit?")
4. Lightweight governance established: new systems must appear in catalogue before procurement

**Sustainability mechanism:** The portal earns its place by being the thing people check before meetings, not something they're told to maintain. If the data is useful, people will flag when it's wrong.

### Timeline Overview

```
Week 1          Weeks 2-4              Month 2+
---------       ------------------     ----------------
Director        Domain Lead Sessions   Portal Launch
  |               |                      |
  |  Endorsement  |  Corrected Data      |  Shared Reference
  +------>--------+-------->-------------+
                  |
                  v
            Same-day diagram
            regeneration after
            each session
```

---

## Part 2: Slide Structure

### Overview

**Objective:** Communicate APAC IT Architecture roadmap and build organizational capability

**Audiences:**
| Audience | Time | Slides | Purpose |
|----------|------|--------|---------|
| IT Director | 30 min | A + B (14) | Decision support, approve rollout |
| Domain Owners | 30 min | A + C (14) | Enable roadmap ownership |
| All IT | 30 min | A + D (18) | Architecture literacy (objective deliverable) |

**Sequencing:**
1. Director first (approves content, pushes to domain owners)
2. Domain owners second (build their roadmaps)
3. All IT third (general education with real examples)

---

## Deck Structure

```
CONTENTS PAGE                                    Slide 1

SECTION A: Common Foundation (All Audiences)    Slides 2-11
SECTION B: Director Focus                       Slides 12-15
SECTION C: Domain Owner Focus                   Slides 12-15
SECTION D: All IT Focus                         Slides 12-19
```

---

## CONTENTS PAGE

**Slide 1: Contents**

```
APAC IT Architecture: Visibility, Roadmaps & Decisions

SECTION A: Our Landscape Today (All Audiences)        Slides 2-11
SECTION B: Completing the Picture (Director)           Slides 12-15
SECTION C: Your Domain, Your Roadmap (Domain Owners)   Slides 12-15
SECTION D: Architecture Literacy (All IT)              Slides 12-19
```

---

## SECTION A: Common Foundation

*Shown to all audiences. Leads with actual output to establish credibility before explaining the framework.*

---

### Slide 2: Here's Our Landscape Today

| Element | Content |
|---------|---------|
| **Title** | APAC IT Application Landscape |
| **Body** | [Actual portfolio-level diagram generated from existing data]. X applications across Y domains. This was built from documents, spreadsheets, and system records we already had. |
| **Visual** | Real landscape diagram from `ea_diagrams/` - the full portfolio view |
| **Talking Point** | "This is what our IT landscape looks like right now, built from data we already have." |

---

### Slide 3: What This Reveals

| Element | Content |
|---------|---------|
| **Title** | What We Can See - and What We Can't |
| **Body** | What's visible: X applications identified, Y integrations mapped, Z domains covered. What's missing: N applications with no owner, M with unknown lifecycle, K with no documented integrations. |
| **Visual** | Split view: "Known" (solid) vs "Gaps" (dotted/faded) with counts |
| **Talking Point** | "The gaps are as important as what we can see. This is where we need your help." |

---

### Slide 4: The Problem This Solves

| Element | Content |
|---------|---------|
| **Title** | Why Visibility Matters |
| **Body** | Investment decisions made without seeing the full picture. Duplicate systems discovered too late. Dependencies found during incidents, not during planning. No shared language for "where is this system going?" |
| **Visual** | 2-3 concrete examples from the actual landscape data (e.g., "3 systems serving similar functions in Domain X") |
| **Talking Point** | "These aren't hypothetical problems - they're in the data we just looked at." |

---

### Slide 5: Two Questions That Organize Everything

| Element | Content |
|---------|---------|
| **Title** | A Simple Framework |
| **Body** | Every system answers two questions: (1) What business function does it support? (2) Where is it going? That's the entire mental model. No jargon, no complex frameworks. |
| **Visual** | 2-axis framework: Function (rows) x Horizon (columns) |
| **Talking Point** | "Two questions. That's it." |

---

### Slide 6: The Horizon Model

| Element | Content |
|---------|---------|
| **Title** | Three Time Horizons |
| **Body** | **H1 - Today:** Current state, running in production. **H2 - In transition (2025-2026):** Active changes, migrations, upgrades underway. **H3 - Target state (2026+):** Where we're heading, strategic platforms. |
| **Visual** | 3 columns with timeline arrow. Annotate with 1-2 real systems from the landscape as examples. |
| **Talking Point** | "Every system sits somewhere on this timeline. The question is: do we agree on where?" |

---

### Slide 7: Domain Example - Roadmap View

| Element | Content |
|---------|---------|
| **Title** | [Best Domain] Application Roadmap |
| **Body** | Key narrative: what's staying, what's changing, what's coming. Show the story the data tells for the domain with the most complete data. |
| **Visual** | Actual horizon diagram from `ea_diagrams/` with 2-3 annotations |
| **Talking Point** | "Here's what a domain roadmap looks like when the data is complete. This is the target for every domain." |

---

### Slide 8: Domain Example - Contrast

| Element | Content |
|---------|---------|
| **Title** | [Second Domain] Application Roadmap |
| **Body** | Different pattern from the first example. Show how the framework reveals different strategic situations: consolidation vs. growth, stability vs. transformation. |
| **Visual** | Actual horizon diagram with annotations highlighting the contrast |
| **Talking Point** | "Same framework, different story. That's the power of consistent visibility." |

---

### Slide 9: How This Works

| Element | Content |
|---------|---------|
| **Title** | From Existing Data to Living Architecture |
| **Body** | Three capabilities: (1) **AI Ingestion** - documents, spreadsheets, diagrams, whiteboard photos all become structured data. No manual data entry. (2) **Automated Artifacts** - roadmap diagrams and detailed views generated on demand. Same-day turnaround on updates. (3) **Portal** - catalogue, elements, and diagrams linked in one browsable reference. |
| **Visual** | Flow: Any Input Format → AI Processing → CMDB → Diagrams + Portal |
| **Talking Point** | "The diagrams you just saw were generated automatically. When data changes, we regenerate. This isn't a one-time exercise." |

---

### Slide 10: What This Enables

| Element | Content |
|---------|---------|
| **Title** | From Data to Decisions |
| **Body** | Compare domains in the same format. Spot duplications and gaps across the portfolio. Plan investments with full visibility of what exists. Shared language for architecture discussions. Foundation for governance without bureaucracy. |
| **Visual** | Before/after: "Scattered spreadsheets" → "Unified portal with linked diagrams" |
| **Talking Point** | "This is the foundation. Now let's talk about what it means for you specifically." |

---

### Slide 11: Audience Transition

| Element | Content |
|---------|---------|
| **Title** | What This Means for You |
| **Body** | "The following slides are tailored to your role and what we need from each other." |
| **Visual** | Simple transition graphic |
| **Talking Point** | "Now let's talk about what this means specifically for you" |

---

## SECTION B: Director Focus

*Shown after Section A for Director audience only.*

---

### Slide B1: The Gaps That Matter

| Element | Content |
|---------|---------|
| **Title** | What We Don't Know Yet |
| **Body** | Specific gap metrics from the landscape: N applications with no assigned owner. M systems with unknown strategic direction. K domains with incomplete coverage. These gaps mean investment decisions are being made with partial information. |
| **Visual** | Gap summary table by domain: Domain / Apps Found / Missing Owner / Missing Horizon |
| **Talking Point** | "We have 70% of the picture. The missing 30% is where risk hides." |

---

### Slide B2: Cross-Domain Patterns

| Element | Content |
|---------|---------|
| **Title** | What the Data Already Reveals |
| **Body** | Even with incomplete data, patterns are visible: consolidation opportunities (similar systems across domains), shared dependencies between domains, investment clusters, potential sequencing conflicts. |
| **Visual** | Pattern summary with concrete examples from the actual landscape data |
| **Talking Point** | "These patterns become clearer as each domain lead fills their gaps." |

---

### Slide B3: The Ask

| Element | Content |
|---------|---------|
| **Title** | Completing the Picture |
| **Body** | I need your endorsement for domain lead working sessions. Each lead reviews their pre-built domain view and corrects it (not building from scratch). Sessions are 45-60 minutes each. Output: complete domain roadmaps in the same format you just saw. Same-day turnaround on updates after each session. |
| **Visual** | Rollout flow: Director Endorsement → Lead Sessions → Complete Landscape → Portal Live |
| **Talking Point** | "Your push gets them engaged. They correct what we have, not build from zero." |

---

### Slide B4: Communication Cascade

| Element | Content |
|---------|---------|
| **Title** | Three Layers of Rollout |
| **Body** | (1) Domain leads correct their views and own their roadmaps. (2) Portal goes live as shared reference when coverage reaches ~80%. (3) All IT education session builds shared vocabulary using real domain examples. Your approval on messaging before each stage. |
| **Visual** | Cascade: Director → Domain Leads (correct) → Portal (publish) → All IT (educate) |
| **Talking Point** | "Each layer only happens when the previous one is solid." |

---

## SECTION C: Domain Owner Focus

*Shown after Section A for Domain Owner audience only.*

---

### Slide C1: Here's Your Domain

| Element | Content |
|---------|---------|
| **Title** | [Domain Name] - What We Have So Far |
| **Body** | [Show their pre-built domain diagram]. This was built from existing documents and system records. Some of it will be wrong. Some of it will be missing. That's why we need you. |
| **Visual** | Their actual domain diagram from `ea_diagrams/` with gaps visibly marked |
| **Talking Point** | "This is your domain as we understand it today. Tell me what's wrong." |

---

### Slide C2: What We Need From You

| Element | Content |
|---------|---------|
| **Title** | Correct, Position, Connect |
| **Body** | In our working session: (1) **Correct** - what's retired, what's missing, what's wrong. (2) **Position** - where is each system going? H1 (staying), H2 (changing), H3 (target). (3) **Connect** - what depends on systems outside your domain? What depends on you? No spreadsheets. We'll work from the diagram and I'll update it same day. |
| **Visual** | Three-step flow: Correct → Position → Connect |
| **Talking Point** | "45 minutes. We work from what we have, you tell me what's wrong, and I'll regenerate your view the same day." |

---

### Slide C3: What You Get Back

| Element | Content |
|---------|---------|
| **Title** | Your Roadmap, Your Story |
| **Body** | After our session you'll have: A complete domain roadmap in the same format as every other domain. A clear visual of what you own and where it's going. A tool to justify investments - show leadership planned evolution vs. current state. A view that updates when things change - not a static slide that goes stale. |
| **Visual** | Before (gaps, unknowns) → After (complete roadmap diagram) |
| **Talking Point** | "This makes your strategic thinking visible. It protects your budget by showing the plan." |

---

### Slide C4: Presenting to Leadership

| Element | Content |
|---------|---------|
| **Title** | The 5-Minute Structure |
| **Body** | When presenting your domain to the Director: 1. "Here's what I own" (landscape). 2. "Here's where each is going" (horizon placement). 3. "Here's why" (rationale for key moves). 4. "Here's what I need" (resources, decisions). 5. "Here's what depends on others" (cross-domain). Your diagram tells this story visually. The narrative is yours. |
| **Visual** | Numbered flow diagram |
| **Talking Point** | "The diagram is the medium. The story is yours to tell." |

---

## SECTION D: All IT Focus

*Shown after Section A for All IT audience. Extended section for architecture literacy objective.*

---

### Slide D1: Why This Matters to You

| Element | Content |
|---------|---------|
| **Title** | Architecture Affects Everyone |
| **Body** | **Developers:** Know what's strategic vs. sunsetting before you build on it. **Project Managers:** Understand dependencies for planning. **Support:** Know what's changing and when. **Everyone:** Speak the same language about systems. |
| **Visual** | Role-based relevance icons or cards |
| **Talking Point** | "This isn't just for architects—it helps everyone" |

---

### Slide D2: The Mental Model

| Element | Content |
|---------|---------|
| **Title** | One Thing to Remember |
| **Body** | **Business Function** (what it does) + **Horizon** (when - today/2025/2026+) = **The Landscape**. That's the core concept. Everything else builds on this. |
| **Visual** | Simple 2-axis diagram with labels |
| **Talking Point** | "If you remember one thing, remember this" |

---

### Slide D3: Questions to Start Asking

| Element | Content |
|---------|---------|
| **Title** | Think Architecturally |
| **Body** | Before starting a project: "Where is this system on the roadmap - today, 2025, or 2026+?" When integrating: "What else connects to this system?" When investing time: "Is this aligned with our roadmap?" When something breaks: "What depends on this?" |
| **Visual** | Question prompts with context |
| **Talking Point** | "Start asking these questions—it changes how you work" |

---

### Slide D4: Key Terms

| Element | Content |
|---------|---------|
| **Title** | Quick Glossary |
| **Body** | **Application:** A software system that supports business functions. **Landscape:** All applications in a domain or organization. **Horizon:** When - H1 (today), H2 (2025), H3 (2026+). **Roadmap:** The plan for how systems evolve over time. **Integration:** How systems connect and share data. |
| **Visual** | Clean glossary card format |
| **Talking Point** | "These are the words you'll hear in architecture conversations" |

---

### Slide D5: What is Enterprise Architecture?

| Element | Content |
|---------|---------|
| **Title** | The Bigger Picture |
| **Body** | Enterprise Architecture is how we organize, connect, and evolve technology to support business goals. It's not about diagrams—it's about decisions. Think of it like city planning: roads, buildings, utilities all need to work together. |
| **Visual** | City planning analogy or layered diagram |
| **Talking Point** | "Architecture is the blueprint for how our technology fits together" |

---

### Slide D6: Layers of Architecture

| Element | Content |
|---------|---------|
| **Title** | Four Layers That Work Together |
| **Body** | **Business:** What the organization does (processes, capabilities). **Application:** Software that supports business functions. **Data:** Information that flows between systems. **Technology:** Infrastructure that runs everything (servers, networks). |
| **Visual** | 4-layer stack diagram |
| **Talking Point** | "Changes in one layer affect the others" |

---

### Slide D7: What Happens Without Architecture

| Element | Content |
|---------|---------|
| **Title** | The Cost of Chaos |
| **Body** | **Duplication:** 5 systems doing the same thing. **Integration nightmares:** Nobody knows what connects to what. **Wasted investment:** Building on systems about to be retired. **Slow delivery:** Every project discovers dependencies the hard way. **Knowledge loss:** Only one person knows how it works. |
| **Visual** | Problem icons or "spaghetti" diagram |
| **Talking Point** | "This is what we're preventing" |

---

### Slide D8: How You Can Contribute

| Element | Content |
|---------|---------|
| **Title** | Your Role in Architecture |
| **Body** | **Know your systems:** What do you work with daily? **Flag issues:** See duplication or confusion? Raise it. **Ask questions:** "Is this system strategic?" is always valid. **Think connections:** What depends on what you're changing? **Share knowledge:** Document what you know. |
| **Visual** | Action checklist |
| **Talking Point** | "Architecture isn't done by architects alone—everyone contributes" |

---

## Slide Count Summary

| Section | Slides | Audience |
|---------|--------|----------|
| Contents | 1 | All |
| Section A: Foundation | 10 | All |
| Section B: Director | 4 | Director only |
| Section C: Domain Owner | 4 | Domain Owners only |
| Section D: All IT | 8 | All IT only |

**Per presentation:**
| Audience | Sections | Total Slides | Est. Time |
|----------|----------|--------------|-----------|
| Director | A + B | 14 slides | ~25-30 min |
| Domain Owners | A + C | 14 slides | ~25-30 min |
| All IT | A + D | 18 slides | ~30 min |

---

## Detailed Deep-Dives (Follow-up Sessions)

These are NOT in the main deck. Schedule separately as needed:

| Session | Audience | Content |
|---------|----------|---------|
| Domain Working Session | Individual Domain Owner | Co-create their specific roadmap |
| Cross-Domain Review | Director + Domain Owners | Compare roadmaps, resolve dependencies |
| Architecture Q&A | All IT (optional) | Open questions, deeper concepts |

---

## Production Notes

### Diagram Generation
- Domain diagrams generated from `archi_inputs/` using repository tooling
- Consistent format across all domains (Business Function × Horizon)
- Color coding: Lifecycle status or risk level
- Annotations: Key callouts for strategic decisions

### Maintenance
- Single data source (`archi_inputs/`) feeds all presentations
- Diagrams regenerate when data updates
- Slide content remains stable; only visuals update

### File Locations
- Slide deck: [TBD - PowerPoint/Google Slides]
- Domain diagrams: `ea_diagrams/`
- Source data: `archi_inputs/`
- View specs: `ea_inputs/views/`
