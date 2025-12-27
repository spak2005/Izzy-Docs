# OAuth Scope Decisions

## Overview

This document explains the OAuth scope configuration for IzzyDocs and the reasoning behind key decisions. Reference this when considering changes to scope requirements.

---

## Current Scope Configuration

**Last Updated:** December 27, 2024

### Active Scopes

| Scope | Classification | Purpose |
|-------|----------------|---------|
| `userinfo.email` | Non-sensitive | Identify user |
| `userinfo.profile` | Non-sensitive | Display user name/picture |
| `openid` | Non-sensitive | OpenID Connect authentication |
| `documents` | Sensitive | Create, edit, delete Google Docs |
| `documents.readonly` | Sensitive | Read Google Docs content |
| `drive.readonly` | Restricted | Search and list all Drive files |
| `drive.file` | Sensitive | Create/edit files app created |

### Removed Scopes

| Scope | Classification | Why Removed |
|-------|----------------|-------------|
| `drive` (full access) | **Restricted** | Requires CASA security assessment |

---

## Decision: Remove Full Drive Access (`drive` scope)

### Date: December 27, 2024

### Context

Google requires a **CASA (Cloud Application Security Assessment)** for apps using certain restricted scopes, including `https://www.googleapis.com/auth/drive` (full Drive access).

CASA involves:
- Third-party security assessment
- Cost: $500 - $15,000+ depending on assessor
- Timeline: Several weeks
- Annual re-assessment may be required

### Decision

**Remove the `drive` scope** and use a combination of:
- `drive.readonly` - For searching and listing files
- `drive.file` - For creating and editing files the app creates

### Trade-offs

#### What We Lose

| Feature | Status |
|---------|--------|
| Move/rename ANY file in Drive | ❌ No longer available |
| Delete ANY file in Drive | ❌ No longer available |
| Share ANY file in Drive | ❌ No longer available |
| Change permissions on ANY file | ❌ No longer available |

#### What We Keep

| Feature | Status |
|---------|--------|
| Create new documents | ✅ Works |
| Edit documents | ✅ Works |
| Read all documents | ✅ Works |
| Search all Drive files | ✅ Works |
| List files in folders | ✅ Works |
| Delete files app created | ✅ Works |
| Share files app created | ✅ Works |

### Impact on Users

Most common use cases are unaffected:
- "Create a document called Project Proposal" ✅
- "Add a section about methodology" ✅
- "Find my document about budgets" ✅
- "List my recent docs" ✅

Affected use cases (rare):
- "Delete that old document" (only works for app-created docs)
- "Share this file with john@example.com" (only works for app-created docs)
- "Move this to my Archive folder" ❌

### Alternatives Considered

1. **Keep full `drive` scope and complete CASA**
   - Pros: Full functionality
   - Cons: Expensive, time-consuming, requires annual renewal
   - Decision: Rejected for initial launch; can revisit later

2. **Remove all Drive scopes**
   - Pros: Simplest verification
   - Cons: Can't search or list files
   - Decision: Rejected; search is core functionality

3. **Use `drive.readonly` + `drive.file` (Chosen)**
   - Pros: Keeps search, avoids CASA, faster approval
   - Cons: Limited write operations on existing files
   - Decision: Best balance for MVP

---

## How to Re-enable Full Drive Access

If you decide to pursue CASA verification later:

### 1. Update `auth/scopes.py`

```python
# Uncomment this line:
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"

# Update DRIVE_SCOPES:
DRIVE_SCOPES = [DRIVE_SCOPE, DRIVE_READONLY_SCOPE, DRIVE_FILE_SCOPE]
```

### 2. Update Google Cloud Console

1. Go to [OAuth consent screen → Data Access](https://console.cloud.google.com/apis/credentials/consent)
2. Add scope: `https://www.googleapis.com/auth/drive`
3. Provide justification
4. Submit for verification

### 3. Complete CASA Assessment

1. Choose a CASA assessor from [Google's approved list](https://developers.google.com/workspace/guides/select-casa-tier)
2. Complete the security assessment
3. Submit results to Google
4. Wait for approval

---

## Verification Status

| Item | Status | Date |
|------|--------|------|
| Branding verification | ✅ Approved | Dec 27, 2024 |
| Domain verification | ✅ Approved | Dec 27, 2024 |
| Sensitive scopes (Docs) | ⏳ Pending | Submitted Dec 27, 2024 |
| Restricted scopes (Drive readonly) | ⏳ Pending | Submitted Dec 27, 2024 |
| CASA assessment | N/A | Not required (full drive removed) |

---

## Related Files

- `auth/scopes.py` - Scope definitions
- `auth/oauth_config.py` - OAuth configuration
- `openai_apps/routes.py` - OAuth endpoints

---

## Contact

For questions about this decision, contact the project maintainer.

