# 🚀 V_Track Desktop App - Quick Reference

**Last Updated**: 2025-10-15
**Purpose**: Central reference for API endpoints, CloudFunction integration, and common naming patterns

---

## 📡 CloudFunction Integration

### Environment Variables (.env)
```bash
CLOUD_PAYMENT_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment
CLOUD_WEBHOOK_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler
CLOUD_LICENSE_URL=https://asia-southeast1-v-track-payments.cloudfunctions.net/license_service
```

### ⚠️ CRITICAL: Function Name Inconsistency
| Service | Deployed Name | Pattern |
|---------|---------------|---------|
| Payment | `create-payment` | ✅ kebab-case (hyphen) |
| Webhook | `webhook-handler` | ✅ kebab-case (hyphen) |
| **License** | **`license_service`** | ⚠️ **snake_case (underscore)** |
| Pricing | `pricing-service` | ✅ kebab-case (hyphen) |

**Common Mistake**: Using `license-service` (hyphen) → Results in 404 error

### CloudFunction Action Names (POST requests)

**License Service Actions**:
```python
# ✅ CORRECT
{'action': 'validate_license', 'license_key': '...'}
{'action': 'get_licenses', 'customer_email': '...'}
{'action': 'check_trial_eligibility', 'machine_fingerprint': '...'}
{'action': 'generate_trial_license', 'machine_fingerprint': '...'}

# ❌ WRONG - Will return "Unknown action" error
{'action': 'validate', ...}  # Missing _license suffix
```

**Health Check** (GET method):
```bash
# All services support health check
curl "https://.../{function_name}?action=health"
```

---

## 🔌 Backend API Endpoints

### Main App Routes (app.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check with cloud status |
| `/api/system-info` | GET | System information |
| `/api/license-status` | GET | Current license status |
| `/api/user/latest` | GET | Get latest authenticated user |
| `/api/user/logout` | POST | Logout and clear session |
| `/api/camera-configurations` | GET | Get camera configs from DB |
| `/api/processing-status` | GET | Current file processing status |
| `/payment/redirect` | GET | Payment popup auto-close (unified) |
| `/cancel` | GET | Legacy cancel route (redirects) |
| `/static/avatars/<filename>` | GET | Serve cached avatar files |

### Payment Blueprint (/api/payment/...)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/payment/create` | POST | Create payment order |
| `/api/payment/packages` | GET | Get available pricing packages |
| `/api/payment/validate-license` | POST | Validate license key |
| `/api/payment/activate-license` | POST | Activate paid license |
| `/api/payment/license-status` | GET | Get license status with trial info |
| `/api/payment/licenses/<email>` | GET | Get all licenses for email |
| `/api/payment/health` | GET | Payment service health |

### Registered Blueprints

| Blueprint | URL Prefix | Module |
|-----------|-----------|--------|
| `program_bp` | `/api` | Scheduler/program management |
| `config_bp` | `/api/config` | Configuration routes |
| `step4_roi_bp` | - | ROI configuration |
| `query_bp` | - | Query endpoints |
| `cutter_bp` | - | Video cutting |
| `hand_detection_bp` | - | Hand detection |
| `simple_hand_detection_bp` | `/api/hand-detection` | Simple hand detection |
| `qr_detection_bp` | `/api/qr-detection` | QR code detection |
| `roi_bp` | - | ROI management |
| `cloud_bp` | - | Cloud endpoints |
| `lazy_folder_bp` | `/api/cloud` | Lazy folder loading |
| `sync_bp` | `/api/sync` | Sync endpoints |
| `payment_bp` | `/api/payment` | Payment integration |

---

## 🗄️ Database Tables

### License System
- `licenses` - Active license records
- `license_activations` - Activation history
- `user_profiles` - User authentication data

### Configuration
- `camera_configurations` - Camera setup
- `video_sources` - Video source definitions
- `program_status` - App state

---

## 🔧 Common Code Patterns

