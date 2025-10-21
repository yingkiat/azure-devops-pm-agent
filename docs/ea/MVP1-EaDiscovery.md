# MVP1: EA Discovery - App-Capability Matrix

## **Overview**

Transform the existing EA discovery engine from JSON output to a live tabular matrix that supports CRUD operations through natural language input. The matrix becomes a queryable dataset for capability gap analysis, sunset risk assessment, and portfolio optimization.

## **Technical Architecture**

### **Core Components**

```
Natural Language Input
         ↓
EA Discovery Engine (enhanced)
         ↓
Shared Storage Layer → App-Capability Matrix (CSV/DB)
         ↓
Data Exploration & Analysis
```

### **1. Enhanced EA Discovery Engine**

**File**: `src/ea/ea_discovery.py`

**Current**: Outputs JSON with EA objects
**Enhanced**: Maintains live App-Capability matrix with CRUD operations

```python
def discover_ea_objects(text_input: str, schema_config: str = "data/ea/ea_schema.yaml"):
    # 1. Schema Ingestion - AI understands current data structure
    storage = get_storage("csv", "ea_matrix", schema_config)
    schema = load_schema(schema_config)
    existing_data = storage.load_data()

    # 2. AI Processing - sophisticated analysis with context
    ai_response = call_ai_with_prompt(
        prompt_file="prompts/ea/ea_discovery.md",
        variables={
            "text_input": text_input,
            "current_schema": schema,
            "existing_data_sample": existing_data.head().to_string(),
            "full_data_context": generate_data_context(existing_data)
        }
    )

    # 3. Apply Changes - AI determines INSERT/UPDATE/DELETE operations
    storage.upsert_rows(ai_response.changes.inserts)
    storage.upsert_rows(ai_response.changes.updates)
    storage.delete_rows(ai_response.changes.deletes)

    return ai_response  # includes discovery + exploration insights
```

### **2. Shared Storage Abstraction**

**Location**: `src/shared/storage/`

**Purpose**: Cross-persona storage layer that both PM and EA agents can use

```
src/shared/storage/
├── __init__.py              # Storage factory
├── base_storage.py          # Abstract interface
├── csv_storage.py           # CSV implementation (MVP)
├── sqlite_storage.py        # SQLite implementation (future)
└── azure_storage.py         # Azure SQL implementation (future)
```

**Key Features**:
- **Modular Design**: Easy migration from CSV → SQLite → Azure SQL
- **Schema Awareness**: Understands data relationships and validation rules
- **CRUD Operations**: INSERT, UPDATE, DELETE with conditions
- **Cross-Persona**: PM agent can also use for work item tracking, etc.

### **3. App-Capability Matrix Schema**

**File**: `data/ea/ea_matrix.csv`

```csv
app_name,capability,domain,maturity,lifecycle_status,remaining_years,strategic_importance,last_updated,source_text_hash
ERP System,Financial Reporting,Finance,5,Strategic,8,Critical,2024-01-15,abc123...
CRM System,Customer Management,Sales,4,Maintain,3,Critical,2024-01-15,def456...
Legacy HR,Employee Management,HR,2,Sunset,1,Important,2024-01-15,ghi789...
```

**Schema Benefits**:
- **Visualization-Ready**: Direct pivot to heatmaps, matrices, dashboards
- **Business Questions**: "What's at sunset risk?", "Where are capability gaps?"
- **Denormalized**: No complex joins, perfect for analytics
- **Extensible**: Easy to add new columns without breaking existing tools

## **AI-Powered Intelligence**

### **Enhanced Prompt System**

**File**: `prompts/ea/ea_discovery.md`

**Capabilities**:
1. **Discovery**: Extract EA objects from natural language
2. **Matrix CRUD**: Determine INSERT/UPDATE/DELETE operations needed
3. **Data Exploration**: Gap analysis, sunset risks, maturity trends, overlaps
4. **Recommendations**: Actionable insights based on discovered patterns

