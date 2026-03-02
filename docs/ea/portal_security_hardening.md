# EA Portal — Security Hardening Runbook

## Background

**Audit:** MSS Compliance Assessment — EA Portal (2026-02-27)
**Full report:** `ea_outputs/EA_Portal_Security_Compliance_MSS_20260227.md`
**Overall score before hardening:** ~11% MSS compliance

### What the audit found

The EA Portal is deployed to Azure Container Apps (ACA) with public external ingress and **no authentication**. Anyone with the URL can access:

- Full internal application inventory (99 applications — names, domains, regions, criticality)
- IT owner usernames for every system in the catalogue
- Tier 1 Mission Critical system names and integration maps
- CRM consolidation roadmap, infrastructure plans, operations transformation plan
- Architecture diagrams covering APAC and all business domains

**Risk classification: HIGH** (MSS Appendix A — internet-facing system with sensitive internal data)

### HIGH priority gaps being addressed by this runbook

| Gap | Fix |
|-----|-----|
| No HTTP security headers (XSS, clickjacking, MIME sniffing) | Custom nginx.conf with CSP, HSTS, X-Frame-Options, etc. |
| nginx version disclosed in response headers | `server_tokens off` |
| No access logging / audit trail | Structured JSON logging to stdout (ACA → Log Analytics) |
| IT owner usernames exposed in element_index.json | Mask to `jan*.***` format at build time |
| nginx image not version-pinned | Pin to `nginx:1.27-alpine` in Dockerfile |
| No authentication (CRITICAL) | AAD app registration + ACA EasyAuth (Phase 2 below) |

---

## Pre-requisites

- Docker installed locally
- `az` CLI authenticated (`az login`)
- Access to Azure Container Registry (ACR) and ACA resource group
- Know your ACA resource group name

---

## Phase 1: Code Hardening

### 1a. Add `nginx.conf` (project root)

Create `nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    server_tokens off;

    root /usr/share/nginx/html;
    index index.html;

    log_format json_combined escape=json
        '{'
            '"time":"$time_iso8601",'
            '"remote_addr":"$remote_addr",'
            '"method":"$request_method",'
            '"uri":"$request_uri",'
            '"status":$status,'
            '"bytes_sent":$bytes_sent,'
            '"http_referer":"$http_referer",'
            '"http_user_agent":"$http_user_agent",'
            '"request_time":$request_time'
        '}';

    access_log /dev/stdout json_combined;
    error_log /dev/stderr warn;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(svg|json|jpg|png|ico|css|js)$ {
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;
    }
}
```

### 1b. Update `Dockerfile`

Pin the nginx version and copy the hardened config:

```dockerfile
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/portal/dist /usr/share/nginx/html
EXPOSE 80
```

### 1c. Mask IT Owner in `portal/backend/indexes.py`

Adds `_mask_it_owner()` and `_mask_properties()` helpers at module level. Applied in `generate_element_index()` — masks `jose.harima` → `jos*.***`.

### 1d. Rebuild and verify locally

```bash
# Rebuild portal data
source .venv/Scripts/activate && python portal/build.py

# Verify It Owner is masked in output
grep -i "it owner" portal/dist/data/element_index.json

# Build and run Docker image
docker build -t ea-portal-test .
docker run -d -p 8080:80 --name ea-test ea-portal-test

# Check security headers
curl -I http://localhost:8080

# Expected headers:
#   X-Frame-Options: DENY
#   X-Content-Type-Options: nosniff
#   Content-Security-Policy: ...
#   Strict-Transport-Security: ...
#   (no Server: nginx/x.x.x version line)

# Check access log format (JSON)
docker logs ea-test

# Cleanup
docker rm -f ea-test
```

### 1e. Deploy to ACA

```bash
# Tag and push
docker build -t ea-portal:latest .
docker tag ea-portal:latest <YOUR-ACR>.azurecr.io/ea-portal:latest
docker push <YOUR-ACR>.azurecr.io/ea-portal:latest

# Update ACA
az containerapp update \
  --name ea-portal \
  --resource-group <YOUR-RG> \
  --image <YOUR-ACR>.azurecr.io/ea-portal:latest

# Verify ingress target port is 80 (not 8000)
az containerapp ingress show --name ea-portal --resource-group <YOUR-RG>

# If targetPort is wrong:
az containerapp ingress update \
  --name ea-portal \
  --resource-group <YOUR-RG> \
  --target-port 80
```

---

## Cloud Ops Request Template

Send the following as a single request to cloud ops. Both items are needed together — the app registration redirect URI must use the custom domain.

---

**Subject:** EA Portal — AAD App Registration + DNS CNAME (Security Hardening)

Hi team,

As part of the MSS compliance remediation for the EA Portal (risk rating: HIGH), I need two things set up in the same change window. The app registration redirect URI depends on the custom domain being live first.

**1. DNS CNAME Record**

