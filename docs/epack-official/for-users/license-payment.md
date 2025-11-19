# License & Payment User Guide

**ePACK Subscription Management & License Activation**

---

## Table of Contents

1. [Overview](#overview)
2. [Subscription Plans](#subscription-plans)
3. [Payment Process](#payment-process)
4. [License Activation](#license-activation)
5. [Machine Fingerprinting](#machine-fingerprinting)
6. [License Validation](#license-validation)
7. [Subscription Management](#subscription-management)
8. [Troubleshooting](#troubleshooting)
9. [Security & Privacy](#security--privacy)

---

## Overview

ePACK uses a cloud-based licensing system with PayOS payment integration. Each license is tied to a specific machine using hardware fingerprinting, ensuring secure single-device activation.

### Key Features

- Cloud-validated licenses
- Offline fallback support
- Single-device activation
- Auto-renewal options
- Trial period support
- Email delivery of license keys

### System Architecture

```
Frontend (Plan Page) → Backend API → Cloud Function → PayOS Gateway
                            ↓
                    Local Database (licenses table)
                            ↓
                    Machine Fingerprint Validation
```

---

## Subscription Plans

### Available Plans

ePACK offers four subscription tiers:

#### 1. Personal Monthly (P1M)
```json
{
  "product_type": "personal_1m",
  "duration": "30 days",
  "price": "Variable (see PayOS)",
  "features": ["full_access"],
  "max_cameras": "Unlimited",
  "cloud_storage": "Google Drive only"
}
```

#### 2. Personal Annual (P1Y)
```json
{
  "product_type": "personal_1y",
  "duration": "365 days",
  "price": "Variable (see PayOS)",
  "features": ["full_access"],
  "max_cameras": "Unlimited",
  "cloud_storage": "Google Drive only",
  "savings": "~17% vs monthly"
}
```

#### 3. Business Monthly (B1M)
```json
{
  "product_type": "business_1m",
  "duration": "30 days",
  "price": "Variable (see PayOS)",
  "features": ["full_access", "priority_support"],
  "max_cameras": "Unlimited",
  "cloud_storage": "Google Drive only"
}
```

#### 4. Business Annual (B1Y)
```json
{
  "product_type": "business_1y",
  "duration": "365 days",
  "price": "Variable (see PayOS)",
  "features": ["full_access", "priority_support"],
  "max_cameras": "Unlimited",
  "cloud_storage": "Google Drive only",
  "savings": "~17% vs monthly"
}
```

#### 5. Trial Extension (T24H)
```json
{
  "product_type": "trial_24h",
  "duration": "1 day (24 hours)",
  "price": "Variable (see PayOS)",
  "features": ["trial_access"],
  "use_case": "Extend trial after initial period"
}
```

### Fetching Available Plans

**API Endpoint**: `GET /api/payment/packages`

**Request Parameters**:
```
?for_upgrade=true  // Force fresh pricing fetch
?fresh=true        // Bypass cache
```

**Response**:
```json
{
  "success": true,
  "packages": {
    "personal_1m": {
      "name": "Personal Monthly",
      "price": 99000,
      "currency": "VND",
      "duration": "30 days",
      "features": ["full_access"]
    },
    "personal_1y": {
      "name": "Personal Annual",
      "price": 990000,
      "currency": "VND",
      "duration": "365 days",
      "features": ["full_access"]
    }
  },
  "server_timestamp": "2025-01-15T10:00:00Z",
  "request_type": "upgrade"
}
```

---

## Payment Process

### Step-by-Step Payment Flow

#### Step 1: Select Plan

Navigate to Plan page (`/plan`) and select subscription:

```typescript
// Frontend: app/plan/page.tsx
import MyPlan from '@/components/account/MyPlan';

export default function PlanPage() {
  return <MyPlan />;
}
```

#### Step 2: Create Payment

**API Endpoint**: `POST /api/payment/create`

**Request**:
```json
{
  "customer_email": "user@example.com",
  "package_type": "personal_1y",
  "return_url": "http://localhost:8080/payment/redirect",
  "cancel_url": "http://localhost:8080/payment/redirect"
}
```

**Response**:
```json
{
  "success": true,
  "payment_url": "https://payos.vn/payment/ABC123",
  "order_code": "VTR2025011512345",
  "amount": 990000,
  "redirect_urls": {
    "success": "http://localhost:8080/payment/redirect",
    "cancel": "http://localhost:8080/payment/redirect"
  }
}
```

#### Step 3: Complete Payment

1. User redirected to PayOS payment page
2. Select payment method (QR, bank transfer, card)
3. Complete payment
4. PayOS validates transaction
5. Cloud Function generates license key
6. License key emailed to customer

#### Step 4: Payment Callback

PayOS sends callback to cloud function:
```
POST https://your-cloud-function.cloudfunctions.net/vtrack-payment/webhook
```

Cloud function processes:
1. Verify payment signature
2. Generate license key format: `VTRACK-{PACKAGE}-{RANDOM}`
3. Save to Firestore
4. Send email to customer
5. Return success response

### Payment Database Tables

#### payment_transactions
```sql
CREATE TABLE payment_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_trans_id TEXT UNIQUE NOT NULL,     -- VTR2025011512345
    payment_trans_id TEXT,                  -- PayOS transaction ID
    customer_email TEXT NOT NULL,
    amount INTEGER NOT NULL,                -- Amount in VND
    status TEXT DEFAULT 'pending',          -- pending, completed, failed
    payment_data TEXT,                      -- JSON metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### licenses
```sql
CREATE TABLE licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT NOT NULL UNIQUE,       -- VTRACK-P1Y-ABC123XYZ
    customer_email TEXT NOT NULL,
    payment_transaction_id INTEGER,
    product_type TEXT NOT NULL,             -- personal_1y, business_1m, etc.
    features TEXT NOT NULL,                 -- JSON array: ["full_access"]
    status TEXT NOT NULL DEFAULT 'active',  -- active, expired, revoked
    activated_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    machine_fingerprint TEXT,
    activation_count INTEGER DEFAULT 0,
    max_activations INTEGER DEFAULT 1,
    FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(id)
);
```

---

## License Activation

### Activation Workflow

#### Step 1: Receive License Key

After payment, customer receives email:

```
Subject: Your ePACK License Key

Dear Customer,

Thank you for your purchase!

License Key: VTRACK-P1Y-ABC123XYZ456
Package: Personal Annual
Expires: 2026-01-15

To activate:
1. Open ePACK application
2. Go to Plan page
3. Click "Activate License"
4. Enter your license key
5. Click "Activate"

Best regards,
ePACK Team
```

#### Step 2: Enter License Key

Navigate to Plan page → "Activate License" section

**Frontend Flow**:
```typescript
const handleActivate = async () => {
  const response = await fetch('/api/payment/activate-license', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ license_key: inputKey })
  });

  const result = await response.json();
  // Handle result
};
```

#### Step 3: Validation & Activation

**API Endpoint**: `POST /api/payment/activate-license`

**Process**:

1. **Cloud Validation**:
```python
# Validate with cloud function
cloud_result = cloud_client.validate_license(license_key)

if not cloud_result.get('valid'):
    # Try offline fallback
    return _database_only_activation(license_key)
```

2. **Create Local Record**:
```python
# Import license models
from modules.licensing.license_models import License

# Extract package info from key format: VTRACK-P1Y-...
package_info = extract_package_from_license_key(license_key)

# Create license record
license_id = License.create(
    license_key=license_key,
    customer_email=license_data.get('customer_email'),
    product_type=package_info.get('product_type'),
    features=license_data.get('features', ['full_access']),
    expires_days=package_info.get('expires_days', 365)
)
```

3. **Machine Activation**:
```python
from modules.license.machine_fingerprint import generate_machine_fingerprint

current_fingerprint = generate_machine_fingerprint()

# Check if already activated on this machine
cursor.execute("""
    SELECT machine_fingerprint
    FROM license_activations
    WHERE license_id = ? AND status = 'active'
""", (license_id,))

# Create activation record
cursor.execute("""
    INSERT INTO license_activations
    (license_id, machine_fingerprint, activation_time, status, device_info)
    VALUES (?, ?, ?, 'active', ?)
""", (license_id, current_fingerprint, now, device_info_json))
```

**Response**:
```json
{
  "success": true,
  "valid": true,
  "data": {
    "license_key": "VTRACK-P1Y-ABC123XYZ456",
    "customer_email": "user@example.com",
    "package_name": "personal_1y",
    "expires_at": "2026-01-15T00:00:00Z",
    "status": "activated",
    "features": ["full_access"],
    "machine_fingerprint": "a1b2c3d4e5f6...",
    "activated_at": "2025-01-15T10:30:00Z"
  },
  "activation": {
    "source": "cloud",
    "method": "cloud",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Activation States

1. **Already Activated (This Machine)**:
```json
{
  "success": true,
  "data": {
    "status": "already_activated_this_machine",
    "activated_at": "2025-01-10T08:00:00Z"
  }
}
```

2. **Already Activated (Other Device)**:
```json
{
  "success": false,
  "valid": false,
  "error": "License already activated on another device",
  "data": {
    "status": "activated_elsewhere",
    "other_device_activated_at": "2025-01-10T08:00:00Z"
  }
}
```

3. **Offline Activation**:
```json
{
  "success": true,
  "data": {
    "status": "activated"
  },
  "activation": {
    "source": "database_only",
    "method": "local_activation"
  },
  "warning": {
    "message": "License activated from local database only",
    "reason": "cloud_completely_unavailable"
  }
}
```

---

## Machine Fingerprinting

### How It Works

ePACK generates a unique hardware fingerprint for each machine:

**Source**: `backend/modules/license/machine_fingerprint.py`

```python
def generate_machine_fingerprint() -> str:
    """Generate unique machine fingerprint using hardware info"""
    import platform
    import hashlib
    import uuid

    components = [
        platform.node(),           # Computer name
        platform.machine(),        # CPU architecture
        platform.processor(),      # Processor type
        str(uuid.getnode()),      # MAC address
        platform.system(),         # OS name
        platform.release()         # OS version
    ]

    fingerprint_string = '|'.join(components)
    fingerprint_hash = hashlib.sha256(
        fingerprint_string.encode()
    ).hexdigest()

    return fingerprint_hash
```

### Fingerprint Components

| Component | Example | Purpose |
|-----------|---------|---------|
| Computer Name | `DESKTOP-ABC123` | Identify specific machine |
| CPU Architecture | `x86_64`, `arm64` | Hardware differentiation |
| Processor Type | `Intel Core i7` | CPU identification |
| MAC Address | `12:34:56:78:90:AB` | Network interface ID |
| OS Name | `Windows`, `Darwin`, `Linux` | Operating system |
| OS Version | `10.0.19041`, `22.6.0` | OS version |

### Security Features

1. **One-Way Hashing**: SHA-256 prevents reverse engineering
2. **Hardware-Based**: Not easily spoofed
3. **Persistent**: Survives software reinstalls
4. **Privacy-Friendly**: No personal information stored

### Fingerprint Storage

**Database Table**: `license_activations`

```sql
CREATE TABLE license_activations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    machine_fingerprint TEXT NOT NULL,
    activation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,
    status TEXT DEFAULT 'active',
    device_info TEXT,                    -- JSON: OS, CPU, etc.
    FOREIGN KEY (license_id) REFERENCES licenses(id),
    UNIQUE(license_id, machine_fingerprint)
);
```

**Example Record**:
```json
{
  "license_id": 1,
  "machine_fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "activation_time": "2025-01-15T10:30:00Z",
  "status": "active",
  "device_info": {
    "os": "Darwin 22.6.0",
    "cpu": "Apple M1",
    "activated_via": "desktop_app",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

---

## License Validation

### Real-Time Validation

**API Endpoint**: `POST /api/payment/validate-license`

**Request**:
```json
{
  "license_key": "VTRACK-P1Y-ABC123XYZ456"
}
```

**Validation Process**:

1. **Pre-Validation** (Local):
```python
def is_obviously_invalid_license(license_key: str) -> bool:
    invalid_patterns = ['INVALID-', 'invalid', 'test', 'fake', 'demo']
    return any(license_key.upper().startswith(p.upper())
               for p in invalid_patterns)
```

2. **Cloud Validation** (Primary):
```python
cloud_client = get_cloud_client()
result = cloud_client.validate_license(license_key)

if result.get('source') == 'cloud':
    # Full validation completed
    return {
        'success': True,
        'valid': True,
        'data': result.get('data')
    }
```

3. **Offline Fallback** (Secondary):
```python
if validation_source == 'offline':
    # Check local database
    existing_license = License.get_by_key(license_key)

    # Validate expiry
    if existing_license.get('expires_at'):
        expiry_date = datetime.fromisoformat(expires_at)
        if datetime.now() > expiry_date:
            return {'valid': False, 'reason': 'expired'}

    return {'valid': True, 'source': 'database_only'}
```

**Response (Online)**:
```json
{
  "success": true,
  "valid": true,
  "data": {
    "license_key": "VTRACK-P1Y-ABC123XYZ456",
    "customer_email": "user@example.com",
    "package_name": "personal_1y",
    "expires_at": "2026-01-15T00:00:00Z",
    "features": ["full_access"]
  },
  "validation": {
    "source": "cloud",
    "method": "cloud",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

**Response (Offline)**:
```json
{
  "success": true,
  "valid": true,
  "data": { /* ... */ },
  "validation": {
    "source": "offline",
    "method": "offline",
    "timestamp": "2025-01-15T10:30:00Z"
  },
  "warning": {
    "message": "License validated offline - some features may be limited",
    "reason": "cloud_unavailable",
    "recommendation": "Please check internet connection for full validation"
  }
}
```

### License Status Check

**API Endpoint**: `GET /api/payment/license-status`

**Response**:
```json
{
  "success": true,
  "license": {
    "license_key": "VTRACK-P1Y-ABC123XYZ456",
    "customer_email": "user@example.com",
    "package_name": "personal_1y",
    "package_type": "personal_1y",
    "expires_at": "2026-01-15T00:00:00Z",
    "status": "active",
    "features": ["full_access"],
    "activated_at": "2025-01-15T10:30:00Z",
    "is_active": true,
    "is_trial": false
  },
  "system_status": {
    "online": true,
    "source": "cloud",
    "timestamp": "2025-01-15T11:00:00Z"
  }
}
```

**No License Found**:
```json
{
  "success": true,
  "license": null,
  "message": "No active license found",
  "system_status": {
    "online": false,
    "source": "database",
    "timestamp": "2025-01-15T11:00:00Z"
  }
}
```

---

## Subscription Management

### Viewing Current License

Navigate to Plan page → View "Current License" section

**Display Information**:
- License key (partially masked): `VTRACK-P1Y-***********`
- Package name: `Personal Annual`
- Expiration date: `2026-01-15`
- Status: `Active` / `Expired` / `Expiring Soon`
- Days remaining: `350 days`

### Renewing Subscription

**Before Expiration**:
1. Navigate to Plan page
2. Click "Renew License"
3. Select same or different package
4. Complete payment
5. New license key generated
6. Activate new license (old one remains valid until expiry)

**After Expiration**:
1. Old license status: `expired`
2. Purchase new license
3. Activate new license key
4. Service restored immediately

### License Deactivation

**Note**: Current implementation does NOT support manual deactivation.

**Future Feature** (Roadmap):
```python
@payment_bp.route('/deactivate-license', methods=['POST'])
def deactivate_license():
    """Deactivate license on current machine"""
    # Remove activation record
    # Allow reactivation on different machine
```

---

## Troubleshooting

### Activation Issues

#### Error: "License already activated on another device"

**Cause**: License is tied to different machine fingerprint

**Solutions**:
1. Check if you're on the correct device
2. If you've reinstalled OS, fingerprint may have changed
3. Contact support to transfer license

#### Error: "Invalid license key format"

**Cause**: License key doesn't match format `VTRACK-{PACKAGE}-{RANDOM}`

**Solutions**:
1. Verify license key from email (copy-paste exactly)
2. Check for extra spaces or characters
3. Request new license key if corrupted

#### Error: "Cloud validation unavailable"

**Cause**: No internet connection or cloud service down

**Behavior**:
- System attempts offline validation
- Limited features may apply
- Recommendation: Connect to internet

**Offline Activation**:
```json
{
  "success": true,
  "warning": {
    "message": "License activated from local database only",
    "limitations": [
      "Payment features unavailable",
      "License updates may be delayed",
      "Cloud sync disabled"
    ]
  }
}
```

### Payment Issues

#### Payment Pending

**Check Status**:
1. Navigate to Plan page
2. Check "Payment History" section
3. View transaction status

**Common Reasons**:
- Bank processing delay (5-10 minutes)
- Insufficient funds
- Payment gateway timeout

#### License Not Received

**Steps**:
1. Check spam/junk email folder
2. Verify email address in payment
3. Wait 15 minutes for email delivery
4. Check cloud function logs (admin)
5. Contact support with order code

### Validation Issues

#### Expired License

**Symptoms**:
- License status: `expired`
- Features locked
- Trial prompt appears

**Solution**:
1. Purchase new license
2. Activate new key
3. Service restored immediately

#### Offline Validation Warnings

**Message**: "License validated offline - some features may be limited"

**Impact**:
- Core features work
- Payment/upgrade features disabled
- Cloud sync may be affected

**Solution**: Connect to internet for full validation

---

## Security & Privacy

### Data Encryption

**License Keys**:
- Generated server-side only
- SHA-256 hashed for storage
- Never stored in plain text

**Payment Data**:
- Handled entirely by PayOS
- PCI DSS compliant
- No card data stored locally

**Machine Fingerprints**:
- One-way SHA-256 hash
- Cannot be reverse-engineered
- No personal information included

### Privacy Policy

**Data Collected**:
- Customer email (for license delivery)
- Machine fingerprint (for activation)
- Payment transaction ID (for records)
- License usage statistics (anonymous)

**Data NOT Collected**:
- Credit card information
- Personal identification documents
- Detailed hardware specifications
- User activity logs

**Data Retention**:
- Active licenses: Indefinite
- Expired licenses: 1 year
- Payment transactions: 7 years (legal requirement)
- Machine fingerprints: Deleted on deactivation

### Compliance

- **GDPR**: Data deletion requests honored
- **PCI DSS**: Payment processing via certified gateway
- **Local Laws**: Vietnam E-commerce regulations

---

## Database Schema Reference

### Complete Licensing Tables

```sql
-- Payment transactions
CREATE TABLE payment_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_trans_id TEXT UNIQUE NOT NULL,
    payment_trans_id TEXT,
    customer_email TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    payment_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Licenses
CREATE TABLE licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT NOT NULL UNIQUE,
    customer_email TEXT NOT NULL,
    payment_transaction_id INTEGER,
    product_type TEXT NOT NULL DEFAULT 'desktop',
    features TEXT NOT NULL DEFAULT '["full_access"]',
    status TEXT NOT NULL DEFAULT 'active',
    activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    machine_fingerprint TEXT,
    activation_count INTEGER DEFAULT 0,
    max_activations INTEGER DEFAULT 1,
    FOREIGN KEY (payment_transaction_id) REFERENCES payment_transactions(id)
);

-- License activations
CREATE TABLE license_activations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    machine_fingerprint TEXT NOT NULL,
    activation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat TIMESTAMP,
    status TEXT DEFAULT 'active',
    device_info TEXT,
    FOREIGN KEY (license_id) REFERENCES licenses(id),
    UNIQUE(license_id, machine_fingerprint)
);

-- Email logs
CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER,
    recipient_email TEXT NOT NULL,
    email_type TEXT DEFAULT 'license_delivery',
    subject TEXT,
    status TEXT DEFAULT 'pending',
    sent_at TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (license_id) REFERENCES licenses(id)
);

-- Indexes
CREATE INDEX idx_payment_email ON payment_transactions(customer_email);
CREATE INDEX idx_licenses_key ON licenses(license_key);
CREATE INDEX idx_licenses_email ON licenses(customer_email);
CREATE INDEX idx_licenses_status ON licenses(status);
CREATE INDEX idx_licenses_expires ON licenses(expires_at);
```

---

## API Reference Summary

### Payment Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/payment/create` | POST | Create PayOS payment |
| `/api/payment/packages` | GET | Get available plans |
| `/api/payment/validate-license` | POST | Validate license key |
| `/api/payment/activate-license` | POST | Activate license on device |
| `/api/payment/license-status` | GET | Get current license status |
| `/api/payment/licenses/<email>` | GET | Get user licenses |
| `/api/payment/health` | GET | Check payment service health |

---

## Next Steps

- **[Trace Tracking Guide](./trace-tracking.md)**: Learn event tracking
- **[Cloud Sync Setup](./cloud-sync-advanced.md)**: Configure Google Drive
- **[API Documentation](../api/payment-endpoints.md)**: Developer reference

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**Author**: ePACK Documentation Team
