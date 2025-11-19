# ePACK Cloud Functions Documentation

Serverless backend infrastructure for ePACK payment processing, license management, and pricing services.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Services](#services)
4. [Integration with ePACK](#integration-with-v_track)
5. [Quick Links](#quick-links)

---

## Overview

ePACK Cloud Functions is a serverless backend deployed on Google Cloud Platform that handles:

- **Payment Processing**: PayOS integration for Vietnamese payment gateway
- **License Management**: Cloud-based license validation and trial system
- **Pricing Service**: Centralized pricing configuration (Single Source of Truth)
- **Webhook Handling**: Automated license generation and email delivery

### Key Features

- Serverless architecture (Google Cloud Functions)
- PayOS payment gateway integration
- Firestore database for persistent storage
- Automated license generation and delivery
- Trial license system with abuse prevention
- SMTP email delivery for license keys
- Dynamic pricing management

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Python | 3.9+ |
| Framework | Functions Framework | 3.4.0 |
| Database | Google Firestore | 2.13.1 |
| Payment SDK | PayOS | 0.1.8 |
| Email | SMTP (Gmail) | Built-in |
| Deployment | gcloud CLI | Latest |

### Project Structure

```
ePACK_CloudFunctions/
├── functions/
│   ├── create_payment/     # Payment creation service
│   ├── webhook_handler/     # PayOS webhook processor
│   ├── license_service/     # License validation & trial system
│   └── pricing_service/     # Centralized pricing management
├── shared/
│   └── payos_client.py     # Shared PayOS utilities
├── deployment/
│   └── deploy_all.sh       # Deployment automation
├── tests/                   # Integration & unit tests
├── scripts/                 # Setup & diagnostic tools
└── tools/                   # Pricing management utilities
```

---

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ePACK Desktop App                          │
│                    (Frontend + Backend)                          │
└───────────────┬──────────────────────────────┬──────────────────┘
                │                              │
                │ POST /api/payment/create     │ POST /api/payment/activate-license
                │                              │ GET /api/payment/validate-license
                │                              │
                ▼                              ▼
┌───────────────────────────────┐  ┌──────────────────────────────┐
│   create-payment Function     │  │  license-service Function    │
│   (asia-southeast1)           │  │  (asia-southeast1)           │
├───────────────────────────────┤  ├──────────────────────────────┤
│ • PayOS SDK integration       │  │ • License validation         │
│ • Dynamic pricing lookup      │  │ • Trial eligibility check    │
│ • Firestore metadata storage  │  │ • Trial license generation   │
│ • Payment link generation     │  │ • Abuse detection            │
└───────────┬───────────────────┘  └────────────┬─────────────────┘
            │                                   │
            │ Fetch pricing                     │ Query licenses
            ▼                                   ▼
┌───────────────────────────────┐  ┌──────────────────────────────┐
│  pricing-service Function     │  │    Google Firestore          │
│  (asia-southeast1)            │  │    (Database)                │
├───────────────────────────────┤  ├──────────────────────────────┤
│ • Centralized pricing config  │  │ Collections:                 │
│ • Package definitions         │  │ • vtrack_licenses            │
│ • Price updates               │  │ • payment_metadata           │
│ • Version control             │  │ • trial_usage                │
└───────────────────────────────┘  │ • trial_settings             │
                                   └──────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                         PayOS Gateway                            │
│                    (Vietnamese Payment System)                   │
└───────────┬─────────────────────────────────────────────────────┘
            │
            │ Webhook callback (on payment success)
            ▼
┌───────────────────────────────┐
│  webhook-handler Function     │
│  (asia-southeast1)            │
├───────────────────────────────┤
│ • Payment verification        │
│ • License key generation      │
│ • Firestore storage           │
│ • Email delivery (SMTP)       │
└───────────────────────────────┘
```

### Data Flow

#### Payment Flow

1. **User selects package** in ePACK desktop app
2. **App calls** `create-payment` Cloud Function
3. **Function fetches** current pricing from `pricing-service`
4. **Function saves** payment metadata to Firestore
5. **Function creates** PayOS payment link
6. **User redirected** to PayOS payment page
7. **User completes** payment
8. **PayOS sends** webhook to `webhook-handler`
9. **Handler generates** license key
10. **Handler saves** license to Firestore
11. **Handler sends** email with license key
12. **User receives** email and activates license

#### License Validation Flow

1. **App sends** license key to `license-service`
2. **Function queries** Firestore for license data
3. **Function validates** expiration date and status
4. **Function returns** validation result
5. **App grants/denies** access based on result

#### Trial License Flow

1. **App sends** machine fingerprint to `license-service`
2. **Function checks** trial usage history
3. **Function validates** eligibility (abuse detection)
4. **Function generates** trial license key
5. **Function records** trial usage (prevent reuse)
6. **Function returns** trial license data

---

## Services

### 1. create-payment

Payment creation service with PayOS integration.

**Entry Point**: `functions/create_payment/main.py:create_payment_handler()`

**Key Features**:
- PayOS SDK integration for payment link generation
- Dynamic pricing from `pricing-service`
- Firestore metadata storage for webhook lookup
- CORS support for cross-origin requests
- Health check endpoint

**API Endpoints**:
- `POST /` - Create payment order
- `GET /?action=health` - Health check

**Dependencies**:
- PayOS SDK (`payos==0.1.8`)
- Firestore client (`firebase-admin`)
- Requests library for pricing service calls

[Full API Documentation →](./api-reference.md#create-payment)

### 2. webhook-handler

PayOS webhook processor for automated license delivery.

**Entry Point**: `functions/webhook_handler/main.py:main()`

**Key Features**:
- PayOS webhook verification
- License key generation (format: `VTRACK-{PKG}-{TIMESTAMP}-{UUID}`)
- Firestore license storage
- Automated email delivery via SMTP
- HTML email templates

**API Endpoints**:
- `POST /` - Process PayOS webhook
- `GET /?action=health` - Health check
- `GET /?action=test_email` - Test email delivery

**License Key Format**:
```
VTRACK-P1Y-1754352670-ABC12345
│      │   │          │
│      │   │          └─ Random UUID (8 chars)
│      │   └─ Unix timestamp
│      └─ Package code (P1M, P1Y, B1M, B1Y, T24H)
└─ Prefix
```

[Full API Documentation →](./api-reference.md#webhook-handler)

### 3. license-service

License validation and trial management service.

**Entry Point**: `functions/license_service/main.py:license_service()`

**Key Features**:
- License validation by key
- License lookup by customer email
- Trial eligibility checking
- Trial license generation
- Abuse detection (IP-based limits)
- Machine fingerprint tracking

**API Endpoints**:
- `GET /?action=validate&license_key={key}` - Validate license
- `GET /?action=health` - Health check
- `POST /` with `action=get_licenses` - Get licenses by email
- `POST /` with `action=check_trial_eligibility` - Check trial eligibility
- `POST /` with `action=generate_trial_license` - Generate trial license

**Trial System**:
- Default trial duration: 7 days
- One trial per machine fingerprint
- IP-based abuse detection
- Configurable trial settings in Firestore

[Full API Documentation →](./api-reference.md#license-service)

### 4. pricing-service

Centralized pricing management (Single Source of Truth).

**Entry Point**: `functions/pricing_service/main.py:pricing_service()`

**Key Features**:
- Centralized package definitions
- Version-controlled pricing
- No external dependencies (pure Python)
- Fast response times (<100ms)
- CORS support

**API Endpoints**:
- `GET /?action=get_packages` - Get all packages
- `GET /?action=get_packages&package={code}` - Get specific package
- `GET /?action=health` - Health check

**Package Configuration**:
```python
CURRENT_PACKAGES = {
    'personal_1m': {
        'name': 'Personal Monthly',
        'price': 3000,  # VND
        'duration_days': 30,
        'features': [...]
    },
    # ... more packages
}
```

[Full API Documentation →](./api-reference.md#pricing-service)

---

## Integration with ePACK

### Desktop App Integration Points

#### Payment Creation

**Backend**: `/backend/blueprints/payment_bp.py`

```python
@payment_bp.route('/create', methods=['POST'])
def create_payment():
    # Calls create-payment Cloud Function
    cloud_function_url = "https://asia-southeast1-epack-payments.cloudfunctions.net/create-payment"
    response = requests.post(cloud_function_url, json={
        'customer_email': request.json['customer_email'],
        'package_type': request.json['package_type'],
        'return_url': 'http://localhost:8080/payment/redirect',
        'cancel_url': 'http://localhost:8080/payment/redirect'
    })
```

**Frontend**: `/frontend/app/plan/page.tsx`

```typescript
const createPayment = async (packageType: string) => {
  const response = await fetch('/api/payment/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      customer_email: userEmail,
      package_type: packageType
    })
  });

  const data = await response.json();
  window.location.href = data.payment_url;
};
```

#### License Validation

**Backend**: `/backend/modules/payments/cloud_function_client.py`

```python
class CloudFunctionClient:
    def validate_license(self, license_key: str):
        url = f"{self.license_service_url}?action=validate&license_key={license_key}"
        response = requests.get(url, timeout=10)
        return response.json()