**Sample AI Output**:
```
=== EA DISCOVERY RESULTS ===

📋 CHANGES APPLIED:
✅ Added: Customer Portal → Account Management (maturity: 3)
✅ Added: Customer Portal → Billing Support (maturity: 3)
⚠️  Updated: Legacy Call Center → lifecycle: Sunset

📊 DATA EXPLORATION:
🔍 Capability Overlap Detected:
   Account Management: Customer Portal (new) + Legacy Call Center (sunset)
   → Recommendation: Define migration timeline

📉 Sunset Risk Analysis:
   Legacy Call Center supports 3 capabilities, retirement impacts:
   - Account Management: covered by Customer Portal ✅
   - Phone Support: NO REPLACEMENT FOUND ⚠️
   - Escalation Management: NO REPLACEMENT FOUND ⚠️

📈 Maturity Trends:
   Customer Experience domain: 2.1 → 2.8 average maturity (+33%)
```

### **Schema-Driven Flexibility**

**File**: `data/ea/ea_schema.yaml`

```yaml
matrix_schema:
  columns:
    - name: app_name
      type: string
      ai_extraction: "application or system name"
    - name: capability
      type: string
      ai_extraction: "business capability or function supported"
    - name: maturity
      type: integer
      range: [1,5]
      ai_assessment: "technical and business maturity based on description"

exploration_templates:
  - "capability gap analysis"
  - "sunset risk assessment"
  - "maturity trend analysis"
  - "overlap detection"
```

## **User Experience**

### **🤖 AI-Powered Persona Detection Interface**

**✅ BREAKTHROUGH: Automatic EA/PM Routing**
The system now automatically detects whether requests are EA-focused or PM-focused and routes them to the appropriate specialist.

```bash
# EA Discovery via AI Chat (Recommended - Auto-detects EA persona)
python -m src.cli.ai_cli ask "Analyze the architecture described in our new customer portal that handles account management and billing inquiries"
# 🏗️ EA Mode (confidence: 0.95) - Automatically routes to EA specialist

# Interactive EA Chat
python -m src.cli.ai_cli chat
# > "We're implementing a new customer portal..."
# 🏗️ EA Mode (confidence: 0.95)
# > "The CRM system was upgraded and now supports advanced analytics"
# 🏗️ EA Mode (confidence: 0.88)
# > "Decommissioning the old HR system next quarter"
# 🏗️ EA Mode (confidence: 0.82)
```

### **🎯 Persona Detection Examples**

```bash
# EA-focused requests (Auto-routed to EA persona)
python -m src.cli.ai_cli ask "analyze the architecture described in examples/system_description.txt"
python -m src.cli.ai_cli ask "discover EA objects from this system design"
python -m src.cli.ai_cli ask "what's our enterprise architecture capability matrix?"

# PM-focused requests (Auto-routed to PM persona)
python -m src.cli.ai_cli ask "show me critical bugs"
python -m src.cli.ai_cli ask "what's our sprint progress?"
python -m src.cli.ai_cli ask "create an epic for the data platform"
```

### **Legacy Direct Commands (Still Available)**

```bash
# Direct EA discovery (bypasses persona detection)
python -m src.cli.main ea-discover "We're implementing a new customer portal..."
python -m src.cli.main ea-discover "Decommissioning the old HR system next quarter"
```

### **Data Exploration (Separate Tools)**

```bash
# Analysis is separate - use any tool on the CSV
python analysis/capability_heatmap.py
python analysis/sunset_risk_report.py

# Or simple pandas exploration
python -c "import pandas as pd; df=pd.read_csv('data/ea/ea_matrix.csv'); print(df.groupby('domain').maturity.mean())"
```

## **Configuration & Storage**

### **Environment-Driven Storage**

```bash
# Current: CSV in data/ea/
EA_STORAGE_TYPE=csv python -m src.cli.main ea-discover "..."

# Future: SQLite migration
EA_STORAGE_TYPE=sqlite python -m src.cli.main ea-discover "..."

# Future: Azure SQL
EA_STORAGE_TYPE=azure AZURE_SQL_CONNECTION="..." python -m src.cli.main ea-discover "..."
```

