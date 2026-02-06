# External Customer Portal - Design Notes

**Date**: 2025-01-20
**Domain**: Commercial
**Scope**: External customer access to SPT pack data via secure B2B portal

---

## Problem Statement

The Commercial Digital Road Map requires exposing customer information (packs, transaction history, order status, inventory) to external customers (Hospital Buyers and Resellers). Currently, MedPack and related systems are internal-only.

### What the Business Wants
- Hospital buyers and resellers can view their SPT packs
- Self-service access to inventory levels and production status
- Transaction history (orders, forecasts)
- No internal system redesign - leverage existing infrastructure

### What Exists Today
Internal systems exist to support this:
- **MedPack** - Pack visibility, BOM, components, pricing (internal portal)
- **QAD ERP + Analytics DB** - Order history, inventory, forecasts
- **Microsoft Dynamics CRM** - Customer master data
- **Real-Time Inventory Dashboard** - Live inventory tracking

But **no external access layer** exists to safely expose this data to B2B customers.

---

## Gap Analysis

| Capability | Required | Current State | Status |
|-----------|----------|---------------|--------|
| **External Identity** | B2B customer login (Entra External ID) | Not implemented | ❌ NEW |
| **Multi-Tenant Data Isolation** | Each customer sees only their data | No isolation layer | ❌ NEW |
| **Customer Portal** | Web UI for external access | Internal portals only | ❌ NEW |
| **Backend Integration Layer** | API that enforces auth + filters data | Not implemented | ❌ NEW |
| **Pack Data** | MedPack data to external customers | Exists internally | ✅ Existing |
| **Transaction History** | Order/inventory data to customers | Exists in QAD | ✅ Existing |

---

## Architecture Decisions

### 1. **Scope: Keep it Simple**
- **Focus**: External customer portal viewing only (no order creation yet)
- **Data sources**: MedPack API + QAD Analytics Database
- **Data flow**: Backend → MedPack API, Backend → QAD Analytics DB → Portal
- **No new core systems** - integrate existing infrastructure

### 2. **Authentication: Entra External ID**
- B2B identity for external customers
- Secure, managed by Microsoft
- Integrates with backend for authorization context

### 3. **Multi-Tenancy Control: Backend-Enforced**
- Backend API is the authoritative filter
- Authenticates via Entra (customer identity)
- Queries MedPack API and QAD Analytics with customer context
- Only returns data the customer is authorized to see

### 4. **Data Sources: Existing Infrastructure**
- **MedPack API** (assumed existing)
  - Provides: Pack BOM, components, pricing, availability
  - Backend calls with customer ID filter

- **QAD Analytics Database** (existing)
  - Provides: Order history, inventory levels, forecasts
  - Backend queries with customer account filter

### 5. **Architecture Layers**

```
┌─────────────────────────────────────────┐
│  EXTERNAL CUSTOMERS                     │
│  (Hospital Buyers, Resellers)           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  ENTRA EXTERNAL ID                      │
│  (B2B Identity + Multi-tenant Context)  │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  EXTERNAL CUSTOMER PORTAL               │
│  (Frontend - Web UI)                    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  BACKEND API                            │
│  (Multi-tenant Authorization)           │
│  - Authenticates customer (Entra)       │
│  - Filters queries by customer context  │
│  - Enforces row-level security          │
└─────────────────────────────────────────┘
                    ↓
        ┌───────────┴────────────┐
        ↓                        ↓
┌──────────────────┐   ┌──────────────────────┐
│  MedPack API     │   │  QAD Analytics DB    │
│  - Pack data     │   │  - Order history     │
│  - Components    │   │  - Inventory levels  │
│  - Pricing       │   │  - Forecasts         │
└──────────────────┘   └──────────────────────┘
```

---

## Key Design Principles

### 1. **Thin External Layer Philosophy**
- Minimize new code and infrastructure
- Reuse existing MedPack and QAD capabilities
- Backend is the integration and security layer
- Portal is primarily a UI wrapper

