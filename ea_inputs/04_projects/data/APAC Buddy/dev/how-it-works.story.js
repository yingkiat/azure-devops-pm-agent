// APAC Buddy facts for docs/how-it-works.html. Values come from the files and
// sessions named in each scene's source; example questions, router scores and
// reply bubbles are illustrative.
(() => {
  const mono = (s) => `<span class="mono">${s}</span>`;
  const ja = (s) => `<span lang="ja">${s}</span>`;
  const qLookup = "NONJ92712の価格は？", qReason = "NONJ92712の売上が今期下がった理由は？", qNone = "おはよう！";

  // ---------- Shared infrastructure graph ----------
  const infraNodes = {
    teams: { who: "Teams", name: "User", icon: "user", col: 0, row: 0 },
    agent: { who: "Copilot Studio", name: "Agent", icon: "sparkle", col: 1, row: 0 },
    flow: { who: "Power Automate", name: "Agent flow", icon: "flow", col: 2, row: 0 },
    apim: { who: "Azure APIM", name: "m3apidwhsp1", small: true, icon: "gateway", col: 3, row: 0 },
    entra: { who: "Entra ID", name: "Token check", icon: "shield", col: 2, row: 1 },
    api: { who: "Node service", name: "API", icon: "braces", col: 3, row: 1 },
    decision: { who: "Router", name: "msoft-decision-1", small: true, icon: "branch", col: 4, row: 1 },
    codex: { who: "Codex SDK", name: "Codex CLI", icon: "terminal", col: 3, row: 2 },
    luna: { who: "Reasoning", name: "gpt-6-luna", small: true, icon: "chip", col: 4, row: 2 },
    mcp: { who: "Loopback", name: "Fabric MCP", icon: "plug", col: 3, row: 3 },
    fabric: { who: "SQL endpoint", name: "Warehouse", icon: "db", col: 4, row: 3 },
    memory: { who: "OneLake", name: "User memory", icon: "doc", col: 5, row: 3 },
  };
  const infraEdges = [
    ["teams", "agent"], ["agent", "flow"], ["flow", "apim"], ["apim", "api"], ["api", "entra"], ["api", "decision"],
    ["api", "codex"], ["codex", "luna"], ["codex", "mcp"], ["mcp", "fabric"],
    ["api", "fabric", { via: [[3.25, 1], [3.25, 1.5], [3.5, 1.5], [3.5, 2.5], [4, 2.5]] }],
    ["api", "memory", { via: [[3.35, 1], [3.35, 1.4], [4.6, 1.4], [4.6, 2.6], [5, 2.6]] }],
  ];
  const sideVia = { via: [[2.75, 1], [2.75, 1.5], [2, 1.5]] };
  const infraZones = [
    { label: "Microsoft 365", nodes: ["teams", "agent", "flow"] },
    { label: "Azure Container App", nodes: ["api", "codex", "mcp"] },
    { label: "Azure AI Foundry", nodes: ["decision", "luna"] },
    { label: "Microsoft Fabric", nodes: ["fabric", "memory"] },
  ];

  // ---------- Chapter 1: how it works ----------
  const infra = {
    id: "infrastructure", label: "Infrastructure view", summary: "The services a request passes through",
    nodes: { ...infraNodes, insights: { who: "Azure Monitor", name: "App Insights", icon: "bars", col: 2, row: 2 } },
    edges: [...infraEdges, ["api", "insights", sideVia]],
    zones: infraZones,
    idle: { title: "Press play to follow a request through the services", text: "From Teams through Power Platform and APIM to the Container App, out to Azure AI Foundry and Microsoft Fabric, and back." },
    paths: [{ id: "main", label: "Infrastructure", scenes: [
      { route: ["teams"], who: "Microsoft Teams", title: "The user asks in Teams",
        text: "The APAC Buddy agent is built in Copilot Studio and published to Teams. The user is signed in with their Medline Microsoft 365 account.",
        bubble: { node: "teams", text: qLookup, lang: "ja" }, source: "docs/COPILOT-INTEGRATION.md" },
      { route: ["teams", "agent"], carry: "message", who: "Copilot Studio", title: "The agent plans the tool call",
        text: "The agent's model (GPT-5.5 Chat in Copilot Studio) reads the message, decides to call its one tool and writes the tool's inputs. Planning, and later writing the reply, are the largest share of the time.",
        note: "Measured: about 10 s end to end in Teams, of which about 3 s is the API. Switching from Claude Sonnet 4.6 halved it from about 20 s.",
        callouts: [{ node: "agent", text: "about 10 s end to end", tone: "accent", at: 300 }], source: "session 16 Oct (GPT-5.5 Chat test); session 15 Oct" },
      { route: ["agent", "flow"], carry: "4 inputs", who: "Power Automate", title: "The agent flow runs",
        text: `${mono("copilot_flow_dhws_api")} takes ${mono("tool_name")}, ${mono("tool_args")}, ${mono("user_email")} and ${mono("question")}. It exists to control how the user's token is passed. Agent flows must answer within 100 s.`,
        callouts: [{ node: "flow", text: "about 1 s of its own", tone: "accent", at: 300 }], source: "docs/COPILOT-INTEGRATION.md; session 15 Oct" },
      { route: ["flow", "apim"], carry: "HTTPS POST", who: "Azure API Management", title: "The flow calls APIM",
        text: `An HTTP action posts to ${mono("m3apidwhsp1.azure-api.net/apac-buddy/api/v1/call_tool")} with the APIM subscription key, an Entra access token for Azure Management, and the user's email.`,
        callouts: [{ node: "apim", text: "subscription key", tone: "accent", at: 300 }], source: "session 13 Oct (flow HTTP step); APIM inbound policy" },
      { route: ["apim", "api"], carry: "request", who: "Azure Container Apps", title: "APIM forwards to the Container App",
        text: `${mono("m3acaapacbuddyp1")} in Southeast Asia runs this repository's Node service. It keeps at least one replica running so the warehouse connections stay warm.`,
        callouts: [{ node: "api", text: "about 3 s per answer", tone: "accent", at: 300 }], source: "azure-pipelines.yml; session 15 Oct" },
      { route: ["api", "entra"], carry: "Entra token", who: "Microsoft Entra ID", title: "The token is checked",
        text: "APIM has already validated the token; the service checks it again against the tenant's published signing keys, which it caches between requests.",
        callouts: [{ node: "entra", text: "signing keys, cached", tone: "good", at: 300 }], source: "src/auth/authorizer.ts; APIM inbound policy" },
      { route: ["api", "fabric"], carry: "user's email", who: "Microsoft Fabric", title: "The employee's roles are looked up",
        text: `The employee table in ${mono("unified_data_warehouse")}, over SQL with a service principal, on one shared connection pool. Warm queries take 0.15 to 1.2 s; a cold warehouse session took up to 25 s, which is why the pool is kept warm.`,
        callouts: [{ node: "fabric", text: "0.15 to 1.2 s warm", tone: "good", at: 300 }], source: "docs/decisions/ADR-004; session 13 Oct" },
      { route: ["api", "memory"], carry: "user key", who: "OneLake", title: "The user's memory is read alongside the router",
        text: `Each user's memory is two small files in ${mono("bronzelakehouse")}. The API reads only ${mono("prompt.json")}, about 70 ms, while Decision-1 decides, which takes about 0.9 s, so it adds nothing to the reply. Reads are cached for 5 minutes, and the service keeps the OneLake connection warm alongside the warehouse's.`,
        callouts: [{ node: "memory", text: "about 70 ms, overlapped", tone: "accent", at: 300 }], source: "src/memory/user-memory.ts; measured 19 Oct; route-eval median 911 ms" },
      { route: ["api", "decision"], carry: "message + playbooks", who: "Azure AI Foundry", title: "Decision-1 chooses",
        text: `One call to the ${mono("msoft-decision-1")} deployment in Azure AI Foundry, East US 2. It returns a choice and its probability. The call crosses regions, from Southeast Asia to East US 2.`,
        callouts: [{ node: "decision", text: "choice + probability", tone: "accent", at: 300 }], source: "deploy/production.yml; docs/decisions/ADR-006" },
      { route: ["api", "fabric"], carry: "fixed SQL", who: "Path 1: lookup", title: "One query in Fabric",
        text: "When Decision-1 picks a capability with probability 0.6 or more, the API runs that capability's fixed query on the same pool. About a second.",
        callouts: [{ node: "fabric", text: "rows", tone: "good", at: 300 }], source: "src/call-tool-service.ts" },
      { route: ["api", "codex", "luna"], carry: "question", who: "Path 2: reasoning", title: "Codex runs inside the container",
        text: `Otherwise the API starts Codex through the Codex SDK, which runs the Codex CLI in the same container. Codex reasons with ${mono("gpt-6-luna")} in Foundry over the Responses API, at most 4 investigations at a time.`,
        busy: "codex-luna", callouts: [{ node: "luna", text: "Responses API", tone: "accent", at: 300 }], source: "src/agent/codex-reasoner.ts; deploy/production.yml" },
      { route: ["codex", "mcp", "fabric"], carry: "MCP tool call", who: "Path 2: reasoning", title: "Codex reaches Fabric through MCP",
        text: "Its tools come from the Fabric MCP host the API runs on loopback, so tool calls never leave the container. The API runs the queries itself; Codex holds no Fabric credential. It answers within 75 s.",
        busy: "fabric-mcp", callouts: [{ node: "mcp", text: "127.0.0.1", tone: "accent", at: 300 }], source: "src/mcp/fabric-mcp-host.ts; ADR-004" },
      { route: ["api", "apim", "flow", "agent", "teams"], carry: "JSON result", who: "Back to the user", title: "The reply goes back the same way",
        text: "The API returns JSON through APIM to the flow, the flow hands it to the agent, and the agent writes the reply in Teams.",
        bubble: { node: "teams", text: "NONJ92712 の平均単価は…", lang: "ja", reply: true }, source: "docs/COPILOT-INTEGRATION.md" },
      { route: ["api", "insights"], carry: "interaction record", who: "Azure Monitor", title: "Every call is recorded",
        text: `The interaction goes to Application Insights ${mono("m3applicationinsightsdwhsp1")}, which the console reads. Afterwards ${mono("gpt-6-luna")} in Foundry scores the answer and, in the same call, proposes edits to the user's memory.`,
        callouts: [{ node: "insights", text: "read by /console", tone: "good", at: 300 }], source: "docs/decisions/ADR-005; deploy/production.yml" },
    ] }],
  };

  // ---------- Chapter 2: how a question is answered ----------
  const ask = (question, translation) => ({ route: ["user"], who: "User, in Teams", title: "Asks a question",
    text: `${ja(question)} (“${translation}”)`, bubble: { node: "user", text: question, lang: "ja" } });
  const fill = (args) => ({ route: ["user", "copilot"], carry: "message", who: "Copilot agent", title: "Fills the tool's inputs",
    text: "Every message goes to one tool. Copilot does not choose a capability: it passes the message as typed, the user's email, one English sentence of intent, and the values it sees, in its own words.",
    code: args, source: "copilot/agent-instructions.md" });
  const forward = (question, args) => ({ route: ["copilot", "flow", "api"], carry: "tool_args", who: "Power Automate flow", title: "Forwards the inputs to the API",
    text: `${mono("POST /api/v1/call_tool")} with the user's token. ${mono("tool_name")} is ${mono("auto")}, so the API chooses.`,
    code: { tool: "auto", question, args, email: "user@medline.com" }, source: "docs/COPILOT-INTEGRATION.md" });
  const identify = { route: ["api"], who: "APAC Buddy API", title: "Checks who is asking",
    text: "It validates the token, finds the email in the employee table, and applies every role the employee matches by country, department and job title. Their scopes decide which capabilities and playbooks are in play.",
    note: "No matching role: the request is refused here.",
    callouts: [{ node: "api", text: "Token valid", tone: "good", slot: 0, at: 350 }, { node: "api", text: "Employee found", tone: "good", slot: 1, at: 900 }, { node: "api", text: "Roles and scopes", tone: "good", slot: 2, at: 1450 }],
    source: "config/roles.json; src/auth/role-resolver.ts" };
  const choose = (scores, note) => ({ route: ["api", "router"], carry: "message + context", who: "Router, msoft-decision-1", title: "Chooses one capability",
    text: `Reads the business context and the user's playbooks, then scores each capability it may choose, plus ${mono("reason")} and ${mono("none")}. It writes nothing.`,
    scores, threshold: 0.6, tag: "example scores", note, callouts: [{ node: "router", text: `${scores[0][0]} ${scores[0][1].toFixed(2)}`, tone: "accent", above: true, at: 1300 }],
    source: "docs/decisions/ADR-006; src/agent/tool-router.ts" });
  const reply = (bubble, text) => ({ route: ["copilot", "user"], carry: "reply", who: "Copilot agent", title: "Writes the reply", text, bubble: { node: "user", text: bubble, lang: "ja", reply: true } });
  const record = { route: ["api", "console", "api", "memory"], carry: "record, then memory edits", who: "APAC Buddy API", title: "Records, scores, and learns",
    text: `One console record per call: the message, the router's choice and confidence, what was returned, and the time each stage took. After the reply has gone, ${mono("gpt-6-luna")} judges the answer and, in the same call, proposes edits to the user's memory: reinforce a line it already holds, add a stated preference or correction, replace or remove what the user contradicted. Code applies the limits: no data values, at most 15 lines, 90-day expiry. None of it slows the reply.`,
    note: "Learning runs in shadow mode for now: the proposals are shown in the console, and nothing is written until they have been reviewed.",
    callouts: [{ node: "console", text: "Recorded and scored", tone: "good", slot: 0, at: 300 }, { node: "memory", text: "edits proposed", tone: "accent", slot: 0, at: 900 }],
    source: "docs/decisions/ADR-005; src/memory/learning.ts; ADR-007" };
  const readMemory = { route: ["api", "memory"], carry: "user key", who: "Memory, in OneLake", title: "Reads the user's memory alongside routing",
    text: "While the router decides, the API reads the user's prompt-ready memory: one small file, cached for 5 minutes. It goes into the reply rules and Codex's prompt, never to the router.",
    callouts: [{ node: "memory", text: "about 70 ms, overlapped", tone: "accent", at: 300 }], source: "src/memory/user-memory.ts; ADR-007" };
  const lookupArgs = { intent: "Get the price of NONJ92712.", parameters: { product: "NONJ92712" } };
  const qRemember = "今後、同等品と言ったら日本市場のことだと覚えておいて";
  const rememberArgs = { intent: "Remember that by 'equivalent' the user means the Japan market.", parameters: {} };
  const qRemind = "次回話す時に、MP-1518の在庫確認をリマインドして";
  const remindArgs = { intent: "Remind the user next time to check the stock of MP-1518.", parameters: { product: "MP-1518" } };
  const reasonArgs = { intent: "Explain why sales of NONJ92712 fell this quarter.", parameters: { product: "NONJ92712", period: "this quarter" } };
  const noneArgs = { intent: "Greet the assistant.", parameters: {} };

  const answer = {
    id: "answering", label: "Logic view", summary: "What the API decides, and the paths a message can take",
    rowHeight: 210, colWidth: 250,
    nodes: {
      user: { who: "Teams", name: "User", icon: "user", col: 0, row: 0 },
      copilot: { who: "Microsoft", name: "Copilot agent", icon: "sparkle", col: 1, row: 0 },
      flow: { who: "Power Automate", name: "Flow", icon: "flow", col: 2, row: 0 },
      api: { who: "APAC Buddy", name: "API", icon: "braces", col: 3, row: 0 },
      router: { who: "Router", name: "msoft-decision-1", small: true, icon: "branch", col: 4, row: 0 },
      console: { who: "APAC Buddy", name: "Console", icon: "bars", col: 2, row: 1 },
      fabric: { who: "Lookup", name: "Fabric", icon: "db", col: 3, row: 1 },
      codex: { who: "Reasoning", name: "Codex", icon: "terminal", col: 4, row: 1 },
      memory: { who: "OneLake", name: "Memory", icon: "doc", col: 1, row: 1 },
    },
    edges: [["user", "copilot"], ["copilot", "flow"], ["flow", "api"], ["api", "router"], ["api", "fabric"], ["api", "codex"], ["codex", "fabric"], ["api", "console"], ["api", "memory"]],
    idle: { title: "Press play to follow the question", text: "Pick a kind of question above: each takes a different path through the API." },
    paths: [
      { id: "lookup", label: "Lookup", time: "about 1 s", question: qLookup, lang: "ja", scenes: [
        ask(qLookup, "What is the price of NONJ92712?"),
        fill(lookupArgs),
        forward(qLookup, lookupArgs),
        identify,
        readMemory,
        choose([["jp_price_lookup", 0.99], ["reason", 0.01], ["none", 0]], `The API reads the capability's inputs from the parameters by their form and name: here, ${mono("NONJ92712")} as the code.`),
        { route: ["api", "fabric"], carry: "NONJ92712", who: "Lookup, in Fabric", title: "Runs the capability's SQL",
          text: "A fixed, parameterised query with the values read from the parameters. It returns the rows and lists any codes it could not find. About a second.",
          callouts: [{ node: "fabric", text: "SQL, about 1 s", tone: "accent", at: 250 }], source: "src/mcp/fabric-tools.ts" },
        { route: ["fabric", "api", "flow", "copilot"], carry: "rows + reply rules", who: "APAC Buddy API", title: "Returns the rows with the reply rules",
          text: "The result carries the \"Reply rules\" of the shared rules and of the user's playbooks, then the user's own memory, so Copilot knows how this domain, and this person, want the data worded.", source: "prompts/shared.md; prompts/playbooks; ADR-007" },
        reply("NONJ92712 の平均単価は…", `Copilot labels and words the data as the domain requires, for Japan prices as ${ja("平均単価")}, without its instructions naming any domain.`),
        record,
      ] },
      { id: "reason", label: "Reasoning", time: "up to 75 s", question: qReason, lang: "ja", scenes: [
        ask(qReason, "Why did sales of NONJ92712 fall this quarter?"),
        fill(reasonArgs),
        forward(qReason, reasonArgs),
        identify,
        readMemory,
        choose([["reason", 0.86], ["jp_price_lookup", 0.09], ["none", 0.01]], "Also sent to reasoning when the top score is below 0.6, the chosen capability needs a value the parameters do not hold, or the router fails."),
        { route: ["api", "codex"], carry: "question + scopes", who: "Reasoning, Codex", title: "Investigates", busy: "codex-fabric",
          text: `Codex, reasoning with ${mono("gpt-6-luna")}, works through the question with every capability the user's scopes allow, including those marked "Codex only", the same playbooks, and the user's memory after them.`,
          callouts: [{ node: "codex", text: "Within 75 s", tone: "accent", at: 400 }], source: "src/reason-service.ts" },
        { route: ["codex", "api", "flow", "copilot"], carry: "answer", who: "APAC Buddy API", title: "Returns the answer within 75 s",
          text: "If time runs out, Codex answers with its findings so far rather than nothing.", source: "docs/decisions/ADR-003" },
        reply("主な要因は次のとおりです…", "From Codex's answer, worded by the same shared rules and playbooks."),
        record,
      ] },
      { id: "none", label: "Not about Medline", time: "about 1 s", question: qNone, lang: "ja", scenes: [
        ask(qNone, "Good morning!"),
        fill(noneArgs),
        forward(qNone, noneArgs),
        identify,
        choose([["none", 0.97], ["reason", 0.02], ["jp_price_lookup", 0]], "A greeting, the weather, 1 plus 1: nothing about Medline to look up."),
        { route: ["api", "flow", "copilot"], carry: "none", who: "APAC Buddy API", title: "Answers in about a second",
          text: `The API returns ${mono("none")} without running a lookup or Codex.`, source: "docs/decisions/ADR-006" },
        reply("おはようございます！", "Copilot replies itself. If a reminder the user asked for is due, it comes back with the greeting, and Copilot mentions it once."),
        record,
      ] },
      { id: "remember", label: "Remember", time: "about 1 s", question: qRemember, lang: "ja", scenes: [
        ask(qRemember, "From now on, remember that when I say equivalent I mean the Japan market."),
        fill(rememberArgs),
        forward(qRemember, rememberArgs),
        identify,
        readMemory,
        choose([["remember", 1.0], ["reason", 0], ["none", 0]], `With memory on, the router can also choose ${mono("remember")}, ${mono("remind")}, ${mono("forget")} or ${mono("recall")}. It still writes nothing itself.`),
        { route: ["api", "memory"], carry: "the message, verbatim", who: "Memory, in OneLake", title: "Stores the instruction as said",
          text: `The API keeps the message word for word in the user's ${mono("memory.json")}, then rewrites ${mono("prompt.json")}, the small file every later request reads. Amounts and percentages are refused: memory says how to answer, never what the data is.`,
          callouts: [{ node: "memory", text: "remembered, version 2", tone: "good", at: 300 }], source: "src/memory/memory-actions.ts; ADR-007" },
        { route: ["api", "flow", "copilot"], carry: "reply", who: "APAC Buddy API", title: "Confirms what was remembered",
          text: `The API returns the ${mono("memory")} route with a short reply, which Copilot relays in the user's language. From the next request on, the instruction travels with every answer. "Forget" removes it, and "what do you remember" lists it.`,
          source: "src/contracts.ts; copilot/agent-instructions.md" },
        reply("覚えました：今後「同等品」は日本市場のことです。", "In the user's language, keeping what was remembered exactly as said."),
        { route: ["api", "console"], carry: "record", who: "APAC Buddy API", title: "Records the change",
          text: "The console record shows what was added and the new version, and the console's User check lists everything remembered about this person.",
          callouts: [{ node: "console", text: "change recorded", tone: "good", at: 300 }], source: "console/index.html; ADR-007" },
      ] },
      { id: "remind", label: "Reminder", time: "said once, next time", question: qRemind, lang: "ja", scenes: [
        ask(qRemind, "Next time we talk, remind me to check the stock of MP-1518."),
        fill(remindArgs),
        forward(qRemind, remindArgs),
        identify,
        readMemory,
        choose([["remind", 1.0], ["remember", 0], ["reason", 0]], `${mono("remind")} is for something to say once; ${mono("remember")} is for something to apply to every answer.`),
        { route: ["api", "memory"], carry: "the message, verbatim", who: "Memory, in OneLake", title: "Keeps it as a reminder",
          text: "The message is stored word for word as a pending reminder, due from 30 minutes later so it is said next time, not in the same chat. It sits in the small prompt file every request already reads.",
          callouts: [{ node: "memory", text: "reminder, due next time", tone: "good", at: 300 }], source: "src/memory/memory-actions.ts; ADR-007" },
        reply("次回、MP-1518の在庫確認をリマインドします。", "Copilot confirms in the user's language."),
        { route: ["user", "copilot", "flow", "api", "memory"], carry: "おはよう！", who: "The next day", title: "The user comes back",
          text: "Any message will do, a greeting included: the memory read runs on every route, and finds the reminder due.",
          bubble: { node: "user", text: "おはよう！", lang: "ja" }, source: "src/call-tool-service.ts" },
        { route: ["memory", "api", "flow", "copilot", "user"], carry: "mention", who: "Copilot agent", title: "Says the reminder once",
          text: `The response carries it as ${mono("mention")}, and Copilot starts its reply with it. Afterwards the API removes it from memory, so it is said once.`,
          bubble: { node: "user", text: "おはようございます。リマインド：MP-1518の在庫確認", lang: "ja", reply: true }, source: "src/memory/memory-actions.ts; copilot/agent-instructions.md" },
      ] },
    ],
  };

  // ---------- Chapter 3: how it is secured ----------
  // Layers 0 to 4 follow the UDW Agent Security Architecture deck; layer 5 is
  // what the agentic design adds.
  const secured = {
    id: "security", label: "Security view", summary: "Each control where it applies, layer by layer",
    nodes: { ...infraNodes, vault: { who: "Key Vault", name: "m3kvdwhsp1", small: true, icon: "lock", col: 2, row: 2 } },
    edges: [...infraEdges, ["api", "vault", sideVia]],
    zones: infraZones,
    idle: { title: "Press play to walk the layers", text: "Five layers from sign-in to the agent, then encryption and the threats each control answers." },
    paths: [{ id: "main", label: "Security", scenes: [
      { route: ["teams", "agent", "flow"], carry: "signed-in user", who: "Layer 0 · Entra ID login", title: "The user proves who they are",
        text: "Users sign in to Teams with Entra ID, where MFA, Conditional Access and device compliance policies apply. The flow then calls the API with an Entra access token for Azure Management and the user's email.",
        callouts: [{ node: "agent", text: "MFA + Conditional Access", tone: "good", at: 300 }, { node: "flow", text: "Entra token + email", tone: "accent", at: 900 }],
        source: "UDW Agent Security Architecture deck, slide 4; APIM inbound policy" },
      { route: ["flow", "apim"], carry: "key + token", who: "Layer 1 · APIM gateway", title: "The gateway checks the key and the token",
        text: "APIM requires the APAC Buddy subscription key, then validates the token against the tenant's OpenID configuration: signature, expiry, an Azure Management audience and the tenant's issuer. Anything else gets 401 before it reaches the service.",
        callouts: [{ node: "apim", text: "subscription key", tone: "good", slot: 0, at: 300 }, { node: "apim", text: "validate-jwt", tone: "good", slot: 1, at: 900 }],
        source: "APIM inbound policy (validate-jwt); deck slide 4" },
      { route: ["apim", "api", "entra"], carry: "token", who: "Layer 2 · token re-validation", title: "The service checks the token again",
        text: "The Container App re-validates the token on its own, against the tenant's published signing keys: signature, issuer, audience and expiry. A failed check gets 401 and is recorded.",
        callouts: [{ node: "entra", text: "tenant signing keys", tone: "good", at: 300 }], source: "src/auth/authorizer.ts; deploy/production.yml" },
      { route: ["api"], who: "Layer 2 · token re-validation", title: "Only trusted callers may state the user",
        text: `The API accepts the email in the body only from the callers listed in ${mono("TRUSTED_CALLER_APP_IDS")}. Every interaction records whether the user came from the token or from the caller, and which application stated it.`,
        callouts: [{ node: "api", text: "identity source recorded", tone: "good", at: 300 }], source: "src/auth/caller-trust.ts; docs/COPILOT-INTEGRATION.md" },
      { route: ["api", "fabric"], carry: "email", who: "Layer 3 · persona authorization", title: "Roles come from the employee table",
        text: `Country, department and job title are matched against ${mono("config/roles.json")}. Every matching role applies and their scopes combine. No row or no matching rule: 403, recorded with the user's identity.`,
        callouts: [{ node: "fabric", text: "no role, no access", tone: "good", at: 300 }], source: "docs/decisions/ADR-004; config/roles.json; deck slide 7" },
      { route: ["api", "memory"], carry: "verified user", who: "Layer 3 · persona authorization", title: "Each user's memory is their own",
        text: "The memory folder is derived only from the verified identity, never from the message or the model, so no request can reach another person's folder. Memory never goes to the router, and holds no amounts or percentages. Every change is recorded in the console.",
        callouts: [{ node: "memory", text: "folder from identity", tone: "good", at: 300 }], source: "src/memory/user-memory.ts; ADR-007" },
      { route: ["api", "fabric"], carry: "fixed SQL", who: "Layer 4 · data controls", title: "Fixed queries, enforced in the capability",
        text: "Each capability checks the user's scopes itself. Queries are fixed and parameterised: at most 20 codes per call, 50 rows per query, a 30 s timeout. No cost column is selected, and free-form SQL is not offered.",
        callouts: [{ node: "fabric", text: "parameterised", tone: "good", slot: 0, at: 300 }, { node: "fabric", text: "scoped service principal", tone: "good", slot: 1, at: 900 }],
        source: "docs/decisions/ADR-004; deck slide 5" },
      { route: ["api", "vault"], carry: "secrets at deploy", who: "Layer 4 · secret management", title: "Secrets stay out of code and prompts",
        text: "The pipeline reads secrets from Key Vault and sets them as Container App secret references. Nothing secret is in the repository, and no credential is passed to a model: the service runs every query itself.",
        callouts: [{ node: "vault", text: "secretref only", tone: "good", at: 300 }], source: "azure-pipelines.yml; deploy/production.yml" },
      { route: ["api", "decision"], carry: "allowed capabilities", who: "Layer 5 · agent containment", title: "The router only sees what the user may use",
        text: "Decision-1 is offered only the capabilities and playbooks the user's scopes allow. Its answer is a label: it cannot run anything, and the API checks the choice again before running it.",
        callouts: [{ node: "decision", text: "scope-filtered", tone: "good", at: 300 }], source: "src/call-tool-service.ts; ADR-006" },
      { route: ["api", "codex", "mcp"], carry: "one-time token", who: "Layer 5 · agent containment", title: "Codex is boxed in",
        text: "Codex runs with a read-only sandbox, no network, web search off and no inherited environment. Its only tools are on the loopback MCP host, opened by a one-time token tied to this request's scopes, which the model never sees. Scopes are checked again when each tool runs.",
        callouts: [{ node: "codex", text: "read-only, no network", tone: "good", at: 300 }, { node: "mcp", text: "one-time token", tone: "good", at: 900 }],
        source: "src/agent/codex-reasoner.ts; ADR-004" },
      { route: ["mcp", "codex", "api", "apim"], carry: "TLS", who: "Encryption", title: "Encrypted in transit and at rest",
        text: "Every hop uses HTTPS or TLS 1.2 and above, including SQL to the warehouse, and the service refuses to start in production with TLS verification turned off. At rest, Azure encrypts storage with AES-256 and the Fabric warehouse with transparent data encryption.",
        callouts: [{ node: "api", text: "TLS on every hop", tone: "good", at: 300 }, { node: "fabric", text: "encrypted at rest", tone: "good", at: 900 }],
        source: "deck slide 6; src/capabilities/fabric/fabric-sql.ts; src/main.ts" },
      { route: ["api"], who: "Threat model", title: "Each threat meets its own control",
        text: "An attacker has to defeat several independent mechanisms, not one: the gateway, the token checks, the persona rules, least-privilege data access, the vault, and the agent's sandbox.",
        callouts: [
          { node: "apim", text: "unauthorized access: 401", tone: "good", at: 300 },
          { node: "entra", text: "token forgery: signatures", tone: "good", at: 700 },
          { node: "api", text: "wrong persona: 403", tone: "good", at: 1100 },
          { node: "vault", text: "credential leaks: Key Vault", tone: "good", at: 1500 },
          { node: "fabric", text: "lateral movement: fixed SQL", tone: "good", at: 1900 },
          { node: "codex", text: "prompt injection: sandbox", tone: "good", at: 2300 },
        ],
        source: "deck slide 9; ADR-004" },
    ] }],
  };

  window.STORY = {
    id: "apac-buddy",
    title: "How APAC Buddy Works",
    eyebrow: "APAC Buddy",
    heading: "How APAC Buddy works",
    lead: "One question, three views: the logic that decides the answer, the infrastructure it travels through, and the security at every hop. Click any box to jump to its step.",
    intro: { title: "Follow one question through APAC Buddy", text: "Logic, infrastructure and security views. Space to pause, arrow keys to step, click a box to jump to it." },
    chapters: [answer, infra, secured],
  };
})();
