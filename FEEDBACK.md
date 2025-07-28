Great idea—but make it two layers:

an LLM “planner/explainer” layer that drafts/iterates on the portfolio plan (Epics/Features) and answers natural‑language questions, and

a deterministic sync/ops layer that idempotently reads/writes Azure DevOps (ADO) work items, links, and reports across projects. Let the LLM never “click the API directly”; it should only emit a strict, typed plan/spec that the ops layer applies and keeps in sync.

Below is how I’d shape it so you actually solve the two pains you called out.

The problem (reframed)
Creating & iterating Epics/Features/Tasks is slow and messy.

People type freeform, structure drifts, acceptance criteria are inconsistent, and updating everything is painful.

Tracking bugs/issues across many projects is fragmented.

Cross-project WIQL is clunky, Delivery Plans are shallow, and linking bugs back to the “portfolio” Feature/Epic in another project is manual.

Target operating model (Hub ↔ Spokes)
One “Portfolio (Hub) project” that owns Epics & Features only.

Many “Delivery (Spoke) projects” that own Stories/Tasks/Bugs.

Your agent enforces:

A canonical YAML/JSON plan (Epics/Features) in the hub.

Automatic creation + linking of child work items in the spoke projects (Stories/Tasks) according to a team/project mapping.

Bi‑directional links so bugs in spokes are automatically linked “up” to the right Feature/Epic in the hub.

The agent system (clear roles)
1) Planner Agent (LLM)
Input: business goal / RFC / PRD.

Output: strict JSON/YAML plan:

yaml
Copy
Edit
epics:
  - external_key: EP-001
    title: Unified Data Platform
    description: ...
    features:
      - external_key: FE-001
        title: Build ingestion layer
        target_projects: ["Data-ETL", "APAC-CRM"]
        stories_per_project:
          Data-ETL:
            story_template: "... {project} ..."
            tasks: ["Design schema", "Implement dbt", "Deploy CI/CD"]
          APAC-CRM:
            story_template: "... {project} ..."
            tasks: ["Map entities", "Write connectors"]
        acceptance_criteria:
          - ...
        metrics:
          - lead_time
          - defect_leakage
The JSON/YAML is versioned, diffed, and reviewed by humans before the ops layer touches ADO.

2) Sync / Upsert Engine (deterministic Python)
Reads the authoritative plan file.

Uses stable external IDs (e.g., external_key, stored in Custom.ExternalKey or a Tag) to:

Create or update Epics/Features/Stories/Tasks.

Keep links (Parent/Child, Related, Affects/Found in) correct.

Never duplicate (idempotent reconciliation).

Runs on demand (cli sync) or scheduled (cron/GitHub Actions/Azure Functions).

3) Bug Router
Subscribes to ADO Service Hooks (work item created/updated).

Classifies each Bug (LLM optional) → which Feature/Epic it should be linked to.

Auto-links the bug to its parent Feature in the Hub project (create “Related” + “Parent/Child” as needed).

Optionally adds labels/tags for the Feature/Epic key.

4) Cross-project Reporter
Queries Analytics OData or REST WIQL to produce:

Feature/Epic status, burn-up, cycle time, WIP limits.

Cross-project open bugs by Feature/Epic.

Can dump to Markdown/HTML/Slack/Teams.

5) Governance / Guardrails
Ensure process template drift is handled (fields differ across projects).

Enforce reviewer and branch policies (via Repos API) if you want the agent to codify SDLC rules per Feature/Epic.

How you actually fix the two pains
1) Create & iterate Epics/Features fast
Let humans talk to the Planner Agent in natural language.

The agent spits out a strict plan file (YAML/JSON), complete with DoR/DoD, ACs, KPIs, team mappings.

Humans approve the diff → Sync Engine applies or updates the tree.

2) Track bugs/issues across projects
Every Bug created anywhere is immediately classified & linked “up” to the correct Feature in the Hub.

Your Reporter command gives a single consolidated view (table or dashboard) by Feature → Bugs, test debt, fix SLA, etc.

Key design choices (don’t skip)
Idempotency:

Store external_key (from your plan) in every created WI (field or tag).

On every sync, look up by that key; never by title.

Diff-first workflow:

Show the “plan vs ADO” diff to the user before writing. Let them approve.

Event-driven bug routing:

Don’t batch; react to events via Service Hooks so links are always up-to-date.

Process template variance:

Abstract field names (System.Title, Microsoft.VSTS.Scheduling.Effort, custom fields) in a field map per project.

Permissions:

PAT vs OAuth app registration; store secrets in Key Vault and never let the LLM see them.

Minimal WIQLs you’ll need
All open bugs across projects, grouped by Feature external key (tag example):

text
Copy
Edit
SELECT
  [System.Id],
  [System.Title],
  [System.TeamProject],
  [System.State],
  [System.AssignedTo]
FROM workitems
WHERE
  [System.WorkItemType] = 'Bug'
  AND [System.State] <> 'Closed'
ORDER BY [System.ChangedDate] DESC
Then, in code, resolve “parent Feature” by following links or by tag feature:FE-001.

Find by external_key on sync:

text
Copy
Edit
SELECT [System.Id], [System.Title]
FROM workitems
WHERE
  [System.TeamProject] = @project
  AND [System.Tags] CONTAINS 'external_key:FE-001'
Delivery plan (fastest path to value)
Milestone 0 – Read-only

cli report: show cross-project bug matrix and status per Feature using WIQL + Analytics.

Milestone 1 – Deterministic sync

cli sync: upsert Epics/Features from plan.yaml into the Hub project.

Milestone 2 – Cross-project story/task fan-out

Extend sync to create Stories/Tasks in mapped spoke projects + create links back.

Milestone 3 – Bug router (service hooks)

Auto-link and tag bugs to Features.

Milestone 4 – Conversational UX

cli plan "Business goal …" → LLM drafts plan.yaml → human approves → cli sync.