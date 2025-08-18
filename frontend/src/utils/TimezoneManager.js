import { DateTime } from 'luxon';
import ct from 'countries-and-timezones';

class TimezoneManager {
  constructor() {
    this.storageKey = 'vtrack_timezone_preference';
    this.defaultTimezone = 'UTC';
    this.isNode = typeof window === 'undefined';
    this.storage = this.initStorage();
    this.init();
  }

  initStorage() {
    if (!this.isNode && typeof localStorage !== 'undefined') {
      return localStorage;
    }
    
    return {
      _data: {},
      getItem(key) {
        return this._data[key] || null;
      },
      setItem(key, value) {
        this._data[key] = value;
      },
      removeItem(key) {
        delete this._data[key];
      }
    };
  }

  init() {
    try {
      this.userTimezone = this.loadUserPreference() || this.detectBrowserTimezone();
      this.systemTimezone = this.detectBrowserTimezone();
      this.conversionCache = new Map();
      this.cacheExpiry = Date.now() + (5 * 60 * 1000);
    } catch (error) {
      console.warn('TimezoneManager initialization error:', error);
      this.userTimezone = this.defaultTimezone;
      this.systemTimezone = this.defaultTimezone;
      this.conversionCache = new Map();
    }
  }

  detectBrowserTimezone() {
    try {
      if (this.isNode) {
        return process.env.TZ || this.defaultTimezone;
      }
      return Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch (error) {
      console.warn('Browser timezone detection failed:', error);
      return this.defaultTimezone;
    }
  }

  /**
   * Auto-detect country from browser/system locale
   * @returns {string|null} Country name or null
   */
  detectBrowserCountry() {
    try {
      if (this.isNode) return null;
      
      const locale = navigator.language || navigator.languages?.[0] || '';
      const countryCode = locale.split('-')[1]?.toUpperCase();
      
      if (countryCode) {
        const country = ct.getCountry(countryCode);
        return country?.name || null;
      }
      
      return null;
    } catch (error) {
      console.warn('Browser country detection failed:', error);
      return null;
    }
  }

  /**
   * Get auto-detected system info
   * @returns {Object} System detection results
   */
  getSystemDetection() {
    return {
      timezone: this.detectBrowserTimezone(),
      country: this.detectBrowserCountry(),
      locale: this.isNode ? null : navigator.language,
      confidence: this.isNode ? 'low' : 'high'
    };
  }

  loadUserPreference() {
    try {
      const saved = this.storage.getItem(this.storageKey);
      if (saved) {
        const preference = JSON.parse(saved);
        if (this.isValidTimezone(preference.timezone)) {
          return preference.timezone;
        }
      }
    } catch (error) {
      console.warn('Failed to load timezone preference:', error);
    }
    return null;
  }

  saveUserPreference(timezone) {
    try {
      if (!this.isValidTimezone(timezone)) {
        throw new Error(`Invalid timezone: ${timezone}`);
      }
      
      const preference = {
        timezone,
        savedAt: new Date().toISOString(),
        browserTimezone: this.systemTimezone
      };
      
      this.storage.setItem(this.storageKey, JSON.stringify(preference));
      this.userTimezone = timezone;
      this.conversionCache.clear();
      
      return true;
    } catch (error) {
      console.error('Failed to save timezone preference:', error);
      return false;
    }
  }

  isValidTimezone(timezone) {
    try {
      DateTime.now().setZone(timezone);
      return true;
    } catch (error) {
      return false;
    }
  }

  displayTime(input, options = {}) {
    const startTime = this.isNode ? 0 : performance.now();
    
    try {
      const {
        format = 'medium',
        locale = 'en-US',
        showTimezone = true
      } = options;

      const cacheKey = `${input}_${format}_${locale}_${showTimezone}_${this.userTimezone}`;
      if (this.conversionCache.has(cacheKey) && Date.now() < this.cacheExpiry) {
        return this.conversionCache.get(cacheKey);
      }

      let dateTime;
      
      if (typeof input === 'string') {
        dateTime = DateTime.fromISO(input);
      } else if (input instanceof Date) {
        dateTime = DateTime.fromJSDate(input);
      } else if (DateTime.isDateTime(input)) {
        dateTime = input;
      } else {
        throw new Error('Invalid input type for displayTime');
      }

      if (!dateTime.isValid) {
        throw new Error(`Invalid date/time: ${dateTime.invalidReason}`);
      }

      const localTime = dateTime.setZone(this.userTimezone);
      
      let result;
      
      switch (format) {
        case 'short':
          result = localTime.toLocaleString(DateTime.TIME_SIMPLE, { locale });
          break;
        case 'medium':
          result = localTime.toLocaleString(DateTime.DATETIME_MED, { locale });
          break;
        case 'long':
          result = localTime.toLocaleString(DateTime.DATETIME_FULL, { locale });
          break;
        case 'full':
          result = localTime.toLocaleString(DateTime.DATETIME_HUGE, { locale });
          break;
        default:
          result = localTime.toFormat(format, { locale });
      }

      if (showTimezone && ['short', 'medium'].includes(format)) {
        result += ` ${localTime.offsetNameShort}`;
      }

      this.conversionCache.set(cacheKey, result);
      
      if (!this.isNode) {
        const duration = performance.now() - startTime;
        if (duration > 50) {
          console.warn(`TimezoneManager.displayTime took ${duration.toFixed(2)}ms - performance threshold exceeded`);
        }
      }

      return result;
    } catch (error) {
      console.error('Error in displayTime:', error);
      return input?.toString() || 'Invalid time';
    }
  }

  toUtcForBackend(input, options = {}) {
    try {
      const { sourceTimezone = this.userTimezone } = options;

      let dateTime;
      
      if (typeof input === 'string') {
        dateTime = DateTime.fromISO(input, { zone: sourceTimezone });
      } else if (input instanceof Date) {
        dateTime = DateTime.fromJSDate(input, { zone: sourceTimezone });
      } else if (DateTime.isDateTime(input)) {
        dateTime = input.setZone(sourceTimezone);
      } else {
        throw new Error('Invalid input type for toUtcForBackend');
      }

      if (!dateTime.isValid) {
        throw new Error(`Invalid date/time: ${dateTime.invalidReason}`);
      }

      return dateTime.toUTC().toISO();
    } catch (error) {
      console.error('Error in toUtcForBackend:', error);
      throw error;
    }
  }

  parseVideoTimestamp(timestamp, options = {}) {
    try {
      if (!timestamp || typeof timestamp !== 'string') {
        throw new Error('Invalid timestamp: must be a non-empty string');
      }

      const timezonePatterns = [
        /^[A-Z][a-z]+\/[A-Z][a-z_]+$/,
        /^[A-Z][a-z]+ \([A-Za-z ]+\)$/,
        /^UTC[+-]\d+$/,
        /^[A-Z]{3,4}$/
      ];

      const isTimezoneIdentifier = timezonePatterns.some(pattern => pattern.test(timestamp.trim()));
      
      if (isTimezoneIdentifier) {
        throw new Error(`Input appears to be a timezone identifier, not a timestamp: ${timestamp}`);
      }

      const minTimestampPatterns = [
        /\d{4}[-\/]\d{1,2}[-\/]\d{1,2}/,
        /\d{10,13}/,
        /\d{1,2}:\d{2}/
      ];

      const hasTimestampPattern = minTimestampPatterns.some(pattern => pattern.test(timestamp));
      
      if (!hasTimestampPattern) {
        throw new Error(`Input does not contain recognizable timestamp patterns: ${timestamp}`);
      }

      const {
        videoTimezone,
        defaultTimezone = this.userTimezone,
        detectFromPath = true
      } = options;

      let detectedTimezone = videoTimezone;
      
      if (!detectedTimezone && detectFromPath) {
        detectedTimezone = this.detectTimezoneFromTimestamp(timestamp);
      }
      
      const finalTimezone = detectedTimezone || defaultTimezone;
      
      let dateTime = DateTime.fromISO(timestamp, { zone: finalTimezone });
      
      if (!dateTime.isValid) {
        const formats = [
          'yyyy-MM-dd HH:mm:ss',
          'yyyy/MM/dd HH:mm:ss',
          'dd-MM-yyyy HH:mm:ss',
          'MM/dd/yyyy HH:mm:ss',
          'yyyy-MM-dd\'T\'HH:mm:ss',
          'yyyyMMdd_HHmmss'
        ];
        
        for (const format of formats) {
          dateTime = DateTime.fromFormat(timestamp, format, { zone: finalTimezone });
          if (dateTime.isValid) break;
        }
      }

      if (!dateTime.isValid) {
        throw new Error(`Could not parse timestamp: ${timestamp}`);
      }

      return {
        originalTimestamp: timestamp,
        parsedDateTime: dateTime,
        detectedTimezone: finalTimezone,
        utcTime: dateTime.toUTC(),
        userTime: dateTime.setZone(this.userTimezone),
        isValid: true,
        confidence: detectedTimezone ? 'high' : 'low'
      };
    } catch (error) {
      console.error('Error parsing video timestamp:', error);
      return {
        originalTimestamp: timestamp,
        parsedDateTime: null,
        detectedTimezone: null,
        utcTime: null,
        userTime: null,
        isValid: false,
        error: error.message
      };
    }
  }

  detectTimezoneFromTimestamp(timestamp) {
    try {
      const timezonePatterns = [
        { pattern: /UTC[\+\-]\d{1,2}/, extract: (match) => this.offsetToTimezone(match[0]) },
        { pattern: /GMT[\+\-]\d{1,2}/, extract: (match) => this.offsetToTimezone(match[0].replace('GMT', 'UTC')) },
        { pattern: /Asia\/Ho_Chi_Minh|ICT|Indochina/i, extract: () => 'Asia/Ho_Chi_Minh' },
        { pattern: /Asia\/Tokyo|JST|Japan/i, extract: () => 'Asia/Tokyo' },
        { pattern: /Europe\/London|GMT|Greenwich/i, extract: () => 'Europe/London' },
        { pattern: /America\/New_York|EST|EDT|Eastern/i, extract: () => 'America/New_York' }
      ];

      for (const { pattern, extract } of timezonePatterns) {
        const match = timestamp.match(pattern);
        if (match) {
          return extract(match);
        }
      }

      return null;
    } catch (error) {
      console.warn('Error detecting timezone from timestamp:', error);
      return null;
    }
  }

  offsetToTimezone(offset) {
    const offsetMap = {
      'UTC+7': 'Asia/Ho_Chi_Minh',
      'UTC+8': 'Asia/Singapore',
      'UTC+9': 'Asia/Tokyo',
      'UTC+0': 'UTC',
      'UTC-5': 'America/New_York',
      'UTC-8': 'America/Los_Angeles'
    };
    
    return offsetMap[offset] || 'UTC';
  }

  getTimezoneInfo() {
    const now = DateTime.now().setZone(this.userTimezone);
    
    return {
      userTimezone: this.userTimezone,
      systemTimezone: this.systemTimezone,
      currentOffset: now.offsetNameShort,
      currentOffsetMinutes: now.offset,
      isDST: now.isInDST,
      zoneName: now.zoneName,
      isValidTimezone: this.isValidTimezone(this.userTimezone)
    };
  }

  getCommonTimezones() {
    try {
      const allCountries = Object.values(ct.getAllCountries());
      const uniqueTimezones = [...new Set(allCountries.flatMap(c => c.timezones))];
      
      return uniqueTimezones.sort().map(tz => {
        const dt = DateTime.now().setZone(tz);
        return {
          value: tz,
          label: `${tz.replace('_', ' ')} (${dt.offsetNameShort})`,
          offset: dt.offsetNameShort,
          current: dt.toFormat('HH:mm')
        };
      });
    } catch (error) {
      console.error('Error loading timezones from library:', error);
      return [];
    }
  }

  reset() {
    try {
      this.storage.removeItem(this.storageKey);
      this.conversionCache.clear();
      this.init();
    } catch (error) {
      console.error('Error resetting TimezoneManager:', error);
    }
  }
}

const timezoneManager = new TimezoneManager();
export default timezoneManager;
export { TimezoneManager };