### 2. **Multi-Tenancy at Backend Level**
- Backend knows which customer is authenticated (via Entra token)
- Backend passes customer context to MedPack API calls
- Backend filters QAD Analytics queries by customer account
- Result: Customers never see each other's data

### 3. **Security Boundary: Backend + Entra**
- Entra External ID = Authentication (who are you?)
- Backend API = Authorization (what can you see?)
- Portal = Presentation (how do you see it?)
- This separation allows each layer to evolve independently

### 4. **Existing Systems Not Modified**
- MedPack API is called as-is (backend handles filtering)
- QAD Analytics DB is queried as-is (backend adds WHERE clauses)
- No changes to internal systems
- Lower risk, faster to market

---

## Data Security Considerations

### Authorization Model
```
Customer logs in with Entra External ID
    ↓
Backend receives authenticated customer context
    ↓
Backend queries MedPack API: "GET /packs?customer_id={authenticated_customer}"
    ↓
Backend queries QAD Analytics: "SELECT * FROM orders WHERE customer_account = {authenticated_customer}"
    ↓
Backend returns filtered results to portal
    ↓
Customer sees only their own data
```

### Trust Boundaries
1. **External → Entra**: Identity is proven by Microsoft
2. **Entra → Backend**: Token grants customer context
3. **Backend → Data Sources**: Backend enforces query filters
4. **Data → Portal**: Portal receives only authorized data

---

## What "New" and "Existing" Means Here

### NEW Components
- **External Customer Portal** - New web UI (not internal)
- **Backend API** - New integration layer with multi-tenant logic
- **Entra External ID Configuration** - New identity setup for B2B
- **Integration from Portal → Backend** - New API calls

### EXISTING Components Being Exposed
- **MedPack API** - Already exists, now called from backend
- **MedPack Aus / MedPack NZ** - Already exist, data provided via API
- **QAD Analytics Database** - Already exists, now queried from backend
- **QAD - EE** - Already exists, source of order/inventory data

### Diagram Will Show
- How the NEW layer sits on top of EXISTING systems
- Clear separation between what's new (Portal, Backend, Entra) and what's existing (MedPack, QAD)
- Data flows from existing systems through new layer to external customers

---

## Next Steps (Post-Architecture)

1. **Design Portal UI**
   - What views should customers see? (Packs, Orders, Inventory, Forecasts)
   - Dashboard layouts, filters, export options

2. **Design Backend API**
   - REST endpoints: GET /customer/packs, GET /customer/orders, etc.
   - Authentication: Validate Entra token, extract customer context
   - Authorization: Implement query filters per endpoint

3. **Entra External ID Setup**
   - Configure B2B user scenarios
   - Define customer groups (Hospital Buyers, Resellers)
   - Map customers to accounts in CRM

4. **Integration Points**
   - How does backend call MedPack API? (API key, OAuth?)
   - How does backend query QAD Analytics? (Connection string, service account?)
   - What error handling and retry logic needed?

5. **Testing & Security**
   - Multi-tenant isolation testing (Customer A can't see Customer B's data)
   - Authentication/authorization testing
   - Data validation (only authorized data returned)

---

## Assumptions

1. **MedPack API exists** (or will exist) and is callable from backend
2. **QAD Analytics Database** is accessible from backend with query permissions
3. **Entra External ID** is configured in tenant and available for use
4. **Customer-to-account mappings** exist in CRM or can be created
5. **Backend is a standard REST/GraphQL service** (hosted in Azure or on-prem)
6. **Portal is a modern web app** (React, Vue, etc.) or Power Apps

---

## Open Questions

1. What's the SLA for data freshness in the portal? (Real-time vs. nightly sync)
2. Should customers be able to download reports? (PDF, Excel?)
3. Do we need to track customer portal usage/analytics?
4. Should there be a mobile app or web-only?
5. What's the rollout plan? (Pilot hospitals first, then resellers?)
6. Do we need customer support/help features in the portal?

