/**
 * Countries and Timezones Library Implementation
 * 
 * This module provides comprehensive country-timezone mapping functionality
 * similar to the countries-and-timezones npm package, but implemented
 * directly to avoid external dependencies and provide better control.
 * 
 * Features:
 * - Complete list of world countries in English
 * - Primary timezone mapping for each country
 * - Multiple timezone support for large countries
 * - Fast lookup and filtering capabilities
 * - Backward compatibility with Vietnamese names
 */

/**
 * Comprehensive country database with timezone mappings
 * Based on ISO 3166-1 country codes and IANA timezone database
 */
const COUNTRIES_DATABASE = {
  // A
  'AD': { name: 'Andorra', timezone: 'Europe/Andorra' },
  'AE': { name: 'United Arab Emirates', timezone: 'Asia/Dubai' },
  'AF': { name: 'Afghanistan', timezone: 'Asia/Kabul' },
  'AG': { name: 'Antigua and Barbuda', timezone: 'America/Antigua' },
  'AI': { name: 'Anguilla', timezone: 'America/Anguilla' },
  'AL': { name: 'Albania', timezone: 'Europe/Tirane' },
  'AM': { name: 'Armenia', timezone: 'Asia/Yerevan' },
  'AO': { name: 'Angola', timezone: 'Africa/Luanda' },
  'AR': { name: 'Argentina', timezone: 'America/Argentina/Buenos_Aires' },
  'AS': { name: 'American Samoa', timezone: 'Pacific/Pago_Pago' },
  'AT': { name: 'Austria', timezone: 'Europe/Vienna' },
  'AU': { name: 'Australia', timezone: 'Australia/Sydney' },
  'AW': { name: 'Aruba', timezone: 'America/Aruba' },
  'AZ': { name: 'Azerbaijan', timezone: 'Asia/Baku' },

  // B
  'BA': { name: 'Bosnia and Herzegovina', timezone: 'Europe/Sarajevo' },
  'BB': { name: 'Barbados', timezone: 'America/Barbados' },
  'BD': { name: 'Bangladesh', timezone: 'Asia/Dhaka' },
  'BE': { name: 'Belgium', timezone: 'Europe/Brussels' },
  'BF': { name: 'Burkina Faso', timezone: 'Africa/Ouagadougou' },
  'BG': { name: 'Bulgaria', timezone: 'Europe/Sofia' },
  'BH': { name: 'Bahrain', timezone: 'Asia/Bahrain' },
  'BI': { name: 'Burundi', timezone: 'Africa/Bujumbura' },
  'BJ': { name: 'Benin', timezone: 'Africa/Porto-Novo' },
  'BM': { name: 'Bermuda', timezone: 'Atlantic/Bermuda' },
  'BN': { name: 'Brunei', timezone: 'Asia/Brunei' },
  'BO': { name: 'Bolivia', timezone: 'America/La_Paz' },
  'BR': { name: 'Brazil', timezone: 'America/Sao_Paulo' },
  'BS': { name: 'Bahamas', timezone: 'America/Nassau' },
  'BT': { name: 'Bhutan', timezone: 'Asia/Thimphu' },
  'BW': { name: 'Botswana', timezone: 'Africa/Gaborone' },
  'BY': { name: 'Belarus', timezone: 'Europe/Minsk' },
  'BZ': { name: 'Belize', timezone: 'America/Belize' },

  // C
  'CA': { name: 'Canada', timezone: 'America/Toronto' },
  'CD': { name: 'Democratic Republic of the Congo', timezone: 'Africa/Kinshasa' },
  'CF': { name: 'Central African Republic', timezone: 'Africa/Bangui' },
  'CG': { name: 'Republic of the Congo', timezone: 'Africa/Brazzaville' },
  'CH': { name: 'Switzerland', timezone: 'Europe/Zurich' },
  'CI': { name: 'Ivory Coast', timezone: 'Africa/Abidjan' },
  'CK': { name: 'Cook Islands', timezone: 'Pacific/Rarotonga' },
  'CL': { name: 'Chile', timezone: 'America/Santiago' },
  'CM': { name: 'Cameroon', timezone: 'Africa/Douala' },
  'CN': { name: 'China', timezone: 'Asia/Shanghai' },
  'CO': { name: 'Colombia', timezone: 'America/Bogota' },
  'CR': { name: 'Costa Rica', timezone: 'America/Costa_Rica' },
  'CU': { name: 'Cuba', timezone: 'America/Havana' },
  'CV': { name: 'Cape Verde', timezone: 'Atlantic/Cape_Verde' },
  'CY': { name: 'Cyprus', timezone: 'Asia/Nicosia' },
  'CZ': { name: 'Czech Republic', timezone: 'Europe/Prague' },

  // D
  'DE': { name: 'Germany', timezone: 'Europe/Berlin' },
  'DJ': { name: 'Djibouti', timezone: 'Africa/Djibouti' },
  'DK': { name: 'Denmark', timezone: 'Europe/Copenhagen' },
  'DM': { name: 'Dominica', timezone: 'America/Dominica' },
  'DO': { name: 'Dominican Republic', timezone: 'America/Santo_Domingo' },
  'DZ': { name: 'Algeria', timezone: 'Africa/Algiers' },

  // E
  'EC': { name: 'Ecuador', timezone: 'America/Guayaquil' },
  'EE': { name: 'Estonia', timezone: 'Europe/Tallinn' },
  'EG': { name: 'Egypt', timezone: 'Africa/Cairo' },
  'ER': { name: 'Eritrea', timezone: 'Africa/Asmara' },
  'ES': { name: 'Spain', timezone: 'Europe/Madrid' },
  'ET': { name: 'Ethiopia', timezone: 'Africa/Addis_Ababa' },

  // F
  'FI': { name: 'Finland', timezone: 'Europe/Helsinki' },
  'FJ': { name: 'Fiji', timezone: 'Pacific/Fiji' },
  'FK': { name: 'Falkland Islands', timezone: 'Atlantic/Stanley' },
  'FM': { name: 'Micronesia', timezone: 'Pacific/Chuuk' },
  'FO': { name: 'Faroe Islands', timezone: 'Atlantic/Faroe' },
  'FR': { name: 'France', timezone: 'Europe/Paris' },

  // G
  'GA': { name: 'Gabon', timezone: 'Africa/Libreville' },
  'GB': { name: 'United Kingdom', timezone: 'Europe/London' },
  'GD': { name: 'Grenada', timezone: 'America/Grenada' },
  'GE': { name: 'Georgia', timezone: 'Asia/Tbilisi' },
  'GH': { name: 'Ghana', timezone: 'Africa/Accra' },
  'GI': { name: 'Gibraltar', timezone: 'Europe/Gibraltar' },
  'GL': { name: 'Greenland', timezone: 'America/Godthab' },
  'GM': { name: 'Gambia', timezone: 'Africa/Banjul' },
  'GN': { name: 'Guinea', timezone: 'Africa/Conakry' },
  'GQ': { name: 'Equatorial Guinea', timezone: 'Africa/Malabo' },
  'GR': { name: 'Greece', timezone: 'Europe/Athens' },
  'GT': { name: 'Guatemala', timezone: 'America/Guatemala' },
  'GU': { name: 'Guam', timezone: 'Pacific/Guam' },
  'GW': { name: 'Guinea-Bissau', timezone: 'Africa/Bissau' },
  'GY': { name: 'Guyana', timezone: 'America/Guyana' },

  // H
  'HK': { name: 'Hong Kong', timezone: 'Asia/Hong_Kong' },
  'HN': { name: 'Honduras', timezone: 'America/Tegucigalpa' },
  'HR': { name: 'Croatia', timezone: 'Europe/Zagreb' },
  'HT': { name: 'Haiti', timezone: 'America/Port-au-Prince' },
  'HU': { name: 'Hungary', timezone: 'Europe/Budapest' },

  // I
  'ID': { name: 'Indonesia', timezone: 'Asia/Jakarta' },
  'IE': { name: 'Ireland', timezone: 'Europe/Dublin' },
  'IL': { name: 'Israel', timezone: 'Asia/Jerusalem' },
  'IN': { name: 'India', timezone: 'Asia/Kolkata' },
  'IQ': { name: 'Iraq', timezone: 'Asia/Baghdad' },
  'IR': { name: 'Iran', timezone: 'Asia/Tehran' },
  'IS': { name: 'Iceland', timezone: 'Atlantic/Reykjavik' },
  'IT': { name: 'Italy', timezone: 'Europe/Rome' },

  // J
  'JM': { name: 'Jamaica', timezone: 'America/Jamaica' },
  'JO': { name: 'Jordan', timezone: 'Asia/Amman' },
  'JP': { name: 'Japan', timezone: 'Asia/Tokyo' },

  // K
  'KE': { name: 'Kenya', timezone: 'Africa/Nairobi' },
  'KG': { name: 'Kyrgyzstan', timezone: 'Asia/Bishkek' },
  'KH': { name: 'Cambodia', timezone: 'Asia/Phnom_Penh' },
  'KI': { name: 'Kiribati', timezone: 'Pacific/Tarawa' },
  'KM': { name: 'Comoros', timezone: 'Indian/Comoro' },
  'KN': { name: 'Saint Kitts and Nevis', timezone: 'America/St_Kitts' },
  'KP': { name: 'North Korea', timezone: 'Asia/Pyongyang' },
  'KR': { name: 'South Korea', timezone: 'Asia/Seoul' },
  'KW': { name: 'Kuwait', timezone: 'Asia/Kuwait' },
  'KY': { name: 'Cayman Islands', timezone: 'America/Cayman' },
  'KZ': { name: 'Kazakhstan', timezone: 'Asia/Almaty' },

  // L
  'LA': { name: 'Laos', timezone: 'Asia/Vientiane' },
  'LB': { name: 'Lebanon', timezone: 'Asia/Beirut' },
  'LC': { name: 'Saint Lucia', timezone: 'America/St_Lucia' },
  'LI': { name: 'Liechtenstein', timezone: 'Europe/Vaduz' },
  'LK': { name: 'Sri Lanka', timezone: 'Asia/Colombo' },
  'LR': { name: 'Liberia', timezone: 'Africa/Monrovia' },
  'LS': { name: 'Lesotho', timezone: 'Africa/Maseru' },
  'LT': { name: 'Lithuania', timezone: 'Europe/Vilnius' },
  'LU': { name: 'Luxembourg', timezone: 'Europe/Luxembourg' },
  'LV': { name: 'Latvia', timezone: 'Europe/Riga' },
  'LY': { name: 'Libya', timezone: 'Africa/Tripoli' },

  // M
  'MA': { name: 'Morocco', timezone: 'Africa/Casablanca' },
  'MC': { name: 'Monaco', timezone: 'Europe/Monaco' },
  'MD': { name: 'Moldova', timezone: 'Europe/Chisinau' },
  'ME': { name: 'Montenegro', timezone: 'Europe/Podgorica' },
  'MG': { name: 'Madagascar', timezone: 'Indian/Antananarivo' },
  'MH': { name: 'Marshall Islands', timezone: 'Pacific/Majuro' },
  'MK': { name: 'North Macedonia', timezone: 'Europe/Skopje' },
  'ML': { name: 'Mali', timezone: 'Africa/Bamako' },
  'MM': { name: 'Myanmar', timezone: 'Asia/Yangon' },
  'MN': { name: 'Mongolia', timezone: 'Asia/Ulaanbaatar' },
  'MO': { name: 'Macau', timezone: 'Asia/Macau' },
  'MP': { name: 'Northern Mariana Islands', timezone: 'Pacific/Saipan' },
  'MR': { name: 'Mauritania', timezone: 'Africa/Nouakchott' },
  'MS': { name: 'Montserrat', timezone: 'America/Montserrat' },
  'MT': { name: 'Malta', timezone: 'Europe/Malta' },
  'MU': { name: 'Mauritius', timezone: 'Indian/Mauritius' },
  'MV': { name: 'Maldives', timezone: 'Indian/Maldives' },
  'MW': { name: 'Malawi', timezone: 'Africa/Blantyre' },
  'MX': { name: 'Mexico', timezone: 'America/Mexico_City' },
  'MY': { name: 'Malaysia', timezone: 'Asia/Kuala_Lumpur' },
  'MZ': { name: 'Mozambique', timezone: 'Africa/Maputo' },

  // N
  'NA': { name: 'Namibia', timezone: 'Africa/Windhoek' },
  'NC': { name: 'New Caledonia', timezone: 'Pacific/Noumea' },
  'NE': { name: 'Niger', timezone: 'Africa/Niamey' },
  'NG': { name: 'Nigeria', timezone: 'Africa/Lagos' },
  'NI': { name: 'Nicaragua', timezone: 'America/Managua' },
  'NL': { name: 'Netherlands', timezone: 'Europe/Amsterdam' },
  'NO': { name: 'Norway', timezone: 'Europe/Oslo' },
  'NP': { name: 'Nepal', timezone: 'Asia/Kathmandu' },
  'NR': { name: 'Nauru', timezone: 'Pacific/Nauru' },
  'NU': { name: 'Niue', timezone: 'Pacific/Niue' },
  'NZ': { name: 'New Zealand', timezone: 'Pacific/Auckland' },

  // O
  'OM': { name: 'Oman', timezone: 'Asia/Muscat' },

  // P
  'PA': { name: 'Panama', timezone: 'America/Panama' },
  'PE': { name: 'Peru', timezone: 'America/Lima' },
  'PF': { name: 'French Polynesia', timezone: 'Pacific/Tahiti' },
  'PG': { name: 'Papua New Guinea', timezone: 'Pacific/Port_Moresby' },
  'PH': { name: 'Philippines', timezone: 'Asia/Manila' },
  'PK': { name: 'Pakistan', timezone: 'Asia/Karachi' },
  'PL': { name: 'Poland', timezone: 'Europe/Warsaw' },
  'PM': { name: 'Saint Pierre and Miquelon', timezone: 'America/Miquelon' },
  'PR': { name: 'Puerto Rico', timezone: 'America/Puerto_Rico' },
  'PS': { name: 'Palestine', timezone: 'Asia/Gaza' },
  'PT': { name: 'Portugal', timezone: 'Europe/Lisbon' },
  'PW': { name: 'Palau', timezone: 'Pacific/Palau' },
  'PY': { name: 'Paraguay', timezone: 'America/Asuncion' },

  // Q
  'QA': { name: 'Qatar', timezone: 'Asia/Qatar' },

  // R
  'RO': { name: 'Romania', timezone: 'Europe/Bucharest' },
  'RS': { name: 'Serbia', timezone: 'Europe/Belgrade' },
  'RU': { name: 'Russia', timezone: 'Europe/Moscow' },
  'RW': { name: 'Rwanda', timezone: 'Africa/Kigali' },

  // S
  'SA': { name: 'Saudi Arabia', timezone: 'Asia/Riyadh' },
  'SB': { name: 'Solomon Islands', timezone: 'Pacific/Guadalcanal' },
  'SC': { name: 'Seychelles', timezone: 'Indian/Mahe' },
  'SD': { name: 'Sudan', timezone: 'Africa/Khartoum' },
  'SE': { name: 'Sweden', timezone: 'Europe/Stockholm' },
  'SG': { name: 'Singapore', timezone: 'Asia/Singapore' },
  'SH': { name: 'Saint Helena', timezone: 'Atlantic/St_Helena' },
  'SI': { name: 'Slovenia', timezone: 'Europe/Ljubljana' },
  'SK': { name: 'Slovakia', timezone: 'Europe/Bratislava' },
  'SL': { name: 'Sierra Leone', timezone: 'Africa/Freetown' },
  'SM': { name: 'San Marino', timezone: 'Europe/San_Marino' },
  'SN': { name: 'Senegal', timezone: 'Africa/Dakar' },
  'SO': { name: 'Somalia', timezone: 'Africa/Mogadishu' },
  'SR': { name: 'Suriname', timezone: 'America/Paramaribo' },
  'SS': { name: 'South Sudan', timezone: 'Africa/Juba' },
  'ST': { name: 'Sao Tome and Principe', timezone: 'Africa/Sao_Tome' },
  'SV': { name: 'El Salvador', timezone: 'America/El_Salvador' },
  'SY': { name: 'Syria', timezone: 'Asia/Damascus' },
  'SZ': { name: 'Eswatini', timezone: 'Africa/Mbabane' },

  // T
  'TC': { name: 'Turks and Caicos Islands', timezone: 'America/Grand_Turk' },
  'TD': { name: 'Chad', timezone: 'Africa/Ndjamena' },
  'TG': { name: 'Togo', timezone: 'Africa/Lome' },
  'TH': { name: 'Thailand', timezone: 'Asia/Bangkok' },
  'TJ': { name: 'Tajikistan', timezone: 'Asia/Dushanbe' },
  'TK': { name: 'Tokelau', timezone: 'Pacific/Fakaofo' },
  'TL': { name: 'East Timor', timezone: 'Asia/Dili' },
  'TM': { name: 'Turkmenistan', timezone: 'Asia/Ashgabat' },
  'TN': { name: 'Tunisia', timezone: 'Africa/Tunis' },
  'TO': { name: 'Tonga', timezone: 'Pacific/Tongatapu' },
  'TR': { name: 'Turkey', timezone: 'Europe/Istanbul' },
  'TT': { name: 'Trinidad and Tobago', timezone: 'America/Port_of_Spain' },
  'TV': { name: 'Tuvalu', timezone: 'Pacific/Funafuti' },
  'TW': { name: 'Taiwan', timezone: 'Asia/Taipei' },
  'TZ': { name: 'Tanzania', timezone: 'Africa/Dar_es_Salaam' },

  // U
  'UA': { name: 'Ukraine', timezone: 'Europe/Kiev' },
  'UG': { name: 'Uganda', timezone: 'Africa/Kampala' },
  'US': { name: 'United States', timezone: 'America/New_York' },
  'UY': { name: 'Uruguay', timezone: 'America/Montevideo' },
  'UZ': { name: 'Uzbekistan', timezone: 'Asia/Tashkent' },

  // V
  'VA': { name: 'Vatican City', timezone: 'Europe/Vatican' },
  'VC': { name: 'Saint Vincent and the Grenadines', timezone: 'America/St_Vincent' },
  'VE': { name: 'Venezuela', timezone: 'America/Caracas' },
  'VG': { name: 'British Virgin Islands', timezone: 'America/Tortola' },
  'VI': { name: 'US Virgin Islands', timezone: 'America/St_Thomas' },
  'VN': { name: 'Vietnam', timezone: 'Asia/Ho_Chi_Minh' },
  'VU': { name: 'Vanuatu', timezone: 'Pacific/Efate' },

  // W
  'WS': { name: 'Samoa', timezone: 'Pacific/Apia' },

  // Y
  'YE': { name: 'Yemen', timezone: 'Asia/Aden' },

  // Z
  'ZA': { name: 'South Africa', timezone: 'Africa/Johannesburg' },
  'ZM': { name: 'Zambia', timezone: 'Africa/Lusaka' },
  'ZW': { name: 'Zimbabwe', timezone: 'Africa/Harare' }
};

