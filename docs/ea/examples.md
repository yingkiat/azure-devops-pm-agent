# EA Discovery Examples

This document provides practical examples of using the EA discovery system with different types of system descriptions.

## Example 1: Simple Integration System

### Input: CRM-ERP Integration

```text
CRM Purchase Order Automation System

We need a system that integrates our CRM with Microsoft Document Intelligence to automatically process purchase orders and create them in our ERP system.

The workflow is:
1. Sales team uploads PO documents (PDFs, images) through CRM interface
2. System calls Microsoft Doc AI service to extract key data (vendor, amounts, line items, dates)
3. Extracted data gets validated and mapped to ERP fields
4. System automatically creates corresponding PO record in ERP
5. Status updates flow back to CRM for sales team visibility

Key integration points:
- CRM system (Salesforce or similar)
- Microsoft Document Intelligence API
- ERP system (SAP, Oracle, or similar)
- File storage for uploaded documents
- Notification system for status updates

Users include sales reps, procurement team, and finance for approval workflows.

System needs to handle document processing errors, data validation failures, and ERP connectivity issues gracefully.
```

### Usage

```bash
python -m src.cli.main ea-discover examples/crm-erp-integration.txt --summary
```

### Expected Output

The system will extract:
- **Business Layer**: PO automation process, document processing capability, sales/procurement stakeholders
- **Application Layer**: CRM, Microsoft Doc AI, ERP systems with their interfaces
- **Data Layer**: Purchase order entity, vendor data, document storage
- **Infrastructure Layer**: File storage, API servers, network connectivity
- **Security Layer**: Data validation, error handling, access controls

## Example 2: E-commerce Platform

### Input: Online Store System

```text
E-commerce Platform

Multi-tenant e-commerce platform supporting multiple brands and storefronts.

Core capabilities:
- Product catalog management with rich media
- Shopping cart and checkout with multiple payment methods
- Order management and fulfillment tracking
- Customer accounts and loyalty programs
- Inventory management across warehouses
- Analytics and reporting for merchants

Technical stack:
- Frontend: React/Next.js storefront applications
- Backend: Node.js microservices architecture
- Database: PostgreSQL for transactions, Redis for caching
- Search: Elasticsearch for product discovery
- Payments: Stripe, PayPal, Apple Pay integration
- CDN: CloudFront for static assets and performance

Users:
- Customers browsing and purchasing
- Merchants managing their stores
- Platform administrators
- Customer service representatives

Requirements:
- Support 100k concurrent users during peak traffic
- 99.95% uptime SLA
- PCI DSS compliance for payment processing
- GDPR compliance for EU customers
- Real-time inventory synchronization
```

### Usage

```bash
python -m src.cli.main ea-discover examples/ecommerce-platform.txt --output ecommerce-ea.json
```

### Expected Analysis Focus

- **Business Layer**: Multi-tenant business model, merchant onboarding process, customer journey
- **Application Layer**: Microservices architecture, payment integrations, search functionality
- **Data Layer**: Product catalog, order transactions, customer profiles, inventory data
- **Infrastructure Layer**: CDN, caching layer, database clustering, auto-scaling
- **Security Layer**: PCI compliance, GDPR controls, authentication, payment security

## Example 3: Healthcare Management System

### Input: Patient Care Platform

```text
Healthcare Patient Management System

Comprehensive platform for managing patient care across multiple clinic locations.

Primary functions:
- Patient registration and demographic management
- Appointment scheduling with provider availability
- Electronic health records (EHR) with FHIR compliance
- Prescription management and pharmacy integration
- Billing and insurance claim processing
- Telehealth video consultations
- Lab results integration and reporting

System integrations:
- HL7 interfaces with hospital systems
- Insurance verification APIs
- Pharmacy networks for prescription fulfillment
- Lab systems for test ordering and results
- Payment processors for billing

Compliance requirements:
- HIPAA for patient data protection
- SOC 2 Type II for data handling
- FHIR R4 for health data interoperability
- State medical board regulations

Users:
- Healthcare providers (doctors, nurses, specialists)
- Administrative staff (schedulers, billing)
- Patients (portal access, telehealth)
- IT administrators and compliance officers

Performance requirements:
- Sub-2 second response for patient lookups
- 99.9% uptime during business hours
- Real-time appointment availability
- Secure video streaming for telehealth
```

