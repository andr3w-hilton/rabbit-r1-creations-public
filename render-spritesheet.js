const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

(async () => {
  fs.mkdirSync('screenshots', { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();

  const filePath = path.resolve(__dirname, 'spritesheet.html');
  await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0' });

  // Read canvas dimensions from the page
  const dims = await page.evaluate(() => {
    var c = document.getElementById('c');
    return { width: c.width, height: c.height };
  });

  console.log(`Canvas: ${dims.width}x${dims.height}`);

  await page.setViewport({ width: dims.width, height: dims.height, deviceScaleFactor: 2 });

  // Re-navigate so the canvas renders at the correct viewport size
  await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0' });

  // Screenshot just the canvas element
  const canvas = await page.$('canvas');
  await canvas.screenshot({ path: 'screenshots/spritesheet.png' });

  await browser.close();
  console.log('Done — screenshots/spritesheet.png ready.');
})();