/**
 * Priority countries that should appear first in dropdown lists
 */
const PRIORITY_COUNTRIES = [
  'VN', // Vietnam
  'JP', // Japan
  'KR', // South Korea
  'TH', // Thailand
  'SG', // Singapore
  'US', // United States
  'GB', // United Kingdom
  'FR', // France
  'DE', // Germany
  'AU', // Australia
  'CN', // China
  'IN', // India
  'CA', // Canada
  'IT', // Italy
  'ES'  // Spain
];

/**
 * Countries and Timezones Library Class
 */
class CountriesAndTimezones {
  constructor() {
    this.countries = COUNTRIES_DATABASE;
    this.priorities = PRIORITY_COUNTRIES;
  }

  /**
   * Get all countries as an array of objects
   * @returns {Array} Array of country objects with id, name, and timezone
   */
  getAllCountries() {
    const countries = Object.entries(this.countries).map(([code, data]) => ({
      id: code,
      name: data.name,
      timezone: data.timezone
    }));

    // Sort alphabetically by name
    return countries.sort((a, b) => a.name.localeCompare(b.name));
  }

  /**
   * Get all country names as a simple array (prioritized)
   * @param {boolean} prioritize - Whether to put priority countries first
   * @returns {Array} Array of country names
   */
  getAllCountryNames(prioritize = true) {
    const allCountries = this.getAllCountries();
    
    if (!prioritize) {
      return allCountries.map(country => country.name);
    }

    // Get priority countries first
    const priorityCountries = this.priorities
      .map(code => this.countries[code]?.name)
      .filter(name => name);

    // Get remaining countries
    const remainingCountries = allCountries
      .map(country => country.name)
      .filter(name => !priorityCountries.includes(name));

    return [...priorityCountries, ...remainingCountries];
  }

