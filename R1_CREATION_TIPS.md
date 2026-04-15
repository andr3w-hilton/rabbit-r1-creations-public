# Rabbit R1 Creation — Tips & Tricks

Hard-won knowledge from building shopping-list, todo, anchor, rep-tracker, spirit-level, notes, dice-roller and the Intern app deep-dive.

---

## Screen & Viewport

- **Fixed size**: 240×282px. Design for this, not the browser window.
- **Correct viewport meta**: `width=240, initial-scale=1.0, user-scalable=no`
  - The Intern app uses `width=240,height=282,user-scalable=no` — both work.
- Set `body { width: 240px; height: 282px; overflow: hidden; }` — never let content overflow.
- No scrollable `body` — implement your own scroll logic with `translateY`.

---

## R1 Native Events (dispatched on `window`)

```javascript
window.addEventListener('sideClick', fn)      // side button single press
window.addEventListener('longPressStart', fn)  // long press begins
window.addEventListener('longPressEnd', fn)    // long press released
window.addEventListener('scrollUp', fn)        // scroll wheel up
window.addEventListener('scrollDown', fn)      // scroll wheel down
```

**Double-click note**: Two `sideClick` events fire ~50ms apart — if you need to distinguish single vs double click, debounce with a short timer.

Always add **keyboard fallbacks** for desktop testing:

```javascript
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape')    window.dispatchEvent(new Event('sideClick'));
  if (e.key === 'ArrowUp')   window.dispatchEvent(new Event('scrollUp'));
  if (e.key === 'ArrowDown') window.dispatchEvent(new Event('scrollDown'));
  if (e.key === ' ' && !e.repeat) window.dispatchEvent(new Event('longPressStart'));
});
document.addEventListener('keyup', function(e) {
  if (e.key === ' ') window.dispatchEvent(new Event('longPressEnd'));
});
```

---

## Voice Input — CreationVoiceHandler (PREFERRED)

Discovered from the Intern app. **Much faster and more accurate** than LiveKit/Deepgram.
No CDN, no tokens, no WebSocket — it's a native R1 bridge.

```javascript
// Start recording (call on longPressStart or sideClick)
if (typeof CreationVoiceHandler !== 'undefined') {
  CreationVoiceHandler.postMessage('start');
}

// Stop recording (call on longPressEnd)
if (typeof CreationVoiceHandler !== 'undefined') {
  CreationVoiceHandler.postMessage('stop');
}

// Result arrives here — wire this up once at page load
window.onPluginMessage = function(data) {
  if (data.type !== 'sttEnded') return;
  var transcript = (data.transcript || '').trim();
  // use transcript...
};
```

**Pattern**: hold side button → listen → release → transcript arrives in `onPluginMessage`.

Guard against double-firing:
```javascript
var isListening = false;
window.addEventListener('longPressStart', function() {
  if (isListening) return;
  isListening = true;
  CreationVoiceHandler.postMessage('start');
});
window.addEventListener('longPressEnd', function() {
  if (!isListening) return;
  CreationVoiceHandler.postMessage('stop');
  // isListening reset to false inside onPluginMessage
});
window.onPluginMessage = function(data) {
  if (data.type !== 'sttEnded') return;
  isListening = false;
  // handle data.transcript
};
```

---

## Keyboard Input / Edit Screens

**Critical discovery**: the R1 WebView supports the keyboard IF you use the right event model.

### What crashes / breaks keyboard
- `touchstart` with `e.preventDefault()` on items — causes crash after ~3 seconds
- Attaching touch events to `document.body` with `preventDefault` — same crash
- Viewport without explicit width

### What works (from Intern app)
- Use `pointerdown` / `pointerup` instead of `touchstart` / `touchend`
- **Do NOT call `e.preventDefault()`** in the item interaction chain
- Open a `<textarea>` edit screen using `classList.add('visible')` / `display: flex`
- Call `textarea.focus()` after making it visible — keyboard opens automatically
- `textarea.blur()` on close — keyboard dismisses

### Double-tap to edit pattern