### Usage

```bash
python -m src.cli.main ea-discover examples/healthcare-system.txt --summary
```

### Expected Comprehensive Analysis

- **Business Layer**: Patient care processes, appointment workflow, billing cycle, compliance management
- **Application Layer**: EHR system, scheduling app, telehealth platform, billing system, portal applications
- **Data Layer**: Patient records, appointment data, prescription information, billing transactions, audit logs
- **Infrastructure Layer**: HIPAA-compliant hosting, video streaming infrastructure, database security, backup systems
- **Security Layer**: HIPAA controls, access logging, encryption standards, user authentication, audit trails

## Example 4: IoT Manufacturing System

### Input: Smart Factory Platform

```text
IoT Manufacturing Analytics Platform

Real-time monitoring and optimization system for manufacturing operations.

Core components:
- IoT sensor network collecting machine data
- Edge computing for real-time processing
- Machine learning for predictive maintenance
- Dashboard for operations monitoring
- Alert system for anomaly detection
- Integration with existing MES/ERP systems

Data sources:
- Temperature, vibration, pressure sensors
- Production line cameras and vision systems
- Quality control measurements
- Energy consumption monitors
- Worker safety sensors

Analytics capabilities:
- Real-time production monitoring
- Predictive maintenance scheduling
- Quality trend analysis
- Energy optimization recommendations
- Safety incident prevention

Technology stack:
- Edge: Industrial PCs running containerized workloads
- Cloud: Azure IoT Hub, Stream Analytics, Machine Learning
- Storage: Time-series database for sensor data
- Visualization: Power BI dashboards and mobile apps

Stakeholders:
- Plant managers and supervisors
- Maintenance technicians
- Quality engineers
- Safety officers
- IT operations team
```

### Usage

```bash
python -m src.cli.main ea-discover examples/iot-manufacturing.txt --output manufacturing-ea.json
```

### Expected IoT-Focused Analysis

- **Business Layer**: Manufacturing optimization process, maintenance workflows, quality assurance
- **Application Layer**: IoT platform, analytics engine, dashboard applications, mobile apps
- **Data Layer**: Sensor telemetry, machine states, production metrics, historical trends
- **Infrastructure Layer**: Edge computing, cloud services, network connectivity, industrial hardware
- **Security Layer**: IoT device security, data encryption, network segmentation, operational technology protection

## Usage Patterns

### Batch Analysis

Process multiple system descriptions:

```bash
# Analyze all systems in a project
for file in systems/*.txt; do
    python -m src.cli.main ea-discover "$file" --output "analysis/$(basename "$file" .txt)-ea.json"
done
```

### Comparative Analysis

Generate multiple outputs for comparison:

```bash
# Current state
python -m src.cli.main ea-discover current-system.txt --output current-ea.json

# Future state
python -m src.cli.main ea-discover future-system.txt --output future-ea.json

# Compare outputs to identify transformation requirements
```

### Integration Workflows

```bash
# Discover EA objects
python -m src.cli.main ea-discover system.txt --output ea-objects.json

# Future: Generate diagrams from EA objects
# python -m src.cli.main ea-diagrams ea-objects.json --type business-process

# Future: Create roadmap from analysis
# python -m src.cli.main ea-roadmap ea-objects.json --strategy modernization
```

## Tips for Better Results

### Writing Effective System Descriptions

1. **Include Context**: Explain the business purpose and value
2. **List Stakeholders**: Identify who uses the system and how
3. **Describe Workflows**: Explain key business processes
4. **Technical Details**: Include architecture components and technologies
5. **Requirements**: Mention performance, security, and compliance needs
6. **Integrations**: Specify external systems and APIs

### Common Pitfalls to Avoid

- **Too High-Level**: "CRM system" vs "Salesforce-based customer management with custom workflows"
- **Missing Context**: Technical components without business purpose
- **No Stakeholders**: Systems don't exist in isolation
- **Vague Requirements**: "High performance" vs "Support 10k concurrent users"

### Iterative Improvement

1. Start with basic description
2. Run EA discovery
3. Review gaps in analysis
4. Add missing detail to description
5. Re-analyze for comprehensive coverage

---

For more examples and advanced usage, see the main EA documentation in `docs/ea/README.md`.