```

#### Trial License Generation

**Backend**: `/backend/modules/payments/cloud_function_client.py`

```python
def generate_trial_license(self, machine_fingerprint: str):
    response = requests.post(self.license_service_url, json={
        'action': 'generate_trial_license',
        'machine_fingerprint': machine_fingerprint,
        'client_ip': get_client_ip(),
        'app_version': get_app_version()
    })
```

### Environment Configuration

**Desktop App** (`.env` or config):
```bash
# Cloud Function URLs
PAYMENT_FUNCTION_URL=https://asia-southeast1-epack-payments.cloudfunctions.net/create-payment
LICENSE_SERVICE_URL=https://asia-southeast1-epack-payments.cloudfunctions.net/license-service
PRICING_SERVICE_URL=https://asia-southeast1-epack-payments.cloudfunctions.net/pricing-service
```

**Cloud Functions** (GCP environment variables):
```bash
# PayOS Configuration
PAYOS_CLIENT_ID=your_client_id
PAYOS_API_KEY=your_api_key
PAYOS_CHECKSUM_KEY=your_checksum_key

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Google Cloud
GOOGLE_CLOUD_PROJECT=epack-payments
```

---

## Quick Links

### Documentation

- [API Reference](./api-reference.md) - Complete API documentation
- [Setup & Deployment](./deployment-guide.md) - Installation and deployment guide
- [Development Guide](./development-guide.md) - Local development and testing
- [Firestore Schema](./firestore-schema.md) - Database structure

### Related ePACK Documentation

- [License & Payment User Guide](../../for-users/license-payment.md)
- [ePACK Architecture Overview](../architecture/overview.md)
- [Backend Payment Blueprint](/backend/blueprints/payment_bp.py)
- [Payment Cloud Client](/backend/modules/payments/cloud_function_client.py)

### External Resources

- [Google Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [PayOS Integration Guide](https://payos.vn/docs)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)

---

## Support

**For Development Issues**:
- Check [Troubleshooting Guide](./troubleshooting.md)
- Review Cloud Function logs: `gcloud functions logs read {function-name}`
- Contact development team

**For Production Issues**:
- Monitor Firestore console
- Check PayOS dashboard
- Review email delivery logs

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**Maintained By**: ePACK Development Team