```javascript
el.addEventListener('pointerdown', function() {
  pressTimer = setTimeout(function() { pressTimer = null; }, 600);
});
el.addEventListener('pointerup', function() {
  clearTimeout(pressTimer);
  var now = Date.now();
  if (now - lastTap < 320) {
    lastTap = 0;
    openEdit(); // double-tap detected
    return;
  }
  lastTap = now;
});
el.addEventListener('pointerleave',  function() { clearTimeout(pressTimer); });
el.addEventListener('pointercancel', function() { clearTimeout(pressTimer); });
```

### Long-press to delete pattern (combined with double-tap)

```javascript
var pressTimer = null, longFired = false, lastTap = 0, singleTimer = null;

row.addEventListener('pointerdown', function(e) {
  if (e.target.closest('.checkbox')) return;
  longFired = false;
  pressTimer = setTimeout(function() {
    longFired = true;
    deleteItem(row.dataset.id);
  }, 600);
});
row.addEventListener('pointerup', function(e) {
  if (e.target.closest('.checkbox')) return;
  clearTimeout(pressTimer);
  if (longFired) return;
  var now = Date.now();
  if (now - lastTap < 320) {
    clearTimeout(singleTimer);
    lastTap = 0;
    editItem(row.dataset.id);
    return;
  }
  lastTap = now;
  singleTimer = setTimeout(function() { lastTap = 0; }, 320);
});
```

### Edit screen HTML template

```html
<div id="edit-screen">
  <div id="edit-header">Edit</div>
  <textarea id="edit-input"></textarea>
  <div id="edit-actions">
    <button id="edit-cancel">Cancel</button>
    <button id="edit-save">Save</button>
  </div>
</div>
```

```css
#edit-screen {
  display: none; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: #0e0e10; flex-direction: column; padding: 14px; z-index: 150;
}
#edit-screen.visible { display: flex; }
#edit-input {
  flex: 1; background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.15); border-radius: 6px;
  color: #fff; font-size: 13px; font-family: inherit;
  padding: 8px; resize: none; outline: none; line-height: 1.5;
}
```

Block side button / scroll when edit screen is open:
```javascript
window.addEventListener('sideClick', function() {
  if ($editScreen.classList.contains('visible')) return;
  // normal handler...
});
```

---

## Storage

### localStorage (works, simple)
```javascript
localStorage.setItem('my_key', JSON.stringify(data));
var data = JSON.parse(localStorage.getItem('my_key') || 'null');
```

### CreationStorageHandler — now works via `window.creationStorage`

**UPDATE**: The old `CreationStorageHandler.postMessage(...)` was broken (fire-and-forget, no return value). The official SDK now injects a proper async API as `window.creationStorage`. Use this for cross-session data that needs to survive app reinstalls, or for secrets. Still use `localStorage` for simple, non-sensitive data.

Data **must be Base64 encoded** before storing. Storage is isolated per plugin ID.

```javascript
// Plain storage (unencrypted)
await window.creationStorage.plain.setItem('key', btoa(JSON.stringify(data)));
const data = JSON.parse(atob(await window.creationStorage.plain.getItem('key')));
await window.creationStorage.plain.removeItem('key');
await window.creationStorage.plain.clear();

// Secure storage (hardware-encrypted, Android M+)
await window.creationStorage.secure.setItem('api_key', btoa('secret_value'));
const secret = atob(await window.creationStorage.secure.getItem('api_key'));
await window.creationStorage.secure.removeItem('api_key');
await window.creationStorage.secure.clear();
```

Returns `null` if the item doesn't exist. Guard with:
```javascript
const raw = await window.creationStorage.plain.getItem('key');
const data = raw ? JSON.parse(atob(raw)) : null;
```

---

## LLM Integration — PluginMessageHandler

**Discovered from official SDK.** Creations can send messages to the R1's built-in LLM and receive structured JSON responses back via `window.onPluginMessage`. The `pluginId` is automatically injected by the system.

