# Step 5 Timing/Storage Configuration API Documentation

Complete REST API wrapper for Step 5 timing and storage configuration in V.PACK video processing application.

## Table of Contents

1. [Overview](#overview)
2. [Base Configuration](#base-configuration)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Validation Rules](#validation-rules)
6. [Error Handling](#error-handling)
7. [Integration Examples](#integration-examples)
8. [Performance Considerations](#performance-considerations)

## Overview

The Step 5 Timing/Storage Configuration API provides comprehensive management of video processing timing parameters and storage settings. It includes enhanced validation, performance analysis, and statistics reporting.

### Key Features

- **Comprehensive Validation**: Input validation for storage paths, time ranges, and numeric values
- **Performance Analysis**: Real-time calculation of processing load and storage impact
- **Change Detection**: Only update configuration when changes are detected
- **Statistics & Monitoring**: Detailed statistics and performance metrics
- **Directory Management**: Automatic creation and validation of output directories
- **Business Rules**: Enhanced validation based on video processing requirements

## Base Configuration

**Base URL**: `http://localhost:8080/api/config`

**Authentication**: Credentials included for CORS support

**Content-Type**: `application/json`

**CORS Origins**: `http://localhost:3000`

## API Endpoints

### 1. Get Current Configuration

**GET** `/step/timing`

Retrieves the current timing and storage configuration from the database.

#### Response

```json
{
  "success": true,
  "data": {
    "min_packing_time": 10,
    "max_packing_time": 120,
    "video_buffer": 2,
    "storage_duration": 30,
    "frame_rate": 30,
    "frame_interval": 5,
    "output_path": "/default/output"
  },
  "message": "Timing configuration retrieved successfully"
}
```

#### Error Response

```json
{
  "success": false,
  "error": "Database connection failed",
  "step": "step5"
}
```

---

### 2. Update Configuration

**PUT** `/step/timing`

Updates timing and storage configuration with enhanced validation.

#### Request Body

```json
{
  "min_packing_time": 15,
  "max_packing_time": 180,
  "video_buffer": 3,
  "storage_duration": 45,
  "frame_rate": 25,
  "frame_interval": 4,
  "output_path": "/custom/output/path"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "min_packing_time": 15,
    "max_packing_time": 180,
    "video_buffer": 3,
    "storage_duration": 45,
    "frame_rate": 25,
    "frame_interval": 4,
    "output_path": "/custom/output/path",
    "changed": true
  },
  "message": "Timing configuration updated successfully"
}
```

#### Validation Errors

```json
{
  "success": false,
  "error": "Minimum packing time must be less than maximum packing time",
  "step": "step5"
}
```

---

### 3. Validate Configuration

**POST** `/step/timing/validate`

Validates timing configuration without saving to database.

#### Request Body

```json
{
  "min_packing_time": 5,
  "max_packing_time": 8,
  "frame_rate": 30,
  "frame_interval": 35
}
```

#### Response

```json
{
  "success": true,
  "valid": false,
  "data": {
    "min_packing_time": 5,
    "max_packing_time": 8,
    "frame_rate": 30,
    "frame_interval": 35
  },
  "error": "Frame interval cannot be greater than frame rate",
  "validation_details": {
    "basic_validation": "failed",
    "business_rules": "failed",
    "field_checks": {
      "min_packing_time": {
        "value": 5,
        "type": "int",
        "valid": true,
        "range_check": {
          "in_range": true,
          "min": 1,
          "max": 300,
          "value": 5
        }
      }
    },
    "performance_analysis": {
      "processing_fps": 0.86,
      "processing_load_percent": 2.86,
      "performance_level": "low_load"
    },
    "recommendations": [
      "Low processing rate - consider decreasing frame interval for better accuracy"
    ]
  }
}
```

---

### 4. Get Configuration Statistics

**GET** `/step/timing/statistics`

Retrieves detailed statistics and performance metrics for current configuration.

#### Response

```json
{
  "success": true,
  "data": {
    "current_config": {
      "min_packing_time": 10,
      "max_packing_time": 120,
      "video_buffer": 2,
      "storage_duration": 30,
      "frame_rate": 30,
      "frame_interval": 5,
      "output_path": "/default/output"
    },
    "packing_time_range": {
      "min": 10,
      "max": 120,
      "range_seconds": 110,
      "gap_adequate": true
    },
    "performance_metrics": {
      "frame_rate": 30,
      "frame_interval": 5,
      "processing_fps": 6.0,
      "processing_load_percent": 20.0,
      "performance_category": "low_load",
      "frames_skipped_percent": 80.0
    },
    "storage_settings": {
      "storage_duration_days": 30,
      "video_buffer_seconds": 2,
      "output_path": "/default/output",
      "output_path_exists": true
    },
    "system_impact": {
      "daily_storage_reduction_percent": 80.0,
      "estimated_daily_frames_processed": 518400,
      "recommended_adjustments": []
    },
    "validation_status": {
      "valid": true,
      "error": null
    }
  },
  "message": "Statistics retrieved successfully"
}
```

---

### 5. Get Default Values

**GET** `/step/timing/defaults`

Retrieves default configuration values.

#### Response

```json
{
  "success": true,
  "data": {
    "min_packing_time": 10,
    "max_packing_time": 120,
    "video_buffer": 2,
    "storage_duration": 30,
    "frame_rate": 30,
    "frame_interval": 5,
    "output_path": "/default/output"
  },
  "message": "Default values retrieved successfully"
}
```

---

### 6. Calculate Performance Estimate

**POST** `/step/timing/performance-estimate`

Calculates performance estimates based on frame processing settings.

#### Request Body

```json
{
  "frame_rate": 30,
  "frame_interval": 3,
  "video_duration_hours": 24
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "frame_processing": {
      "frames_per_second_original": 30,
      "frames_per_second_processed": 10.0,
      "processing_load_percentage": 33.33,
      "frames_skipped_percentage": 66.67
    },
    "daily_estimates": {
      "total_frames_24h": 2592000,
      "processed_frames_24h": 864000,
      "estimated_storage_reduction": "66.7%"
    },
    "performance_category": "balanced",
    "recommendations": []
  },
  "message": "Performance estimates calculated successfully"
}
```

## Data Models

### TimingStorageData

Core configuration data structure:

```typescript
interface TimingStorageData {
  min_packing_time: number;      // 1-300 seconds
  max_packing_time: number;      // 10-600 seconds  
  video_buffer: number;          // 0-60 seconds
  storage_duration: number;      // 1-365 days
  frame_rate: number;            // 1-120 fps
  frame_interval: number;        // 1-60 seconds
  output_path: string;           // Absolute path
}
```

### Field Descriptions

| Field | Description | Range | Default |
|-------|-------------|-------|---------|
| `min_packing_time` | Minimum duration for packing detection | 1-300 seconds | 10 |
| `max_packing_time` | Maximum duration for packing detection | 10-600 seconds | 120 |
| `video_buffer` | Buffer time before/after events | 0-60 seconds | 2 |
| `storage_duration` | How long to keep processed videos | 1-365 days | 30 |
| `frame_rate` | Original video frame rate | 1-120 fps | 30 |
| `frame_interval` | Process every Nth frame | 1-60 frames | 5 |
| `output_path` | Directory for processed videos | Valid path | "/default/output" |

## Validation Rules

### Basic Validation

1. **Type Checking**: All numeric fields must be integers
2. **Range Validation**: Each field has specific min/max limits
3. **Path Validation**: Output path must be absolute and writable

### Business Rules

1. **Timing Relationship**: `min_packing_time < max_packing_time`
2. **Minimum Gap**: At least 5 seconds between min and max packing time
3. **Frame Logic**: `frame_interval <= frame_rate`
4. **Performance Limits**: Processing FPS should not exceed 60
5. **Storage Limits**: Storage duration should not exceed 180 days
6. **Buffer Logic**: Video buffer should not exceed half of min packing time

### Enhanced Path Validation

1. **Absolute Path**: Must be an absolute filesystem path
2. **Invalid Characters**: No `<>:"|?*` characters allowed
3. **Length Limit**: Maximum 255 characters
4. **Directory Check**: Path must exist and be writable
5. **Auto-Creation**: Service can create missing directories

## Error Handling

### Standard Error Response Format

```json
{
  "success": false,
  "error": "Descriptive error message",
  "step": "step5"
}
```

### Common Error Types

| HTTP Status | Error Type | Description |
|-------------|------------|-------------|
| 400 | Validation Error | Input data fails validation rules |
| 404 | Not Found | Configuration record not found |
| 500 | Database Error | Database operation failed |
| 500 | System Error | Unexpected system error |

### Detailed Validation Errors

Validation endpoint returns detailed error analysis:

```json
{
  "valid": false,
  "error": "Primary error message",
  "validation_details": {
    "basic_validation": "failed",
    "business_rules": "failed",
    "basic_error": "Specific validation error",
    "business_error": "Business rule violation",
    "field_checks": {
      "field_name": {
        "valid": false,
        "range_check": {
          "in_range": false,
          "min": 1,
          "max": 300,
          "value": 350
        }
      }
    }
  }
}
```

## Integration Examples

### TypeScript Frontend Integration

```typescript
import { stepConfigService, TimingStorageData } from './stepConfigService';

// Fetch current configuration
const config = await stepConfigService.fetchTimingStorageState();
console.log('Current config:', config.data);

// Update configuration
const updates: Partial<TimingStorageData> = {
  min_packing_time: 15,
  max_packing_time: 180,
  frame_interval: 3
};

const result = await stepConfigService.updateTimingStorageState(updates);
if (result.success && result.data.changed) {
  console.log('Configuration updated successfully');
} else {
  console.log('No changes detected');
}

// Validate before saving
const validation = await stepConfigService.validateTimingSettings(updates);
if (!validation.valid) {
  console.error('Validation failed:', validation.error);
  console.log('Recommendations:', validation.validation_details?.recommendations);
}

// Get performance statistics
const stats = await stepConfigService.getTimingStatistics();
console.log('Processing load:', stats.data.performance_metrics.processing_load_percent + '%');
console.log('Recommendations:', stats.data.system_impact.recommended_adjustments);
```

### Real-time Validation Example

```typescript
// Validate form fields in real-time
const validateField = async (field: string, value: number) => {
  const testData = { [field]: value };
  const validation = await stepConfigService.validateTimingSettings(testData);
  
  return {
    valid: validation.valid,
    error: validation.error,
    suggestions: validation.validation_details?.recommendations || []
  };
};

// Usage in form component
const handleMinPackingTimeChange = async (value: number) => {
  const validation = await validateField('min_packing_time', value);
  setFieldError(validation.valid ? null : validation.error);
  setSuggestions(validation.suggestions);
};
```

### Performance Monitoring Example

```typescript
// Monitor configuration performance impact
const analyzePerformance = async () => {
  const stats = await stepConfigService.getTimingStatistics();
  const performance = stats.data.performance_metrics;
  
  if (performance.processing_load_percent > 75) {
    console.warn('High processing load detected:', performance.processing_load_percent + '%');
    console.log('Recommendations:', stats.data.system_impact.recommended_adjustments);
  }
  
  // Calculate daily impact
  const dailyFrames = performance.processing_fps * 86400; // 24 hours
  const storageReduction = performance.frames_skipped_percent;
  
  console.log(`Daily frames processed: ${dailyFrames.toLocaleString()}`);
  console.log(`Storage reduction: ${storageReduction}%`);
};
```

## Performance Considerations

### Processing Load Categories

| Category | Load % | Description | Recommendation |
|----------|--------|-------------|----------------|
| Low Load | < 25% | Minimal processing, high storage reduction | Consider decreasing frame_interval for better accuracy |
| Balanced | 25-50% | Good balance of accuracy and performance | Optimal for most use cases |
| High Accuracy | 50-75% | High processing load, better detection | Monitor system resources |
| Maximum Accuracy | > 75% | Very high load, maximum detection | Consider increasing frame_interval |

### Storage Impact Calculation

```
Processing FPS = frame_rate / frame_interval
Processing Load % = (Processing FPS / frame_rate) * 100
Storage Reduction % = 100 - Processing Load %
Daily Frames Processed = Processing FPS * 86400
```

### Recommendations Engine

The API automatically generates recommendations based on:

1. **Processing Load Analysis**: Suggests frame_interval adjustments
2. **Storage Efficiency**: Identifies potential storage waste
3. **Configuration Conflicts**: Highlights invalid parameter combinations
4. **System Resources**: Warns about high resource usage
5. **Path Issues**: Identifies directory problems

### Best Practices

1. **Start Conservative**: Begin with higher frame_interval values and decrease as needed
2. **Monitor Resources**: Use statistics endpoint to track system impact
3. **Validate Early**: Use validation endpoint before saving configuration
4. **Regular Review**: Periodically review performance statistics and recommendations
5. **Path Management**: Ensure output directories exist and have proper permissions

### Common Configuration Patterns

#### High Performance (Storage Optimized)
```json
{
  "min_packing_time": 15,
  "max_packing_time": 180,
  "frame_rate": 30,
  "frame_interval": 10,
  "video_buffer": 2,
  "storage_duration": 14
}
```

#### Balanced (Recommended)
```json
{
  "min_packing_time": 10,
  "max_packing_time": 120,
  "frame_rate": 30,
  "frame_interval": 5,
  "video_buffer": 2,
  "storage_duration": 30
}
```

#### High Accuracy (Processing Intensive)
```json
{
  "min_packing_time": 5,
  "max_packing_time": 90,
  "frame_rate": 30,
  "frame_interval": 2,
  "video_buffer": 3,
  "storage_duration": 60
}
```

---

## Summary

The Step 5 Timing/Storage Configuration API provides a comprehensive solution for managing video processing timing parameters with:

- ✅ **Enhanced Validation**: Comprehensive input validation with business rules
- ✅ **Performance Analysis**: Real-time processing load calculation and recommendations
- ✅ **Change Detection**: Efficient updates only when changes are detected  
- ✅ **Statistics & Monitoring**: Detailed performance metrics and system impact analysis
- ✅ **Path Management**: Automatic directory creation and permission validation
- ✅ **TypeScript Support**: Full type definitions for frontend integration
- ✅ **Error Handling**: Standardized error responses with detailed validation feedback

This API design follows V.PACK's reliability-first approach while providing the flexibility needed for advanced video processing configuration.