### CloudFunction Client Usage
```python
from modules.payments.cloud_function_client import get_cloud_client

cloud_client = get_cloud_client()

# Validate license
result = cloud_client.validate_license(license_key)

# Get licenses by email
licenses = cloud_client.get_licenses_by_email(customer_email)

# Check trial eligibility
eligible = cloud_client.check_trial_eligibility(machine_fingerprint)
```

### Database Connection
```python
from modules.db_utils.safe_connection import safe_db_connection

with safe_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
    results = cursor.fetchall()
```

### License Repository
```python
from modules.licensing.repositories.license_repository import LicenseRepository

repository = LicenseRepository()

# Create license
license_id = repository.create_license(
    license_key=key,
    customer_email=email,
    product_type='desktop',
    features=['full_access'],
    expires_days=365
)

# Get license
license = repository.get_license_by_key(license_key)
```

---

## ⚠️ Common Mistakes & Fixes

### 1. CloudFunction URL Mismatch
```python
# ❌ WRONG
CLOUD_LICENSE_URL = "https://.../license-service"  # Hyphen

# ✅ CORRECT
CLOUD_LICENSE_URL = "https://.../license_service"  # Underscore
```

### 2. Wrong Action Name
```python
# ❌ WRONG
payload = {'action': 'validate', 'license_key': key}

# ✅ CORRECT
payload = {'action': 'validate_license', 'license_key': key}
```

### 3. Missing Environment Variable
```python
# ❌ BAD - Silent failure
url = os.getenv('CLOUD_LICENSE_URL', 'default_wrong_url')

# ✅ GOOD - Fail loudly
url = os.getenv('CLOUD_LICENSE_URL')
if not url:
    raise ValueError("CLOUD_LICENSE_URL not configured!")
```

### 4. Hardcoded URLs
```python
# ❌ WRONG - Brittle
url = "https://asia-southeast1-v-track-payments.cloudfunctions.net/license-service"

# ✅ CORRECT - Flexible
url = os.getenv('CLOUD_LICENSE_URL')
```

---

## 🧪 Testing & Validation

### Test CloudFunction Connectivity
```bash
# From terminal
curl "https://asia-southeast1-v-track-payments.cloudfunctions.net/license_service?action=health"

# From Python
cloud_client = get_cloud_client()
health = cloud_client.health_check()
print(health)
```

### Validate Configuration on Startup
```python
# Add to app.py startup
from modules.payments.cloud_function_client import get_cloud_client

cloud_client = get_cloud_client()
connection_test = cloud_client.test_connection()

if not connection_test.get('success'):
    logger.error(f"CloudFunction connection failed: {connection_test.get('error')}")
```

### List Deployed Functions
```bash
gcloud functions list --project=v-track-payments --region=asia-southeast1
```

---

## 📝 Notes for Developers

1. **Always check `.env` file** when CloudFunction calls fail
2. **Use constants** instead of hardcoding action names
3. **Test immediately** after changing CloudFunction URLs
4. **Check logs** at `/var/logs/app_latest.log` for detailed errors
5. **Validate configuration** on every app startup
6. **Never commit** `.env` files to Git

---

## 🆘 Troubleshooting

### CloudFunction Returns 404
→ Check function name in URL (underscore vs hyphen)
→ Run: `gcloud functions list --project=v-track-payments`

### "Unknown action" Error
→ Check action name spelling (must match CloudFunction exactly)
→ Reference this document's action name table

### License Activation Fails
→ Check `CLOUD_LICENSE_URL` in `.env`
→ Verify network connectivity
→ Check logs for detailed error messages

### Database Empty After Activation
→ Check CloudFunction returned success
→ Verify License.create() was called
→ Check database file permissions

---

**See Also**:
- CloudFunction deployment guide: `/V_Track_CloudFunctions/QUICK_REFERENCE.md`
- Full naming conventions: `/V_Track/docs/NAMING_CONVENTIONS.md`
- Payment routes: `/backend/modules/payments/payment_routes.py`
- CloudFunction client: `/backend/modules/payments/cloud_function_client.py`
