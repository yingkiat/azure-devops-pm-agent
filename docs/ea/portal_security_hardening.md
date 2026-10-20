# EA Portal — Security Hardening Runbook

## Background

**Audit:** MSS Compliance Assessment — EA Portal (2026-02-27)
**Full report:** `ea_outputs/EA_Portal_Security_Compliance_MSS_20260227.md`
**Overall score before hardening:** ~11% MSS compliance

### Deployment details

| Field | Value |
|-------|-------|
| Container App | `m3acaeaportalp1` |
| Resource Group | `M3-RG-ALZ-DWHS-ALYTICS-P-1` |
| ACA Environment | `m3acaenvdwhsagentp1` |
| ACR | `m3acrdwhsp1.azurecr.io` |
| ACA URL (internal) | `https://m3acaeaportalp1.livelyflower-5b5b456d.southeastasia.azurecontainerapps.io` |
| Custom domain (requested) | `https://eaportal.medline.com.au` |

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
- Access to Azure Container Registry (`m3acrdwhsp1`) and resource group `M3-RG-ALZ-DWHS-ALYTICS-P-1`

---

## Phase 1: Code Hardening

### 1a. Add `nginx.conf` (project root)

Create `nginx.conf`. The `log_format` directive must sit **outside** the `server {}` block because nginx only allows it at the `http` level — `conf.d/` files are included inside the `http {}` block of the main nginx config.

```nginx
# log_format must be at http level
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

server {
    listen 80;
    server_name _;
    server_tokens off;

    root /usr/share/nginx/html;
    index index.html;

    access_log /dev/stdout json_combined;
    error_log /dev/stderr warn;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none';" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(svg|json|jpg|png|ico|css|js)$ {
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
        # Re-apply security headers (nginx add_header doesn't inherit in nested locations)
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none';" always;
    }
}
```

#### What each directive does

**Top level (http context)**

`log_format json_combined` — defines a named log format that outputs each request as a single JSON object. Fields: timestamp, client IP, HTTP method, URI, status code, bytes sent, referer, user agent, response time. Must live outside `server {}` because nginx only allows `log_format` in the `http` block.

**Server block**

| Directive | Purpose |
|-----------|---------|
| `listen 80` | Accept connections on port 80. TLS termination happens at the ACA ingress layer before traffic reaches nginx, so nginx only needs HTTP. |
| `server_name _` | Wildcard catch-all — matches any hostname since the container has no fixed DNS name of its own. |
| `server_tokens off` | Removes the `Server: nginx/1.27.x` version string from response headers. Prevents attackers from targeting known CVEs for a specific nginx version. |
| `root / index` | Where the static files live and the default document name. |
| `access_log /dev/stdout json_combined` | Writes access logs to stdout in JSON format. ACA captures container stdout and forwards it to Log Analytics, giving an audit trail with no extra log shipper. |
| `error_log /dev/stderr warn` | Writes nginx errors to stderr. `warn` level filters out noisy info/debug messages. |

**Security headers**

| Header | Purpose |
|--------|---------|
| `X-Frame-Options: DENY` | Prevents the portal from being embedded in an `<iframe>` on another site, blocking clickjacking attacks. |
| `X-Content-Type-Options: nosniff` | Stops browsers from guessing the content type of a response. Without this, a browser might execute a JSON file as JavaScript. |
| `Referrer-Policy: strict-origin-when-cross-origin` | When navigating to an external site, only sends the origin (not path/query string) in the `Referer` header. Prevents internal URLs from leaking to third parties. |
| `Permissions-Policy` | Explicitly disables browser APIs the portal doesn't use — geolocation, microphone, camera. Even if a script tried to request them, the browser refuses. |
| `Strict-Transport-Security: max-age=31536000; includeSubDomains` | Tells browsers to only ever contact this domain over HTTPS for the next year, even if the user types `http://`. `includeSubDomains` extends this to any subdomains. |
| `Content-Security-Policy` | The main XSS defence. Controls what the browser may load and execute, source by source (see table below). |

