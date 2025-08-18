/**
 * Test Script for Country-Timezone Mapping Implementation
 * 
 * This script validates the country-timezone mapping functionality
 * including the transition from Vietnamese to English country names
 * and auto-timezone selection capabilities.
 */

import countryTimezoneMapper from './CountryTimezoneMapper.js';

/**
 * Test suite for country-timezone mapping functionality
 */
class CountryTimezoneTest {
  constructor() {
    this.testResults = [];
    this.passedTests = 0;
    this.failedTests = 0;
  }

  /**
   * Run a single test with error handling
   * @param {string} testName - Name of the test
   * @param {Function} testFunction - Test function to execute
   */
  runTest(testName, testFunction) {
    try {
      const result = testFunction();
      if (result === true) {
        this.testResults.push({ name: testName, status: 'PASS', message: 'Test passed' });
        this.passedTests++;
        console.log(`✅ ${testName}: PASS`);
      } else {
        this.testResults.push({ name: testName, status: 'FAIL', message: result || 'Test failed' });
        this.failedTests++;
        console.log(`❌ ${testName}: FAIL - ${result}`);
      }
    } catch (error) {
      this.testResults.push({ name: testName, status: 'ERROR', message: error.message });
      this.failedTests++;
      console.log(`🚨 ${testName}: ERROR - ${error.message}`);
    }
  }

  /**
   * Test basic country list functionality
   */
  testCountryList() {
    return this.runTest('Country List Generation', () => {
      const countries = countryTimezoneMapper.getAllCountries();
      
      if (!Array.isArray(countries)) {
        return 'Countries should be an array';
      }
      
      if (countries.length === 0) {
        return 'Countries array should not be empty';
      }
      
      if (!countries.includes('Vietnam')) {
        return 'Countries should include Vietnam';
      }
      
      if (!countries.includes('United States')) {
        return 'Countries should include United States';
      }
      
      if (!countries.includes('Japan')) {
        return 'Countries should include Japan';
      }
      
      console.log(`  Found ${countries.length} countries`);
      return true;
    });
  }

  /**
   * Test priority country ordering
   */
  testPriorityOrdering() {
    return this.runTest('Priority Country Ordering', () => {
      const countries = countryTimezoneMapper.getAllCountries(true);
      const priorityCountries = ['Vietnam', 'Japan', 'South Korea', 'Thailand', 'Singapore'];
      
      // Check if priority countries appear first
      for (let i = 0; i < Math.min(priorityCountries.length, countries.length); i++) {
        if (!priorityCountries.includes(countries[i])) {
          return `Priority country ${priorityCountries[i]} should appear early in the list`;
        }
      }
      
      console.log(`  Priority countries: ${countries.slice(0, 5).join(', ')}`);
      return true;
    });
  }

  /**
   * Test timezone retrieval for countries
   */
  testTimezoneRetrieval() {
    return this.runTest('Timezone Retrieval', () => {
      const testCases = [
        { country: 'Vietnam', expectedTimezone: 'Asia/Ho_Chi_Minh', expectedOffset: 'UTC+7' },
        { country: 'Japan', expectedTimezone: 'Asia/Tokyo', expectedOffset: 'UTC+9' },
        { country: 'United States', expectedTimezone: 'America/New_York', expectedOffset: 'UTC-5' },
        { country: 'United Kingdom', expectedTimezone: 'Europe/London', expectedOffset: 'UTC+0' },
        { country: 'Singapore', expectedTimezone: 'Asia/Singapore', expectedOffset: 'UTC+8' }
      ];
      
      for (const testCase of testCases) {
        const timezone = countryTimezoneMapper.getPrimaryTimezone(testCase.country);
        const offset = countryTimezoneMapper.getTimezoneOffset(testCase.country);
        
        if (timezone !== testCase.expectedTimezone) {
          return `${testCase.country} should have timezone ${testCase.expectedTimezone}, got ${timezone}`;
        }
        
        if (offset !== testCase.expectedOffset) {
          return `${testCase.country} should have offset ${testCase.expectedOffset}, got ${offset}`;
        }
        
        console.log(`  ${testCase.country}: ${timezone} (${offset})`);
      }
      
      return true;
    });
  }