```javascript
// Send a plain message to the server (no LLM)
PluginMessageHandler.postMessage(JSON.stringify({
  message: "Hello from my creation"
}));

// Ask the LLM for a JSON response — arrives via window.onPluginMessage
PluginMessageHandler.postMessage(JSON.stringify({
  message: "Give me 3 cat facts. Return JSON: {\"facts\": [\"...\",\"...\",\"...\"]}",
  useLLM: true
}));

// Have the R1 speak the response aloud (does NOT save to journal)
PluginMessageHandler.postMessage(JSON.stringify({
  message: "Tell me something interesting.",
  useLLM: true,
  wantsR1Response: true
}));

// Speak AND save to journal
PluginMessageHandler.postMessage(JSON.stringify({
  message: "Tell me something interesting.",
  useLLM: true,
  wantsR1Response: true,
  wantsJournalEntry: true
}));
```

**Receiving the response** — `data.data` is a JSON string you must parse; fall back to `data.message` for plain text:

```javascript
window.onPluginMessage = function(data) {
  // For STT results: data.type === 'sttEnded', data.transcript
  // For LLM results: data.data (JSON string) or data.message (plain string)
  if (data.data) {
    try {
      var parsed = JSON.parse(data.data);
      // use parsed.facts, parsed.action, etc.
    } catch (e) {
      // plain string
    }
  }
};
```

**Flags summary:**
| Flag | Default | Effect |
|---|---|---|
| `useLLM` | false | Route message through the R1's LLM |
| `wantsR1Response` | false | LLM speaks response through R1 speaker |
| `wantsJournalEntry` | false | Log this interaction to the journal |

---

## Accelerometer — window.creationSensors

**Note: `window.creationSensors` is not available on all R1 firmware versions.** Always check availability and fall back to `DeviceMotionEvent` (see below).

```javascript
// Check availability first
const available = await window.creationSensors.accelerometer.isAvailable();

// Start streaming — callback fires at specified Hz
window.creationSensors.accelerometer.start(function(data) {
  // data.x, data.y, data.z — normalized -1 to 1 (orientation/tilt values)
  // x: positive = tilt right,  negative = tilt left
  // y: positive = tilt forward, negative = tilt back
  // z: positive = facing up,    negative = facing down
  // NOTE: these are orientation values, NOT raw acceleration —
  // magnitude is always ~1.0 regardless of motion speed.
}, { frequency: 60 }); // 10 / 30 / 60 / 100 Hz

// Stop when not needed (saves battery)
window.creationSensors.accelerometer.stop();
```

Always guard with `isAvailable()` before starting, and stop the sensor when leaving the relevant view.

---

## Shake Detection — DeviceMotionEvent (RELIABLE FALLBACK)

`window.creationSensors` may not be available on all firmware. For shake detection, use `DeviceMotionEvent` which works reliably on the R1's Android WebView without any permission request.

`accelerationIncludingGravity` is in **m/s²** — at rest ≈ 9.8 on the z-axis. A deliberate shake produces a large jerk (delta between samples) well above that baseline.

```javascript
function initShakeDetection() {
  var px = null, py = null, pz = null;
  var canShake = true;

  window.addEventListener('devicemotion', function(e) {
    var a = e.accelerationIncludingGravity;
    if (!a) return;
    var x = a.x || 0, y = a.y || 0, z = a.z || 0;

    if (px !== null) {
      var jx = x - px, jy = y - py, jz = z - pz;
      var jmag = Math.sqrt(jx*jx + jy*jy + jz*jz);

      if (jmag > 8 && canShake) {   // 8 m/s² = reliable shake threshold
        canShake = false;
        onShake();                   // your handler here
        setTimeout(function() { canShake = true; }, 1000); // cooldown
      }
    }
    px = x; py = y; pz = z;
  });
}
```

**Recommended pattern** — try native bridge first, fall back to DeviceMotionEvent:

```javascript
async function initSensors() {
  if (typeof window.creationSensors !== 'undefined') {
    try {
      var ok = await window.creationSensors.accelerometer.isAvailable();
      if (ok) {
        window.creationSensors.accelerometer.start(onData, { frequency: 60 });
        return;
      }
    } catch(e) {}
  }
  // Fall back to DeviceMotionEvent
  initShakeDetection();
}
```