**CSP directive breakdown**

| Directive | Value | Reason |
|-----------|-------|--------|
| `default-src 'self'` | Catch-all fallback | Anything not explicitly listed is restricted to same-origin. |
| `script-src` | `'self' unpkg.com cdn.jsdelivr.net 'unsafe-eval' 'unsafe-inline'` | Vue 3 and Chart.js load from CDN. `'unsafe-eval'` required because Vue compiles templates at runtime in CDN mode. `'unsafe-inline'` required because the app bootstrap is an inline `<script>` block. |
| `style-src` | `'self' 'unsafe-inline' fonts.googleapis.com` | Portal injects inline styles for dynamic theming and colour injection. Imported how-it-works pages load their font stylesheet from Google Fonts. |
| `font-src` | `'self' fonts.gstatic.com` | Font files referenced by the Google Fonts stylesheet. |
| `img-src` | `'self' data:` | Allows base64-encoded images (`data:` URIs) used for embedded chart exports. |
| `connect-src` | `'self' cdn.jsdelivr.net` | Chart.js fetches its sourcemap from jsdelivr at runtime. |
| `frame-ancestors 'none'` | — | Supersedes `X-Frame-Options` in modern browsers — no site may embed this portal in a frame. |

`always` on every `add_header` — ensures headers are sent on error responses (4xx, 5xx) too. Without this, a CSP or X-Frame-Options header would be absent on a 404 page.

**Location blocks**

| Block | Purpose |
|-------|---------|
| `location /` with `try_files` | SPA routing. nginx looks for a real file, then a directory, then falls back to `index.html`. Deep-linked URLs like `/diagram/crm` are handled by Vue's client-side router rather than returning a 404. |
| `location ~* \.(svg\|json\|...)$` | Matches static asset extensions (case-insensitive). Sets a 1-hour browser cache. Security headers are re-declared here in full because **nginx's `add_header` does not inherit from parent blocks into `location` blocks** — any `location` that sets its own headers completely replaces the parent's header set. |

---

### 1b. Update `Dockerfile`

Pin the nginx version and copy the hardened config:

```dockerfile
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/portal/dist /usr/share/nginx/html
EXPOSE 80
```

### 1c. Mask IT Owner in `portal/backend/indexes.py`

Adds `_mask_it_owner()` and `_mask_properties()` helpers at module level. Applied in `generate_element_index()` — masks `jose.harima` → `jos*.***`. Same masking applied in `portal/backend/builder.py` `_convert_catalogue()` for `catalogue.json` (`it_owner` column).

Fixed-length masking is intentional — actual-length asterisks would reveal the length of the username, aiding enumeration.

### 1d. Rebuild and verify locally

```bash
# Rebuild portal data
source .venv/Scripts/activate && python portal/build.py

# Verify It Owner is masked in output
grep -i "it owner" portal/dist/data/element_index.json
grep "it_owner" portal/dist/data/catalogue.json | head -3

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

Deployment is handled by the Azure DevOps pipeline (`azure-pipelines.yml`) on push to `main`. To deploy manually:

```bash
az acr build \
  --registry m3acrdwhsp1 \
  --image azdo-pm-ea-agent:latest \
  --file Dockerfile .

az containerapp update \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --image m3acrdwhsp1.azurecr.io/azdo-pm-ea-agent:latest

# Verify ingress target port is 80
az containerapp ingress show \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1
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
| Host / Name | `eaportal` |
| Points to | `m3acaeaportalp1.livelyflower-5b5b456d.southeastasia.azurecontainerapps.io` |
| TTL | 3600 |

Resulting URL: `https://eaportal.medline.com.au`

After the CNAME is live, I will run the ACA custom domain binding command myself to provision the managed TLS certificate:

```bash
az containerapp hostname add \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --hostname eaportal.medline.com.au

az containerapp hostname bind \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --hostname eaportal.medline.com.au \
  --environment m3acaenvdwhsagentp1 \
  --validation-method CNAME
```

