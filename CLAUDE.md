# Rabbit R1 Projects — Dev Notes

## R1 Scroll Direction

Always use **natural scrolling**: physical scroll up = value/selection goes UP, physical scroll down = value/selection goes DOWN.

On the R1 device, the physical wheel directions map **inverted** to the JS events:
- Physical scroll up → fires `scrollUp` event → should **decrease** numeric values / move selection up
- Physical scroll down → fires `scrollDown` event → should **increase** numeric values / move selection down

This means for counters, lists, and menus:
```js
window.addEventListener('scrollUp',   () => { value--; }); // UP = decrease index/value in event terms
window.addEventListener('scrollDown', () => { value++; }); // DOWN = increase
```

Apply this consistently in all creations. Never default to the opposite without checking here first.