**Threshold guide (jmag in m/s²):**
| Value | Sensitivity |
|---|---|
| `> 5` | Very sensitive — may false-trigger from quick tilts |
| `> 8` | Good default — catches deliberate shake, ignores normal movement |
| `> 12` | Firm shake required |

---

## closeWebView — Exit to Home Screen

```javascript
// Close the creation and return to the R1 home screen
closeWebView.postMessage("");
```

Useful for apps with a "Done" or quit button.

---

## TouchEventHandler — Simulate Touch Programmatically

```javascript
// Tap at coordinates
TouchEventHandler.postMessage(JSON.stringify({ type: "tap", x: 120, y: 141 }));

// Other event types
TouchEventHandler.postMessage(JSON.stringify({ type: "down", x: 120, y: 141 }));
TouchEventHandler.postMessage(JSON.stringify({ type: "up",   x: 120, y: 141 }));
TouchEventHandler.postMessage(JSON.stringify({ type: "move", x: 120, y: 141 }));
```

Primarily useful for automation, accessibility, or onboarding tutorials.

---

## Scrolling

Manual scroll with `translateY` — standard pattern:

```javascript
var scrollOffset = 0; // in pixels (for pixel scroll) or items (for list scroll)

function doScroll(delta) {
  var maxScroll = Math.max(0, contentHeight() - viewHeight());
  scrollOffset = Math.min(maxScroll, Math.max(0, scrollOffset + delta));
  content.style.transform = 'translateY(-' + scrollOffset + 'px)';
  updateScrollbar();
}

window.addEventListener('scrollUp',   function() { doScroll(-30); });
window.addEventListener('scrollDown', function() { doScroll(30); });
```

For item-based lists (fixed row height):
```javascript
window.addEventListener('scrollUp',   function() { if (scrollOffset > 0) { scrollOffset--; render(); } });
window.addEventListener('scrollDown', function() { if (scrollOffset < max) { scrollOffset++; render(); } });
```

---

## Multi-page / Tab Pattern

Use `sideClick` to cycle pages, store index in a variable:

```javascript
var PAGES = ['Page1', 'Page2', 'Page3'];
var currentPage = 0;

window.addEventListener('sideClick', function() {
  if (editScreenVisible) return; // guard
  currentPage = (currentPage + 1) % PAGES.length;
  render();
});
```

Navigation dots:
```html
<div id="dots">
  <div class="dot" id="dot-0"></div>
  <div class="dot" id="dot-1"></div>
</div>
```
```javascript
document.querySelectorAll('.dot').forEach(function(d, i) {
  d.classList.toggle('active', i === currentPage);
});
```

---

## Theming with CSS Custom Properties

For multi-page apps with different accent colours per page:

```javascript
var THEMES = [
  { accent: '#FF9EBB', dim: 'rgba(255,158,187,0.22)' },
  { accent: '#2DD4BF', dim: 'rgba(45,212,191,0.22)' }
];

function setTheme(idx) {
  var t = THEMES[idx];
  document.documentElement.style.setProperty('--accent', t.accent);
  document.documentElement.style.setProperty('--accent-dim', t.dim);
}
```

Then use `var(--accent)` throughout CSS — buttons, borders, text highlights all update automatically when page changes.

---

## Collapsible Sections

Pure CSS with `max-height` transition — no JS height calculation needed:

```css
.section-body { max-height: 0; overflow: hidden; transition: max-height 0.25s ease; }
.section.open .section-body { max-height: 600px; } /* large enough to fit content */
.section-arrow { transition: transform 0.22s ease; }
.section.open .section-arrow { transform: rotate(90deg); }
```

```javascript
// Use 'click' not 'touchstart' — avoids conflict with double-tap detection
hdr.addEventListener('click', function() {
  hdr.parentElement.classList.toggle('open');
  updateScrollbar(); // recalculate after expand/collapse
});
```

---

## Inline Bold/Highlight Syntax

For editable content that needs rich text, use a lightweight `**bold**` marker:

```javascript
function renderText(text) {
  // First escape HTML, then apply bold markers
  return esc(text).replace(/\*\*(.+?)\*\*/g,
    '<strong style="color:var(--accent);font-weight:700">$1</strong>');
}
```

In the edit textarea, the user sees and edits the raw `**...**` markers — simple and transparent.

---

## Card Appearance (install.html QR payload)

The `themeColor` in the QR JSON controls the card colour shown in the R1 app stack:

```javascript
var qrData = JSON.stringify({
  title: "My Creation",
  url: "https://your-domain.com/my-slug/?v=1",
  description: "What it does",
  iconUrl: "",
  themeColor: "#FE5000"  // ← card colour in the stack
});
```

Colour reference used across our apps:
| App           | themeColor  | Notes              |
|---------------|-------------|-------------------|
| Anchor        | `#C0C4CC`   | Light grey        |
| Rep Tracker   | `#86EFAC`   | Light green       |
| Shopping List | `#FDE047`   | Yellow            |
| Todo          | `#FE5000`   | R1 orange         |

---

## Cache Busting

**The R1 caches creations by URL.** To force a fresh install after updates:

1. Bump `?v=N` in `install.html`: `https://your-domain.com/my-slug/?v=2`
2. Regenerate and scan the new QR code
3. The old installed version keeps running until the user rescans

The `index.html` itself is not cached between loads — only the initial install URL is.

---

## Deployment

Each creation is a plain HTML file — no build step, no dependencies. Any static host works.

**Netlify (recommended — free, drag and drop):**
1. Go to [netlify.com](https://netlify.com) and drag your app folder onto the dashboard
2. Netlify gives you a URL like `https://my-app.netlify.app`
3. Update `install.html` with that URL and regenerate your QR

**GitHub Pages (free, version controlled):**
1. Push your app folder to a GitHub repo
2. Go to Settings → Pages → set source to your branch
3. Your URL will be `https://username.github.io/repo-name/app-name/`

**Your own server:**
```bash
# Copy files to your server
scp index.html install.html user@your-server:/var/www/my-slug/

# Verify it's live
curl -sk -o /dev/null -w "%{http_code}" https://your-domain.com/my-slug/
```

---

## General Design Rules

- **Dark background**: `#0e0e10` — works best on the small screen
- **Default accent**: `#FE5000` (R1 brand orange)
- **Font**: `-apple-system, sans-serif` — no external fonts, they won't load reliably
- **Font sizes**: brand/label 10px · secondary 11px · list items 12–13px · primary content 14–18px
- **No WebGL** — Flutter WebView doesn't support it. Canvas 2D only.
- **No `onclick` in `innerHTML`** — always use `addEventListener`
- **HTTPS required** for mic access (`navigator.mediaDevices` is undefined over HTTP)
- **Self-contained** — inline all CSS and JS. CDN `<script>` tags are fine.
- Keep UI minimal — every pixel counts at 240×282

### Performance (R1 hardware is limited)
- Prefer hardware-accelerated CSS properties: `transform` and `opacity` over `top`/`left`/`width`
- Use **CSS transitions** instead of JavaScript animations wherever possible
- Minimise DOM operations — batch updates, avoid layout thrash
- Avoid particle effects or heavy canvas animations

---

## What Didn't Work (Lessons Learned)

| Approach | Problem | Solution |
|---|---|---|
| LiveKit + Deepgram STT | Fragmented transcripts, duplicate words, complex setup | Switch to `CreationVoiceHandler` |
| `touchstart` + `preventDefault` on items | Keyboard crashes after ~3s | Use `pointerdown`/`pointerup`, no `preventDefault` |
| Old `CreationStorageHandler.postMessage(...)` directly | Fire-and-forget — `getItem` always returned nothing | Use `window.creationStorage.plain` / `.secure` (official SDK, promise-based) |
| Deepgram cumulative segments | "wallnut pictue wallnut picture frames from wallnut..." | Moot — `CreationVoiceHandler` returns a single clean transcript |
| `onclick` in innerHTML strings | Silent failures in WebView | Always `addEventListener` |
