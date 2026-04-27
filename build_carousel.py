# “””
RELEASED Healing Method – Carousel PPTX Builder

Flask service. Make POSTs Claude’s JSON output to /build-carousel.
Returns a .pptx file as a binary response.

Deploy to Railway, Render, or any Python host.
Set PHOTOS_DIR environment variable to the folder containing PHOTO-A.jpg through PHOTO-G.jpg.

Dependencies: flask, python-pptx, Pillow, numpy, lxml
“””

import io
import json
import os
import sys
import tempfile
from copy import deepcopy

import numpy as np
from flask import Flask, request, send_file, jsonify
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt, Emu
from lxml import etree

app = Flask(**name**)

# ─────────────────────────────────────────────

# CANVAS

# ─────────────────────────────────────────────

SLIDE_W = Inches(11.25)
SLIDE_H = Inches(14.0625)
LM = Inches(0.9375) # left margin
TW = Inches(9.375) # text width
TOP_S1 = Inches(2.25) # headline top – slide 1
TOP_INT = Inches(0.875) # section label top – interior slides

# ─────────────────────────────────────────────

# COLORS

# ─────────────────────────────────────────────

def s(val):
“”“Safely convert any value to string. Returns empty string for None/dict/list.”””
if val is None:
return ‘’
if isinstance(val, (dict, list)):
return ‘’
return str(val)

