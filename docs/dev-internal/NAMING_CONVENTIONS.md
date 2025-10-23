# 🏷️ V_Track Naming Conventions & Anti-Pattern Guide

**Purpose**: Prevent naming inconsistency bugs that cause CloudFunction integration failures

## ⚠️ The Problem That Happened

### Root Cause of Recent Bug (October 2025)
```
Desktop App Called: license-service (hyphen)
Deployed Function:  license_service (underscore)
Result: 404 Not Found → 100% license activation failure
```

**Impact**: All paid license activations failed silently for days until manually discovered.

---

## ✅ OFFICIAL NAMING STANDARDS

### 1. CloudFunction Naming Convention

| Component | Standard | Example | ❌ WRONG |
|-----------|----------|---------|---------|
| **Folder Name** | `snake_case` | `license_service/` | `license-service/` |
| **Deployed Function Name** | `kebab-case` | `license-service` | `license_service` |
| **Python Entry Point** | `snake_case` | `license_service()` | `licenseService()` |
| **Environment Variable** | `UPPER_SNAKE` | `CLOUD_LICENSE_URL` | `CloudLicenseUrl` |

### 2. Current CloudFunction Inventory

| Service | Folder | Deployed Name | Entry Point | URL Variable |
|---------|--------|---------------|-------------|---------------|
| Payment | `create_payment/` | `create-payment` | `create_payment_handler()` | `CLOUD_PAYMENT_URL` |
| Webhook | `webhook_handler/` | `webhook-handler` | `webhook_handler()` | `CLOUD_WEBHOOK_URL` |
| License | `license_service/` | `license_service` | `license_service()` | `CLOUD_LICENSE_URL` |
| Pricing | `pricing_service/` | `pricing-service` | `pricing_service()` | `CLOUD_PRICING_URL` |

⚠️ **INCONSISTENCY ALERT**: `license_service` deployed name uses UNDERSCORE while others use HYPHENS!

---

## 🔒 Mandatory Validation Checkpoints

### Before Deployment Checklist

**Run this script BEFORE every CloudFunction deployment:**

```bash
# Location: V_Track_CloudFunctions/scripts/validate_naming.sh
./scripts/validate_naming.sh
```

**What it checks:**
1. ✅ Folder names match `snake_case` pattern
2. ✅ Deploy scripts use correct function names
3. ✅ Backend `.env` URLs match deployed function names
4. ✅ Python action names match CloudFunction expectations
5. ✅ No hardcoded incorrect URLs in codebase

### After Deployment Validation

```bash
# Test all endpoints immediately after deployment
python scripts/test_endpoints.py
```

---

## 🛠️ Configuration Files to Check

### 1. Backend Environment (`.env`)

**Location**: `/Users/annhu/vtrack_app/V_Track/backend/.env`

```bash
# ✅ CORRECT - Must match deployed function names exactly
CLOUD_PAYMENT_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment
CLOUD_WEBHOOK_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler
CLOUD_LICENSE_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/license_service

# ❌ WRONG - These will cause 404 errors
CLOUD_LICENSE_URL=https://.../license-service  # Wrong! Should be license_service
```

### 2. Backend Fallback Defaults (`app.py`)

**Location**: `/Users/annhu/vtrack_app/V_Track/backend/app.py` (Lines 101-103)

```python
# ⚠️ DANGER ZONE: These defaults MUST match deployed function names
os.environ.setdefault('CLOUD_PAYMENT_URL', 'https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment')
os.environ.setdefault('CLOUD_WEBHOOK_URL', 'https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler')
os.environ.setdefault('CLOUD_LICENSE_URL', 'https://asia-southeast1-v-track-payments.cloudfunctions.net/license_service')
                                                                                                    # ↑ UNDERSCORE!
```

**Rule**: If you change a deployed function name, you MUST update BOTH:
- `.env` file (primary configuration)
- `app.py` defaults (fallback configuration)

### 3. CloudFunction Action Parameters

**Location**: Desktop client → CloudFunction communication

```python
# ✅ CORRECT
{'action': 'validate_license', 'license_key': '...'}  # CloudFunction expects THIS

# ❌ WRONG - Will return "Unknown action" error
{'action': 'validate', 'license_key': '...'}  # Old/wrong action name
```

**Action Name Standards:**

| Service | Action | ❌ Don't Use |
|---------|--------|-------------|
| License | `validate_license` | `validate` |
| License | `get_licenses` | `list_licenses` |
| Trial | `check_trial_eligibility` | `check_trial` |
| Trial | `generate_trial_license` | `create_trial` |
| Payment | `create_payment` | `new_payment` |

---

## 🚨 Common Failure Patterns

### Pattern 1: Hardcoded Wrong URLs

```python
# ❌ BAD - Hardcoded and wrong
url = "https://.../license-service"  # Will break if function name changes

# ✅ GOOD - Use environment variable
url = os.getenv('CLOUD_LICENSE_URL')
```

### Pattern 2: Inconsistent Action Names

```python
# ❌ BAD - Guessing action name
payload = {'action': 'validate', ...}  # What does backend expect?

# ✅ GOOD - Use constants
from config.cloud_actions import VALIDATE_LICENSE
payload = {'action': VALIDATE_LICENSE, ...}
```

### Pattern 3: Silent Fallback to Wrong Default

```python
# ❌ BAD - Wrong default value
url = os.getenv('CLOUD_LICENSE_URL', 'https://.../license-service')  # Wrong default!

# ✅ GOOD - Fail loudly if missing
url = os.getenv('CLOUD_LICENSE_URL')
if not url:
    raise ValueError("CLOUD_LICENSE_URL not configured!")
```

---

## 🔧 Prevention Tools

### 1. Pre-Commit Hook

**Location**: `.git/hooks/pre-commit`

```bash
#!/bin/bash
echo "🔍 Validating naming conventions..."

# Check for hardcoded wrong URLs
if git diff --cached | grep -i "license-service"; then
    echo "❌ Found 'license-service' with hyphen - should be 'license_service' with underscore"
    exit 1
fi

echo "✅ Naming validation passed"
```

### 2. Startup Validation

**Location**: `backend/app.py` (Add to startup sequence)

```python
def validate_cloud_endpoints():
    """Validate CloudFunction endpoints on startup"""
    endpoints = {
        'license_service': os.getenv('CLOUD_LICENSE_URL'),
        'create_payment': os.getenv('CLOUD_PAYMENT_URL'),
        'webhook_handler': os.getenv('CLOUD_WEBHOOK_URL')
    }

    for name, url in endpoints.items():
        if not url:
            logger.error(f"❌ Missing {name} URL in environment")
            continue

        # Quick validation: URL should contain correct function name
        if name == 'license_service' and 'license-service' in url:
            logger.error(f"❌ WRONG URL: {url} contains 'license-service' (hyphen), should be 'license_service' (underscore)")
            raise ValueError(f"Invalid CloudFunction URL for {name}")
```

### 3. Health Check with Detailed Errors

```python
@app.route('/api/validate-config', methods=['GET'])
def validate_configuration():
    """Validate all CloudFunction configurations"""
    results = {}

    for service in ['license_service', 'create_payment', 'webhook_handler']:
        url = os.getenv(f'CLOUD_{service.upper()}_URL')

        # Test actual connectivity
        try:
            response = requests.get(f"{url}?action=health", timeout=5)
            results[service] = {
                'configured': True,
                'reachable': response.status_code == 200,
                'url': url
            }
        except Exception as e:
            results[service] = {
                'configured': bool(url),
                'reachable': False,
                'error': str(e),
                'url': url
            }

    return jsonify(results)
```

---

## 📝 When to Update This Document

Update this document when:
1. ✅ Adding new CloudFunction
2. ✅ Renaming existing CloudFunction
3. ✅ Discovering new naming-related bug
4. ✅ Changing action parameter names
5. ✅ Updating deployment scripts

**Last Updated**: 2025-10-15
**Last Incident**: 2025-10-14 (License activation failure due to hyphen/underscore mismatch)

---

## 🎯 Quick Reference

**When in doubt, follow this order:**

1. **Check deployed function name**: `gcloud functions list --project=v-track-payments`
2. **Match exactly in `.env`**: Copy deployed name exactly into `CLOUD_*_URL`
3. **Update `app.py` defaults**: Keep fallbacks in sync
4. **Test immediately**: Run health check after any change
5. **Document the change**: Update this file

**Golden Rule**: Configuration should be explicit, validated, and fail loudly if wrong.