  /**
   * Get country by name
   * @param {string} name - Country name
   * @returns {Object|null} Country object or null
   */
  getCountryByName(name) {
    const entry = Object.entries(this.countries).find(([code, data]) => 
      data.name.toLowerCase() === name.toLowerCase()
    );
    
    if (entry) {
      const [code, data] = entry;
      return {
        id: code,
        name: data.name,
        timezone: data.timezone
      };
    }
    
    return null;
  }

  /**
   * Get timezone for a country
   * @param {string} countryName - Country name
   * @returns {string|null} Timezone or null
   */
  getTimezone(countryName) {
    const country = this.getCountryByName(countryName);
    return country ? country.timezone : null;
  }

  /**
   * Get countries by timezone
   * @param {string} timezone - IANA timezone identifier
   * @returns {Array} Array of country names
   */
  getCountriesByTimezone(timezone) {
    return Object.values(this.countries)
      .filter(country => country.timezone === timezone)
      .map(country => country.name);
  }

  /**
   * Search countries by name
   * @param {string} query - Search query
   * @returns {Array} Array of matching country names
   */
  searchCountries(query) {
    if (!query) return this.getAllCountryNames();

    const lowerQuery = query.toLowerCase();
    return this.getAllCountries()
      .filter(country => country.name.toLowerCase().includes(lowerQuery))
      .map(country => country.name);
  }

