Appendix A 
Minimum Security Standards (MSS) for Networked Devices
1. MSS Requirements for Networked Devices
1.1. The minimum security standards are the basic rules or requirements for all networked
Information Technology devices within Medline. The goal is to reduce cybersecurity risks, ensure
compliance with regulatory requirements, and protect the confidentiality, integrity, and
availability of Medline Systems and Medline Data.
1.2. The standards are designed based on risk and are aligned with the function of the IT device, the
sensitivity of the data, and the importance to business operations. To simplify usage, networked
devices are categorized as low, moderate, or high, depending on their vulnerability to Medline.
Risk Level
Types of Networked Devices
Low End-user class systems – devices used by individuals to perform
daily tasks
Examples: Laptops, desktops, mobile devices
Moderate Server-class or infrastructure systems – Systems that provide
services, data, or applications to other systems/users
Examples: Web servers, file servers, database servers
High Internet-facing or mission-critical systems (e.g., DMZ, financial
systems, PHI) – Systems essential to the core function of the
organization – failure causes major disruption
Examples: EMRs, financial systems
2. Scope
2.1. Appendix A applies to all:
• Networked IT devices (servers, endpoints, IoT, appliances, etc.)
• IT devices connecting to Medline networks
• On-premises, cloud, and hybrid environments
• Internal, contractor, and third party-owned IT devices with Medline network access
3. Definitions
• Capitalized terms used in this Policy will have the meanings set forth in Appendix E: Definitions.
4. Minimum Security Controls for Networked Devices
Category Low Risk Moderate Risk High Risk
Asset Inventory Registered in CMDB CMDB + owner
assigned
CMDB + asset classification +
owner
Authentication Local account with
strong password
Centralized
authentication (e.g.,
AD)
MFA + Role-based access
control (RBAC)
Patching / Updates 45 Days 60 Days 30 Days
Endpoint Protection AV/EDR required EDR + continuous
monitoring + alerting
EDR + continuous monitoring
+ alerting
Encryption At rest or in transit if
needed
Mandatory (at rest and
in transit)
Mandatory (at rest and in
transit)
Network Access VLAN segmentation
+ firewalls
Network segmentation
+ firewalls + NAC
Network segmentation +
firewalls + NAC
Logging &
Monitoring
Basic local logs Centralized logging (90
days retained)
SIEM logging (365 days
retained)
Backup
Requirements
Optional Weekly backup Daily backup with test
restores monthly
Exposure
Management
Annual scan Quarterly scan +
remediation
Continuous scan + tracked
remediation
Configuration
Hardening
Vendor defaults
removed
CIS baseline applied CIS + custom hardening +
config monitoring
Remote Access VPN with MFA VPN with MFA ZTNA or secure gateway
Change Control Ad hoc changes Changes logged Formal change control
process (CAB)

Appendix B
Minimum Security Standards (MSS) for Network Access
1. MSS Requirements for Network Access
1.1. The minimum security standards are the basic rules or requirements for all accessing networks
across Medline. It ensures that all IT devices and End Users connecting to corporate networks do
so securely, with access controlled based on sensitivity, risk, and Zero Trust principles. Zero Trust
assumes no implicit trust, meaning every access request must be verified regardless of where it
comes from.
1.2. The standards are designed based on risk and are aligned with the function of the IT device, the
sensitivity of the data, and the importance to business operations. To simplify usage, networked
devices are categorized as low, moderate, or high, depending on their vulnerability to Medline.
Risk Level
Types of Network Access
Low Access to guest or end-user networks
Examples: Guest Wi-Fi Access
Moderate Access to internal business application and Medline Systems.
Examples: Access to the WMS Portal
High Access to critical infrastructure, production environments, or
systems with regulated data.
Examples: Access to Medline Data Center
2. Scope
2.1. This policy applies to all forms of network access within Medline, including:
• Wired and wireless internal networks
• Remote VPN, Zero Trust Network Access (ZTNA), and third-party access
• Cloud network connections and hybrid connectivity
• All employees, contractors, guests, and third-party Vendors
3. Definitions
Capitalized terms used in this Policy will have the meanings set forth in Appendix E: Definitions.
4. Minimum Security Controls for Network Access
Category Low Risk Moderate Risk High Risk
Network
Segmentation
Flat network or basic
VLANs
Network segmentation Micro-segmentation or SDP
Access
Authentication
Password-only or
captive portal
AD or RADIUS
authentication
MFA + posture-based auth
Remote Access VPN with MFA VPN with MFA ZTNA or secure gateway
Network
Encryption
Optional TLS for apps TLS for apps
Firewall Rules Default-deny +
allowlists
Default-deny + allowlists Strict allowlists by app/user
Access
Monitoring
Minimal local logging Centralized logging
(NetFlow, syslog)
Real-time SIEM alerting +
behavioral analytics
Wireless Access Shared SSID +
password or
certificate
Per-user credentials +
certificate
Per-user credentials +
certificate + isolation
Guest and Third-
Party Access
Isolated VLAN with
internet only
ZTNA or secure gateway ZTNA or secure gateway
only
Device Posture
Checks
Agent-based posture
check
Agent-based posture check Continuous assessment
(EDR, compliance check)
DNS Filtering Threat intel-enriched
filtering
Threat intel-enriched
filtering
Threat intel-enriched
filtering
Network Change
Control
Ad hoc changes
allowed
Change requests logged CAB-reviewed changes only

