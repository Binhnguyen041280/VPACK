# Cloud Functions API Reference

Complete API documentation for ePACK Cloud Functions.

---

## Table of Contents

1. [create-payment](#create-payment)
2. [webhook-handler](#webhook-handler)
3. [license-service](#license-service)
4. [pricing-service](#pricing-service)
5. [Common Response Patterns](#common-response-patterns)
6. [Error Handling](#error-handling)

---

## create-payment

Payment creation service with PayOS integration.

**Base URL**: `https://asia-southeast1-epack-payments.cloudfunctions.net/create-payment`

### Create Payment Order

Create a new PayOS payment order for license purchase.

**Endpoint**: `POST /`

**Request Headers**:
```
Content-Type: application/json
```

**Request Body**:
```json
{
  "customer_email": "user@example.com",
  "package_type": "personal_1y",
  "return_url": "http://localhost:8080/payment/redirect",
  "cancel_url": "http://localhost:8080/payment/redirect"
}
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `customer_email` | string | Yes | Customer email address (must contain @) |
| `package_type` | string | Yes | Package code: `personal_1m`, `personal_1y`, `business_1m`, `business_1y`, `trial_24h` |
| `return_url` | string | No | URL to redirect after successful payment (default: localhost) |
| `cancel_url` | string | No | URL to redirect after cancelled payment (default: localhost) |

**Success Response** (200 OK):
```json
{
  "success": true,
  "payment_url": "https://payos.vn/payment/ABC123",
  "order_code": 9876543,
  "order_id": "vtrack_9876543",
  "provider": "payos",
  "amount": 20000,
  "customer_email": "user@example.com",
  "package_type": "personal_1y",
  "package_name": "Personal Annual",
  "firestore_metadata": true,
  "firestore_available": true,
  "metadata_error": null,
  "pricing_source": "pricing_service_cloudfunction"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Operation success status |
| `payment_url` | string | PayOS payment page URL (redirect user here) |
| `order_code` | integer | Unique order identifier |
| `order_id` | string | Formatted order ID with prefix |
| `provider` | string | Payment provider name |
| `amount` | integer | Payment amount in VND |
| `customer_email` | string | Customer email |
| `package_type` | string | Package type code |
| `package_name` | string | Human-readable package name |
| `firestore_metadata` | boolean | Whether metadata was saved to Firestore |
| `firestore_available` | boolean | Firestore service availability |
| `metadata_error` | string/null | Error message if metadata save failed |
| `pricing_source` | string | Source of pricing data |

**Error Responses**:

Missing required field (400 Bad Request):
```json
{
  "error": "Missing required field: customer_email"
}
```

Invalid email format (400 Bad Request):
```json
{
  "error": "Invalid email format"
}
```

Invalid package type (400 Bad Request):
```json
{
  "error": "Invalid package type: invalid_package. Please check pricing service."
}
```

Payment creation failed (500 Internal Server Error):
```json
{
  "error": "Payment creation failed"
}
```

### Health Check

Check service health and dependencies.

**Endpoint**: `GET /?action=health`

**Success Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "create_payment",
  "timestamp": "2025-10-06T10:30:00.123456",
  "provider": "payos_sdk",
  "firestore": {
    "status": "healthy",
    "available": true,
    "project_id": "epack-payments",
    "timestamp": "2025-10-06T10:30:00.123456"
  },
  "pricing_service": {
    "status": "healthy",
    "available": true,
    "url": "https://asia-southeast1-epack-payments.cloudfunctions.net/pricing-service"
  },
  "project_id": "epack-payments",
  "features": [
    "payos_integration",
    "firestore_integration",
    "dynamic_pricing"
  ]
}
```

---

## webhook-handler

PayOS webhook processor for automated license delivery.

**Base URL**: `https://asia-southeast1-epack-payments.cloudfunctions.net/webhook-handler`

### Process Payment Webhook

Process PayOS payment completion webhook.

**Endpoint**: `POST /`

**Request Headers**:
```
Content-Type: application/json
```

**Request Body** (PayOS webhook format):
```json
{
  "data": {
    "orderCode": 9876543,
    "amount": 20000,
    "code": "00",
    "paymentLinkId": "abc123xyz",
    "description": "VTrack-P1Y-6543",
    "transactions": [
      {
        "reference": "FT25100612345",
        "amount": 20000,
        "accountNumber": "1234567890",
        "description": "Payment for order 9876543"
      }
    ]
  },
  "signature": "payos_signature_hash"
}
```

**PayOS Webhook Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `data.orderCode` | integer | Order code from create-payment |
| `data.amount` | integer | Payment amount in VND |
| `data.code` | string | Payment status code ("00" = success) |
| `data.paymentLinkId` | string | PayOS payment link ID |
| `data.description` | string | Order description (contains package code) |

**Success Response** (200 OK):
```json
{
  "success": true,
  "order_code": 9876543,
  "license_generated": true,
  "license_key": "VTRACK-P1Y-1754352670-ABC12345",
  "email_sent": true,
  "customer_email": "user@example.com"
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Operation success status |
| `order_code` | integer | Order code from webhook |
| `license_generated` | boolean | Whether license was generated |
| `license_key` | string | Generated license key |
| `email_sent` | boolean | Whether email was sent successfully |
| `customer_email` | string | Recipient email address |

**Payment Failed Response** (200 OK):
```json
{
  "success": false,
  "status": "01",
  "message": "Payment not successful"
}
```

**Error Response** (400 Bad Request):
```json
{
  "error": "Webhook processing failed: {error_details}"
}
```

### Health Check

Check webhook handler health.

**Endpoint**: `GET /?action=health`

**Success Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "webhook_handler",
  "version": "firestore_only",
  "timestamp": "2025-10-06T10:30:00.123456",
  "features": {
    "payos_webhook": true,
    "license_generation": true,
    "email_delivery": true,
    "firestore_storage": true,
    "signature_verification": false
  }
}
```

### Test Email Delivery

Test email delivery system.

**Endpoint**: `GET /?action=test_email`

**Success Response** (200 OK):
```json
{
  "success": true,
  "message": "Test email sent",
  "email_result": {
    "success": true,
    "message": "Email sent to binhnguyen041280@gmail.com"
  }
}
```

**Error Response** (500 Internal Server Error):
```json
{
  "success": false,
  "error": "Test email failed: SMTP authentication error"
}
```

---

## license-service

License validation and trial management service.

**Base URL**: `https://asia-southeast1-epack-payments.cloudfunctions.net/license-service`

### Validate License (GET)

Validate a license key.

**Endpoint**: `GET /?action=validate&license_key={key}`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | Must be "validate" |
| `license_key` | string | Yes | License key to validate |

**Success Response** (200 OK):
```json
{
  "valid": true,
  "license_key": "VTRACK-P1Y-1754352670-ABC12345",
  "status": "active",
  "customer_email": "user@example.com",
  "package_type": "personal_1y",
  "valid_until": "2026-10-06T00:00:00Z",
  "is_expired": false,
  "validated_at": "2025-10-06T10:30:00.123456"
}
```

**License Not Found** (404 Not Found):
```json
{
  "valid": false,
  "error": "License not found"
}
```

**Validation Failed** (500 Internal Server Error):
```json
{
  "valid": false,
  "error": "Validation failed"
}
```

### Get Licenses by Email (POST)

Retrieve all licenses for a customer email.

**Endpoint**: `POST /`

**Request Body**:
```json
{
  "action": "get_licenses",
  "customer_email": "user@example.com"
}
```

**Success Response** (200 OK):
```json
{
  "success": true,
  "customer_email": "user@example.com",
  "licenses": [
    {
      "license_key": "VTRACK-P1Y-1754352670-ABC12345",
      "package_type": "personal_1y",
      "package_name": "Personal Annual",
      "status": "active",
      "valid_until": "2026-10-06T00:00:00Z",
      "is_expired": false,
      "created_at": "2025-10-06T10:00:00Z"
    },
    {
      "license_key": "VTRACK-P1M-1751760670-XYZ67890",
      "package_type": "personal_1m",
      "package_name": "Personal Monthly",
      "status": "expired",
      "valid_until": "2025-09-06T00:00:00Z",
      "is_expired": true,
      "created_at": "2025-08-07T10:00:00Z"
    }
  ],
  "total_count": 2
}
```

**Error Response** (400 Bad Request):
```json
{
  "success": false,
  "error": "Missing customer_email"
}
```

### Check Trial Eligibility (POST)

Check if a machine is eligible for a trial license.

**Endpoint**: `POST /`

**Request Body**:
```json
{
  "action": "check_trial_eligibility",
  "machine_fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "client_ip": "123.45.67.89",
  "app_version": "2.1.0",
  "device_info": {
    "os": "Darwin 22.6.0",
    "cpu": "Apple M1"
  }
}
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | Must be "check_trial_eligibility" |
| `machine_fingerprint` | string | Yes | Unique machine identifier (SHA256 hash) |
| `client_ip` | string | No | Client IP address for abuse detection |
| `app_version` | string | No | Application version |
| `device_info` | object | No | Additional device information |

**Eligible Response** (200 OK):
```json
{
  "success": true,
  "eligible": true,
  "trial_data": {
    "duration_days": 7,
    "features": ["basic_access", "trial_mode"],
    "machine_fingerprint": "a1b2c3d4e5f6g7h8..."
  },
  "message": "Device is eligible for trial"
}
```

**Already Used Response** (200 OK):
```json
{
  "success": true,
  "eligible": false,
  "reason": "trial_already_used",
  "trial_used_at": "2025-09-01T10:00:00Z",
  "message": "Trial has already been used on this device"
}
```

**Trial Disabled Response** (200 OK):
```json
{
  "success": true,
  "eligible": false,
  "reason": "trial_disabled",
  "message": "Trial system is temporarily disabled"
}
```

**Abuse Detected Response** (200 OK):
```json
{
  "success": true,
  "eligible": false,
  "reason": "abuse_detected",
  "message": "Too many trial requests from this location"
}
```

### Generate Trial License (POST)

Generate a trial license for an eligible machine.

**Endpoint**: `POST /`

**Request Body**:
```json
{
  "action": "generate_trial_license",
  "machine_fingerprint": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "customer_email": "trial@example.com",
  "client_ip": "123.45.67.89",
  "app_version": "2.1.0",
  "device_info": {
    "os": "Darwin 22.6.0",
    "cpu": "Apple M1"
  }
}
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | Must be "generate_trial_license" |
| `machine_fingerprint` | string | Yes | Unique machine identifier |
| `customer_email` | string | No | Customer email (fallback to machine-based) |
| `client_ip` | string | No | Client IP for tracking |
| `app_version` | string | No | Application version |
| `device_info` | object | No | Device information |

**Success Response** (200 OK):
```json
{
  "success": true,
  "trial_license_key": "VTRACK-T7D-ABC12345-XYZ678",
  "license_data": {
    "license_key": "VTRACK-T7D-ABC12345-XYZ678",
    "customer_email": "trial@example.com",
    "package_type": "trial_7d",
    "product_type": "trial_7d",
    "expires_at": "2025-10-13T10:30:00.123456",
    "trial_duration_days": 7,
    "features": ["basic_access", "trial_mode"],
    "is_trial": true,
    "status": "active"
  },
  "expires_at": "2025-10-13T10:30:00.123456",
  "trial_duration_days": 7,
  "message": "Trial license generated for 7 days"
}
```

**Already Used Error** (400 Bad Request):
```json
{
  "success": false,
  "error": "Trial already used on this device"
}
```

**Generation Failed** (500 Internal Server Error):
```json
{
  "success": false,
  "error": "Trial license generation failed"
}
```

### Health Check

Check license service health.

**Endpoint**: `GET /?action=health`

**Success Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-06T10:30:00.123456",
  "service": "license_service",
  "firestore": {
    "status": "healthy",
    "available": true,
    "project_id": "epack-payments",
    "timestamp": "2025-10-06T10:30:00.123456"
  }
}
```

---

## pricing-service

Centralized pricing management service.

**Base URL**: `https://asia-southeast1-epack-payments.cloudfunctions.net/pricing-service`

### Get All Packages

Retrieve all available pricing packages.

**Endpoint**: `GET /?action=get_packages`

**Success Response** (200 OK):
```json
{
  "success": true,
  "packages": {
    "personal_1m": {
      "code": "personal_1m",
      "name": "Personal Monthly",
      "price": 3000,
      "original_price": 2000,
      "duration_days": 30,
      "features": [
        "unlimited_cameras",
        "basic_analytics",
        "email_support"
      ],
      "description": "Personal plan for family use",
      "recommended": false
    },
    "personal_1y": {
      "code": "personal_1y",
      "name": "Personal Annual",
      "price": 20000,
      "original_price": 24000,
      "duration_days": 365,
      "features": [
        "unlimited_cameras",
        "advanced_analytics",
        "priority_support"
      ],
      "description": "Annual personal plan (Save 16%)",
      "recommended": false
    },
    "business_1m": {
      "code": "business_1m",
      "name": "Business Monthly",
      "price": 5000,
      "original_price": 5000,
      "duration_days": 30,
      "features": [
        "multi_location",
        "advanced_analytics",
        "api_access",
        "priority_support"
      ],
      "description": "Business plan for offices",
      "recommended": false
    },
    "business_1y": {
      "code": "business_1y",
      "name": "Business Annual",
      "price": 50000,
      "original_price": 60000,
      "duration_days": 365,
      "features": [
        "multi_location",
        "advanced_analytics",
        "api_access",
        "dedicated_support"
      ],
      "description": "Annual business plan (Save 16%)",
      "recommended": true
    },
    "trial_24h": {
      "code": "trial_24h",
      "name": "24 Hours Trial Extension",
      "price": 2000,
      "original_price": 30000,
      "duration_days": 1,
      "features": [
        "limited_cameras",
        "basic_analytics_only"
      ],
      "description": "24-hour trial extension (limited features)",
      "recommended": false
    }
  },
  "version": "1.0.0",
  "last_updated": "2025-08-14T16:00:00Z",
  "updated_by": "system",
  "total_packages": 5,
  "timestamp": "2025-10-06T10:30:00.123456"
}
```

### Get Specific Package

Retrieve a specific package by code.

**Endpoint**: `GET /?action=get_packages&package={code}`

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action` | string | Yes | Must be "get_packages" |
| `package` | string | Yes | Package code (e.g., "personal_1y") |

**Success Response** (200 OK):
```json
{
  "success": true,
  "package": {
    "code": "personal_1y",
    "name": "Personal Annual",
    "price": 20000,
    "original_price": 24000,
    "duration_days": 365,
    "features": [
      "unlimited_cameras",
      "advanced_analytics",
      "priority_support"
    ],
    "description": "Annual personal plan (Save 16%)",
    "recommended": false
  },
  "version": "1.0.0",
  "timestamp": "2025-10-06T10:30:00.123456"
}
```

**Package Not Found** (200 OK):
```json
{
  "success": false,
  "error": "Package personal_2y not found"
}
```

### Health Check

Check pricing service health.

**Endpoint**: `GET /?action=health`

**Success Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "v_track_pricing_service",
  "version": "1.0.0",
  "packages_available": 5,
  "last_updated": "2025-08-14T16:00:00Z",
  "timestamp": "2025-10-06T10:30:00.123456"
}
```

---

## Common Response Patterns

### CORS Headers

All Cloud Functions include CORS headers for cross-origin access:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 3600
```

### OPTIONS Preflight

All functions support CORS preflight requests:

**Request**: `OPTIONS /`

**Response**: `204 No Content` with CORS headers

### Success Response Pattern

Successful operations follow this pattern:

```json
{
  "success": true,
  "data": { /* operation-specific data */ },
  "timestamp": "2025-10-06T10:30:00.123456"
}
```

### Error Response Pattern

Errors follow this pattern:

```json
{
  "success": false,
  "error": "Error message",
  "details": "Optional detailed error information"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 204 | No Content | CORS preflight successful |
| 400 | Bad Request | Invalid request parameters, missing fields |
| 404 | Not Found | Resource not found (license, package) |
| 405 | Method Not Allowed | Invalid HTTP method |
| 500 | Internal Server Error | Server-side error, external service failure |

### Common Error Scenarios

#### Missing Required Field

```json
{
  "error": "Missing required field: customer_email"
}
```

**HTTP Status**: 400 Bad Request

#### Invalid Package Type

```json
{
  "error": "Invalid package type: invalid_package. Please check pricing service."
}
```

**HTTP Status**: 400 Bad Request

#### License Not Found

```json
{
  "valid": false,
  "error": "License not found"
}
```

**HTTP Status**: 404 Not Found

#### Service Unavailable

```json
{
  "error": "Internal server error",
  "details": "Firestore connection failed"
}
```

**HTTP Status**: 500 Internal Server Error

### Retry Logic

For transient errors (500, network issues), implement exponential backoff:

```python
import time
import requests

def call_cloud_function_with_retry(url, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code < 500:
                return response.json()
        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                raise

        # Exponential backoff: 1s, 2s, 4s
        time.sleep(2 ** attempt)
```

### Timeout Configuration

Recommended timeout values:

| Function | Timeout | Reason |
|----------|---------|--------|
| create-payment | 30s | Includes pricing service call + PayOS API |
| webhook-handler | 60s | License generation + email delivery |
| license-service | 30s | Firestore queries + trial generation |
| pricing-service | 10s | Simple read-only operation |

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**API Version**: v1