**2. Entra ID App Registration**

Please create an app registration with the following parameters:

| Field | Value |
|-------|-------|
| Name | `ea-portal` |
| Supported account types | Accounts in this organizational directory only (single tenant) |
| Redirect URI (Web) | `https://eaportal.medline.com.au/.auth/login/aad/callback` |

Once created, please share:
- Application (client) ID
- Directory (tenant) ID
- One client secret (any expiry ≥ 1 year)

I will configure EasyAuth on the ACA container app using those values — no further action needed from cloud ops after the credentials are shared.

**Business justification:** MSS audit finding — EA Portal is internet-facing with no authentication, exposing internal application inventory, IT owner data, and architecture roadmaps. This is the final blocker before the portal can be brought to MSS compliance.

Thanks

---

## Phase 2a: App Registration (Do This Now — No CNAME Required)

The app registration is independent of the CNAME. Create it now using the internal ACA URL as the redirect URI. EasyAuth will enforce authentication on the internal URL immediately. When the CNAME is eventually live, add the custom domain redirect URI and EasyAuth will cover both.

### Step 1: Create the app registration

Go to [portal.azure.com](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations** → **New registration**.

| Field | Value |
|-------|-------|
| Name | `ea-portal` |
| Supported account types | Accounts in this organizational directory only (single tenant) |
| Redirect URI — Platform | Web |
| Redirect URI — URI | `https://m3acaeaportalp1.livelyflower-5b5b456d.southeastasia.azurecontainerapps.io/.auth/login/aad/callback` |

Click **Register**.

### Step 2: Note the IDs

From the app registration **Overview** page, copy:
- **Application (client) ID** → `<CLIENT_ID>`
- **Directory (tenant) ID** → `<TENANT_ID>`

### Step 3: Create a client secret

Go to **Certificates & secrets** → **New client secret**.

| Field | Value |
|-------|-------|
| Description | `ea-portal-easyauth` |
| Expires | 24 months |

Click **Add**, then immediately copy the secret **Value** (it is only shown once) → `<CLIENT_SECRET>`.

### Step 3b: Enable ID token issuance

Go to **Authentication** → under **Implicit grant and hybrid flows**, tick **ID tokens** → **Save**.

Or via CLI:

```bash
az ad app update --id <CLIENT_ID> --enable-id-token-issuance true
```

**Why this is required — for IAM:**

EasyAuth (Azure's built-in authentication sidecar) uses the OpenID Connect implicit flow to get an ID token directly from the authorization endpoint after the user logs in. This ID token is what tells EasyAuth who the user is — their UPN, object ID, and tenant — so it can set the session cookie and let them through.

By default, Entra ID app registrations created since 2021 have this disabled as a security default, because the implicit flow has known weaknesses in browser-based SPAs (tokens exposed in the URL fragment, no refresh token). Microsoft's guidance for new apps is to use the authorization code flow with PKCE instead.

However, EasyAuth is not a browser SPA — it is a server-side middleware running in the container sidecar. The token is never exposed to the browser; it is received server-to-server at the `/.auth/login/aad/callback` endpoint. The implicit flow weakness does not apply here. Microsoft's own EasyAuth documentation explicitly requires ID token issuance to be enabled for this middleware pattern.

Enabling this setting does not weaken the overall security posture — access is still restricted to org accounts only (single-tenant), and the client secret provides an additional layer of verification.

### Step 3c: Grant Microsoft Graph User.Read permission

Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions** → search for and select **User.Read** → **Add permissions**.

Then click **Grant admin consent for [your organisation]** and confirm.

Or via CLI:

```bash
# Add the User.Read delegated permission (Graph API permission ID: e1fe6dd8-ba31-4d61-89e7-88639da4683d)
az ad app permission add \
  --id <CLIENT_ID> \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Grant admin consent
az ad app permission grant \
  --id <CLIENT_ID> \
  --api 00000003-0000-0000-c000-000000000000 \
  --scope User.Read
```

**Why this is required:**

EasyAuth reads the authenticated user's basic profile (UPN, display name, object ID) from Microsoft Graph after login to populate the `X-MS-CLIENT-PRINCIPAL` session claims. Without `User.Read`, the Graph call fails and EasyAuth cannot build the principal — users will see a consent or permission error after successfully authenticating with their org account.

`User.Read` is a low-privilege delegated permission that only allows reading the signed-in user's own profile. It does not grant access to other users' data or any directory-wide information.

### Step 4: Enable EasyAuth on ACA

```bash
az containerapp auth update \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --enabled true \
  --action RedirectToLoginPage

az containerapp auth microsoft update \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --client-id <CLIENT_ID> \
  --client-secret <CLIENT_SECRET> \
  --tenant-id <TENANT_ID>
```

### Step 5: Verify authentication is active

Open a private browser window and navigate to:

```
https://m3acaeaportalp1.livelyflower-5b5b456d.southeastasia.azurecontainerapps.io
```

It should redirect to the Microsoft login page. Confirm that:
- [ ] Unauthenticated access redirects to Microsoft login
- [ ] Org account login succeeds and portal loads
- [ ] Non-org account (e.g. personal Microsoft account) is rejected

### When the CNAME is eventually live

Add the custom domain as a second redirect URI in the app registration (**Authentication** → **Add URI**):

```
https://eaportal.medline.com.au/.auth/login/aad/callback
```

Then run the ACA custom domain binding commands in Phase 2 below. No changes to EasyAuth are required — it will cover both URLs automatically.

---

## Phase 2: Custom Domain Binding (After CNAME is Live)

Do this **after** the Cloud Ops CNAME request is fulfilled.

### Step 1: Confirm custom domain is live

```bash
curl -I https://eaportal.medline.com.au
# Should return 200 with security headers
```

### Step 2: Add custom domain redirect URI to app registration

In the `ea-portal` app registration (**Authentication** → **Add URI**), add:

```
https://eaportal.medline.com.au/.auth/login/aad/callback
```

The internal ACA URL redirect can be left in place or removed at this point.

---

### Step 3: Bind the custom domain on ACA

```bash
az containerapp hostname add \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --hostname eaportal.medline.com.au

az containerapp hostname bind \
  --name m3acaeaportalp1 \
  --resource-group M3-RG-ALZ-DWHS-ALYTICS-P-1 \
  --hostname eaportal.medline.com.au \
  --environment m3acaenvdwhsagentp1 \
  --validation-method CNAME
```

EasyAuth is already configured from Phase 2a — no auth commands needed here.

### How it works

```
Browser hits eaportal.medline.com.au
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
- [ ] `curl -I https://m3acaeaportalp1.livelyflower-5b5b456d.southeastasia.azurecontainerapps.io` returns `X-Frame-Options: DENY`
- [ ] Response includes `Content-Security-Policy` header
- [ ] Response includes `Strict-Transport-Security` header
- [ ] No `Server: nginx/x.x.x` version in response headers
- [ ] `element_index.json` shows `"It Owner": "jos*.***"` format (not real usernames)
- [ ] `catalogue.json` shows `"it_owner": "jos*.***"` format
- [ ] ACA container logs show JSON-structured access log entries
- [ ] Dockerfile uses `nginx:1.27-alpine` (pinned)

### Phase 2a Complete
- [ ] `ea-portal` app registration exists in Entra ID (single-tenant)
- [ ] Redirect URI set to internal ACA URL `/.auth/login/aad/callback`
- [ ] Client secret created and stored securely
- [ ] EasyAuth enabled on ACA — unauthenticated access to internal URL redirects to Microsoft login
- [ ] Org account login succeeds and portal loads
- [ ] Non-org account login is rejected

### Phase 2 Complete (after CNAME)
- [ ] `https://eaportal.medline.com.au` resolves (CNAME live, TLS certificate issued)
- [ ] Custom domain redirect URI added to app registration
- [ ] ACA hostname binding complete with managed TLS certificate

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
