/**
 * Integration Test Script for V_Track Program Control
 *
 * This script tests the complete frontend-backend integration
 * by simulating user interactions and API calls.
 */

const BASE_URL = 'http://localhost:8080/api';

// Test API endpoints
async function testApiEndpoints() {
  console.log('🧪 Testing API Endpoints...\n');

  const tests = [
    {
      name: 'Health Check',
      url: 'http://localhost:8080/health',
      method: 'GET'
    },
    {
      name: 'Program Status',
      url: `${BASE_URL}/program`,
      method: 'GET'
    },
    {
      name: 'Check First Run',
      url: `${BASE_URL}/check-first-run`,
      method: 'GET'
    },
    {
      name: 'Camera Configurations',
      url: `${BASE_URL}/camera-configurations`,
      method: 'GET'
    },
    {
      name: 'Program Progress',
      url: `${BASE_URL}/program-progress`,
      method: 'GET'
    }
  ];

  for (const test of tests) {
    try {
      console.log(`📡 Testing: ${test.name}`);

      const response = await fetch(test.url, {
        method: test.method,
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`✅ ${test.name}: Success`);
        console.log(`   Status: ${response.status}`);
        console.log(`   Data: ${JSON.stringify(data, null, 2).substring(0, 200)}...\n`);
      } else {
        console.log(`❌ ${test.name}: Failed`);
        console.log(`   Status: ${response.status}`);
        console.log(`   Error: ${response.statusText}\n`);
      }
    } catch (error) {
      console.log(`💥 ${test.name}: Network Error`);
      console.log(`   Error: ${error.message}\n`);
    }
  }
}

// Test program operations
async function testProgramOperations() {
  console.log('🎬 Testing Program Operations...\n');

  // Test Default Program Start
  try {
    console.log('📡 Testing: Start Default Program');

    const response = await fetch(`${BASE_URL}/program`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        card: 'Mặc định',
        action: 'run'
      })
    });

    if (response.ok) {
      const data = await response.json();
      console.log('✅ Start Default Program: Success');
      console.log(`   Status: ${response.status}`);
      console.log(`   Current Running: ${data.current_running}`);
      console.log('');

      // Wait a moment then stop
      setTimeout(async () => {
        try {
          console.log('📡 Testing: Stop Program');

          const stopResponse = await fetch(`${BASE_URL}/program`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              card: 'Mặc định',
              action: 'stop'
            })
          });

          if (stopResponse.ok) {
            const stopData = await stopResponse.json();
            console.log('✅ Stop Program: Success');
            console.log(`   Status: ${stopResponse.status}`);
            console.log(`   Current Running: ${stopData.current_running}`);
          } else {
            console.log('❌ Stop Program: Failed');
            console.log(`   Status: ${stopResponse.status}`);
          }
        } catch (error) {
          console.log('💥 Stop Program: Network Error');
          console.log(`   Error: ${error.message}`);
        }
      }, 3000);

    } else {
      const errorData = await response.json();
      console.log('❌ Start Default Program: Failed');
      console.log(`   Status: ${response.status}`);
      console.log(`   Error: ${errorData.error || response.statusText}`);
    }
  } catch (error) {
    console.log('💥 Start Default Program: Network Error');
    console.log(`   Error: ${error.message}`);
  }
}

// Test error scenarios
async function testErrorScenarios() {
  console.log('\n🚨 Testing Error Scenarios...\n');

  const errorTests = [
    {
      name: 'Invalid Program Type',
      body: {
        card: 'InvalidType',
        action: 'run'
      }
    },
    {
      name: 'Missing Action',
      body: {
        card: 'Mặc định'
      }
    },
    {
      name: 'Custom without Path',
      body: {
        card: 'Chỉ định',
        action: 'run'
      }
    }
  ];

  for (const test of errorTests) {
    try {
      console.log(`📡 Testing Error: ${test.name}`);

      const response = await fetch(`${BASE_URL}/program`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(test.body)
      });

      const data = await response.json();

      if (!response.ok) {
        console.log(`✅ ${test.name}: Correctly handled error`);
        console.log(`   Status: ${response.status}`);
        console.log(`   Error: ${data.error}`);
      } else {
        console.log(`⚠️ ${test.name}: Expected error but got success`);
      }
      console.log('');
    } catch (error) {
      console.log(`💥 ${test.name}: Network Error`);
      console.log(`   Error: ${error.message}\n`);
    }
  }
}

// Main test function
async function runTests() {
  console.log('🚀 V_Track Program Control Integration Tests\n');
  console.log('='.repeat(50) + '\n');

  try {
    await testApiEndpoints();
    await testProgramOperations();
    await testErrorScenarios();

    console.log('='.repeat(50));
    console.log('✅ Integration tests completed!');
    console.log('🌐 Frontend URL: http://localhost:3000/program');
    console.log('⚡ Backend URL: http://localhost:8080/api/program');
    console.log('\n📝 Next Steps:');
    console.log('   1. Open http://localhost:3000/program in browser');
    console.log('   2. Test program selection and execution');
    console.log('   3. Monitor real-time progress updates');
    console.log('   4. Test error handling scenarios');

  } catch (error) {
    console.log('💥 Test suite failed:');
    console.log(error.message);
  }
}

// Run the tests
runTests();