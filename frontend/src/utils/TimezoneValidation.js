import timezoneManager from './TimezoneManager';

/**
 * Timezone validation utilities for form inputs
 */
class TimezoneValidation {
  /**
   * Validate date range is within reasonable bounds
   * @param {Date} startDate - Start date
   * @param {Date} endDate - End date
   * @returns {Object} Validation result
   */
  static validateDateRange(startDate, endDate) {
    const errors = [];
    
    if (!startDate || !endDate) {
      return { isValid: false, errors: ['Vui lòng chọn cả ngày bắt đầu và kết thúc'] };
    }

    // Convert to user timezone for validation
    const now = new Date();
    const maxPastDays = 365; // 1 year
    const minDate = new Date(now.getTime() - (maxPastDays * 24 * 60 * 60 * 1000));

    // Validate date order
    if (startDate >= endDate) {
      errors.push('Ngày bắt đầu phải trước ngày kết thúc');
    }

    // Validate not too far in the past
    if (startDate < minDate) {
      errors.push(`Ngày bắt đầu không thể quá ${maxPastDays} ngày trước`);
    }

    // Validate not in the future
    if (endDate > now) {
      errors.push('Ngày kết thúc không thể trong tương lai');
    }

    // Validate range duration (max 90 days)
    const diffDays = (endDate - startDate) / (1000 * 60 * 60 * 24);
    if (diffDays > 90) {
      errors.push('Khoảng thời gian tìm kiếm tối đa 90 ngày');
    }

    return {
      isValid: errors.length === 0,
      errors,
      diffDays: Math.ceil(diffDays)
    };
  }

  /**
   * Validate time range (from/to time) in working hours
   * @param {Date} fromTime - Start time
   * @param {Date} toTime - End time
   * @returns {Object} Validation result
   */
  static validateTimeRange(fromTime, toTime) {
    const errors = [];
    
    if (!fromTime || !toTime) {
      return { isValid: false, errors: ['Vui lòng chọn cả giờ bắt đầu và kết thúc'] };
    }

    // Extract hours and minutes
    const fromHour = fromTime.getHours();
    const fromMinute = fromTime.getMinutes();
    const toHour = toTime.getHours();
    const toMinute = toTime.getMinutes();

    const fromTotalMinutes = fromHour * 60 + fromMinute;
    const toTotalMinutes = toHour * 60 + toMinute;

    // Validate time order
    if (fromTotalMinutes >= toTotalMinutes) {
      errors.push('Giờ bắt đầu phải trước giờ kết thúc');
    }

    // Validate reasonable working hours (5 AM - 11 PM)
    const minHour = 5; // 5 AM
    const maxHour = 23; // 11 PM

    if (fromHour < minHour || fromHour > maxHour) {
      errors.push(`Giờ bắt đầu nên trong khoảng ${minHour}:00 - ${maxHour}:00`);
    }

    if (toHour < minHour || toHour > maxHour) {
      errors.push(`Giờ kết thúc nên trong khoảng ${minHour}:00 - ${maxHour}:00`);
    }

    // Validate minimum duration (30 minutes)
    const durationMinutes = toTotalMinutes - fromTotalMinutes;
    if (durationMinutes < 30) {
      errors.push('Thời gian làm việc tối thiểu 30 phút');
    }

    // Validate maximum duration (18 hours)
    if (durationMinutes > 18 * 60) {
      errors.push('Thời gian làm việc tối đa 18 giờ');
    }

    return {
      isValid: errors.length === 0,
      errors,
      durationHours: Math.round(durationMinutes / 60 * 100) / 100
    };
  }

