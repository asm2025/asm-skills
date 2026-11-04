# Full-page screenshots

Use this when the user wants the whole page in one image. A plain `fullPage=true` capture only grows the page when the document itself scrolls. Many web apps (a header, a sidebar, and a main area) scroll inside a box instead, and `fullPage` then returns the viewport only.

## Which recipe

Run the detection function once, with the browser at the tutorial's viewport size and the page in the state you want to capture:

```js
() => {
  const se = document.scrollingElement || document.documentElement;
  const docHidden = Math.max(0, se.scrollHeight - innerHeight);
  const boxes = [];
  for (const el of document.querySelectorAll('body, body *')) {
    if (!/(auto|scroll|overlay)/.test(getComputedStyle(el).overflowY)) continue;
    const hidden = el.scrollHeight - el.clientHeight;
    if (hidden <= 1) continue;
    const r = el.getBoundingClientRect();
    const w = Math.min(r.right, innerWidth) - Math.max(r.left, 0);
    const h = Math.min(r.bottom, innerHeight) - Math.max(r.top, 0);
    if (w <= 0 || h <= 0) continue;
    boxes.push({ el, hidden, area: w * h, isMain: el.matches('main, [role=main]') });
  }
  boxes.sort((a, b) => (b.area - a.area) || (b.isMain - a.isMain));
  const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    [...e.classList].slice(0, 3).map(c => '.' + c).join('');
  const main = boxes[0];
  document.querySelectorAll('[data-dw-scroll]').forEach(e => e.removeAttribute('data-dw-scroll'));
  if (main) { main.el.setAttribute('data-dw-scroll', 'main'); main.el.scrollTop = 0; }
  return {
    viewport: [innerWidth, innerHeight],
    documentScrolls: docHidden > 1, documentHidden: docHidden,
    box: main ? { selector: '[data-dw-scroll=main]', name: name(main.el), hidden: main.hidden } : null,
    others: boxes.slice(1, 6).map(b => ({ name: name(b.el), hidden: b.hidden })),
  };
}
```

- `documentScrolls` is `true`: use "Document scrolls".
- `box` is not `null`: use "Page scrolls inside a box".
- Neither: the viewport screenshot already is the full page.

## Document scrolls

A full-page capture drops the page's scrollbar, which shifts centered content sideways. Hide the scrollbar first and measure (`SKILL.md` step 3) in that same state, then capture:

```
browser_evaluate         function="() => { document.documentElement.style.overflow = 'hidden'; scrollTo(0, 0); }"
browser_take_screenshot  scale="css"  fullPage=true  filename="<shots>/<step_name>_full.png"
browser_evaluate         function="() => { document.documentElement.style.overflow = ''; }"
```

Run the last line before interacting with the page again.

## Page scrolls inside a box

Make the browser window as tall as the content, so nothing scrolls, then take a viewport screenshot.

1. Note the size: `viewport` from the detection result is `[width, height]`; `hidden` is the box's hidden height.
2. `browser_resize  width=<width>  height=<height + hidden>`, then `browser_wait_for  time=1` so the layout settles.
3. Run the detection function again. If `box` is not `null`, a box is still cut off (an app that sizes itself from the window height can grow while it loads more): add the new `hidden` to the current window height and repeat step 2. Stop after three rounds.
4. `browser_take_screenshot  scale="css"  filename="<shots>/<step_name>_full.png"` (a viewport screenshot, not `fullPage`).
5. Measure markers now, in this tall state (`SKILL.md` step 3, viewport row: image x, y = viewport x, y).
6. `browser_resize` back to the tutorial's width and height before interacting with the page again.

## Limits

- Cap the window height at 16000 px. If `height + hidden` is more, resize to 16000, capture, and tell the user the image is cut at that height.
- Pages sized in `vh` units stretch with the window, so the content may change shape; check the image.
- Any `others` entry still cut off after the final round is a second scroll area (a sidebar, for example). Tell the user it is cut off in the image.
- Content inside iframes and shadow roots is not detected. If the screenshot still looks cut off, say so and use element screenshots for that part.