  /**
   * Test Vietnamese to English country name conversion
   */
  testVietnameseConversion() {
    return this.runTest('Vietnamese to English Conversion', () => {
      const testCases = [
        { vietnamese: 'Việt Nam', english: 'Vietnam' },
        { vietnamese: 'Nhật Bản', english: 'Japan' },
        { vietnamese: 'Hàn Quốc', english: 'South Korea' },
        { vietnamese: 'Thái Lan', english: 'Thailand' },
        { vietnamese: 'Mỹ', english: 'United States' },
        { vietnamese: 'Anh', english: 'United Kingdom' }
      ];
      
      for (const testCase of testCases) {
        const converted = countryTimezoneMapper.convertVietnameseToEnglish(testCase.vietnamese);
        
        if (converted !== testCase.english) {
          return `${testCase.vietnamese} should convert to ${testCase.english}, got ${converted}`;
        }
        
        console.log(`  ${testCase.vietnamese} → ${converted}`);
      }
      
      return true;
    });
  }

  /**
   * Test country search functionality
   */
  testCountrySearch() {
    return this.runTest('Country Search', () => {
      const searchResults = countryTimezoneMapper.searchCountries('United');
      
      if (!Array.isArray(searchResults)) {
        return 'Search results should be an array';
      }
      
      if (!searchResults.includes('United States')) {
        return 'Search for "United" should include United States';
      }
      
      if (!searchResults.includes('United Kingdom')) {
        return 'Search for "United" should include United Kingdom';
      }
      
      // Test case insensitive search
      const caseInsensitiveResults = countryTimezoneMapper.searchCountries('vietnam');
      if (!caseInsensitiveResults.includes('Vietnam')) {
        return 'Case insensitive search should work';
      }
      
      console.log(`  Search "United": ${searchResults.join(', ')}`);
      console.log(`  Search "vietnam": ${caseInsensitiveResults.join(', ')}`);
      return true;
    });
  }

  /**
   * Test multiple timezone countries
   */
  testMultipleTimezones() {
    return this.runTest('Multiple Timezone Support', () => {
      const usTimezones = countryTimezoneMapper.getAllTimezones('United States');
      const australiaTimezones = countryTimezoneMapper.getAllTimezones('Australia');
      
      if (!Array.isArray(usTimezones) || usTimezones.length < 4) {
        return 'United States should have multiple timezones';
      }
      
      if (!usTimezones.includes('America/New_York')) {
        return 'US timezones should include America/New_York';
      }
      
      if (!usTimezones.includes('America/Los_Angeles')) {
        return 'US timezones should include America/Los_Angeles';
      }
      
      if (!Array.isArray(australiaTimezones) || australiaTimezones.length < 3) {
        return 'Australia should have multiple timezones';
      }
      
      console.log(`  US timezones: ${usTimezones.join(', ')}`);
      console.log(`  Australia timezones: ${australiaTimezones.join(', ')}`);
      return true;
    });
  }

  /**
   * Test country information retrieval
   */
  testCountryInfo() {
    return this.runTest('Country Information', () => {
      const vietnamInfo = countryTimezoneMapper.getCountryInfo('Vietnam');
      
      if (!vietnamInfo) {
        return 'Should be able to get Vietnam country info';
      }
      
      if (vietnamInfo.name !== 'Vietnam') {
        return 'Country info should have correct name';
      }
      
      if (vietnamInfo.primaryTimezone !== 'Asia/Ho_Chi_Minh') {
        return 'Vietnam should have correct primary timezone';
      }
      
      if (!Array.isArray(vietnamInfo.allTimezones)) {
        return 'Country info should include all timezones array';
      }
      
      if (typeof vietnamInfo.hasMultipleTimezones !== 'boolean') {
        return 'Country info should indicate if country has multiple timezones';
      }
      
      console.log(`  Vietnam info: ${JSON.stringify(vietnamInfo, null, 2)}`);
      return true;
    });
  }

  /**
   * Test statistics functionality
   */
  testStatistics() {
    return this.runTest('Database Statistics', () => {
      const stats = countryTimezoneMapper.getStatistics();
      
      if (typeof stats.totalCountries !== 'number' || stats.totalCountries === 0) {
        return 'Statistics should include total countries count';
      }
      
      if (typeof stats.totalTimezones !== 'number' || stats.totalTimezones === 0) {
        return 'Statistics should include total timezones count';
      }
      
      if (typeof stats.coverage !== 'object') {
        return 'Statistics should include regional coverage';
      }
      
      if (stats.coverage.asia === 0) {
        return 'Should have Asian countries in coverage';
      }
      
      console.log(`  Statistics: ${JSON.stringify(stats, null, 2)}`);
      return true;
    });
  }