  /**
   * Validate timezone selection
   * @param {string} timezone - Timezone identifier
   * @returns {Object} Validation result
   */
  static validateTimezone(timezone) {
    const errors = [];
    
    if (!timezone) {
      return { isValid: false, errors: ['Vui lòng chọn múi giờ'] };
    }

    // Check if timezone is valid
    if (!timezoneManager.isValidTimezone(timezone)) {
      errors.push('Múi giờ không hợp lệ');
    }

    // Warn about potential data issues when switching timezones
    const currentTz = timezoneManager.getTimezoneInfo().userTimezone;
    const warnings = [];
    
    if (currentTz && timezone !== currentTz) {
      warnings.push('Thay đổi múi giờ sẽ ảnh hưởng đến cách hiển thị thời gian trong toàn bộ ứng dụng');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Validate working days selection
   * @param {Array} workingDays - Array of selected working days
   * @returns {Object} Validation result
   */
  static validateWorkingDays(workingDays) {
    const errors = [];
    
    if (!Array.isArray(workingDays) || workingDays.length === 0) {
      errors.push('Vui lòng chọn ít nhất một ngày làm việc');
    }

    // Validate all selected days are valid
    const validDays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"];
    const invalidDays = workingDays.filter(day => !validDays.includes(day));
    
    if (invalidDays.length > 0) {
      errors.push(`Ngày không hợp lệ: ${invalidDays.join(', ')}`);
    }

    // Suggest common patterns
    const suggestions = [];
    if (workingDays.length === 7) {
      suggestions.push('Làm việc 7 ngày/tuần có thể gây quá tải hệ thống');
    } else if (workingDays.length === 1) {
      suggestions.push('Chỉ làm việc 1 ngày/tuần có thể không đủ để theo dõi hiệu quả');
    }

    return {
      isValid: errors.length === 0,
      errors,
      suggestions,
      totalDays: workingDays.length
    };
  }

  /**
   * Validate complete general info form
   * @param {Object} formData - Form data object
   * @returns {Object} Complete validation result
   */
  static validateGeneralInfo(formData) {
    const {
      country,
      timezone,
      brandName,
      workingDays,
      fromTime,
      toTime
    } = formData;

    const results = {
      isValid: true,
      errors: [],
      warnings: [],
      fieldErrors: {}
    };

    // Validate country
    if (!country || country.trim().length === 0) {
      results.fieldErrors.country = ['Vui lòng chọn quốc gia'];
      results.isValid = false;
    }

    // Validate timezone
    const tzValidation = this.validateTimezone(timezone);
    if (!tzValidation.isValid) {
      results.fieldErrors.timezone = tzValidation.errors;
      results.isValid = false;
    }
    if (tzValidation.warnings) {
      results.warnings.push(...tzValidation.warnings);
    }

    // Validate brand name
    if (!brandName || brandName.trim().length === 0) {
      results.fieldErrors.brandName = ['Vui lòng nhập tên thương hiệu'];
      results.isValid = false;
    } else if (brandName.trim().length < 2) {
      results.fieldErrors.brandName = ['Tên thương hiệu phải có ít nhất 2 ký tự'];
      results.isValid = false;
    } else if (brandName.length > 100) {
      results.fieldErrors.brandName = ['Tên thương hiệu không được quá 100 ký tự'];
      results.isValid = false;
    }

    // Validate working days
    const workingDaysValidation = this.validateWorkingDays(workingDays);
    if (!workingDaysValidation.isValid) {
      results.fieldErrors.workingDays = workingDaysValidation.errors;
      results.isValid = false;
    }
    if (workingDaysValidation.suggestions) {
      results.warnings.push(...workingDaysValidation.suggestions);
    }

    // Validate time range
    const timeValidation = this.validateTimeRange(fromTime, toTime);
    if (!timeValidation.isValid) {
      results.fieldErrors.timeRange = timeValidation.errors;
      results.isValid = false;
    }

    return results;
  }

  /**
   * Format validation errors for display
   * @param {Object} validationResult - Result from validation function
   * @returns {string} Formatted error message
   */
  static formatErrors(validationResult) {
    if (!validationResult || validationResult.isValid) {
      return '';
    }

    const allErrors = [];
    
    // Add general errors
    if (validationResult.errors) {
      allErrors.push(...validationResult.errors);
    }

    // Add field-specific errors
    if (validationResult.fieldErrors) {
      Object.values(validationResult.fieldErrors).forEach(fieldErrors => {
        allErrors.push(...fieldErrors);
      });
    }

    return allErrors.join('; ');
  }

  /**
   * Format validation warnings for display
   * @param {Object} validationResult - Result from validation function
   * @returns {string} Formatted warning message
   */
  static formatWarnings(validationResult) {
    if (!validationResult || !validationResult.warnings) {
      return '';
    }

    return validationResult.warnings.join('; ');
  }
}

export default TimezoneValidation;