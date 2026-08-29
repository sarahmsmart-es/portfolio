# Rebuilding the portfolio site

`work.sarahmsmart.net` serves a password gate (`index.html`) plus one encrypted
blob (`site.enc`). The blob is the entire site — markup, styles, and all 57
images inlined as data URIs — so nothing is fetchable without the password,
including the résumé PDF.

## ⚠️ This repo is public

GitHub Pages' free tier requires it. So:

- **Never commit `site.html`** (the unencrypted site). It's gitignored.
- **Never commit the design handoff or its assets.** They live outside the repo,
  in `../portfolio-site-source/`.
- `site.enc` is safe to commit — it's useless without the password.
- `deck/` is public **on purpose**: the PDF there is meant to be shareable.

## Layout

```
portfolio-site/              (this repo — PUBLIC)
  index.html                 password gate
  encrypt-site.js            site.html -> site.enc
  site.enc                   what actually ships
  site.html                  gitignored, generated
  deck/                      public PDF
  build/
    build.py                 assembles site.html
    runtime.js               renderer for the .dc template format
    optimize-assets.py       image compression

portfolio-site-source/       (NOT in git — keep it off GitHub)
  design_handoff_portfolio_site/   unzipped Claude Design handoff
  design-handoff-original.zip      the handoff as delivered
  optimized/                       compressed assets (generated)
```

## Rebuild

```sh
python3 build/optimize-assets.py     # only after a new handoff
python3 build/build.py               # writes site.html
node encrypt-site.js                 # prompts for the password -> site.enc
git add -A && git commit && git push
```

Then confirm the deployed blob matches what you encrypted:

```sh
curl -s https://work.sarahmsmart.net/site.enc | cmp - site.enc && echo match
```

## What `runtime.js` is for

The handoff is a Claude Design `.dc.html` prototype, not a runnable site — its
runtime (`support.js`) isn't included, and the README calls it a design
reference to be recreated. Rather than hand-port 400 lines of inline styles,
`runtime.js` implements the four directives the prototype actually uses:

| Directive | Behaviour |
|---|---|
| `<sc-if value="{{ expr }}">` | render children when truthy |
| `<sc-for list="{{ expr }}" as="x">` | repeat children with `x` in scope |
| `{{ expr }}` | interpolate in text and attributes |
| `onClick="{{ fn }}"` | bind as a listener |

Everything else passes through verbatim, so the design renders exactly as
delivered and the content comes straight from the `sections()` object in the
prototype — the README's stated source of truth.

Two things that will bite if you touch it:

- Elements are **cloned**, not recreated. `document.createElement` drops the SVG
  namespace and the pizza-slice icons silently vanish.
- Asset paths are assembled at runtime (`A + 'p04-i1.png'`), so they're resolved
  through `window.__ASSETS` at attribute-set time — static `src`s included, or
  the logos break.

## The mobile layer

`build.py` injects a `@media (max-width: 760px)` block. The prototype is
desktop-only: fixed 96px side gutters to clear the arrow buttons, heavy
letter-spacing, `white-space:nowrap` rows, and `flex:1` dotted leaders — all of
which overflow a phone.

The rules target the prototype's **inline-style strings**
(`[style*="padding:34px 96px 70px"]`), which keeps the designer's markup
untouched and leaves desktop identical. If a new handoff changes those inline
styles, the selectors need re-checking — that's the tradeoff.

Note the leaders are matched on `border-bottom:2px dotted`; the label underlines
are `1px` and deliberately survive.

## Verifying mobile

Chrome headless clamps its viewport to **500px minimum**, so `--window-size=390`
lays out at 500 and crops to 390 — which looks exactly like an overflow bug that
isn't there. Render inside a fixed-width iframe instead:

```sh
printf '<body style="margin:0"><iframe src="site.html" style="width:390px;height:1800px;border:0;display:block"></iframe></body>' > /tmp/h.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --hide-scrollbars --allow-file-access-from-files \
  --virtual-time-budget=10000 --window-size=390,1800 \
  --screenshot=/tmp/mobile.png "file:///tmp/h.html"
```

## Changing copy

All slide content lives in the `sections()` object inside the handoff's
`.dc.html`. Editing there and rebuilding is the clean path. `build.py` also
applies one owner-approved override (the `HOW TO PLAY (BEST ON DESKTOP)` label)
and will fail loudly if that string stops matching, rather than silently
dropping the change.