| Field | Value |
|-------|-------|
| Record type | CNAME |
| Host / Name | `portal` (or your preferred subdomain) |
| Points to | `<YOUR-ACA-FQDN>` (e.g. `ea-portal.bluesky-abc123.australiaeast.azurecontainerapps.io`) |
| TTL | 3600 |

Resulting URL: `https://portal.enterprise.com`

After the CNAME is live, I will run the ACA custom domain binding command myself to provision the managed TLS certificate:

```bash
az containerapp hostname add \
  --name ea-portal \
  --resource-group <YOUR-RG> \
  --hostname portal.enterprise.com

az containerapp hostname bind \
  --name ea-portal \
  --resource-group <YOUR-RG> \
  --hostname portal.enterprise.com \
  --environment <YOUR-ACA-ENVIRONMENT> \
  --validation-method CNAME
```

**2. Entra ID App Registration**

Please create an app registration with the following parameters:

| Field | Value |
|-------|-------|
| Name | `ea-portal` |
| Supported account types | Accounts in this organizational directory only (single tenant) |
| Redirect URI (Web) | `https://portal.enterprise.com/.auth/login/aad/callback` |

Once created, please share:
- Application (client) ID
- Directory (tenant) ID
- One client secret (any expiry ≥ 1 year)

I will configure EasyAuth on the ACA container app using those values — no further action needed from cloud ops after the credentials are shared.

**Business justification:** MSS audit finding — EA Portal is internet-facing with no authentication, exposing internal application inventory, IT owner data, and architecture roadmaps. This is the final blocker before the portal can be brought to MSS compliance.

Thanks

---

## Phase 2: AAD App Registration + EasyAuth

Do this **after** the Cloud Ops request is fulfilled and the custom domain is live.

### Step 1: Confirm custom domain is live

```bash
curl -I https://portal.enterprise.com
# Should return 200 with security headers
```

### Step 2: App registration credentials from cloud ops

Cloud ops will share after fulfilling the request above:
- Application (client) ID → `<CLIENT_ID>`
- Directory (tenant) ID → `<TENANT_ID>`
- Client secret → `<CLIENT_SECRET>`

The redirect URI registered will be `https://portal.enterprise.com/.auth/login/aad/callback`.

After creating:
- Copy **Application (client) ID** → `<CLIENT_ID>`
- Copy **Directory (tenant) ID** → `<TENANT_ID>`
- Go to **Certificates & secrets** → New client secret → copy value → `<CLIENT_SECRET>`

---

### Step 3: Enable EasyAuth on ACA

```bash
az containerapp auth update \
  --name ea-portal \
  --resource-group <YOUR-RG> \
  --enabled true \
  --action RedirectToLoginPage

az containerapp auth microsoft update \
  --name ea-portal \
  --resource-group <YOUR-RG> \
  --client-id <CLIENT_ID> \
  --client-secret <CLIENT_SECRET> \
  --tenant-id <TENANT_ID>
```

### How it works

```
Browser hits ACA URL
    ↓
EasyAuth middleware intercepts (before nginx ever sees it)
    ↓
Redirects to Microsoft login
    ↓
User authenticates with org account
    ↓
Redirected back to /.auth/login/aad/callback
    ↓
EasyAuth sets session cookie
    ↓
nginx serves static HTML as normal
```

Zero changes to nginx or Dockerfile required for EasyAuth — it is purely an ACA sidecar.

---

## Verification Checklist

### Phase 1 Complete
- [ ] `curl -I <ACA-URL>` returns `X-Frame-Options: DENY`
- [ ] `curl -I <ACA-URL>` returns `Content-Security-Policy` header
- [ ] `curl -I <ACA-URL>` returns `Strict-Transport-Security` header
- [ ] No `Server: nginx/x.x.x` version in response headers
- [ ] `element_index.json` shows `"It Owner": "jos*.***"` format (not real usernames)
- [ ] ACA container logs show JSON-structured access log entries
- [ ] Dockerfile uses `nginx:1.27-alpine` (pinned)

### Phase 2 Complete
- [ ] `https://portal.enterprise.com` resolves (CNAME live, TLS certificate issued)
- [ ] Unauthenticated browser access redirects to Microsoft login
- [ ] Org account login succeeds and portal loads
- [ ] Non-org account login is rejected
- [ ] App registration in Entra ID set to "this org only"

---

## Remaining Items (Phase 3+)

| Item | Priority | Effort |
|------|----------|--------|
| WAF on ACA ingress (Azure Front Door) | Medium | 1 day |
| Container image vulnerability scan | Medium | 2 hours |
| Source file backup posture confirmed | Medium | 2 hours |
| Portal registered in CMDB | Medium | 30 min |
| RBAC per view category (MVP14) | Low | 2 weeks |
| SIEM integration with 365-day retention | Low | 1 week |

**Full audit report:** `ea_outputs/EA_Portal_Security_Compliance_MSS_20260227.md`