  /**
   * Test backward compatibility features
   */
  testBackwardCompatibility() {
    return this.runTest('Backward Compatibility', () => {
      // Test that all old Vietnamese country names can be converted
      const oldCountries = ['Việt Nam', 'Nhật Bản', 'Hàn Quốc', 'Thái Lan', 'Mỹ', 'Anh'];
      const newCountries = countryTimezoneMapper.getAllCountries();
      
      for (const oldCountry of oldCountries) {
        const englishName = countryTimezoneMapper.convertVietnameseToEnglish(oldCountry);
        
        if (!newCountries.includes(englishName)) {
          return `Converted country ${englishName} should exist in new country list`;
        }
        
        const timezone = countryTimezoneMapper.getPrimaryTimezone(englishName);
        if (!timezone) {
          return `Converted country ${englishName} should have a valid timezone`;
        }
      }
      
      console.log(`  Backward compatibility verified for ${oldCountries.length} countries`);
      return true;
    });
  }

  /**
   * Run all tests
   */
  runAllTests() {
    console.log('🧪 Starting Country-Timezone Mapping Tests...\n');
    
    this.testCountryList();
    this.testPriorityOrdering();
    this.testTimezoneRetrieval();
    this.testVietnameseConversion();
    this.testCountrySearch();
    this.testMultipleTimezones();
    this.testCountryInfo();
    this.testStatistics();
    this.testBackwardCompatibility();
    
    this.printSummary();
  }

  /**
   * Print test summary
   */
  printSummary() {
    console.log('\n' + '='.repeat(60));
    console.log('🎯 COUNTRY-TIMEZONE MAPPING TEST SUMMARY');
    console.log('='.repeat(60));
    
    console.log(`\n📊 Test Results:`);
    console.log(`  ✅ Passed: ${this.passedTests}`);
    console.log(`  ❌ Failed: ${this.failedTests}`);
    console.log(`  📈 Success Rate: ${((this.passedTests / (this.passedTests + this.failedTests)) * 100).toFixed(1)}%`);
    
    if (this.failedTests > 0) {
      console.log(`\n❌ Failed Tests:`);
      this.testResults.filter(result => result.status !== 'PASS').forEach(result => {
        console.log(`  • ${result.name}: ${result.message}`);
      });
    }
    
    console.log(`\n🔧 System Status:`);
    const stats = countryTimezoneMapper.getStatistics();
    console.log(`  • Total Countries: ${stats.totalCountries}`);
    console.log(`  • Total Timezones: ${stats.totalTimezones}`);
    console.log(`  • Multi-timezone Countries: ${stats.multiTimezoneCountries}`);
    console.log(`  • Priority Countries: ${stats.priorityCountries}`);
    
    console.log(`\n🌍 Regional Coverage:`);
    console.log(`  • Asia: ${stats.coverage.asia} countries`);
    console.log(`  • Europe: ${stats.coverage.europe} countries`);
    console.log(`  • Americas: ${stats.coverage.america} countries`);
    console.log(`  • Africa: ${stats.coverage.africa} countries`);
    
    const verdict = this.failedTests === 0 ? 
      '🎉 ALL TESTS PASSED! Country-timezone mapping is working correctly.' :
      '⚠️  SOME TESTS FAILED. Please review the implementation.';
    
    console.log(`\n🏆 Final Verdict:`);
    console.log(`  ${verdict}`);
    
    return {
      passed: this.passedTests,
      failed: this.failedTests,
      successRate: (this.passedTests / (this.passedTests + this.failedTests)) * 100,
      verdict: this.failedTests === 0 ? 'PASS' : 'FAIL'
    };
  }
}

// Export the test class for use in other environments
export default CountryTimezoneTest;

// If running directly in browser console or Node.js
if (typeof window !== 'undefined' || typeof global !== 'undefined') {
  // Auto-run tests when script is loaded
  const tester = new CountryTimezoneTest();
  tester.runAllTests();
}