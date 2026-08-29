#!/usr/bin/env python3
"""Assemble the Claude Design handoff into one self-contained HTML file.

    python3 build.py

Reads the handoff + compressed assets from ../../portfolio-site-source and
writes ../site.html -- a single file with every asset inlined as a data URI and
no external dependency except Google Fonts. That file is then encrypted by
../encrypt-site.js into site.enc, which is what actually ships.

site.html is gitignored on purpose: this repo is public, so the unencrypted
site must never be committed.
"""
import base64, glob, json, mimetypes, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..'))
SOURCE = os.path.normpath(os.path.join(REPO, '..', 'portfolio-site-source'))

HANDOFF = os.path.join(SOURCE, 'design_handoff_portfolio_site')
SRC = os.path.join(HANDOFF, 'Sarah Smart Portfolio Site.dc.html')
OPT = os.path.join(SOURCE, 'optimized')
UPLOADS = os.path.join(HANDOFF, 'uploads')
RUNTIME = os.path.join(HERE, 'runtime.js')
OUT = os.path.join(REPO, 'site.html')

for path, what in [(SRC, 'design handoff'), (OPT, 'optimized assets')]:
    if not os.path.exists(path):
        sys.exit('Missing %s: %s\n'
                 'Expected the private source folder at %s\n'
                 '(run build/optimize-assets.py first if only "optimized" is missing)'
                 % (what, path, SOURCE))

raw = open(SRC, encoding='utf-8').read()

# --- 1. template: the <x-dc> subtree, verbatim -------------------------------
m = re.search(r'(<x-dc>.*?</x-dc>)', raw, re.S)
if not m:
    sys.exit('could not find <x-dc> block')
template = m.group(1)

# --- 2. logic: the data + component class ------------------------------------
m = re.search(r'<script type="text/x-dc"[^>]*>(.*?)</script>', raw, re.S)
if not m:
    sys.exit('could not find data-dc-script block')
logic = m.group(1).strip()

# default prop values declared in data-props
props = {'tracker': 'slices', 'lightbox': True}

# --- 3. assets -> data URIs ---------------------------------------------------
assets = {}


def add(key, path):
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    with open(path, 'rb') as fh:
        assets[key] = 'data:%s;base64,%s' % (mime, base64.b64encode(fh.read()).decode())


for p in sorted(glob.glob(os.path.join(OPT, '*'))):
    name = os.path.basename(p)
    stem, ext = os.path.splitext(name)
    if name.startswith('photos-'):
        # chef photo, referenced as uploads/<original name>.jpeg
        add('uploads/' + stem + '.jpeg', p)
    else:
        # referenced in the source as assets/<stem>.png regardless of new ext
        add('assets/' + stem + '.png', p)

# résumé PDF passes through untouched
add('uploads/sarahmsmart-resume-2026.pdf',
    os.path.join(UPLOADS, 'sarahmsmart-resume-2026.pdf'))

runtime = open(RUNTIME, encoding='utf-8').read()

# --- 4. approved copy change --------------------------------------------------
# Owner-requested: flag that the prototype is best viewed on desktop.
before = logic
logic = logic.replace("label: 'HOW TO PLAY'", "label: 'HOW TO PLAY (BEST ON DESKTOP)'")
if logic == before:
    sys.exit('copy change failed: "HOW TO PLAY" label not found')

# --- 5. mobile layer ----------------------------------------------------------
# The prototype is desktop-only: fixed 96px side gutters (to clear the fixed
# arrow buttons), heavy letter-spacing, nowrap rows and flex-1 dotted leaders.
# Below ~760px those overflow the viewport. Targeting the inline-style strings
# lets us fix it without editing the designer's markup.
MOBILE_CSS = """
@media (max-width: 760px) {
  html, body { overflow-x: hidden; }
  img { max-width: 100%; height: auto; }

  /* Content column: reclaim the desktop gutters, leave room for the arrows. */
  [style*="padding:34px 96px 70px"] {
    padding-left: 18px !important;
    padding-right: 18px !important;
    padding-bottom: 92px !important;
  }

  /* Arrows move from the mid-edges (where they sat on top of the text) to the
     bottom corners. Previous keeps its mirroring. */
  button[aria-label="Previous"], button[aria-label="Next"] {
    top: auto !important;
    bottom: 12px !important;
  }
  button[aria-label="Previous"] { left: 10px !important; transform: scaleX(-1) !important; }
  button[aria-label="Next"]     { right: 10px !important; transform: none !important; }
  button[aria-label="Previous"] svg, button[aria-label="Next"] svg {
    width: 44px !important; height: 44px !important;
  }

  /* Dotted leaders have no room to read as leaders in a narrow column. The 2px
     rule matches only leaders; the 1px dotted label underlines are untouched. */
  [style*="border-bottom:2px dotted"] { display: none !important; }

  /* Awards: keep the title and year on one line, drop the description below,
     instead of letting the year strand on its own row. */
  [style*="font-size:12px;color:#B03A22"] {
    order: 2 !important;
    margin-left: auto !important;
  }
  [style*="font-style:italic;font-size:12.5px;color:#5C4B3A"] {
    order: 3 !important;
    flex-basis: 100% !important;
  }
  /* Let a long award title wrap within its own column so the year stays
     alongside it rather than being pushed onto a line of its own.
     A zero flex-basis is what makes this work: with flex-wrap on the row the
     browser wraps items rather than shrinking them, so the title has to start
     from zero width and grow into the space the year leaves. */
  [style*="font-size:13px;color:#2A1F16"] {
    flex: 1 1 0% !important;
    min-width: 0 !important;
  }

  /* Award names, role titles and dates are nowrap for the desktop grid. */
  [style*="white-space:nowrap"] { white-space: normal !important; }

  /* Rows that assume a wide single line: let them stack. */
  [data-screen-label="Menu"]   [style*="display:flex"],
  [data-screen-label="Resume"] [style*="display:flex"] { flex-wrap: wrap !important; }
  [style*="display:flex;align-items:baseline;gap:9px"] {
    flex-wrap: wrap !important;
    gap: 2px 9px !important;
  }

  /* Masthead tracking is tuned for a wide viewport. */
  [style*="letter-spacing:9px"] { letter-spacing: 3px !important; }
  [style*="letter-spacing:6px"] { letter-spacing: 2px !important; }
  [style*="letter-spacing:5px"] { letter-spacing: 2px !important; }

  /* The résumé ends flush with the page, so its last line sat under the
     fixed arrow button. Give it the same clearance the section pages get. */
  [data-screen-label="Resume"] { padding-bottom: 90px !important; }

  /* Logo strip and top bar tighten up. */
  [style*="gap:36px"] { gap: 16px !important; }
  [style*="position:sticky"] { gap: 10px !important; padding: 9px 12px !important; }
}
"""

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Sarah M. Smart &mdash; Portfolio</title>
<style>%s</style>
</head>
<body>
%s
<script>window.__ASSETS = %s;</script>
<script>%s</script>
<script>
%s
__dcBoot(Component, %s);
</script>
</body>
</html>
""" % (MOBILE_CSS, template, json.dumps(assets), runtime, logic, json.dumps(props))

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write(html)

print('assets inlined : %d' % len(assets))
print('output         : %s  (%.2f MB)' % (OUT, os.path.getsize(OUT) / 1e6))
