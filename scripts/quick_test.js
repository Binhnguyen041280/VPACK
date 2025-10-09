const puppeteer = require('puppeteer');

async function testProgramPage() {
  let browser;
  try {
    browser = await puppeteer.launch({ headless: false });
    const page = await browser.newPage();

    console.log('🌐 Navigating to program page...');
    await page.goto('http://localhost:3000/program');

    console.log('⏳ Waiting for page to load...');
    await page.waitForSelector('[data-testid="program-card"], .chakra-button, button', { timeout: 10000 });

    console.log('🔍 Looking for clickable elements...');

    // Check for program cards
    const programCards = await page.$$('div[role="button"], .css-*');
    console.log(`Found ${programCards.length} potential program cards`);

    // Check for buttons
    const buttons = await page.$$('button');
    console.log(`Found ${buttons.length} buttons`);

    // Try to find Default Program card and click it
    const defaultCard = await page.$x("//text()[contains(., 'Default')]/ancestor::div[contains(@class, 'css-')]");
    if (defaultCard.length > 0) {
      console.log('✅ Found Default Program card, attempting click...');
      await defaultCard[0].click();
      await page.waitForTimeout(2000);
      console.log('✅ Click successful!');
    } else {
      console.log('❌ Default Program card not found');
    }

    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('❌ Error:', error.message);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

testProgramPage();