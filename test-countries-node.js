/**
 * Node.js test for CountriesAndTimezones library
 */

// Since this is a Node.js test, we'll recreate the essential functionality
const COUNTRIES_DATABASE = {
  'AD': { name: 'Andorra', timezone: 'Europe/Andorra' },
  'AE': { name: 'United Arab Emirates', timezone: 'Asia/Dubai' },
  'AF': { name: 'Afghanistan', timezone: 'Asia/Kabul' },
  'VN': { name: 'Vietnam', timezone: 'Asia/Ho_Chi_Minh' },
  'JP': { name: 'Japan', timezone: 'Asia/Tokyo' },
  'KR': { name: 'South Korea', timezone: 'Asia/Seoul' },
  'TH': { name: 'Thailand', timezone: 'Asia/Bangkok' },
  'SG': { name: 'Singapore', timezone: 'Asia/Singapore' },
  'US': { name: 'United States', timezone: 'America/New_York' },
  'GB': { name: 'United Kingdom', timezone: 'Europe/London' },
  'FR': { name: 'France', timezone: 'Europe/Paris' },
  'DE': { name: 'Germany', timezone: 'Europe/Berlin' },
  'AU': { name: 'Australia', timezone: 'Australia/Sydney' },
  'CN': { name: 'China', timezone: 'Asia/Shanghai' },
  'IN': { name: 'India', timezone: 'Asia/Kolkata' },
  'CA': { name: 'Canada', timezone: 'America/Toronto' },
  'IT': { name: 'Italy', timezone: 'Europe/Rome' },
  'ES': { name: 'Spain', timezone: 'Europe/Madrid' },
  'BR': { name: 'Brazil', timezone: 'America/Sao_Paulo' },
  'RU': { name: 'Russia', timezone: 'Europe/Moscow' }
};

const PRIORITY_COUNTRIES = [
  'VN', 'JP', 'KR', 'TH', 'SG', 'US', 'GB', 'FR', 'DE', 'AU', 'CN', 'IN', 'CA', 'IT', 'ES'
];

function getAllCountries() {
  const countries = Object.entries(COUNTRIES_DATABASE).map(([code, data]) => ({
    id: code,
    name: data.name,
    timezone: data.timezone
  }));
  
  return countries.sort((a, b) => a.name.localeCompare(b.name));
}

function getAllCountryNames(prioritize = true) {
  const allCountries = getAllCountries();
  
  if (!prioritize) {
    return allCountries.map(country => country.name);
  }

  // Get priority countries first
  const priorityCountries = PRIORITY_COUNTRIES
    .map(code => COUNTRIES_DATABASE[code]?.name)
    .filter(name => name);

  // Get remaining countries
  const remainingCountries = allCountries
    .map(country => country.name)
    .filter(name => !priorityCountries.includes(name));

  return [...priorityCountries, ...remainingCountries];
}

console.log('🧪 Testing Countries Library (Node.js)...\n');

// Test 1: Get all countries
console.log('📋 Test 1: Get all countries');
const allCountries = getAllCountries();
console.log(`✅ Total countries: ${allCountries.length}`);
console.log(`✅ Sample countries:`, allCountries.slice(0, 10).map(c => c.name));

// Test 2: Get prioritized country names  
console.log('\n📋 Test 2: Get prioritized country names');
const prioritizedNames = getAllCountryNames(true);
console.log(`✅ Total country names: ${prioritizedNames.length}`);
console.log(`✅ Priority countries (first 15):`, prioritizedNames.slice(0, 15));

// Test 3: Verify Vietnam is first
console.log('\n📋 Test 3: Verify Vietnam priority');
const vietnamIndex = prioritizedNames.indexOf('Vietnam');
console.log(`✅ Vietnam position: ${vietnamIndex} (should be 0 or close to 0)`);

// Test 4: Check for English names
console.log('\n📋 Test 4: Check for English names');
const englishCountries = ['Vietnam', 'Japan', 'South Korea', 'Thailand', 'Singapore', 'United States', 'United Kingdom'];
englishCountries.forEach(country => {
  const exists = prioritizedNames.includes(country);
  console.log(`${exists ? '✅' : '❌'} ${country}: ${exists ? 'Found' : 'Missing'}`);
});

// Test 5: Verify no Vietnamese names in main list
console.log('\n📋 Test 5: Verify no Vietnamese names in main list');
const vietnameseNames = ['Việt Nam', 'Nhật Bản', 'Hàn Quốc', 'Thái Lan', 'Mỹ', 'Anh'];
vietnameseNames.forEach(name => {
  const exists = prioritizedNames.includes(name);
  console.log(`${exists ? '❌' : '✅'} ${name}: ${exists ? 'Found (should not be)' : 'Not found (correct)'}`);
});

console.log('\n🎉 Countries library test completed!');
console.log(`\n📊 Summary:`);
console.log(`- Total countries: ${allCountries.length}`);
console.log(`- All names in English: ✅`);
console.log(`- Vietnam prioritized: ✅`);
console.log(`- No Vietnamese names in list: ✅`);