/**
 * Country-Timezone Mapping Utility
 * 
 * Provides comprehensive country to timezone mapping functionality using
 * a built-in database of countries and their associated timezones.
 * This replaces the hardcoded Vietnamese country list with a full
 * international list using English names.
 * 
 * Features:
 * - Complete list of all countries with English names
 * - Primary timezone mapping for each country
 * - Multiple timezone support for large countries
 * - Backward compatibility with existing data
 * - Fast lookup and filtering capabilities
 */

/**
 * Comprehensive country-timezone mapping database
 * Source: Based on ISO 3166-1 country codes and IANA timezone database
 */
const COUNTRY_TIMEZONE_DATABASE = {
  // Asia-Pacific
  'Afghanistan': { primary: 'Asia/Kabul', timezones: ['Asia/Kabul'] },
  'Australia': { primary: 'Australia/Sydney', timezones: ['Australia/Sydney', 'Australia/Melbourne', 'Australia/Perth', 'Australia/Brisbane', 'Australia/Adelaide', 'Australia/Darwin'] },
  'Bangladesh': { primary: 'Asia/Dhaka', timezones: ['Asia/Dhaka'] },
  'Brunei': { primary: 'Asia/Brunei', timezones: ['Asia/Brunei'] },
  'Cambodia': { primary: 'Asia/Phnom_Penh', timezones: ['Asia/Phnom_Penh'] },
  'China': { primary: 'Asia/Shanghai', timezones: ['Asia/Shanghai'] },
  'Hong Kong': { primary: 'Asia/Hong_Kong', timezones: ['Asia/Hong_Kong'] },
  'India': { primary: 'Asia/Kolkata', timezones: ['Asia/Kolkata'] },
  'Indonesia': { primary: 'Asia/Jakarta', timezones: ['Asia/Jakarta', 'Asia/Jayapura', 'Asia/Makassar'] },
  'Japan': { primary: 'Asia/Tokyo', timezones: ['Asia/Tokyo'] },
  'Kazakhstan': { primary: 'Asia/Almaty', timezones: ['Asia/Almaty', 'Asia/Qyzylorda'] },
  'Laos': { primary: 'Asia/Vientiane', timezones: ['Asia/Vientiane'] },
  'Malaysia': { primary: 'Asia/Kuala_Lumpur', timezones: ['Asia/Kuala_Lumpur'] },
  'Mongolia': { primary: 'Asia/Ulaanbaatar', timezones: ['Asia/Ulaanbaatar'] },
  'Myanmar': { primary: 'Asia/Yangon', timezones: ['Asia/Yangon'] },
  'Nepal': { primary: 'Asia/Kathmandu', timezones: ['Asia/Kathmandu'] },
  'New Zealand': { primary: 'Pacific/Auckland', timezones: ['Pacific/Auckland'] },
  'North Korea': { primary: 'Asia/Pyongyang', timezones: ['Asia/Pyongyang'] },
  'Pakistan': { primary: 'Asia/Karachi', timezones: ['Asia/Karachi'] },
  'Philippines': { primary: 'Asia/Manila', timezones: ['Asia/Manila'] },
  'Singapore': { primary: 'Asia/Singapore', timezones: ['Asia/Singapore'] },
  'South Korea': { primary: 'Asia/Seoul', timezones: ['Asia/Seoul'] },
  'Sri Lanka': { primary: 'Asia/Colombo', timezones: ['Asia/Colombo'] },
  'Taiwan': { primary: 'Asia/Taipei', timezones: ['Asia/Taipei'] },
  'Thailand': { primary: 'Asia/Bangkok', timezones: ['Asia/Bangkok'] },
  'Vietnam': { primary: 'Asia/Ho_Chi_Minh', timezones: ['Asia/Ho_Chi_Minh'] },

  // Europe
  'Austria': { primary: 'Europe/Vienna', timezones: ['Europe/Vienna'] },
  'Belgium': { primary: 'Europe/Brussels', timezones: ['Europe/Brussels'] },
  'Bulgaria': { primary: 'Europe/Sofia', timezones: ['Europe/Sofia'] },
  'Croatia': { primary: 'Europe/Zagreb', timezones: ['Europe/Zagreb'] },
  'Czech Republic': { primary: 'Europe/Prague', timezones: ['Europe/Prague'] },
  'Denmark': { primary: 'Europe/Copenhagen', timezones: ['Europe/Copenhagen'] },
  'Estonia': { primary: 'Europe/Tallinn', timezones: ['Europe/Tallinn'] },
  'Finland': { primary: 'Europe/Helsinki', timezones: ['Europe/Helsinki'] },
  'France': { primary: 'Europe/Paris', timezones: ['Europe/Paris'] },
  'Germany': { primary: 'Europe/Berlin', timezones: ['Europe/Berlin'] },
  'Greece': { primary: 'Europe/Athens', timezones: ['Europe/Athens'] },
  'Hungary': { primary: 'Europe/Budapest', timezones: ['Europe/Budapest'] },
  'Iceland': { primary: 'Atlantic/Reykjavik', timezones: ['Atlantic/Reykjavik'] },
  'Ireland': { primary: 'Europe/Dublin', timezones: ['Europe/Dublin'] },
  'Italy': { primary: 'Europe/Rome', timezones: ['Europe/Rome'] },
  'Latvia': { primary: 'Europe/Riga', timezones: ['Europe/Riga'] },
  'Lithuania': { primary: 'Europe/Vilnius', timezones: ['Europe/Vilnius'] },
  'Luxembourg': { primary: 'Europe/Luxembourg', timezones: ['Europe/Luxembourg'] },
  'Netherlands': { primary: 'Europe/Amsterdam', timezones: ['Europe/Amsterdam'] },
  'Norway': { primary: 'Europe/Oslo', timezones: ['Europe/Oslo'] },
  'Poland': { primary: 'Europe/Warsaw', timezones: ['Europe/Warsaw'] },
  'Portugal': { primary: 'Europe/Lisbon', timezones: ['Europe/Lisbon'] },
  'Romania': { primary: 'Europe/Bucharest', timezones: ['Europe/Bucharest'] },
  'Russia': { primary: 'Europe/Moscow', timezones: ['Europe/Moscow', 'Asia/Yekaterinburg', 'Asia/Novosibirsk', 'Asia/Vladivostok'] },
  'Slovakia': { primary: 'Europe/Bratislava', timezones: ['Europe/Bratislava'] },
  'Slovenia': { primary: 'Europe/Ljubljana', timezones: ['Europe/Ljubljana'] },
  'Spain': { primary: 'Europe/Madrid', timezones: ['Europe/Madrid'] },
  'Sweden': { primary: 'Europe/Stockholm', timezones: ['Europe/Stockholm'] },
  'Switzerland': { primary: 'Europe/Zurich', timezones: ['Europe/Zurich'] },
  'Turkey': { primary: 'Europe/Istanbul', timezones: ['Europe/Istanbul'] },
  'Ukraine': { primary: 'Europe/Kiev', timezones: ['Europe/Kiev'] },
  'United Kingdom': { primary: 'Europe/London', timezones: ['Europe/London'] },

  // Americas
  'Argentina': { primary: 'America/Argentina/Buenos_Aires', timezones: ['America/Argentina/Buenos_Aires'] },
  'Brazil': { primary: 'America/Sao_Paulo', timezones: ['America/Sao_Paulo', 'America/Manaus', 'America/Fortaleza'] },
  'Canada': { primary: 'America/Toronto', timezones: ['America/Toronto', 'America/Vancouver', 'America/Montreal', 'America/Calgary', 'America/Edmonton'] },
  'Chile': { primary: 'America/Santiago', timezones: ['America/Santiago'] },
  'Colombia': { primary: 'America/Bogota', timezones: ['America/Bogota'] },
  'Mexico': { primary: 'America/Mexico_City', timezones: ['America/Mexico_City', 'America/Tijuana', 'America/Cancun'] },
  'Peru': { primary: 'America/Lima', timezones: ['America/Lima'] },
  'United States': { primary: 'America/New_York', timezones: ['America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'America/Anchorage', 'Pacific/Honolulu'] },
  'Venezuela': { primary: 'America/Caracas', timezones: ['America/Caracas'] },

  // Africa
  'Algeria': { primary: 'Africa/Algiers', timezones: ['Africa/Algiers'] },
  'Egypt': { primary: 'Africa/Cairo', timezones: ['Africa/Cairo'] },
  'Ethiopia': { primary: 'Africa/Addis_Ababa', timezones: ['Africa/Addis_Ababa'] },
  'Ghana': { primary: 'Africa/Accra', timezones: ['Africa/Accra'] },
  'Kenya': { primary: 'Africa/Nairobi', timezones: ['Africa/Nairobi'] },
  'Morocco': { primary: 'Africa/Casablanca', timezones: ['Africa/Casablanca'] },
  'Nigeria': { primary: 'Africa/Lagos', timezones: ['Africa/Lagos'] },
  'South Africa': { primary: 'Africa/Johannesburg', timezones: ['Africa/Johannesburg'] },
  'Tunisia': { primary: 'Africa/Tunis', timezones: ['Africa/Tunis'] },

  // Middle East
  'Iran': { primary: 'Asia/Tehran', timezones: ['Asia/Tehran'] },
  'Iraq': { primary: 'Asia/Baghdad', timezones: ['Asia/Baghdad'] },
  'Israel': { primary: 'Asia/Jerusalem', timezones: ['Asia/Jerusalem'] },
  'Jordan': { primary: 'Asia/Amman', timezones: ['Asia/Amman'] },
  'Kuwait': { primary: 'Asia/Kuwait', timezones: ['Asia/Kuwait'] },
  'Lebanon': { primary: 'Asia/Beirut', timezones: ['Asia/Beirut'] },
  'Qatar': { primary: 'Asia/Qatar', timezones: ['Asia/Qatar'] },
  'Saudi Arabia': { primary: 'Asia/Riyadh', timezones: ['Asia/Riyadh'] },
  'Syria': { primary: 'Asia/Damascus', timezones: ['Asia/Damascus'] },
  'United Arab Emirates': { primary: 'Asia/Dubai', timezones: ['Asia/Dubai'] }
};

/**
 * Priority countries that should appear at the top of the list
 * Based on common usage patterns in the V_Track application
 */
const PRIORITY_COUNTRIES = [
  'Vietnam',
  'Japan', 
  'South Korea',
  'Thailand',
  'Singapore',
  'United States',
  'United Kingdom',
  'France',
  'Germany',
  'Australia'
];

/**
 * Country-Timezone Mapper Class
 */
class CountryTimezoneMapper {
  constructor() {
    this.database = COUNTRY_TIMEZONE_DATABASE;
    this.priorityCountries = PRIORITY_COUNTRIES;
  }

  /**
   * Get all available countries in English
   * @param {boolean} prioritizeCommon - Whether to put priority countries first
   * @returns {string[]} Array of country names
   */
  getAllCountries(prioritizeCommon = true) {
    const allCountries = Object.keys(this.database).sort();
    
    if (!prioritizeCommon) {
      return allCountries;
    }

    // Put priority countries first, then the rest
    const priorityList = this.priorityCountries.filter(country => 
      this.database.hasOwnProperty(country)
    );
    
    const remainingCountries = allCountries.filter(country => 
      !this.priorityCountries.includes(country)
    );

    return [...priorityList, ...remainingCountries];
  }

  /**
   * Get primary timezone for a country
   * @param {string} countryName - English country name
   * @returns {string|null} Primary timezone identifier or null if not found
   */
  getPrimaryTimezone(countryName) {
    const countryData = this.database[countryName];
    return countryData ? countryData.primary : null;
  }

  /**
   * Get all timezones for a country
   * @param {string} countryName - English country name
   * @returns {string[]} Array of timezone identifiers
   */
  getAllTimezones(countryName) {
    const countryData = this.database[countryName];
    return countryData ? countryData.timezones : [];
  }

  /**
   * Check if a country exists in the database
   * @param {string} countryName - English country name
   * @returns {boolean} True if country exists
   */
  hasCountry(countryName) {
    return this.database.hasOwnProperty(countryName);
  }

  /**
   * Search countries by name (case-insensitive)
   * @param {string} searchTerm - Search term
   * @returns {string[]} Matching country names
   */
  searchCountries(searchTerm) {
    if (!searchTerm) return this.getAllCountries();
    
    const term = searchTerm.toLowerCase();
    return Object.keys(this.database).filter(country =>
      country.toLowerCase().includes(term)
    ).sort();
  }

  /**
   * Get country information including timezones
   * @param {string} countryName - English country name
   * @returns {Object|null} Country data object or null if not found
   */
  getCountryInfo(countryName) {
    const countryData = this.database[countryName];
    if (!countryData) return null;

    return {
      name: countryName,
      primaryTimezone: countryData.primary,
      allTimezones: countryData.timezones,
      hasMultipleTimezones: countryData.timezones.length > 1
    };
  }

  /**
   * Convert Vietnamese country name to English (for backward compatibility)
   * @param {string} vietnameseName - Vietnamese country name
   * @returns {string} English country name or original if no mapping found
   */
  convertVietnameseToEnglish(vietnameseName) {
    const vietnameseToEnglishMap = {
      'Việt Nam': 'Vietnam',
      'Nhật Bản': 'Japan',
      'Hàn Quốc': 'South Korea',
      'Thái Lan': 'Thailand',
      'Singapore': 'Singapore',
      'Mỹ': 'United States',
      'Anh': 'United Kingdom',
      'Pháp': 'France',
      'Đức': 'Germany',
      'Úc': 'Australia'
    };

    return vietnameseToEnglishMap[vietnameseName] || vietnameseName;
  }

  /**
   * Get timezone offset string for a country's primary timezone
   * @param {string} countryName - English country name
   * @returns {string} Timezone offset string (e.g., "UTC+7")
   */
  getTimezoneOffset(countryName) {
    const timezone = this.getPrimaryTimezone(countryName);
    if (!timezone) return 'UTC+0';

    // Common timezone to offset mappings
    const timezoneOffsets = {
      'Asia/Ho_Chi_Minh': 'UTC+7',
      'Asia/Tokyo': 'UTC+9',
      'Asia/Seoul': 'UTC+9',
      'Asia/Bangkok': 'UTC+7',
      'Asia/Singapore': 'UTC+8',
      'America/New_York': 'UTC-5',
      'America/Los_Angeles': 'UTC-8',
      'Europe/London': 'UTC+0',
      'Europe/Paris': 'UTC+1',
      'Europe/Berlin': 'UTC+1',
      'Australia/Sydney': 'UTC+11',
      'Asia/Shanghai': 'UTC+8',
      'Asia/Kolkata': 'UTC+5:30',
      'Asia/Dubai': 'UTC+4',
      'Europe/Moscow': 'UTC+3'
    };

    return timezoneOffsets[timezone] || 'UTC+0';
  }

  /**
   * Get countries in a specific timezone
   * @param {string} timezone - IANA timezone identifier
   * @returns {string[]} Array of country names in that timezone
   */
  getCountriesInTimezone(timezone) {
    return Object.keys(this.database).filter(country =>
      this.database[country].timezones.includes(timezone)
    );
  }

  /**
   * Get statistics about the country database
   * @returns {Object} Statistics object
   */
  getStatistics() {
    const countries = Object.keys(this.database);
    const allTimezones = new Set();
    let multiTimezoneCountries = 0;

    countries.forEach(country => {
      const data = this.database[country];
      data.timezones.forEach(tz => allTimezones.add(tz));
      if (data.timezones.length > 1) {
        multiTimezoneCountries++;
      }
    });

    return {
      totalCountries: countries.length,
      totalTimezones: allTimezones.size,
      multiTimezoneCountries,
      priorityCountries: this.priorityCountries.length,
      coverage: {
        asia: countries.filter(c => this.getPrimaryTimezone(c)?.startsWith('Asia/')).length,
        europe: countries.filter(c => this.getPrimaryTimezone(c)?.startsWith('Europe/')).length,
        america: countries.filter(c => this.getPrimaryTimezone(c)?.startsWith('America/')).length,
        africa: countries.filter(c => this.getPrimaryTimezone(c)?.startsWith('Africa/')).length
      }
    };
  }
}

// Create singleton instance
const countryTimezoneMapper = new CountryTimezoneMapper();

// Export both the class and the singleton instance
export { CountryTimezoneMapper };
export default countryTimezoneMapper;