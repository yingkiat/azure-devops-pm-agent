03 DSL_and_Schema: EA Domain-Specific Language and Graph Schema
Overview: This section defines the EA DSL (Domain-Specific Language) – a structured schema to represent our enterprise architecture in a technology-agnostic way – and the corresponding graph data model. The DSL is designed to be minimal yet sufficient to capture key artifacts across Business, Application, Data, and Technology layers, including their interrelationships. It draws inspiration from The Open Group’s ArchiMate (which has ~50 core concepts) but trims it down to about a dozen core concepts for simplicity (a “lean notation” that is easier to adopt[30]). Each concept in the DSL is mapped to standard architecture framework elements (ArchiMate, UML) to ensure interoperability and understanding by those familiar with industry standards.
The DSL will serve as the common vocabulary for architects, tools, and AI agents – enabling, for example, an AI to output an architecture model as a YAML according to this schema, or a script to validate and transform it. The schema is expressed in YAML format for human readability and ease of editing, but it could be translated to JSON Schema or a database schema as needed. Validation rules are included (e.g., required fields, ID formats, allowable relationships) to maintain model integrity.
Below we present the DSL schema (file dsl_schema.yaml), two example model instances (“Purchase Order Process” domain and “Core Banking” domain) under dsl_examples, and mapping tables linking DSL elements to ArchiMate and UML equivalents (files in mappings/). These deliverables ensure that our DSL is well-defined, exemplified, and aligned with standard terms.

In this Purchase Order example (sample_purchase_order.yaml), we see how everything ties together:

Capabilities (Procure-to-Pay) contains processes (PO Processing, Payment Processing). The ERP application (APP-001) and Supplier Portal (APP-002) both realize and support that capability, and the processes depend on those applications. The ERP and Portal integrate via an interface INT-001.

DataObjects like Purchase Order Document and Supplier Invoice are used in the process (we implicitly see that in steps or through the service interactions; we could add explicit relationships like Step depends_on Data if needed).

KPIs measure process performance (cycle time for POs, on-time payment rate).

A Risk of late delivery impacts the process, mitigated by a Control (contract SLA). Another risk of audit non-compliance is mitigated by a control (3-way match policy). Additionally, a corporate Policy (POL-001) governs the process (ensuring approvals happen) and the ERP system (which must enforce that workflow), and a data retention policy governs the data objects.

Technology hosting is captured: ERP on on-prem servers, Portal in Azure – useful for infra teams and impact analysis (e.g., if Azure East US region has an outage, which capabilities are affected? This model would show Procure-to-Pay is one).

The example is simplified but reflects real connections an enterprise might want to see. For instance, if we want to check compliance: does every high-impact process have at least one control mitigating its risks? We can query that. Here PO Processing had a risk and control; another process might not, which would stand out.

In the Core Banking/Onboarding example (sample_core_banking.yaml), highlights include:

A Capability hierarchy (Customer Onboarding is a subset of Retail Banking Services).

The onboarding Process (PROC-010) with steps (submit application, do KYC, open account). The process depends on multiple systems: CRM (for data entry), KYC tool (for checks), and Core Banking (to create account). This is a realistic multi-system workflow.

We see system integrations: CRM integrates with Core Banking (to send account data) and with the KYC service – these are captured via interfaces INT-010 and INT-011.

DataObjects: Customer Profile data is used and leads to creation of Account Record (and we show lineage). This could help in data lineage tracing and ensuring, for example, that privacy policy is applied across.

Risks: Money laundering risk tied to onboarding (which is mitigated by doing enhanced due diligence on high-risk customers), and a customer experience risk (if onboarding is slow, mitigated by monitoring SLAs).

Policies: KYC Compliance Policy governs the process and the tool (ensuring KYC steps happen), and a Data Privacy policy governs the personal data in CRM and usage.

Hosting: shows a hybrid environment (mainframe + cloud). If the bank plans to modernize, one roadmap might be migrating off the mainframe to cloud – the model would make the impact clear (e.g., which capabilities rely on that mainframe? Here, Retail Banking broadly does).

These examples demonstrate the DSL’s applicability and expressiveness. They also serve as test cases for our validation and generation pipelines – for instance, we can run dsl_validate.py on these YAML files to ensure the schema rules catch any errors.

mappings/dsl_to_archimate.csv (Mapping DSL concepts to ArchiMate 3.1)

The following table maps each DSL element to an ArchiMate element (and layer) that is most closely equivalent. This is useful for understanding how our meta-model aligns with a standard EA language, and it could be used to translate our DSL models into ArchiMate diagrams or exchange formats if needed. (Note: ArchiMate has more nuances, but we choose the closest match.)

DSL Element	ArchiMate Element (Layer)	Notes
Capability	Capability (Strategy layer)	(ArchiMate Strategy element representing an ability)
Process	Business Process (Business layer)	(A behavior element in Business layer)
Step	n/a (no direct ArchiMate element)	ArchiMate doesn’t model individual steps; use BPMN for detailed process flow
Application	Application Component (Application layer)	(Active structure element in Application layer – a software application)
Service	Application Service (Application layer) or Business Service (Business layer)	(Depending on context: an internal technical service vs. a business service offered externally)
Interface	Application Interface (Application layer) or Technology Interface (Technology layer)	(If interface is at app level vs. infra level)
DataObject	Data Object (Application layer)	(Passive structure representing data; could also map to Business Object if high-level data)
KPI	Outcome or Assessment (Motivation extension)	(ArchiMate doesn’t have a KPI element; a “Measure” concept is often represented as an Assessment result or a Performance Indicator in motivation domain)
Risk	Assessment (Motivation extension)	(ArchiMate’s motivation layer can model outcomes of analysis like risks/opportunities as Assessments)
Control	Requirement or Constraint (Motivation)	(Depending on if it’s a functional requirement or a constraint; could also be a Goal if it’s a desired condition, but usually policies/controls are modeled as Requirements/Constraints)
Technology	Node or Device (Technology layer)	(An infrastructure node; if it’s a platform service, could be Technology Service. We map broadly to Node/Device for physical/logical infra)
Policy	Principle (Motivation extension)	(High-level policy or guideline maps to a Principle in ArchiMate’s motivation elements; could also be a Constraint if it’s a binding rule)

Relationship mappings: In ArchiMate, similar relationships exist, though names differ: e.g., realizes (same term in ArchiMate) is used when e.g. Application Component realizes a Capability (through outcome realization). serves corresponds to ArchiMate’s Serving relationship (e.g., Application serves Business Process). depends_on is a generic dependency; ArchiMate often uses Used-By/Access or Association to model dependencies. integrates might correspond to a Flow relationship (for data flow between components). mitigates isn’t native in ArchiMate; we’d represent a Control mitigating a Risk via an Influence relationship (stating that a Requirement/Constraint has a positive influence on reducing a Risk/Assessment). measures would be an Association from a metric to what it measures. contains (composition) and hosted_on (deployment relationship) are present in ArchiMate (composition/aggregation, and assignment used for deployment). governed_by can be represented by ArchiMate’s association or a specialization of influence (policy influences behavior of something). In summary, our DSL relationships can be mapped to ArchiMate relationships with some interpretation, but the semantics remain consistent.

(Date: ArchiMate 3.1 Spec, The Open Group, 2019 – our mappings are based on that standard
orbussoftware.com
orbussoftware.com
, ensuring alignment with known concepts.)

mappings/dsl_to_uml.csv (Mapping DSL concepts to UML)

UML (Unified Modeling Language) is a broad standard primarily for software design (classes, objects, etc.), and it doesn’t directly encode enterprise concepts like capabilities. However, we can map our DSL elements to UML constructs or stereotypes for those who want to use UML diagrams (like class diagrams, use case, etc.) in conjunction.