### **File Structure**

```
data/ea/                 # Gitignored data directory
├── ea_matrix.csv        # Live matrix data
├── ea_schema.yaml       # Schema definition
└── backups/            # Automatic backups
    ├── ea_matrix_20240123.csv
    └── ea_matrix_20240124.csv

src/shared/storage/     # Storage implementations
├── base_storage.py     # Abstract interface
├── csv_storage.py      # CSV implementation
└── __init__.py         # Storage factory

prompts/ea/
└── ea_discovery.md     # Enhanced AI prompt for matrix operations
```

## **Benefits & Value Proposition**

### **🚀 BREAKTHROUGH: AI-Powered Persona Detection**
- **Automatic Routing**: "analyze architecture" → EA specialist, "show bugs" → PM specialist
- **Natural Language**: No need to remember specific commands or persona switches
- **Confidence Indicators**: Transparent routing decisions with confidence scores
- **Context Awareness**: Each persona specializes in their domain expertise

### **Immediate Value**
- **Live Documentation**: Matrix stays current through natural language updates
- **Intelligent Routing**: Requests automatically go to the right specialist
- **Visual Analytics**: Direct pivot to heatmaps showing capability maturity vs strategic importance
- **Risk Assessment**: Automatic detection of sunset systems supporting critical capabilities
- **Gap Analysis**: Identify capabilities with no supporting applications

### **Future Growth**
- **Multi-Persona Expansion**: Easy to add new specialist personas (Security, Data, etc.)
- **Cross-Persona Integration**: PM agent can use same storage for work item matrices
- **Database Migration**: Seamless upgrade from CSV → SQLite → Azure SQL
- **Advanced Analytics**: Machine learning on historical matrix changes
- **Portfolio Optimization**: ROI analysis, rationalization recommendations

## **Implementation Phases**

### **Phase 1 (Week 1): Storage Layer**
- [ ] Create `src/shared/storage/` abstraction layer
- [ ] Implement CSV storage with CRUD operations
- [ ] Add configuration factory for storage types

### **Phase 2 (Week 2): Enhanced Discovery**
- [ ] Enhance `ea_discovery.py` to use shared storage
- [ ] Update AI prompt for matrix-aware analysis
- [ ] Add schema validation and data context generation

### **Phase 3 (Week 3): Integration & Testing**
- [ ] Test natural language CRUD operations
- [ ] Validate AI-generated matrix updates
- [ ] Create sample analysis scripts

### **Phase 4 (Week 4): Documentation & Examples**
- [ ] Document usage patterns and examples
- [ ] Create capability heatmap visualization
- [ ] Test migration scenarios (CSV → SQLite)

## **Success Criteria**

1. **Functional**: Natural language input correctly updates matrix (90% accuracy)
2. **Analytical**: Matrix enables capability gap and sunset risk analysis
3. **Extensible**: Storage layer supports future PM agent integration
4. **Maintainable**: Schema-driven approach allows easy column additions
5. **Migration-Ready**: Clear path from CSV to database storage

---

## **Manual Testing Guide**

### **Prerequisites**

Ensure dependencies are installed:
```bash
pip install -e .
```

### **Test 1: Basic CLI Functionality**

**Command:**
```bash
python -m src.cli.main ea-discover --help
```

**Expected Output:**
- Shows help text for ea-discover command
- Lists available options (--output, --summary, --matrix, --storage)

### **Test 2: AI Persona Detection Test**

**Primary AI Interface (Recommended):**
```bash
# Test EA persona detection
python -m src.cli.ai_cli ask "Analyze the architecture of our new CRM system for customer management"
# Expected: 🏗️ EA Mode (confidence: 0.90+)

# Test PM persona detection
python -m src.cli.ai_cli ask "Show me critical bugs in the CRM system"
# Expected: 🤖 PM Mode (confidence: 0.90+)

# Interactive chat mode
python -m src.cli.ai_cli chat
# Then type: "We have a new CRM system - analyze its architecture"
# Expected: 🏗️ EA Mode (confidence: 0.85+)
```

