/**
 * Test Script for CountriesAndTimezones Library
 * 
 * This script validates that the comprehensive countries library
 * displays complete English country list correctly.
 */

import countriesAndTimezones from './CountriesAndTimezones.js';

/**
 * Test the countries library functionality
 */
function testCountriesLibrary() {
  console.log('🧪 Testing CountriesAndTimezones Library...\n');
  
  // Test 1: Get all countries
  console.log('📋 Test 1: Get all countries');
  const allCountries = countriesAndTimezones.getAllCountries();
  console.log(`✅ Total countries: ${allCountries.length}`);
  console.log(`✅ Sample countries:`, allCountries.slice(0, 10).map(c => c.name));
  
  // Test 2: Get prioritized country names
  console.log('\n📋 Test 2: Get prioritized country names');
  const prioritizedNames = countriesAndTimezones.getAllCountryNames(true);
  console.log(`✅ Total country names: ${prioritizedNames.length}`);
  console.log(`✅ Priority countries (first 15):`, prioritizedNames.slice(0, 15));
  
  // Test 3: Test specific country lookups
  console.log('\n📋 Test 3: Test specific country lookups');
  const testCountries = ['Vietnam', 'Japan', 'United States', 'United Kingdom', 'Germany'];
  
  testCountries.forEach(country => {
    const countryData = countriesAndTimezones.getCountryByName(country);
    const timezone = countriesAndTimezones.getTimezone(country);
    const offset = countriesAndTimezones.getTimezoneOffset(country);
    
    console.log(`✅ ${country}:`);
    console.log(`   - Country Data: ${countryData ? `${countryData.id} - ${countryData.name}` : 'Not found'}`);
    console.log(`   - Timezone: ${timezone}`);
    console.log(`   - Offset: ${offset}`);
  });
  
  // Test 4: Test Vietnamese to English conversion
  console.log('\n📋 Test 4: Test Vietnamese to English conversion');
  const vietnameseTests = [
    { vietnamese: 'Việt Nam', expected: 'Vietnam' },
    { vietnamese: 'Nhật Bản', expected: 'Japan' },
    { vietnamese: 'Mỹ', expected: 'United States' },
    { vietnamese: 'Anh', expected: 'United Kingdom' }
  ];
  
  vietnameseTests.forEach(test => {
    const converted = countriesAndTimezones.convertVietnameseToEnglish(test.vietnamese);
    const success = converted === test.expected;
    console.log(`${success ? '✅' : '❌'} ${test.vietnamese} → ${converted} (expected: ${test.expected})`);
  });
  
  // Test 5: Search functionality
  console.log('\n📋 Test 5: Search functionality');
  const searchResults = countriesAndTimezones.searchCountries('United');
  console.log(`✅ Search "United": ${searchResults.length} results`);
  console.log(`   Results: ${searchResults.join(', ')}`);
  
  // Test 6: Statistics
  console.log('\n📋 Test 6: Library statistics');
  const stats = countriesAndTimezones.getStatistics();
  console.log(`✅ Statistics:`, stats);
  
  // Test 7: Verify priority countries exist
  console.log('\n📋 Test 7: Verify priority countries');
  const priorityTest = ['Vietnam', 'Japan', 'South Korea', 'Thailand', 'Singapore', 'United States'];
  priorityTest.forEach(country => {
    const exists = prioritizedNames.includes(country);
    const index = prioritizedNames.indexOf(country);
    console.log(`${exists ? '✅' : '❌'} ${country}: ${exists ? `Found at index ${index}` : 'Not found'}`);
  });
  
  console.log('\n🎉 Countries library test completed!');
  
  return {
    totalCountries: allCountries.length,
    totalNames: prioritizedNames.length,
    hasVietnam: prioritizedNames.includes('Vietnam'),
    hasBackwardCompatibility: typeof countriesAndTimezones.convertVietnameseToEnglish === 'function',
    statistics: stats
  };
}

// Test the library
const results = testCountriesLibrary();

// Export for use in other components
export default testCountriesLibrary;
export { results };