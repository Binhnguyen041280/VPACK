# Cloud Functions Deployment Guide

Complete guide for setting up, deploying, and managing V_Track Cloud Functions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Local Development](#local-development)
4. [Deployment](#deployment)
5. [Configuration](#configuration)
6. [Testing](#testing)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Installation |
|----------|---------|--------------|
| Python | 3.9+ | https://python.org |
| Google Cloud SDK | Latest | https://cloud.google.com/sdk/docs/install |
| Git | Latest | https://git-scm.com |
| pip | Latest | Included with Python |

### Google Cloud Setup

1. **Create GCP Project**:
   ```bash
   gcloud projects create v-track-payments
   gcloud config set project v-track-payments
   ```

2. **Enable Required APIs**:
   ```bash
   gcloud services enable cloudfunctions.googleapis.com
   gcloud services enable firestore.googleapis.com
   gcloud services enable storage.googleapis.com
   gcloud services enable logging.googleapis.com
   gcloud services enable errorrepporting.googleapis.com
   ```

3. **Set up Firestore**:
   - Go to [Firestore Console](https://console.cloud.google.com/firestore)
   - Select "Native mode"
   - Choose region: `asia-southeast1` (Singapore - closest to Vietnam)
   - Click "Create Database"

4. **Create Service Account** (for local development):
   ```bash
   gcloud iam service-accounts create v-track-functions \
     --display-name="V_Track Cloud Functions"

   gcloud projects add-iam-policy-binding v-track-payments \
     --member="serviceAccount:v-track-functions@v-track-payments.iam.gserviceaccount.com" \
     --role="roles/datastore.user"

   gcloud iam service-accounts keys create service-account.json \
     --iam-account=v-track-functions@v-track-payments.iam.gserviceaccount.com
   ```

### PayOS Setup

1. **Register for PayOS Account**:
   - Visit https://payos.vn
   - Complete merchant registration
   - Verify business details

2. **Get API Credentials**:
   - Login to PayOS dashboard
   - Navigate to API Keys section
   - Copy:
     - Client ID
     - API Key
     - Checksum Key

3. **Configure Webhook URL** (after deployment):
   - Set webhook URL to your `webhook-handler` function URL
   - Example: `https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler`

### Email Setup (Gmail)

1. **Create Gmail Account** or use existing
2. **Enable 2-Factor Authentication**
3. **Generate App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail" app
   - Save password for configuration

---

## Initial Setup

### 1. Clone Repository

```bash
cd /Users/annhu/vtrack_app
git clone <repository-url> V_Track_CloudFunctions
cd V_Track_CloudFunctions
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
# Install all function dependencies
pip install -r functions/create_payment/requirements.txt
pip install -r functions/webhook_handler/requirements.txt
pip install -r functions/license_service/requirements.txt
pip install -r functions/pricing_service/requirements.txt

# Install shared dependencies
pip install -r shared/requirements.txt
```

### 4. Configure Environment

Create `.env` file in project root:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=v-track-payments
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# PayOS Configuration
PAYOS_CLIENT_ID=your_client_id_here
PAYOS_API_KEY=your_api_key_here
PAYOS_CHECKSUM_KEY=your_checksum_key_here

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_NAME=V_track License System
SENDER_EMAIL=your-email@gmail.com

# Development Settings
FUNCTIONS_FRAMEWORK_PORT=8080
LOG_LEVEL=INFO
```

### 5. Initialize Firestore Collections

Run initialization script (optional - collections auto-created):

```bash
python scripts/setup.py
```

This creates initial Firestore collections:
- `vtrack_licenses`
- `payment_metadata`
- `trial_usage`
- `trial_settings`

---

## Local Development

### Running Functions Locally

#### 1. Payment Creation Function

```bash
cd functions/create_payment

# Set environment variables
export GOOGLE_CLOUD_PROJECT=v-track-payments
export GOOGLE_APPLICATION_CREDENTIALS=../../service-account.json
export PAYOS_CLIENT_ID=your_client_id
export PAYOS_API_KEY=your_api_key
export PAYOS_CHECKSUM_KEY=your_checksum_key

# Run function
functions-framework --target=create_payment_handler --debug --port=8081
```

Test endpoint:
```bash
curl http://localhost:8081 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "package_type": "personal_1y"
  }'
```

#### 2. Webhook Handler Function

```bash
cd functions/webhook_handler

# Set environment variables
export GOOGLE_CLOUD_PROJECT=v-track-payments
export GOOGLE_APPLICATION_CREDENTIALS=../../service-account.json
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password

# Run function
functions-framework --target=main --debug --port=8082
```

Test webhook:
```bash
curl http://localhost:8082 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "orderCode": 123456,
      "amount": 20000,
      "code": "00",
      "description": "VTrack-P1Y-6543"
    }
  }'
```

#### 3. License Service Function

```bash
cd functions/license_service

export GOOGLE_CLOUD_PROJECT=v-track-payments
export GOOGLE_APPLICATION_CREDENTIALS=../../service-account.json

functions-framework --target=main --debug --port=8083
```

Test validation:
```bash
curl "http://localhost:8083?action=validate&license_key=VTRACK-P1Y-TEST123"
```

#### 4. Pricing Service Function

```bash
cd functions/pricing_service

functions-framework --target=pricing_service --debug --port=8084
```

Test pricing:
```bash
curl "http://localhost:8084?action=get_packages"
```

### Running All Functions Concurrently

Use `tmux` or multiple terminal windows:

```bash
# Terminal 1
cd functions/create_payment && functions-framework --target=create_payment_handler --port=8081

# Terminal 2
cd functions/webhook_handler && functions-framework --target=main --port=8082

# Terminal 3
cd functions/license_service && functions-framework --target=main --port=8083

# Terminal 4
cd functions/pricing_service && functions-framework --target=pricing_service --port=8084
```

---

## Deployment

### Deploy All Functions

Using deployment script:

```bash
cd deployment
./deploy_all.sh
```

This script:
1. Checks gcloud authentication
2. Enables required GCP APIs
3. Deploys all 4 Cloud Functions
4. Saves function URLs to `function_urls.txt`

### Deploy Individual Functions

#### create-payment

```bash
cd functions/create_payment

gcloud functions deploy create-payment \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --memory 256MB \
  --timeout 30s \
  --region asia-southeast1 \
  --entry-point create_payment_handler \
  --set-env-vars PAYOS_CLIENT_ID=$PAYOS_CLIENT_ID,PAYOS_API_KEY=$PAYOS_API_KEY,PAYOS_CHECKSUM_KEY=$PAYOS_CHECKSUM_KEY
```

#### webhook-handler

```bash
cd functions/webhook_handler

gcloud functions deploy webhook-handler \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --memory 512MB \
  --timeout 60s \
  --region asia-southeast1 \
  --entry-point main \
  --set-env-vars SMTP_USER=$SMTP_USER,SMTP_PASSWORD=$SMTP_PASSWORD
```

#### license-service

```bash
cd functions/license_service

gcloud functions deploy license-service \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --memory 256MB \
  --timeout 30s \
  --region asia-southeast1 \
  --entry-point main
```

#### pricing-service

```bash
cd functions/pricing_service

gcloud functions deploy pricing-service \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --memory 128MB \
  --timeout 10s \
  --region asia-southeast1 \
  --entry-point pricing_service
```

### Get Function URLs

After deployment:

```bash
# Create-payment URL
gcloud functions describe create-payment \
  --region=asia-southeast1 \
  --format="value(httpsTrigger.url)"

# Webhook-handler URL
gcloud functions describe webhook-handler \
  --region=asia-southeast1 \
  --format="value(httpsTrigger.url)"

# License-service URL
gcloud functions describe license-service \
  --region=asia-southeast1 \
  --format="value(httpsTrigger.url)"

# Pricing-service URL
gcloud functions describe pricing-service \
  --region=asia-southeast1 \
  --format="value(httpsTrigger.url)"
```

---

## Configuration

### Environment Variables

Set environment variables for deployed functions:

```bash
# Set variables for create-payment
gcloud functions deploy create-payment \
  --update-env-vars PAYOS_CLIENT_ID=new_value,PAYOS_API_KEY=new_value

# Set variables for webhook-handler
gcloud functions deploy webhook-handler \
  --update-env-vars SMTP_USER=new_email@gmail.com,SMTP_PASSWORD=new_password
```

### Update Pricing

Edit `functions/pricing_service/main.py`:

```python
CURRENT_PACKAGES = {
    'personal_1m': {
        'price': 3000,  # Update price here
        # ... other fields
    },
    # ... other packages
}
```

Deploy updated pricing:

```bash
cd functions/pricing_service
gcloud functions deploy pricing-service \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --region asia-southeast1 \
  --entry-point pricing_service
```

### Firestore Security Rules

Set security rules for Firestore:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Payment metadata - read/write by Cloud Functions only
    match /payment_metadata/{document=**} {
      allow read, write: if false; // No direct access
    }

    // Licenses - read by authenticated users
    match /vtrack_licenses/{licenseId} {
      allow read: if request.auth != null;
      allow write: if false; // Only Cloud Functions can write
    }

    // Trial usage - read/write by Cloud Functions only
    match /trial_usage/{document=**} {
      allow read, write: if false;
    }

    // Trial settings - read by Cloud Functions only
    match /trial_settings/{document=**} {
      allow read, write: if false;
    }
  }
}
```

Apply rules:

```bash
# Save rules to firestore.rules
gcloud firestore databases patch \
  --security-rules-file=firestore.rules
```

---

## Testing

### Unit Tests

Run unit tests:

```bash
cd V_Track_CloudFunctions

# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run specific function tests
pytest tests/test_create_payment.py -v
pytest tests/test_webhook.py -v
pytest tests/test_license_service.py -v
```

### Integration Tests

Test end-to-end payment flow:

```bash
# Run E2E test
pytest tests/test_e2e_payment.py -v
```

### Manual Testing

#### Test Payment Creation

```bash
PAYMENT_URL="https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment"

curl $PAYMENT_URL \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "customer_email": "test@example.com",
    "package_type": "personal_1y",
    "return_url": "http://localhost:8080/payment/redirect",
    "cancel_url": "http://localhost:8080/payment/redirect"
  }'
```

Expected response:
```json
{
  "success": true,
  "payment_url": "https://payos.vn/payment/...",
  "order_code": 123456,
  ...
}
```

#### Test License Validation

```bash
LICENSE_URL="https://asia-southeast1-v-track-payments.cloudfunctions.net/license-service"

curl "$LICENSE_URL?action=validate&license_key=VTRACK-P1Y-TEST123"
```

#### Test Pricing Service

```bash
PRICING_URL="https://asia-southeast1-v-track-payments.cloudfunctions.net/pricing-service"

curl "$PRICING_URL?action=get_packages"
```

#### Test Email Delivery

```bash
WEBHOOK_URL="https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler"

curl "$WEBHOOK_URL?action=test_email"
```

### Health Checks

Check all function health:

```bash
# Create-payment health
curl "https://asia-southeast1-v-track-payments.cloudfunctions.net/create-payment?action=health"

# Webhook-handler health
curl "https://asia-southeast1-v-track-payments.cloudfunctions.net/webhook-handler?action=health"

# License-service health
curl "https://asia-southeast1-v-track-payments.cloudfunctions.net/license-service?action=health"

# Pricing-service health
curl "https://asia-southeast1-v-track-payments.cloudfunctions.net/pricing-service?action=health"
```

---

## Monitoring

### View Logs

#### Real-time logs

```bash
# Create-payment logs
gcloud functions logs read create-payment \
  --region=asia-southeast1 \
  --limit=50

# Webhook-handler logs
gcloud functions logs read webhook-handler \
  --region=asia-southeast1 \
  --limit=50 \
  --follow
```

#### Filter logs by severity

```bash
gcloud functions logs read create-payment \
  --region=asia-southeast1 \
  --filter="severity>=ERROR"
```

#### Filter logs by timestamp

```bash
gcloud functions logs read webhook-handler \
  --region=asia-southeast1 \
  --filter="timestamp>='2025-10-06T00:00:00Z'"
```

### Metrics & Dashboards

View in GCP Console:
- **Cloud Functions Console**: https://console.cloud.google.com/functions
- **Logs Explorer**: https://console.cloud.google.com/logs
- **Error Reporting**: https://console.cloud.google.com/errors

Key metrics to monitor:
- **Invocations/min**: Function call rate
- **Execution time**: Performance metrics
- **Error rate**: Failed invocations
- **Memory usage**: Resource consumption
- **Active instances**: Scaling behavior

### Alerts

Set up alerts for critical issues:

```bash
# Create alert for error rate > 5%
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cloud Function Errors" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s
```

---

## Troubleshooting

### Common Issues

#### 1. Deployment Fails

**Error**: `Permission denied`

**Solution**:
```bash
# Check authentication
gcloud auth list

# Re-authenticate
gcloud auth login

# Set project
gcloud config set project v-track-payments
```

#### 2. Function Returns 500 Error

**Check logs**:
```bash
gcloud functions logs read FUNCTION_NAME \
  --region=asia-southeast1 \
  --filter="severity>=ERROR" \
  --limit=10
```

**Common causes**:
- Missing environment variables
- Firestore connection issues
- PayOS API credentials invalid
- SMTP authentication failure

#### 3. Firestore Connection Failed

**Error**: `Failed to initialize Firestore`

**Solutions**:
1. Check Firestore is enabled:
   ```bash
   gcloud services enable firestore.googleapis.com
   ```

2. Verify service account has permissions:
   ```bash
   gcloud projects get-iam-policy v-track-payments
   ```

3. Check Firestore database exists in correct region

#### 4. PayOS Payment Creation Failed

**Error**: `PayOS payment creation failed`

**Solutions**:
1. Verify PayOS credentials:
   ```bash
   gcloud functions describe create-payment \
     --region=asia-southeast1 \
     --format="value(environmentVariables)"
   ```

2. Test PayOS API directly:
   ```bash
   # Use PayOS test environment
   curl https://api-merchant.payos.vn/v2/payment-requests \
     -H "x-client-id: YOUR_CLIENT_ID" \
     -H "x-api-key: YOUR_API_KEY"
   ```

3. Check PayOS dashboard for service status

#### 5. Email Not Sent

**Error**: `Email sending failed: SMTP authentication error`

**Solutions**:
1. Verify Gmail App Password is correct
2. Check 2FA is enabled on Gmail account
3. Test SMTP connection:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-app-password')
   ```

4. Check environment variables:
   ```bash
   gcloud functions describe webhook-handler \
     --region=asia-southeast1 \
     --format="value(environmentVariables)"
   ```

#### 6. Trial Already Used (False Positive)

**Issue**: User eligible for trial but system says already used

**Solution**:
1. Check Firestore `trial_usage` collection
2. Verify machine fingerprint generation is consistent
3. Manually clear trial usage (admin only):
   ```python
   from google.cloud import firestore
   db = firestore.Client()
   db.collection('trial_usage').document(machine_fingerprint).delete()
   ```

### Debug Mode

Enable debug logging:

```bash
gcloud functions deploy FUNCTION_NAME \
  --runtime python39 \
  --set-env-vars LOG_LEVEL=DEBUG \
  --region=asia-southeast1
```

### Function Not Responding

1. **Check function status**:
   ```bash
   gcloud functions describe FUNCTION_NAME \
     --region=asia-southeast1 \
     --format="value(status)"
   ```

2. **Check recent errors**:
   ```bash
   gcloud functions logs read FUNCTION_NAME \
     --region=asia-southeast1 \
     --limit=50 \
     --filter="severity>=ERROR"
   ```

3. **Redeploy function**:
   ```bash
   gcloud functions deploy FUNCTION_NAME \
     --runtime python39 \
     --trigger-http \
     --region=asia-southeast1
   ```

### Performance Issues

1. **Increase memory allocation**:
   ```bash
   gcloud functions deploy FUNCTION_NAME \
     --memory 512MB \
     --region=asia-southeast1
   ```

2. **Increase timeout**:
   ```bash
   gcloud functions deploy FUNCTION_NAME \
     --timeout 60s \
     --region=asia-southeast1
   ```

3. **Add more instances**:
   ```bash
   gcloud functions deploy FUNCTION_NAME \
     --max-instances 100 \
     --region=asia-southeast1
   ```

---

## Best Practices

### Security

1. **Never commit credentials**:
   - Use `.env` for local development
   - Use GCP environment variables for production
   - Add `*.env`, `service-account.json` to `.gitignore`

2. **Restrict function access**:
   ```bash
   # Remove public access (if needed)
   gcloud functions remove-iam-policy-binding FUNCTION_NAME \
     --region=asia-southeast1 \
     --member=allUsers \
     --role=roles/cloudfunctions.invoker
   ```

3. **Use HTTPS only**: All Cloud Functions use HTTPS by default

### Performance

1. **Minimize cold starts**:
   - Keep function code small
   - Use lightweight dependencies
   - Set minimum instances for critical functions

2. **Optimize Firestore queries**:
   - Use indexes for frequently queried fields
   - Limit query results with `.limit()`
   - Cache pricing data

3. **Handle timeouts**:
   - Set appropriate timeout values
   - Implement retry logic in clients

### Cost Optimization

1. **Monitor usage**:
   ```bash
   gcloud functions describe FUNCTION_NAME \
     --region=asia-southeast1 \
     --format="value(usage)"
   ```

2. **Set max instances**:
   ```bash
   gcloud functions deploy FUNCTION_NAME \
     --max-instances 50 \
     --region=asia-southeast1
   ```

3. **Use appropriate memory**:
   - `128MB`: pricing-service (read-only)
   - `256MB`: create-payment, license-service
   - `512MB`: webhook-handler (email delivery)

---

## Next Steps

After successful deployment:

1. **Update V_Track Desktop App**:
   - Configure Cloud Function URLs in `/backend/.env`
   - Test payment flow end-to-end
   - Verify license activation

2. **Configure PayOS Webhook**:
   - Set webhook URL in PayOS dashboard
   - Test with sandbox payments
   - Monitor webhook logs

3. **Set up Monitoring**:
   - Create GCP alerts for errors
   - Set up uptime checks
   - Configure email notifications

4. **Test Trial System**:
   - Generate trial licenses
   - Verify abuse detection
   - Test expiration handling

---

**Last Updated**: 2025-10-06
**Version**: 1.0.0
**Deployment Region**: asia-southeast1 (Singapore)
