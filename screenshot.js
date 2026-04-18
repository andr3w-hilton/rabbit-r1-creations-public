const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const APPS = [
  'shopping-list',
  'todo',
  'rep-tracker',
  'rep-timer',
  'spirit-level',
  'dice-roller',
  'notes',
  'r1-buddy',
  'calendar',
  'gemma-chat',
];

// Seed data injected into localStorage before each page loads
const SEEDS = {
  'shopping-list': {
    r1_shopping: JSON.stringify([
      { id: '1', text: 'Milk', checked: false },
      { id: '2', text: 'Bread', checked: false },
      { id: '3', text: 'Coffee', checked: true, checkedAt: Date.now() },
      { id: '4', text: 'Eggs', checked: false },
      { id: '5', text: 'Butter', checked: false },
    ])
  },
  'todo': {
    r1_todo_home: JSON.stringify([
      { id: '1', text: 'Take out the bins', checked: false },
      { id: '2', text: 'Call the dentist', checked: false },
      { id: '3', text: 'Fix the back gate', checked: true, checkedAt: Date.now() },
      { id: '4', text: 'Book car service', checked: false },
    ])
  },
  'notes': {
    r1_notes: JSON.stringify([
      { id: '1', text: 'Pick up dry cleaning before Thursday', created: Date.now() - 3600000, updated: Date.now() - 3600000 },
      { id: '2', text: 'Ideas for the back garden\nDecking near the fence\nPlanter boxes along the wall', created: Date.now() - 86400000, updated: Date.now() - 86400000 },
      { id: '3', text: 'Call landlord about the boiler', created: Date.now() - 172800000, updated: Date.now() - 172800000 },
    ])
  },
  'gemma-chat': {
    gemma_chat: JSON.stringify([
      { role: 'user',  content: 'What should I have for dinner tonight?' },
      { role: 'gemma', content: 'How about a simple pasta with garlic, olive oil and parmesan? Quick to make and always satisfying.' },
      { role: 'user',  content: 'Sounds good, anything I can add to it?' },
      { role: 'gemma', content: 'Chilli flakes and a handful of fresh basil at the end make a big difference. Crispy pancetta if you have it.' },
    ])
  },
  'calendar': (() => {
    const today = new Date(); today.setHours(0,0,0,0);
    const pad = n => n < 10 ? '0'+n : ''+n;
    const ds = today.getFullYear()+'-'+pad(today.getMonth()+1)+'-'+pad(today.getDate());
    return {
      ['r1_cal_'+ds]: JSON.stringify([
        { id: 'a1', time: '09:00', text: 'Morning standup', created: Date.now() },
        { id: 'a2', time: '12:30', text: 'Lunch with Sarah', created: Date.now() },
        { id: 'a3', time: '15:00', text: 'Code review session', created: Date.now() },
      ])
    };
  })(),
  'r1-buddy': {
    // Stage 2 = KID. born = now minus 5 hours (past the 4h kid threshold)
    r1_buddy: JSON.stringify({
      born: Date.now() - (5 * 60 * 60 * 1000),
      hunger: 72,
      happiness: 85,
      stage: 2
    })
  }
};

(async () => {
  fs.mkdirSync('screenshots', { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  for (const app of APPS) {
    const filePath = path.resolve(__dirname, app, 'index.html');
    if (!fs.existsSync(filePath)) {
      console.log(`Skipping ${app} — no index.html found`);
      continue;
    }

    const page = await browser.newPage();
    await page.setViewport({ width: 240, height: 282, deviceScaleFactor: 2 });

    const seed = SEEDS[app] || {};

    await page.evaluateOnNewDocument((seedData) => {
      // Inject seed localStorage data
      for (const [key, value] of Object.entries(seedData)) {
        localStorage.setItem(key, value);
      }
      // Stub out R1-only APIs so pages don't error
      window.CreationVoiceHandler = { postMessage: () => {} };
      window.creationSensors = {
        accelerometer: {
          isAvailable: async () => false,
          start: () => {},
          stop: () => {}
        }
      };
      window.creationStorage = {
        plain: { getItem: async () => null, setItem: async () => {}, removeItem: async () => {}, clear: async () => {} },
        secure: { getItem: async () => null, setItem: async () => {}, removeItem: async () => {}, clear: async () => {} }
      };
    }, seed);

    await page.goto(`file://${filePath}`, { waitUntil: 'networkidle0', timeout: 10000 }).catch(() => {
      page.goto(`file://${filePath}`, { waitUntil: 'domcontentloaded' });
    });

    // For dice-roller: trigger a roll and wait for animation to finish
    if (app === 'dice-roller') {
      await new Promise(r => setTimeout(r, 500));
      await page.evaluate(() => {
        if (typeof doRoll === 'function') doRoll();
      });
      await new Promise(r => setTimeout(r, 800));
    }

    // Wait for canvas/animations to settle
    await new Promise(r => setTimeout(r, 1500));

    await page.screenshot({ path: `screenshots/${app}.png` });
    await page.close();
    console.log(`✓ ${app}`);
  }

  await browser.close();
  console.log('\nDone — screenshots/ folder ready.');
})();