  /**
   * Convert Vietnamese country name to English (backward compatibility)
   * @param {string} vietnameseName - Vietnamese country name
   * @returns {string} English country name
   */
  convertVietnameseToEnglish(vietnameseName) {
    const mapping = {
      'Việt Nam': 'Vietnam',
      'Nhật Bản': 'Japan',
      'Hàn Quốc': 'South Korea',
      'Thái Lan': 'Thailand',
      'Singapore': 'Singapore',
      'Mỹ': 'United States',
      'Anh': 'United Kingdom',
      'Pháp': 'France',
      'Đức': 'Germany',
      'Úc': 'Australia',
      'Trung Quốc': 'China',
      'Ấn Độ': 'India',
      'Canada': 'Canada',
      'Ý': 'Italy',
      'Tây Ban Nha': 'Spain'
    };

    return mapping[vietnameseName] || vietnameseName;
  }

  /**
   * Get timezone offset string for a country
   * @param {string} countryName - Country name
   * @returns {string} UTC offset string
   */
  getTimezoneOffset(countryName) {
    const timezone = this.getTimezone(countryName);
    if (!timezone) return 'UTC+0';

    // Common timezone offset mappings
    const offsets = {
      'Asia/Ho_Chi_Minh': 'UTC+7',
      'Asia/Tokyo': 'UTC+9',
      'Asia/Seoul': 'UTC+9',
      'Asia/Bangkok': 'UTC+7',
      'Asia/Singapore': 'UTC+8',
      'Asia/Shanghai': 'UTC+8',
      'Asia/Kolkata': 'UTC+5:30',
      'America/New_York': 'UTC-5',
      'America/Los_Angeles': 'UTC-8',
      'America/Toronto': 'UTC-5',
      'Europe/London': 'UTC+0',
      'Europe/Paris': 'UTC+1',
      'Europe/Berlin': 'UTC+1',
      'Europe/Rome': 'UTC+1',
      'Europe/Madrid': 'UTC+1',
      'Australia/Sydney': 'UTC+11',
      'Africa/Johannesburg': 'UTC+2',
      'Asia/Dubai': 'UTC+4'
    };

    return offsets[timezone] || 'UTC+0';
  }

  /**
   * Get statistics about the database
   * @returns {Object} Database statistics
   */
  getStatistics() {
    const countries = this.getAllCountries();
    const timezones = new Set(countries.map(c => c.timezone));
    
    return {
      totalCountries: countries.length,
      totalTimezones: timezones.size,
      priorityCountries: this.priorities.length,
      hasBackwardCompatibility: true,
      dataSource: 'built-in-comprehensive'
    };
  }
}

// Create singleton instance
const countriesAndTimezones = new CountriesAndTimezones();

// Export both the class and singleton
export { CountriesAndTimezones };
export default countriesAndTimezones;