DSL Element	UML Correspondence	Notes
Capability	Package (stereotyped as <<Capability>>)	(Could use a UML Package or Component to represent a business capability grouping)
Process	Activity (in an Activity Diagram) or Use Case	(UML Activity for workflow; or a high-level Use Case representing the process from an actor’s perspective)
Step	Action (within an Activity)	(A step would be a granular action in an Activity diagram)
Application	Component (in Component Diagram)	(A UML Component or a set of Classes representing the system; can use <<System>> stereotype)
Service	Interface (provided interface in Component Diagram) or Component	(If modeling as a software service, could be an Interface provided by a component; or treat it as a Component named for the service)
Interface	Interface (provided/required interface)	(UML Interface element, possibly with a realization / usage link between components)
DataObject	Class (in a Class or ER diagram)	(Data object can be a UML Class or even a Data Model entity; could stereotype as <<DataObject>>)
KPI	Note or Constraint (attached to model)	(UML doesn’t have metrics; can model as a constraint with a tagged value, or a Note on a diagram indicating a performance measure)
Risk	Note or Constraint (<<Risk>> stereotype)	(Can be attached to elements as a comment, possibly with a stereotype to indicate risk; UML doesn’t model risks natively)
Control	Constraint (<<Control>> stereotype)	(A UML Constraint (like an OCL or just an informal rule) attached to elements; or a Note with <<Control>>)
Technology	Node (Deployment Diagram)	(UML Node for hardware/infra in a Deployment diagram; e.g., a server, execution environment)
Policy	Constraint (<<Policy>> or <<Requirement>> stereotype)	(Can be modeled similar to a Constraint or Requirement in a UML profile; otherwise as notes that certain components must comply with X)

Relationship-wise in UML:

realizes: UML has Realization (often used between a specification and implementation, e.g., an interface and the class implementing it). We could use Realization to show, e.g., a component realizes a use case or requirement (if using UML’s use case or requirement extension).

depends_on: UML’s Dependency relationship fits (dashed line arrow) indicating one element depends on another.

integrates: Could be shown as an Association or as two components connected by an interface usage (a component providing an interface that another requires).

serves: UML doesn’t have a direct “serves” but we might show it as Dependency or as a Use relationship (if we treat capability as a use case, an application can “use” or support that use case).

mitigates: Could be a dependency with a stereotype <<mitigates>> from control to risk note.

measures: a note or constraint linking KPI to whatever it measures (no standard, but could use a dependency <<measures>>).

contains: UML uses composition or aggregation (the filled diamond or hollow diamond arrows) for hierarchical contains relationships (e.g., Capability composite of sub-capabilities, can be shown as a package containment or composition association).

governed_by: possibly a dependency <<governed_by>> from an element to a policy note.

hosted_on: UML Deployment relationship (an artifact or component deployed on a node). We can show an Application (as an artifact/component) deployed on a Node (Technology).

lineage_of: no direct UML concept; could use dependency or trace to show data lineage, or use an <<flow>> dependency indicating data flow.

In practice, if UML is needed, we might create a UML profile with stereotypes for these DSL concepts, as some EA tools do (ArchiMate can be profiled onto UML
medium.com
). However, since our approach is tool-agnostic, we likely won’t do heavy UML modeling, but this mapping ensures we can communicate with teams who use UML (e.g., solution designers) how our concepts relate to theirs (for example, they design a component diagram – we can incorporate those components as Applications in our EA model).

(This mapping is based on UML 2.5 standard and common EA practice of using UML profiles. Note that UML is not typically used for enterprise architecture descriptions, but overlaps exist, and as Dr. Figay (2024) notes, “ArchiMate is for blueprinting, UML is for designing”
medium.com
. Our DSL serves the blueprinting role, and detailed design can still be done in UML as needed, with alignment through these mappings.)

Conclusion: The DSL and schema provided here form the backbone of our EA repository. By using a consistent, constrained vocabulary, we achieve traceability (every artifact is typed and linked) and tool-agnosticism (the YAML/CSV data can be loaded into various tools – graph databases, visualization engines, etc.). This minimal DSL captures the essence of the enterprise architecture in a way that supports our automation goals: it’s straightforward enough for AI to generate or check (no overly complex meta-model), and robust enough to answer key questions about alignment, impact, and risk. As we implement, we will continuously test the schema against real scenarios (like the examples) and adjust if new needs arise, keeping the mappings to standards for reference. This ensures that our custom approach remains grounded in proven frameworks while giving us the flexibility to innovate in how we maintain and use our enterprise architecture knowledge base.