def rgb(h):
“”“Convert hex string to RGBColor.”””
h = h.lstrip(’#’)
return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def rgb_tuple(h):
h = h.lstrip(’#’)
return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

# Brand palette – exact values only

C = {
‘cream’: ‘#FAF6EE’,
‘offwhite’: ‘#F5F0E8’,
‘dark_brown’: ‘#4a403a’,
‘fg_green’: ‘#11836b’,
‘fg_deep’: ‘#2D3D31’,
‘teal’: ‘#6fafb8’,
‘terra’: ‘#c47a6a’,
‘terra_deep’: ‘#a0503c’,
‘gold’: ‘#e6c98a’,
‘sage’: ‘#83b7a8’,
‘sage_deep’: ‘#4a7a6e’,
‘salmon’: ‘#e6a78f’,
‘deep_terra’: ‘#7b2d1a’,
‘mid_terra’: ‘#a34e3a’,
‘teal_deep’: ‘#3a6e78’,
‘espresso’: ‘#3D2E24’,
}

# Gradient recipes: name -> list of hex stops (top to bottom)

GRADIENTS = {
‘deep_terra’: [’#7b2d1a’, ‘#a34e3a’, ‘#c47a6a’],
‘terra_salmon’: [’#c47a6a’, ‘#e6a78f’],
‘green_teal’: [’#11836b’, ‘#6fafb8’],
‘fg_deep’: [’#2c3d31’, ‘#1a493b’],
‘sage_sagedeep’: [’#4a7a6e’, ‘#83b7a8’],
‘forest_teal’: [’#1c4a38’, ‘#2d7a6a’],
}

# ─────────────────────────────────────────────

# GRADIENT GENERATION (PIL / numpy)

# ─────────────────────────────────────────────

def make_gradient_image(stops, width=1080, height=1350):
“””
Build a vertical gradient from a list of hex color stops.
Uses numpy interpolation – never PPTX native gradients.
“””
stops_rgb = [rgb_tuple(s) for s in stops]
n = len(stops_rgb)
arr = np.zeros((height, width, 3), dtype=np.uint8)

```
segment_h = height // (n - 1)
for seg in range(n - 1):
c1 = stops_rgb[seg]
c2 = stops_rgb[seg + 1]
y_start = seg * segment_h
y_end = (seg + 1) * segment_h if seg < n - 2 else height
seg_len = y_end - y_start
for i in range(seg_len):
t = i / max(seg_len - 1, 1)
row = y_start + i
arr[row, :] = [
int(c1[j] + t * (c2[j] - c1[j])) for j in range(3)
]
return Image.fromarray(arr, 'RGB')
```

def add_gradient_bg(slide, stops):
“”“Add a PIL gradient as a full-slide background image at z-index 2.”””
img = make_gradient_image(stops)
buf = io.BytesIO()
img.save(buf, format=‘PNG’)
buf.seek(0)
pic = slide.shapes.add_picture(buf, 0, 0, SLIDE_W, SLIDE_H)
# Push to back (behind all text boxes)
sp_tree = slide.shapes._spTree
sp_tree.remove(pic._element)
sp_tree.insert(2, pic._element)

def add_solid_bg(slide, hex_color):
“”“Add a solid color rectangle as background.”””
shape = slide.shapes.add_shape(
1, # MSO_SHAPE_TYPE.RECTANGLE
0, 0, SLIDE_W, SLIDE_H
)
shape.fill.solid()
shape.fill.fore_color.rgb = rgb(hex_color)
shape.line.fill.background()
# Push to back
sp_tree = slide.shapes._spTree
sp_tree.remove(shape._element)
sp_tree.insert(2, shape._element)

# ─────────────────────────────────────────────

# PHOTO HANDLING

# ─────────────────────────────────────────────

PHOTOS_DIR = os.environ.get(‘PHOTOS_DIR’, ‘./photos’)

PHOTO_FILES = {
‘PHOTO-A’: ‘PHOTO-A.jpg’,
‘PHOTO-B’: ‘PHOTO-B.jpg’,
‘PHOTO-C’: ‘PHOTO-C.jpg’,
‘PHOTO-D’: ‘PHOTO-D.jpg’,
‘PHOTO-E’: ‘PHOTO-E.jpg’,
‘PHOTO-F’: ‘PHOTO-F.jpg’,
‘PHOTO-G’: ‘PHOTO-G.jpg’,
}

def add_photo_bg(slide, photo_key, tint_color_hex, tint_opacity=0.52):
“””
Load photo, crop to 1080x1350, apply tint, embed at z-index 2.
Text zone: PHOTO-F = top (clear wall zone). PHOTO-A = lower 40%.
Tint opacity range: 0.45-0.62.
“””
path = os.path.join(PHOTOS_DIR, PHOTO_FILES.get(photo_key, ‘PHOTO-A.jpg’))
if not os.path.exists(path):
# Fallback: solid background in tint color if photo missing
add_solid_bg(slide, tint_color_hex)
return

```
img = Image.open(path).convert('RGB')

# Center-crop to 1080x1350
target_w, target_h = 1080, 1350
w_scale = target_w / img.width
h_scale = target_h / img.height
scale = max(w_scale, h_scale)
new_w = int(img.width * scale)
new_h = int(img.height * scale)
img = img.resize((new_w, new_h), Image.LANCZOS)

# For portrait photos (PHOTO-F): crop from top to preserve face at bottom
if photo_key == 'PHOTO-F':
ty = 0
else:
ty = (new_h - target_h) // 2
tx = (new_w - target_w) // 2
img = img.crop((tx, ty, tx + target_w, ty + target_h))

# Apply tint overlay
tint = Image.new('RGB', (target_w, target_h), rgb_tuple(tint_color_hex))
img = Image.blend(img, tint, alpha=tint_opacity)

buf = io.BytesIO()
img.save(buf, format='PNG')
buf.seek(0)

pic = slide.shapes.add_picture(buf, 0, 0, SLIDE_W, SLIDE_H)
sp_tree = slide.shapes._spTree
sp_tree.remove(pic._element)
sp_tree.insert(2, pic._element)
```

# ─────────────────────────────────────────────

# TEXT BOX HELPERS

# ─────────────────────────────────────────────

def add_textbox(slide, text, x, y, w, h, font_name, pt_size,
color_hex, italic=False, align=PP_ALIGN.LEFT, space_after=0):
“”“Add a single-run text box. Returns the shape.”””
txBox = slide.shapes.add_textbox(x, y, w, h)
tf = txBox.text_frame
tf.word_wrap = True
tf.auto_size = None
p = tf.paragraphs[0]
p.alignment = align
run = p.add_run()
run.text = text
run.font.name = font_name
run.font.size = Pt(pt_size)
run.font.color.rgb = rgb(color_hex)
run.font.italic = italic
run.font.bold = False
if space_after:
p.space_after = Pt(space_after)
return txBox

def add_headline_mixed(slide, regular_text, italic_text, x, y, w, h,
font_name, pt_size, reg_color, italic_color,
align=PP_ALIGN.LEFT):
“””
Add a headline with a regular portion and an italic accent portion.
Both on the same line (same paragraph, two runs).
“””
txBox = slide.shapes.add_textbox(x, y, w, h)
tf = txBox.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.alignment = align

```
if regular_text:
r1 = p.add_run()
r1.text = regular_text
r1.font.name = font_name
r1.font.size = Pt(pt_size)
r1.font.color.rgb = rgb(reg_color)
r1.font.italic = False
r1.font.bold = False

if italic_text:
r2 = p.add_run()
r2.text = italic_text
r2.font.name = font_name
r2.font.size = Pt(pt_size)
r2.font.color.rgb = rgb(italic_color)
r2.font.italic = True
r2.font.bold = False

return txBox
```

def set_letter_spacing(run, spc_value=150):
“””
Set letter spacing (character spacing) on a run via XML.
spc=150 in OOXML = 1.5pt letter spacing.
Required for section labels – cannot be set via python-pptx API.
“””
rPr = run._r.get_or_add_rPr()
rPr.set(‘spc’, str(spc_value))

# ─────────────────────────────────────────────

# BRAND ELEMENTS

# ─────────────────────────────────────────────

def add_accent_mark(slide, color_hex):
“””
Short horizontal rule at bottom-left.
Appears on Slide 1 and final slide only. Never interior slides.
“””
shape = slide.shapes.add_shape(
1,
LM, Inches(12.08),
Inches(1.458), Inches(0.104)
)
shape.fill.solid()
shape.fill.fore_color.rgb = rgb(color_hex)
shape.line.fill.background()

def add_section_label(slide, label_text, accent_color_hex):
“””
Section label: short accent bar + tracked-caps Calibri text.
Interior slides 2-5 only. Never Slide 1.
label_text should already be ALL CAPS.
“””
# Accent bar
bar = slide.shapes.add_shape(
1,
LM, Inches(0.90),
Inches(0.43), Inches(0.04)
)
bar.fill.solid()
bar.fill.fore_color.rgb = rgb(accent_color_hex)
bar.line.fill.background()

```
# Label text with letter spacing
txBox = slide.shapes.add_textbox(
Inches(1.47), Inches(0.875),
Inches(8.5), Inches(0.35)
)
tf = txBox.text_frame
p = tf.paragraphs[0]
run = p.add_run()
run.text = label_text.upper()
run.font.name = 'Calibri'
run.font.size = Pt(16)
run.font.color.rgb = rgb(accent_color_hex)
run.font.bold = True
run.font.italic = False
set_letter_spacing(run, 150)
```

# ─────────────────────────────────────────────

# SLIDE BUILDERS

# ─────────────────────────────────────────────

def build_slide_1(prs, copy, carousel_type, photo_assignment, italic_accent_color, gradient_spec):
“””
S1 Hook – type-driven background.
Type 1: full-bleed photo + tint.
Type 2: deep gradient cover.
Type 3: cream background.
No section label. No logo. Accent mark on.
“””
slide_layout = prs.slide_layouts[6] # blank
slide = prs.slides.add_slide(slide_layout)

```
headline = s(copy.get('headline', ''))
headline_it = s(copy.get('headline_italic', ''))
sub = s(copy.get('sub_statement', ''))

if carousel_type == 1:
# Photo + tint -- use topic primary dark color as tint
tint_color = C['fg_deep'] if 'green' in gradient_spec.lower() else \
C['terra'] if 'terra' in gradient_spec.lower() else \
C['sage_deep'] if 'sage' in gradient_spec.lower() else C['fg_deep']
add_photo_bg(slide, photo_assignment, tint_color, tint_opacity=0.52)
text_y = Inches(7.5) # lower 40% of slide
hl_color = C['offwhite']
hl_it_color = italic_accent_color
sub_color = C['offwhite']
accent_color = C['offwhite']

elif carousel_type == 2:
# Deep gradient cover
stops = GRADIENTS.get(gradient_spec, GRADIENTS['deep_terra'])
add_gradient_bg(slide, stops)
text_y = TOP_S1
hl_color = C['offwhite']
hl_it_color = italic_accent_color
sub_color = C['offwhite']
accent_color = C['offwhite']

else: # Type 3 -- cream
# Accent mark -- always Terracotta on cream background
violations.append('Caption uses she/her for reader -- should use you/your')

s1 = data.get('slide_1_copy', {})
if s1.get('label'):
violations.append('Slide 1 has a section label -- must be removed')
'error': 'Quality gate failures -- do not deliver',