Appendix C
Minimum Security Standards (MSS) for Identity and Access Controls
1. MSS Requirements for Identity and Access Controls
1.1. The minimum security standards are the basic rules or requirements for identity and access
controls across Medline. It ensures that access to Medline Systems is appropriately authenticated,
authorized, and audited based on the sensitivity of the Medline System component and the role
of the Authorized User.
1.2. The standards are designed based on risk and are aligned with the function of the IT device, the
sensitivity of the data, and the importance to business operations. To simplify usage, identity and
access controls are categorized as low, moderate, or high, depending on the type of access and
the system’s vulnerability to Medline.
Risk Level
Types of Network Access Control
Low Standard user access to Medline managed device.
Examples: Employee logging into a Medline-provided laptop.
Moderate Standard user access to Medline Systems.
Examples: Authorized user access to the WMS Portal
High Administrative or privileged access to critical infrastructure,
production environments, or systems with regulated data.
Examples: Administrative access to Medline Data Center
2. Scope
2.1. Appendix C applies to all End User accounts, Medline Systems, and Services within Medline, including:
• Employees, contractors, and third-party Vendors
• On-premises and cloud applications
• Privileged, standard, and system accounts
• Federated and non-federated identities
3. Definitions
Capitalized terms used in this Policy will have the meanings set forth in Appendix E: Definitions.
4. Minimum Security Controls for Identity and Access
Category Low Risk Moderate Risk High Risk
User Authentication Password-based
login
MFA for remote access MFA always required
Privileged Access
Management
Not applicable Monitored admin roles PAM with session recording
Account
Provisioning
Workflow-based
with approvals
Workflow-based
with approvals
Workflow-based
with approvals
Access Reviews As needed Quarterly review Quarterly review
Password Policy Basic complexity
rules and rotation
Enforced complexity
and rotation
Enforced complexity and
rotation
Session
Management
Default timeouts Auto timeout + session
lock
Time-based + behavioral
session validation
Access Logging Basic local logging Centralized logging
(SIEM)
Centralized logging (SIEM) +
anomaly detection
Federation & SSO Optional Required for SaaS Federated with policy
enforcement
Separation of Duties Not enforced Reviewed during
provisioning
Enforced via RBAC
Context-Aware
Access
Not required Geolocation & device
checks
Real-time conditional access
Third-Party Access Password-based
login
VDI + PAM VDI + PAM

Appendix D
Minimum Security Standards (MSS) for Data Recoverability
1. MSS Requirements for Data Recoverability
1.1. Appendix D defines the MSS requirements for Medline Data backup recoverability based on
Medline Data criticality and sensitivity. It ensures appropriate backup protections are in place
to support business continuity, disaster recovery, and regulatory requirements.
1.2. The standards are designed based on risk and are aligned with the function of the IT device,
the sensitivity of the data, and the importance to business operations. To simplify usage,
networked devices are categorized as low, moderate, or high, depending on their vulnerability
to Medline.
Risk Level
Types of Data
Low Non-critical or publicly accessible data
Examples: Basic information about products listed on Medline.com
Moderate Business-important but non-regulated data
Examples: Internal apps, departmental file shares
High Regulated, mission-critical, or Customer-impacting data
Examples: Financial transactions, PHI, Customer databases
2. Scope
Appendix D applies to all End User accounts, Medline Systems, and Services within Medline, including:
• On-premises and cloud-hosted data
• Structured and unstructured data
• Production, development, and archival data
• Endpoints, servers, applications, and storage systems
3. Definitions
Capitalized terms used in this Policy will have the meanings set forth in Appendix E: Definitions.
4. Minimum Security Controls for Data Recoverability
Category Low Risk Moderate Risk High Risk
Backup Method No backup or optional
local backup
Network-based
backups (NAS, shared
drives)
Off-network &/or
Immutable backups (e.g.,
WORM, air-gapped)
Frequency Optional or weekly Daily or nightly Daily or nightly
Retention Up to 1 week 10-14 days 10-14 days
Access Control Local access only Privileged access only
(logged and reviewed)
Privileged access only
(logged and reviewed)
Encryption Optional In transit and at rest In transit and at rest
Testing Annual test (if applicable) Semiannual restore
test
Semiannual restore test
Recovery Time
Objective (RTO)
3-5 business days 3-5 business days 1 business day
Recovery Point
Objective (RPO)
Up to 1 week 24 hours 24 hours