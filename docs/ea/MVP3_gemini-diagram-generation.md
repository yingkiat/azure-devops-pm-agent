# EA MVP3: Gemini Diagram Generation

## 🎯 Overview

This MVP delivers **AI-powered visual diagram generation** for Enterprise Architecture using **Gemini Flash 2.5**. The system transforms EA discovery data into professional visual diagrams suitable for executive presentations.

## ✅ Current Capabilities

### **Visual Diagram Generation**
- **7 Diagram Types**: Overview, Business Process, Application, Data, Infrastructure, Security, Integration
- **High-Quality Images**: PNG output (1MB+ professional diagrams)
- **Executive Ready**: Professional formatting with boxes, arrows, labels, and legends
- **Real-time Generation**: Direct API integration with Gemini Flash 2.5

### **Corporate Environment Support**
- **CrowdStrike SSL Bypass**: Advanced SSL workarounds for corporate environments
- **Windows Compatible**: Full Windows 11 support with proper file handling
- **Encoding Safety**: UTF-8 support with fallback error handling

### **Integration Architecture**
- **CLI Integration**: Seamless integration with existing EA discovery system
- **File Management**: Automatic output directory creation and timestamp naming
- **Dual Output**: Both visual diagrams (PNG) and text descriptions (TXT)

## 🚀 Usage Examples

### **Basic Diagram Generation**
```bash
# Generate overview diagram from EA analysis
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type overview

# Generate application architecture diagram
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type application

# Generate business process diagram with custom output
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type business-process --output my_diagram.txt
```

### **List Available Options**
```bash
# Show all supported diagram types
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --list
```

### **Complete Workflow Example**
```bash
# 1. Discover EA objects from system description
python -m src.cli.main ea-discover system_description.txt

# 2. Generate visual diagrams from discovery
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type overview
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type application
python -m src.cli.main ea-diagrams ea_outputs/ea_analysis.json --type data
```

## 📊 Supported Diagram Types

| Type | Description | Use Case |
|------|-------------|----------|
| **overview** | High-level EA overview showing all major components | Executive presentations |
| **business-process** | Detailed business process flows and workflows | Process documentation |
| **application** | Application architecture with systems and interfaces | Technical architecture |
| **data** | Data architecture with entities and flows | Data governance |
| **infrastructure** | Infrastructure deployment and network architecture | Operations planning |
| **security** | Security controls, threats, and compliance boundaries | Security reviews |
| **integration** | System integration patterns and data exchanges | Integration planning |

## 🔧 Technical Architecture

### **Core Components**

#### **1. Gemini Client (`src/utils/gemini_client.py`)**
- **SSL Bypass**: Advanced CrowdStrike-compatible SSL workarounds
- **Image Handling**: Automatic PNG extraction and saving
- **Error Recovery**: Comprehensive error handling with debug output

#### **2. EA Diagram Generator (`src/ea/ea_diagrams.py`)**
- **Prompt Engineering**: Specialized prompts for each diagram type
- **File Management**: Automatic directory creation and naming
- **Output Processing**: Dual text/image output handling

#### **3. CLI Integration (`src/cli/main.py`)**
- **Command Interface**: `ea-diagrams` command with full options
- **Error Handling**: User-friendly error messages and guidance
- **Help System**: Built-in documentation and examples

### **Data Flow**
```
EA Discovery Data (JSON)
         ↓
Diagram Type Classification
         ↓
Specialized Prompt Generation
         ↓
Gemini Flash 2.5 API Call
         ↓
Image + Text Response Processing
         ↓
PNG Image + TXT Description Files
```

## 🛡️ Corporate Environment Setup

### **SSL Configuration for CrowdStrike**
The system includes advanced SSL bypasses for corporate environments:

```bash
# Add to .env file (if needed)
GEMINI_DISABLE_SSL_VERIFY=true
```

### **Required Dependencies**
```bash
pip install google-genai>=1.39.1
pip install httpx>=0.25.0
pip install certifi>=2023.0.0
```

### **Environment Variables**
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
GEMINI_MODEL=gemini-2.5-flash-image-preview
```

## 📁 Output Structure

### **Generated Files**
```
ea_diagrams/
├── ea-overview-20250929-135610.txt        # Text description
├── ea-image-20250929-135610.png           # Visual diagram
├── ea-application-20250929-140030.txt     # Application diagram text
├── ea-image-20250929-140030.png           # Application diagram image
└── ...
```

### **File Naming Convention**
- **Text Files**: `ea-{type}-{timestamp}.txt`
- **Image Files**: `ea-image-{timestamp}.{ext}`
- **Timestamp Format**: `YYYYMMDD-HHMMSS`

## 🧪 Testing & Validation

### **Test Suite**
```bash
# Run comprehensive test suite
python test_gemini_diagrams.py
```

**Test Coverage:**
- ✅ Diagram type listing
- ✅ EA data loading
- ✅ Gemini client initialization
- ✅ End-to-end diagram generation
- ✅ SSL bypass validation
- ✅ File encoding handling

### **Success Metrics**
- **Image Generation**: 1MB+ PNG files successfully created
- **SSL Bypass**: Works in CrowdStrike corporate environments
- **Error Handling**: Graceful handling of encoding and network issues
- **Integration**: Seamless CLI workflow with existing EA system

## 🚀 Next Phase Enhancements

### **Planned Capabilities**
1. **Batch Generation**: Generate all diagram types in one command
2. **Custom Templates**: User-defined diagram templates and styling
3. **Export Formats**: SVG, PDF, and PowerPoint export options
4. **Interactive Diagrams**: Clickable diagrams with drill-down capability
5. **Version Control**: Diagram versioning and change tracking

### **Integration Roadmap**
1. **EA Matrix Integration**: Direct integration with EA matrix data
2. **Wiki Publishing**: Automatic wiki page creation with diagrams
3. **Report Generation**: Executive reports with embedded diagrams
4. **API Endpoints**: REST API for diagram generation services

## 📚 Additional Resources

- **EA Discovery System**: See `docs/ARCHITECTURE.md` for EA discovery workflow
- **Configuration Guide**: See the [root README](../../README.md#setup) for current environment setup
- **Troubleshooting**: See SSL bypass guide in `src/utils/gemini_client.py`

---

## 🎉 MVP3 Achievement Summary

**Delivered Capabilities:**
- ✅ **7 Professional Diagram Types** ready for executive use
- ✅ **CrowdStrike SSL Bypass** working in corporate environments
- ✅ **High-Quality Visual Output** (1MB+ PNG diagrams)
- ✅ **Complete CLI Integration** with existing EA workflow
- ✅ **Comprehensive Error Handling** with UTF-8 encoding support
- ✅ **Production Ready** with full test coverage

**Business Value:**
- **Executive Presentations**: Professional diagrams ready for C-level meetings
- **Documentation Automation**: Automated visual documentation from EA data
- **Corporate Compatibility**: Works in restricted enterprise environments
- **Workflow Integration**: Seamless integration with existing EA processes

MVP3 successfully transforms text-based EA discovery into executive-ready visual presentations using cutting-edge AI capabilities.