**Legacy Direct Command (Still Available):**
```bash
python -m src.cli.main ea-discover "We have a new CRM system for customer management"
```

**Expected Behavior:**
- Shows persona routing: `🏗️ EA Mode (confidence: 0.XX)` or `🤖 PM Mode (confidence: 0.XX)`
- Shows "🏗️ [EA] Processing request: ..." for EA requests
- Creates `data/ea/` directory if it doesn't exist
- May show AI authentication errors (expected without real API keys)
- Should not crash and should route correctly based on content

### **Test 3: Check Generated Files**

**Commands:**
```bash
# Check if data directory was created
ls -la data/ea/

# Check if matrix file exists
cat data/ea/ea_matrix.csv

# Check schema file
cat data/ea/ea_schema.yaml
```

**Expected Files:**
- `data/ea/ea_matrix.csv` (may be empty without AI)
- `data/ea/ea_schema.yaml` (should contain schema definition)
- `data/ea/.gitkeep` (ensures directory is tracked)

### **Test 4: Different CLI Options**

**No-Matrix Mode (Legacy):**
```bash
python -m src.cli.main ea-discover "Test system" --no-matrix --summary
```

**Storage Type Options:**
```bash
python -m src.cli.main ea-discover "Test system" --storage csv
```

**JSON Output:**
```bash
python -m src.cli.main ea-discover "Test system" --output results.json
```

### **Test 5: File Input & Architecture Analysis**

**Create test file:**
```bash
echo "Our new e-commerce platform handles product catalog and order processing. It uses modern microservices architecture with React frontend and Node.js backend." > test_system.txt
```

**AI Architecture Analysis (Recommended):**
```bash
# File content analysis with persona detection
python -m src.cli.ai_cli ask "Analyze the architecture described in test_system.txt"
# Expected: 🏗️ EA Mode (confidence: 0.90+)

python -m src.cli.ai_cli ask "Analyze the architecture described in examples/system_description.txt"
# Expected: 🏗️ EA Mode (confidence: 0.95+)

# Read file content and pass to AI chat
python -m src.cli.ai_cli ask "$(cat test_system.txt)"
# Expected: 🏗️ EA Mode (confidence: 0.85+)
```

**Legacy Direct File Input:**
```bash
python -m src.cli.main ea-discover test_system.txt
python -m src.cli.main ea-discover examples/system_description.txt
```

**Interactive Chat with Architecture Discussion:**
```bash
python -m src.cli.ai_cli chat
# Then type: "Analyze the architecture in test_system.txt - it's an e-commerce platform with microservices"
# Expected: 🏗️ EA Mode (confidence: 0.88+)
```

### **Expected Issues & Solutions**

**Issue: Missing AI Configuration**
```
Error: OpenAI authentication failed
```
**Solution:** Expected without real API keys. Core logic still executes.

**Issue: Wrong Persona Detection**
```
🤖 PM Mode (confidence: 0.85) when expecting EA Mode
```
**Solution:** Use more explicit EA keywords:
- ✅ "analyze the architecture"
- ✅ "EA discovery"
- ✅ "enterprise architecture"
- ✅ "system architecture"
- ❌ "analyze the system" (may route to PM)

**Issue: Missing Dependencies**
```
ModuleNotFoundError: No module named 'yaml'
```
**Solution:** Install missing packages:
```bash
pip install PyYAML pandas
```

**Issue: Import Errors**
```
ImportError: attempted relative import beyond top-level package
```
**Solution:** Ensure proper Python path:
```bash
cd azure-devops-pm-agent
python -m src.cli.ai_cli ask "your request"
```

