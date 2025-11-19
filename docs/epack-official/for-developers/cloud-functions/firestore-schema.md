# Firestore Database Schema

Database structure for ePACK Cloud Functions persistent storage.

---

## Table of Contents

1. [Overview](#overview)
2. [Collections](#collections)
3. [Data Models](#data-models)
4. [Indexes](#indexes)
5. [Security Rules](#security-rules)
6. [Data Flow](#data-flow)

---

## Overview

ePACK Cloud Functions uses Google Firestore (NoSQL document database) for persistent storage of:

- License data
- Payment metadata
- Trial usage tracking
- Configuration settings

### Database Location

- **Project**: `epack-payments`
- **Region**: `asia-southeast1` (Singapore)
- **Mode**: Native mode
- **Time Zone**: UTC

### Connection

Functions automatically connect using Application Default Credentials:

```python
from google.cloud import firestore

# Initialize client
db = firestore.Client(project='epack-payments')

# Access collection
licenses_ref = db.collection('vtrack_licenses')
```

---

## Collections

### 1. vtrack_licenses

Stores all generated license keys and their metadata.

**Collection Path**: `/vtrack_licenses/{license_key}`

**Document Structure**:

```json
{
  "license_key": "VTRACK-P1Y-1754352670-ABC12345",
  "customer_email": "user@example.com",
  "package_type": "personal_1y",
  "package_name": "Personal Annual",
  "product_type": "personal_1y",
  "features": [
    "Unlimited cameras",
    "Advanced analytics",
    "Priority support"
  ],
  "status": "active",
  "created_at": "2025-10-06T10:00:00Z",
  "expires_at": "2026-10-06T00:00:00Z",
  "order_code": "9876543",
  "amount": 20000,
  "price": 20000,
  "machine_fingerprint": null,
  "is_trial": false,
  "trial_duration_days": null,
  "created_timestamp": Timestamp(1728208800, 0)
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `license_key` | string | Yes | Unique license key (also document ID) |
| `customer_email` | string | Yes | Customer email address |
| `package_type` | string | Yes | Package code (personal_1m, personal_1y, etc.) |
| `package_name` | string | Yes | Human-readable package name |
| `product_type` | string | Yes | Product type identifier |
| `features` | array | Yes | List of included features |
| `status` | string | Yes | License status: `active`, `expired`, `revoked` |
| `created_at` | string | Yes | ISO 8601 timestamp |
| `expires_at` | string | Yes | ISO 8601 expiration timestamp |
| `order_code` | string | Yes | PayOS order code |
| `amount` | number | Yes | Payment amount in VND |
| `price` | number | Yes | Package price |
| `machine_fingerprint` | string | No | Machine fingerprint (for activated licenses) |
| `is_trial` | boolean | No | Whether this is a trial license |
| `trial_duration_days` | number | No | Trial duration if applicable |
| `created_timestamp` | Timestamp | Yes | Firestore server timestamp |

**Indexes**:

- `customer_email` (Ascending) + `created_at` (Descending)
- `status` (Ascending) + `expires_at` (Ascending)
- `machine_fingerprint` (Ascending)

**Sample Query**:

```python
# Get all licenses for a customer
licenses = db.collection('vtrack_licenses') \
    .where('customer_email', '==', 'user@example.com') \
    .order_by('created_at', direction='DESCENDING') \
    .get()

# Get active licenses expiring soon
import datetime
soon = datetime.datetime.now() + datetime.timedelta(days=30)
expiring_licenses = db.collection('vtrack_licenses') \
    .where('status', '==', 'active') \
    .where('expires_at', '<', soon.isoformat()) \
    .get()
```

---

### 2. payment_metadata

Stores payment metadata for webhook lookup.

**Collection Path**: `/payment_metadata/{order_code}`

**Document Structure**:

```json
{
  "order_code": 9876543,
  "customer_email": "user@example.com",
  "package_type": "personal_1y",
  "amount": 20000,
  "created_at": Timestamp(1728208800, 0),
  "updated_at": Timestamp(1728208800, 0),
  "status": "pending",
  "provider": "payos",
  "project_id": "epack-payments"
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `order_code` | number | Yes | Unique order code (also document ID) |
| `customer_email` | string | Yes | Customer email address |
| `package_type` | string | Yes | Package type code |
| `amount` | number | Yes | Payment amount in VND |
| `created_at` | Timestamp | Yes | Creation timestamp |
| `updated_at` | Timestamp | Yes | Last update timestamp |
| `status` | string | Yes | Payment status: `pending`, `completed`, `failed` |
| `provider` | string | Yes | Payment provider name |
| `project_id` | string | Yes | GCP project ID |

**Indexes**:

- `customer_email` (Ascending) + `created_at` (Descending)
- `status` (Ascending)

**Lifecycle**:

1. Created when payment order is generated
2. Status: `pending`
3. Updated to `completed` when webhook processes payment
4. Can be queried by webhook handler to retrieve customer info

**Sample Query**:

```python
# Get pending payments
pending = db.collection('payment_metadata') \
    .where('status', '==', 'pending') \
    .get()

# Get payment by order code
payment = db.collection('payment_metadata') \
    .document(str(order_code)) \
    .get()
```

---

### 3. trial_usage

Tracks trial license usage to prevent abuse.

**Collection Path**: `/trial_usage/{machine_fingerprint}`

**Document Structure**:

```json
{
  "machine_fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "trial_license_key": "VTRACK-T7D-ABC12345-XYZ678",
  "trial_activated_at": Timestamp(1728208800, 0),
  "trial_expires_at": Timestamp(1728813600, 0),
  "ip_address": "123.45.67.89",
  "app_version": "2.1.0",
  "device_info": {
    "os": "Darwin 22.6.0",
    "cpu": "Apple M1",
    "activated_via": "desktop_app"
  },
  "status": "active"
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `machine_fingerprint` | string | Yes | Unique machine identifier (document ID) |
| `trial_license_key` | string | Yes | Generated trial license key |
| `trial_activated_at` | Timestamp | Yes | Trial activation timestamp |
| `trial_expires_at` | Timestamp | Yes | Trial expiration timestamp |
| `ip_address` | string | No | Client IP address |
| `app_version` | string | No | Application version |
| `device_info` | map | No | Device information object |
| `status` | string | Yes | Trial status: `active`, `expired`, `revoked` |

**Indexes**:

- `ip_address` (Ascending) + `trial_activated_at` (Descending)
- `status` (Ascending)
- `trial_expires_at` (Ascending)

**Purpose**:

- Enforce one trial per machine
- Detect abuse patterns (multiple trials from same IP)
- Track trial expirations

**Sample Query**:

```python
# Check if machine has used trial
trial_usage = db.collection('trial_usage') \
    .document(machine_fingerprint) \
    .get()

if trial_usage.exists:
    print("Trial already used")

# Get all trials from an IP (abuse detection)
trials_from_ip = db.collection('trial_usage') \
    .where('ip_address', '==', '123.45.67.89') \
    .get()

if len(trials_from_ip) > 5:
    print("Potential abuse detected")
```

---

### 4. trial_settings

Global trial system configuration.

**Collection Path**: `/trial_settings/config`

**Document Structure**:

```json
{
  "trial_enabled": true,
  "trial_duration_days": 7,
  "max_trials_per_ip": 5,
  "max_trials_per_day": 100,
  "abuse_detection_enabled": true,
  "last_updated": Timestamp(1728208800, 0),
  "updated_by": "admin@vtrack.com"
}
```

**Field Descriptions**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trial_enabled` | boolean | Yes | Whether trial system is active |
| `trial_duration_days` | number | Yes | Trial duration in days |
| `max_trials_per_ip` | number | Yes | Maximum trials from single IP |
| `max_trials_per_day` | number | Yes | Maximum total trials per day |
| `abuse_detection_enabled` | boolean | Yes | Enable abuse detection |
| `last_updated` | Timestamp | Yes | Last configuration update |
| `updated_by` | string | Yes | Admin who updated config |

**Usage**:

```python
# Get trial settings
settings = db.collection('trial_settings') \
    .document('config') \
    .get()

if settings.exists:
    config = settings.to_dict()
    if config['trial_enabled']:
        duration = config['trial_duration_days']
```

---

## Data Models

### License Key Format

```
VTRACK-{PACKAGE}-{TIMESTAMP}-{UUID}

Examples:
- VTRACK-P1M-1754352670-ABC12345  (Personal Monthly)
- VTRACK-P1Y-1754352670-XYZ67890  (Personal Annual)
- VTRACK-B1M-1754352670-DEF12345  (Business Monthly)
- VTRACK-B1Y-1754352670-GHI67890  (Business Annual)
- VTRACK-T7D-1754352670-JKL12345  (Trial 7 Days)
- VTRACK-T24H-1754352670-MNO67890 (Trial 24 Hours)
```

**Components**:

1. **Prefix**: `VTRACK`
2. **Package Code**:
   - `P1M` = Personal 1 Month
   - `P1Y` = Personal 1 Year
   - `B1M` = Business 1 Month
   - `B1Y` = Business 1 Year
   - `T7D` = Trial 7 Days
   - `T24H` = Trial 24 Hours
3. **Timestamp**: Unix timestamp (10 digits)
4. **UUID**: Random 8-character uppercase alphanumeric

### Machine Fingerprint Format

SHA256 hash of hardware components:

```python
import hashlib
import platform
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
fingerprint = hashlib.sha256(fingerprint_string.encode()).hexdigest()

# Result: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"
```

---

## Indexes

### Composite Indexes

Required for complex queries:

```javascript
// vtrack_licenses collection
{
  "collectionGroup": "vtrack_licenses",
  "queryScope": "COLLECTION",
  "fields": [
    { "fieldPath": "customer_email", "order": "ASCENDING" },
    { "fieldPath": "created_at", "order": "DESCENDING" }
  ]
}

{
  "collectionGroup": "vtrack_licenses",
  "queryScope": "COLLECTION",
  "fields": [
    { "fieldPath": "status", "order": "ASCENDING" },
    { "fieldPath": "expires_at", "order": "ASCENDING" }
  ]
}

// trial_usage collection
{
  "collectionGroup": "trial_usage",
  "queryScope": "COLLECTION",
  "fields": [
    { "fieldPath": "ip_address", "order": "ASCENDING" },
    { "fieldPath": "trial_activated_at", "order": "DESCENDING" }
  ]
}
```

### Create Indexes via CLI

```bash
gcloud firestore indexes composite create \
  --collection-group=vtrack_licenses \
  --field-config field-path=customer_email,order=ascending \
  --field-config field-path=created_at,order=descending

gcloud firestore indexes composite create \
  --collection-group=vtrack_licenses \
  --field-config field-path=status,order=ascending \
  --field-config field-path=expires_at,order=ascending
```

---

## Security Rules

Firestore security rules for production:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Helper functions
    function isAuthenticated() {
      return request.auth != null;
    }

    function isCloudFunction() {
      // Cloud Functions use service account
      return request.auth.token.email.matches('.*@epack-payments.iam.gserviceaccount.com$');
    }

    // vtrack_licenses - Read by authenticated users, write by Cloud Functions only
    match /vtrack_licenses/{licenseKey} {
      allow read: if isAuthenticated();
      allow write: if isCloudFunction();
    }

    // payment_metadata - Cloud Functions only
    match /payment_metadata/{orderCode} {
      allow read, write: if isCloudFunction();
    }

    // trial_usage - Cloud Functions only
    match /trial_usage/{fingerprint} {
      allow read, write: if isCloudFunction();
    }

    // trial_settings - Read by Cloud Functions, write by admins
    match /trial_settings/{document=**} {
      allow read: if isCloudFunction();
      allow write: if isCloudFunction() &&
                     request.auth.token.email == 'admin@vtrack.com';
    }
  }
}
```

Apply rules:

```bash
# Save to firestore.rules file
gcloud firestore databases patch \
  --security-rules-file=firestore.rules \
  --project=epack-payments
```

---

## Data Flow

### Payment Flow

```
1. create-payment → Creates payment_metadata document
   ├─ Collection: payment_metadata
   ├─ Document ID: order_code
   └─ Status: pending

2. User completes payment on PayOS

3. webhook-handler → Receives PayOS callback
   ├─ Queries payment_metadata by order_code
   ├─ Creates vtrack_licenses document
   │  ├─ Document ID: license_key
   │  └─ Status: active
   └─ Updates payment_metadata status to completed
```

### Trial License Flow

```
1. license-service (check_trial_eligibility)
   ├─ Queries trial_usage by machine_fingerprint
   ├─ If exists → Return "already used"
   └─ If not exists → Return "eligible"

2. license-service (generate_trial_license)
   ├─ Creates vtrack_licenses document
   │  ├─ Document ID: trial_license_key
   │  ├─ is_trial: true
   │  └─ Status: active
   └─ Creates trial_usage document
      ├─ Document ID: machine_fingerprint
      └─ Status: active
```

### License Validation Flow

```
1. license-service (validate_license)
   ├─ Queries vtrack_licenses by license_key
   ├─ Checks expires_at vs current time
   ├─ Checks status == "active"
   └─ Returns validation result
```

---

## Maintenance

### Cleanup Expired Licenses

```python
from google.cloud import firestore
from datetime import datetime, timedelta

db = firestore.Client()

# Find expired licenses
now = datetime.now()
expired = db.collection('vtrack_licenses') \
    .where('status', '==', 'active') \
    .where('expires_at', '<', now.isoformat()) \
    .get()

# Update status
for doc in expired:
    doc.reference.update({'status': 'expired'})
    print(f"Expired: {doc.id}")
```

### Archive Old Payment Metadata

```python
# Archive metadata older than 1 year
cutoff = datetime.now() - timedelta(days=365)

old_payments = db.collection('payment_metadata') \
    .where('created_at', '<', cutoff) \
    .get()

for doc in old_payments:
    # Move to archive collection
    archive_ref = db.collection('payment_metadata_archive').document(doc.id)
    archive_ref.set(doc.to_dict())

    # Delete from main collection
    doc.reference.delete()
```

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**Database**: Firestore Native Mode
