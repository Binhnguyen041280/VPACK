import React, { useState, useEffect, useCallback } from 'react';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import useGlobalTimezone from '../../hooks/useGlobalTimezone';
import timezoneManager from '../../utils/TimezoneManager';

/**
 * Timezone-Aware Time Range Picker Component
 * 
 * Provides intelligent time range selection with:
 * - Automatic timezone detection and conversion
 * - Local time input with UTC output
 * - Multiple preset time ranges
 * - Real-time timezone display
 * - Validation and error handling
 * 
 * @param {Object} props - Component props
 * @param {Date} props.startDate - Current start date
 * @param {Date} props.endDate - Current end date
 * @param {Function} props.onStartDateChange - Start date change handler
 * @param {Function} props.onEndDateChange - End date change handler
 * @param {Function} props.onTimeRangeChange - Combined time range change handler
 * @param {string} props.className - Additional CSS classes
 * @param {boolean} props.showTimezone - Show timezone information
 * @param {boolean} props.showPresets - Show time range presets
 */
const TimezoneAwareTimeRangePicker = ({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onTimeRangeChange,
  className = '',
  showTimezone = true,
  showPresets = true,
  maxDayRange = 30
}) => {
  const [localStartDate, setLocalStartDate] = useState(startDate);
  const [localEndDate, setLocalEndDate] = useState(endDate);
  const [timeZoneOffset, setTimeZoneOffset] = useState('');
  const [validationError, setValidationError] = useState('');
  const [selectedPreset, setSelectedPreset] = useState('custom');

  const {
    timezoneInfo,
    getTimezoneDisplay,
    getTimezoneOffset,
    loading: timezoneLoading
  } = useGlobalTimezone();

  // Time range presets
  const timeRangePresets = [
    {
      id: 'last1hour',
      label: 'Last 1 Hour',
      getValue: () => {
        const now = new Date();
        return {
          start: new Date(now.getTime() - 60 * 60 * 1000),
          end: now
        };
      }
    },
    {
      id: 'last6hours',
      label: 'Last 6 Hours',
      getValue: () => {
        const now = new Date();
        return {
          start: new Date(now.getTime() - 6 * 60 * 60 * 1000),
          end: now
        };
      }
    },
    {
      id: 'last24hours',
      label: 'Last 24 Hours',
      getValue: () => {
        const now = new Date();
        return {
          start: new Date(now.getTime() - 24 * 60 * 60 * 1000),
          end: now
        };
      }
    },
    {
      id: 'last3days',
      label: 'Last 3 Days',
      getValue: () => {
        const now = new Date();
        return {
          start: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000),
          end: now
        };
      }
    },
    {
      id: 'last7days',
      label: 'Last 7 Days',
      getValue: () => {
        const now = new Date();
        return {
          start: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000),
          end: now
        };
      }
    },
    {
      id: 'today',
      label: 'Today',
      getValue: () => {
        const now = new Date();
        const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        return {
          start: startOfDay,
          end: now
        };
      }
    },
    {
      id: 'yesterday',
      label: 'Yesterday',
      getValue: () => {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const startOfYesterday = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());
        const endOfYesterday = new Date(startOfYesterday.getTime() + 24 * 60 * 60 * 1000 - 1);
        return {
          start: startOfYesterday,
          end: endOfYesterday
        };
      }
    }
  ];

  // Update timezone offset display
  useEffect(() => {
    if (!timezoneLoading && timezoneInfo) {
      const offset = getTimezoneOffset();
      setTimeZoneOffset(offset);
    }
  }, [timezoneInfo, timezoneLoading, getTimezoneOffset]);

  // Sync with prop changes
  useEffect(() => {
    setLocalStartDate(startDate);
  }, [startDate]);

  useEffect(() => {
    setLocalEndDate(endDate);
  }, [endDate]);

  // Validation function
  const validateTimeRange = useCallback((start, end) => {
    if (!start || !end) {
      return 'Both start and end times are required';
    }

    if (start >= end) {
      return 'Start time must be before end time';
    }

    const diffDays = (end - start) / (1000 * 60 * 60 * 24);
    if (diffDays > maxDayRange) {
      return `Time range cannot exceed ${maxDayRange} days`;
    }

    const now = new Date();
    if (end > now) {
      return 'End time cannot be in the future';
    }

    return '';
  }, [maxDayRange]);

  // Handle start date change
  const handleStartDateChange = useCallback((date) => {
    setLocalStartDate(date);
    setSelectedPreset('custom');
    
    const error = validateTimeRange(date, localEndDate);
    setValidationError(error);
    
    if (!error && onStartDateChange) {
      onStartDateChange(date);
    }

    // Notify combined handler
    if (!error && onTimeRangeChange) {
      onTimeRangeChange({
        startDate: date,
        endDate: localEndDate,
        timezone: timezoneInfo?.timezone_iana,
        timezoneOffset: timeZoneOffset
      });
    }
  }, [localEndDate, validateTimeRange, onStartDateChange, onTimeRangeChange, timezoneInfo, timeZoneOffset]);

  // Handle end date change
  const handleEndDateChange = useCallback((date) => {
    setLocalEndDate(date);
    setSelectedPreset('custom');
    
    const error = validateTimeRange(localStartDate, date);
    setValidationError(error);
    
    if (!error && onEndDateChange) {
      onEndDateChange(date);
    }

    // Notify combined handler
    if (!error && onTimeRangeChange) {
      onTimeRangeChange({
        startDate: localStartDate,
        endDate: date,
        timezone: timezoneInfo?.timezone_iana,
        timezoneOffset: timeZoneOffset
      });
    }
  }, [localStartDate, validateTimeRange, onEndDateChange, onTimeRangeChange, timezoneInfo, timeZoneOffset]);

  // Handle preset selection
  const handlePresetChange = useCallback((presetId) => {
    setSelectedPreset(presetId);
    
    if (presetId === 'custom') {
      return;
    }

    const preset = timeRangePresets.find(p => p.id === presetId);
    if (!preset) return;

    const { start, end } = preset.getValue();
    
    setLocalStartDate(start);
    setLocalEndDate(end);
    
    const error = validateTimeRange(start, end);
    setValidationError(error);
    
    if (!error) {
      if (onStartDateChange) onStartDateChange(start);
      if (onEndDateChange) onEndDateChange(end);
      
      if (onTimeRangeChange) {
        onTimeRangeChange({
          startDate: start,
          endDate: end,
          timezone: timezoneInfo?.timezone_iana,
          timezoneOffset: timeZoneOffset,
          preset: presetId
        });
      }
    }
  }, [validateTimeRange, onStartDateChange, onEndDateChange, onTimeRangeChange, timezoneInfo, timeZoneOffset]);

  // Format timezone display
  const getTimezoneDisplayText = () => {
    if (timezoneLoading) return 'Loading timezone...';
    if (!timezoneInfo) return 'UTC+0 (Fallback)';
    
    return getTimezoneDisplay();
  };

  // Get local time display
  const formatLocalTime = (date) => {
    if (!date) return '';
    
    try {
      return timezoneManager.displayTime(date.toISOString(), {
        format: 'yyyy-MM-dd HH:mm:ss',
        showTimezone: false
      });
    } catch (error) {
      return date.toLocaleString();
    }
  };

  return (
    <div className={`timezone-aware-time-picker ${className}`}>
      {/* Timezone Information */}
      {showTimezone && (
        <div className="timezone-info mb-3 p-2 bg-light rounded">
          <div className="d-flex align-items-center">
            <i className="fas fa-globe me-2 text-primary"></i>
            <span className="fw-bold">Current Timezone:</span>
            <span className="ms-2">{getTimezoneDisplayText()}</span>
          </div>
          <div className="mt-1 text-muted small">
            All times are entered in local timezone and automatically converted to UTC for queries
          </div>
        </div>
      )}

      {/* Time Range Presets */}
      {showPresets && (
        <div className="time-range-presets mb-3">
          <label className="form-label fw-bold">Quick Time Ranges</label>
          <div className="d-flex flex-wrap gap-2">
            {timeRangePresets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`btn btn-sm ${
                  selectedPreset === preset.id ? 'btn-primary' : 'btn-outline-primary'
                }`}
                onClick={() => handlePresetChange(preset.id)}
              >
                {preset.label}
              </button>
            ))}
            <button
              type="button"
              className={`btn btn-sm ${
                selectedPreset === 'custom' ? 'btn-primary' : 'btn-outline-primary'
              }`}
              onClick={() => handlePresetChange('custom')}
            >
              Custom Range
            </button>
          </div>
        </div>
      )}

      {/* Date Pickers */}
      <div className="row">
        {/* Start Date */}
        <div className="col-md-6">
          <label className="form-label fw-bold">
            <i className="fas fa-calendar-alt me-2"></i>
            Start Time
          </label>
          <DatePicker
            selected={localStartDate}
            onChange={handleStartDateChange}
            showTimeSelect
            timeFormat="HH:mm"
            timeIntervals={15}
            dateFormat="yyyy-MM-dd HH:mm"
            className="form-control"
            placeholderText="Select start time"
            maxDate={new Date()}
            autoComplete="off"
          />
          {localStartDate && (
            <div className="mt-1 text-muted small">
              Local: {formatLocalTime(localStartDate)}
            </div>
          )}
        </div>

        {/* End Date */}
        <div className="col-md-6">
          <label className="form-label fw-bold">
            <i className="fas fa-calendar-alt me-2"></i>
            End Time
          </label>
          <DatePicker
            selected={localEndDate}
            onChange={handleEndDateChange}
            showTimeSelect
            timeFormat="HH:mm"
            timeIntervals={15}
            dateFormat="yyyy-MM-dd HH:mm"
            className="form-control"
            placeholderText="Select end time"
            maxDate={new Date()}
            minDate={localStartDate}
            autoComplete="off"
          />
          {localEndDate && (
            <div className="mt-1 text-muted small">
              Local: {formatLocalTime(localEndDate)}
            </div>
          )}
        </div>
      </div>

      {/* Validation Error */}
      {validationError && (
        <div className="alert alert-warning mt-3" role="alert">
          <i className="fas fa-exclamation-triangle me-2"></i>
          {validationError}
        </div>
      )}

      {/* Time Range Summary */}
      {localStartDate && localEndDate && !validationError && (
        <div className="time-range-summary mt-3 p-2 bg-success bg-opacity-10 rounded">
          <div className="d-flex justify-content-between align-items-center">
            <span className="fw-bold text-success">
              <i className="fas fa-check-circle me-2"></i>
              Valid Time Range
            </span>
            <span className="text-muted">
              {Math.round((localEndDate - localStartDate) / (1000 * 60 * 60 * 24 * 10)) / 10} days
            </span>
          </div>
          
          <div className="mt-2 small">
            <div>
              <strong>From:</strong> {formatLocalTime(localStartDate)} ({timeZoneOffset})
            </div>
            <div>
              <strong>To:</strong> {formatLocalTime(localEndDate)} ({timeZoneOffset})
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimezoneAwareTimeRangePicker;