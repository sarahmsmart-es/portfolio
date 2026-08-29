#!/usr/bin/env python3
"""Compress the design handoff's images before they get inlined.

The handoff ships 1400px RGBA PNGs that the layout displays at <=600px, which
made the bundle ~19MB. Screenshots render on white figure cards, so flattening
their alpha onto white and re-encoding as JPEG is visually lossless at the sizes
they're shown. Logos sit on a cream strip and do need transparency, so they stay
as palette PNGs.

    python3 optimize-assets.py            # uses the default paths below
    python3 optimize-assets.py SRC OUT

Requires Pillow:  python3 -m pip install pillow
"""
import glob
import io
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.normpath(os.path.join(HERE, '..', '..', 'portfolio-site-source'))

src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SOURCE, 'design_handoff_portfolio_site')
out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SOURCE, 'optimized')

JPEG_QUALITY = 82

os.makedirs(out_dir, exist_ok=True)

paths = sorted(glob.glob(os.path.join(src_dir, 'assets', '*.png'))) + \
        sorted(glob.glob(os.path.join(src_dir, 'uploads', '*.jpeg')))
if not paths:
    sys.exit('No images found under %s' % src_dir)

before = after = 0
for path in paths:
    name = os.path.basename(path)
    im = Image.open(path)
    before += os.path.getsize(path)

    if name.startswith('logo-'):
        # Needs transparency: palette PNG keeps alpha and shrinks well.
        out = im.convert('RGBA').quantize(colors=256, method=Image.FASTOCTREE)
        buf = io.BytesIO()
        out.save(buf, 'PNG', optimize=True)
        ext = 'png'
    else:
        # Rendered on white cards, so flattening alpha changes nothing visually.
        rgba = im.convert('RGBA')
        flat = Image.new('RGB', rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.getchannel('A'))
        buf = io.BytesIO()
        flat.save(buf, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        ext = 'jpg'

    data = buf.getvalue()
    with open(os.path.join(out_dir, os.path.splitext(name)[0] + '.' + ext), 'wb') as fh:
        fh.write(data)
    after += len(data)

print('%d images: %.2f MB -> %.2f MB (%d%% smaller)'
      % (len(paths), before / 1e6, after / 1e6, round((1 - after / before) * 100)))
print('written to %s' % out_dir)