**Issue: Prompt File Missing**
```
FileNotFoundError: EA discovery prompt not found
```
**Solution:** Verify prompt files exist:
- `prompts/ea/ea_discovery.md`
- `prompts/ea/intent_classification.md`
- `prompts/ea/execution_planning.md`

### **Success Indicators**

✅ **CLI Command Executes:** No import errors or crashes
✅ **Directory Creation:** `data/ea/` directory created
✅ **File Generation:** Matrix CSV file created (may be empty)
✅ **Help System:** `--help` shows proper documentation
✅ **Option Parsing:** Different flags are recognized

### **With Real AI Configuration**

If you have Azure OpenAI credentials, create `.env`:
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

**Test with AI (Direct Command):**
```bash
python -m src.cli.main ea-discover "We're implementing a new customer portal that will handle account management and billing inquiries. This modern React-based application will replace our legacy call center system."
```

**Test with AI (Chat Interface):**
```bash
# Single question
python -m src.cli.ai_cli ask "We're implementing a new customer portal for account management and billing. It will replace our legacy call center system."

# Interactive conversation
python -m src.cli.ai_cli chat
# Then have a natural conversation:
# > "We're adding a new customer portal"
# > "It handles account management and billing"
# > "We're retiring the old call center system"
# > "Show me our EA matrix summary"
```

**Expected Output with AI:**
```
=== EA DISCOVERY RESULTS ===

📋 CHANGES APPLIED:
✅ Added: Customer Portal → Account Management (maturity: 4)
✅ Added: Customer Portal → Billing Support (maturity: 3)
⚠️  Updated: Legacy Call Center → lifecycle: Sunset

📊 DATA EXPLORATION:
🔍 Capability Overlap Detected:
   Account Management: Customer Portal (new) + Legacy Call Center (sunset)

EA MATRIX SUMMARY
==================
Total Records: 2
Applications: 2
Capabilities: 2
```

### **Manual Testing Checklist**

**Basic Functionality:**
- [ ] Main CLI help works (`python -m src.cli.main --help`)
- [ ] AI CLI help works (`python -m src.cli.ai_cli --help`)
- [ ] Legacy EA discover help works (`python -m src.cli.main ea-discover --help`)

**🎯 Persona Detection & Routing:**
- [ ] EA persona detection works (`ai_cli ask "analyze architecture..."`)
- [ ] PM persona detection works (`ai_cli ask "show critical bugs..."`)
- [ ] Confidence scores displayed correctly (0.80+ for clear requests)
- [ ] EA routing shows "🏗️ EA Mode" indicator
- [ ] PM routing shows "🤖 PM Mode" indicator

**🏗️ EA Discovery Interface:**
- [ ] AI EA discovery works (`ai_cli ask "analyze architecture described in file.txt"`)
- [ ] Interactive EA chat works (`ai_cli chat` then EA requests)
- [ ] File content analysis works (`ai_cli ask "$(cat file.txt)"`)
- [ ] Architecture keywords trigger EA persona correctly

**📂 Legacy Direct Commands:**
- [ ] Direct EA discovery works (`ea-discover "text"`)
- [ ] File input works (`ea-discover file.txt`)
- [ ] Storage options recognized (`--storage csv`)
- [ ] JSON output works (`--output results.json`)

**Data Management:**
- [ ] Data directory structure created (`data/ea/`)
- [ ] Matrix CSV file generated (`ea_matrix.csv`)
- [ ] Schema file exists and is valid (`ea_schema.yaml`)
- [ ] Error handling doesn't crash system

**🤖 With AI Configuration:**
- [ ] Persona detection routes correctly (EA vs PM)
- [ ] Proper matrix updates occur in EA mode
- [ ] EA exploration insights generated
- [ ] Multiple conversation rounds maintain persona context
- [ ] Matrix summary shows correct data
- [ ] EA analysis includes gap analysis and recommendations

---

This MVP transforms EA discovery from static JSON output to a live, queryable dataset that grows and evolves with natural language input, providing immediate analytical value while building the foundation for advanced portfolio management capabilities.