#!/usr/bin/env node

/**
 * Test script for TimezoneManager.js in Node.js environment
 * Tests core functionality to ensure module works outside browser
 */

// Import the TimezoneManager
const { TimezoneManager } = require('./src/utils/TimezoneManager.js');

console.log('🧪 Testing TimezoneManager in Node.js environment...\n');

// Test 1: Basic instantiation
console.log('1. Testing basic instantiation:');
try {
  const tm = new TimezoneManager();
  console.log('✅ TimezoneManager created successfully');
  console.log(`   Environment detected: ${tm.isNode ? 'Node.js' : 'Browser'}`);
  console.log(`   Storage type: ${tm.storage._data ? 'Fallback' : 'localStorage'}`);
} catch (error) {
  console.log('❌ Failed to create TimezoneManager:', error.message);
}

// Test 2: Timezone detection
console.log('\n2. Testing timezone detection:');
try {
  const tm = new TimezoneManager();
  const detected = tm.detectBrowserTimezone();
  console.log('✅ Timezone detection works');
  console.log(`   Detected timezone: ${detected}`);
} catch (error) {
  console.log('❌ Timezone detection failed:', error.message);
}

// Test 3: Storage operations
console.log('\n3. Testing storage operations:');
try {
  const tm = new TimezoneManager();
  
  // Test save
  const success = tm.saveUserPreference('Asia/Tokyo');
  console.log(`✅ Save preference: ${success}`);
  
  // Test load
  const loaded = tm.loadUserPreference();
  console.log(`✅ Load preference: ${loaded}`);
  
  // Test validation
  console.log(`✅ Storage working correctly: ${loaded === 'Asia/Tokyo'}`);
} catch (error) {
  console.log('❌ Storage operations failed:', error.message);
}

// Test 4: Time display functionality
console.log('\n4. Testing time display:');
try {
  const tm = new TimezoneManager();
  const testTime = '2024-01-15T10:30:00Z';
  
  const displayed = tm.displayTime(testTime);
  console.log('✅ Time display works');
  console.log(`   Input: ${testTime}`);
  console.log(`   Output: ${displayed}`);
} catch (error) {
  console.log('❌ Time display failed:', error.message);
}

// Test 5: UTC conversion
console.log('\n5. Testing UTC conversion:');
try {
  const tm = new TimezoneManager();
  const testTime = '2024-01-15 15:30:00';
  
  const utc = tm.toUtcForBackend(testTime);
  console.log('✅ UTC conversion works');
  console.log(`   Input: ${testTime}`);
  console.log(`   UTC: ${utc}`);
} catch (error) {
  console.log('❌ UTC conversion failed:', error.message);
}

// Test 6: Video timestamp parsing
console.log('\n6. Testing video timestamp parsing:');
try {
  const tm = new TimezoneManager();
  const testTimestamp = '2024-01-15_143000';
  
  const parsed = tm.parseVideoTimestamp(testTimestamp);
  console.log('✅ Video timestamp parsing works');
  console.log(`   Input: ${testTimestamp}`);
  console.log(`   Valid: ${parsed.isValid}`);
  console.log(`   Detected timezone: ${parsed.detectedTimezone}`);
} catch (error) {
  console.log('❌ Video timestamp parsing failed:', error.message);
}

// Test 7: Timezone info
console.log('\n7. Testing timezone info:');
try {
  const tm = new TimezoneManager();
  const info = tm.getTimezoneInfo();
  console.log('✅ Timezone info retrieval works');
  console.log(`   User timezone: ${info.userTimezone}`);
  console.log(`   System timezone: ${info.systemTimezone}`);
  console.log(`   Valid timezone: ${info.isValidTimezone}`);
} catch (error) {
  console.log('❌ Timezone info failed:', error.message);
}

// Test 8: Common timezones
console.log('\n8. Testing common timezones list:');
try {
  const tm = new TimezoneManager();
  const common = tm.getCommonTimezones();
  console.log('✅ Common timezones list works');
  console.log(`   Count: ${common.length}`);
  console.log(`   First entry: ${common[0].label}`);
} catch (error) {
  console.log('❌ Common timezones failed:', error.message);
}

// Test 9: Reset functionality
console.log('\n9. Testing reset functionality:');
try {
  const tm = new TimezoneManager();
  tm.reset();
  console.log('✅ Reset works without errors');
} catch (error) {
  console.log('❌ Reset failed:', error.message);
}

console.log('\n🎉 Node.js environment testing complete!');
console.log('\n📝 Next: Test in browser environment by opening frontend');