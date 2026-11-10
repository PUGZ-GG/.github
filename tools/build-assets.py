#!/usr/bin/env python3
"""Builds the SVG graphics used by profile/README.md into profile/assets/.

GitHub renders README images without our web fonts, so every piece of text here is converted to
outlines with the real brand fonts (Archivo, JetBrains Mono). The colours and shapes follow the
PUGZ design system ("Velocity"): deep navy, the cyan -> blue -> violet -> pink gradient and the
logo's slanted strokes. The logo itself is the real mark, traced from the brand icon.

Several graphics are animated with plain CSS (works inside <img>). Every animation has a visible
resting state and switches off for people who prefer reduced motion.

Usage:  pip install fonttools brotli && python3 tools/build-assets.py
The fonts are downloaded once into tools/.fonts (not committed).
"""

from __future__ import annotations

import hashlib
import math
import re
import urllib.request
from xml.sax.saxutils import escape
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "profile" / "assets"
FONTS = Path(__file__).resolve().parent / ".fonts"
CDN = "https://cdn.jsdelivr.net/npm/@fontsource-variable"

# --- Brand tokens (docs/design-system/pugz/MASTER.md) ---------------------------------------------
INK_950, INK_925, INK_900, INK_850 = "#050516", "#070719", "#0d0d26", "#121233"
TEXT, MUTED, FAINT = "#f0f0fb", "#a2a2c3", "#7c7ca0"
CYAN, BLUE, VIOLET, VIOLET_600, PINK = "#3de3ff", "#4c6bff", "#9b5cff", "#8b4dff", "#f47cf4"
GREEN, RED, AMBER, GOLD, INK_TEXT = "#63f0b5", "#ff8fa3", "#ffcc4d", "#ffd36b", "#07071a"
# The PUG rating ladder of a tiered season (TIER_RANKS in packages/shared/src/domain/tiers.ts):
# a name, the rating it starts at, its colour and its tier. Staff can change all of it per season.
TIERS = [  # lowest first
    ("Rookie", "<1150", "#6583A3", "rookie", "B"),
    ("Prospect", "1150+", "#6194C4", "prospect", "B"),
    ("Contender", "1300+", "#58A5E4", "contender", "B"),
    ("Challenger", "1450+", "#4DBF74", "challenger", "A"),
    ("Pro", "1600+", "#5ECD6B", "pro", "A"),
    ("Elite", "1750+", "#74DA5C", "elite", "A"),
    ("Star", "1900+", "#E6D441", "star", "S"),
    ("All-Star", "2050+", "#FFB90E", "allstar", "S"),
    ("Legend", "2200+", "#FF8C1E", "legend", "S"),
]

DISCORD_GLYPH = (
    "M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447."
    "8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077."
    "077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-"
    ".319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294"
    "a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-."
    "6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-."
    "2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095"
    "c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766."
    "0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 "
    "3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a"
    ".061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2."
    "4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7."
    "9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.175"
    "7 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"
)

# The logo's two strokes, traced from the brand icon (pugz-icon.png) so the curves are the real
# ones: the rounded bowl, the soft tip and the sharp counter. Image coordinates, viewBox below.
MARK_VIEW = (180, 305, 912, 702)
MARK_TOP = (
    "M824 747.5C858.4 743.5 886.7 730.8 913.8 707C929 693.7 933 688.6 971.3 633.7C979.7 621.8 995.7 "
    "598.8 1006.9 582.7C1040.5 534.7 1043 531.2 1054.7 514.1C1076.7 482.1 1085.3 459.8 1086.6 431C1089.6 "
    "369 1048 320 984.4 310.5C972.7 308.8 347.3 308.1 341.5 309.8C322.6 315.4 314.1 333.8 323.3 349.2C328.5 "
    "357.8 414.2 462.1 422.2 469.5C435.7 482 450.7 489.9 469.5 494.4C478.5 496.5 478.8 496.5 632.5 496.5C757.5 "
    "496.5 787.1 496.7 789.5 497.8C799.3 502.1 803.9 513.3 799.8 523C799 524.9 774.7 562 745.8 605.5C661.4 "
    "732.6 651.9 747.1 652.5 748.1C653.6 749.7 809.2 749.3 824 747.5Z"
)
MARK_LOW = (
    "M248.5 984.2C272.2 974.9 328.4 952.7 373.5 935C498.6 885.9 492.6 888.4 507.6 878.3C524.5 867.1 534.7 "
    "854.7 569.5 803C578.2 790.1 592.4 769.1 601 756.5C609.6 743.9 627.8 716.9 641.5 696.5C655.2 676.1 672 "
    "651.2 678.9 641C721.5 577.7 722 576.8 722 572.2C722 566.8 719.8 562.5 715.7 560C711.3 557.3 534.1 556.9 "
    "520.1 559.5C494.9 564.3 474.5 575.4 456.8 593.9C448.7 602.4 441.1 613.3 390.5 689.5C323.4 790.5 297.6 "
    "829.4 252 898.5C182.9 1003.2 187.8 994.9 192.6 999.7C197 1004.1 201.1 1003 248.5 984.2Z"
)


# --- Text as outlines -----------------------------------------------------------------------------
class Face:
    """One instance of a variable font, able to measure text and turn it into an SVG path."""

    def __init__(self, family: str, filename: str, axes: dict[str, float]):
        FONTS.mkdir(exist_ok=True)
        path = FONTS / filename
        if not path.exists():
            urllib.request.urlretrieve(f"{CDN}/{family}/files/{filename}", path)
        self.tag = f"{filename}{sorted(axes.items())}"
        self.font = instancer.instantiateVariableFont(TTFont(path), axes, inplace=False)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upem = self.font["head"].unitsPerEm
        self.cap = self.font["OS/2"].sCapHeight / self.upem

    def _glyph(self, ch: str) -> str:
        if ord(ch) not in self.cmap:
            raise KeyError(f"glyph {ch!r} missing from font")
        return self.cmap[ord(ch)]

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        advance = sum(self.glyphs[self._glyph(c)].width for c in text) * size / self.upem
        return advance + tracking * size * (len(text) - 1)

    def outline(self, text: str, size: float, x: float, y: float, tracking: float = 0.0) -> str:
        """Path data for `text` with its baseline-left at (x, y)."""
        scale = size / self.upem
        pen_x, parts = x, []
        for ch in text:
            glyph = self.glyphs[self._glyph(ch)]
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
            glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, pen_x, y)))
            parts.append(pen.getCommands())
            pen_x += glyph.width * scale + tracking * size
        return "".join(parts)

    def glyph(self, ch: str, size: float) -> tuple[str, float]:
        """The id of an outlined glyph at the origin (defined once per SVG, see `svg`) and its advance."""
        scale = size / self.upem
        gid = "g" + hashlib.md5(f"{self.tag}|{size:.3f}|{ch}".encode()).hexdigest()[:8]
        if gid not in GLYPH_DEFS:
            glyph = self.glyphs[self._glyph(ch)]
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
            glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, 0, 0)))
            GLYPH_DEFS[gid] = pen.getCommands()
        return gid, self.glyphs[self._glyph(ch)].width * scale

    def fit(self, text: str, size: float, max_width: float, tracking: float = 0.0) -> float:
        width = self.width(text, size, tracking)
        return size if width <= max_width else size * max_width / width

    def wrap(self, text: str, size: float, max_width: float) -> list[str]:
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if line and self.width(trial, size) > max_width:
                lines.append(line)
                line = word
            else:
                line = trial
        return lines + [line] if line else lines


GLYPH_DEFS: dict[str, str] = {}


DISPLAY = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 800, "wdth": 125})
HEADING = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 700, "wdth": 112})
BODY = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 500, "wdth": 100})
BODY_BOLD = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 700, "wdth": 100})
LABEL = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 800, "wdth": 100})
H2 = LABEL  # the profit card's heading, as on the site (Archivo 800)
LEAD = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 400, "wdth": 100})
BLACK = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 900, "wdth": 125})
MONO = Face("jetbrains-mono", "jetbrains-mono-latin-wght-normal.woff2", {"wght": 600})


def text(face: Face, s: str, size: float, x: float, y: float, fill: str, *, tracking: float = 0.0,
         anchor: str = "start", extra: str = "") -> str:
    """Text as references to outlined glyphs, so each letter's outline is stored once per SVG."""
    width = face.width(s, size, tracking)
    pen_x = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
    if fill.startswith("url("):
        # A gradient has to span the whole text in one coordinate space, which shared glyph
        # references can't do (each would sample the gradient from its own origin).
        return f'<path d="{face.outline(s, size, pen_x, y, tracking)}" fill="{fill}" {extra}/>'
    uses = []
    for ch in s:
        gid, advance = face.glyph(ch, size)
        if ch != " ":
            uses.append(f'<use href="#{gid}" x="{pen_x:.1f}" y="{y:.1f}"/>')
        pen_x += advance + tracking * size
    return f'<g fill="{fill}" {extra}>{"".join(uses)}</g>'


# --- Shared SVG pieces ----------------------------------------------------------------------------
REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
PULSE_CSS = ".pulse{animation:pulse 2.2s ease-in-out infinite}@keyframes pulse{50%{opacity:.3}}"

GRADIENTS = f"""
<linearGradient id="brand" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{CYAN}"/><stop offset=".34" stop-color="{BLUE}"/>
  <stop offset=".66" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/>
</linearGradient>
<linearGradient id="button" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#6fe9ff"/><stop offset=".34" stop-color="#7b8cff"/>
  <stop offset=".66" stop-color="#b07cff"/><stop offset="1" stop-color="#f79cf7"/>
</linearGradient>
<linearGradient id="markTop" x1="0" y1="0" x2="1" y2=".6">
  <stop offset="0" stop-color="#43e6ff"/><stop offset=".4" stop-color="{BLUE}"/>
  <stop offset=".72" stop-color="#b07cff"/><stop offset="1" stop-color="#ff8af0"/>
</linearGradient>
<linearGradient id="markLow" x1="0" y1="1" x2="1" y2="0">
  <stop offset="0" stop-color="#d6e0ff"/><stop offset="1" stop-color="#3b5bff"/>
</linearGradient>
"""

BLUR_FILTERS = (
    '<filter id="glow-sm" x="-30%" y="-60%" width="160%" height="240%"><feGaussianBlur stdDeviation="9"/></filter>'
    '<filter id="glow-lg" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="34"/></filter>'
)


def svg(width: int, height: int, title: str, desc: str, body: str, defs: str = "", style: str = "") -> str:
    style_tag = f"<style>{style}{REDUCED}</style>" if style else ""
    used = sorted(set(re.findall(r'href="#(g[0-9a-f]{8})"', body)))
    glyph_defs = "".join(f'<path id="{g}" d="{GLYPH_DEFS[g]}"/>' for g in used)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">'
        f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
        f"<defs>{GRADIENTS}{defs}{glyph_defs}</defs>{style_tag}{body}</svg>\n"
    )


def attrs(**kw: str) -> str:
    return " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())


def para(x: float, y: float, w: float, h: float, slant: float, **kw: str) -> str:
    """The brand's slanted parallelogram (a "/" lean), top edge shifted right by `slant`."""
    pts = f"{x + slant:.1f},{y:.1f} {x + w:.1f},{y:.1f} {x + w - slant:.1f},{y + h:.1f} {x:.1f},{y + h:.1f}"
    return f'<polygon points="{pts}" {attrs(**kw)}/>'


def mark(x: float, y: float, width: float) -> str:
    vx, vy, vw, _ = MARK_VIEW
    s = width / vw
    return (
        f'<g transform="translate({x} {y}) scale({s:.4f}) translate({-vx} {-vy})">'
        f'<path d="{MARK_LOW}" fill="url(#markLow)"/><path d="{MARK_TOP}" fill="url(#markTop)"/></g>'
    )


def button(x: float, y: float, label: str, w: float = 196, h: float = 46) -> str:
    """The primary button: brand-button fill, ink text, violet glow."""
    size, icon, gap = 15, 20, 10
    label_w = LABEL.width(label, size, 0.01)
    start = x + (w - (icon + gap + label_w)) / 2
    return (
        f'<rect x="{x}" y="{y + 6}" width="{w}" height="{h}" rx="12" fill="{VIOLET}" opacity=".45" filter="url(#glow-sm)"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="url(#button)"/>'
        f'<g transform="translate({start:.1f} {y + (h - icon) / 2:.1f}) scale({icon / 24})">'
        f'<path d="{DISCORD_GLYPH}" fill="{INK_TEXT}"/></g>'
        + text(LABEL, label, size, start + icon + gap, y + h / 2 + size * LABEL.cap / 2, INK_TEXT, tracking=0.01)
    )


def tag(x: float, y: float, label: str, color: str, *, h: float = 24, dot: bool = False, size: float = 10.5,
        cls: str = "") -> tuple[str, float]:
    """A slanted tag with tinted fill; returns (svg, width)."""
    label_w = LABEL.width(label, size, 0.16)
    pad = 14 + (14 if dot else 0)
    w = label_w + pad * 2
    parts = [para(x, y, w, h, 6, fill=color, fill_opacity=".14", stroke=color, stroke_opacity=".45", stroke_width="1")]
    if dot:
        parts.append(f'<circle class="pulse" cx="{x + pad + 3:.1f}" cy="{y + h / 2:.1f}" r="3.5" fill="{color}"/>')
    parts.append(text(LABEL, label, size, x + pad + (14 if dot else 0), y + h / 2 + size * LABEL.cap / 2, color, tracking=0.16))
    return "".join(parts), w


def panel(w: int, h: int, fill: str = INK_950, radius: int = 24) -> str:
    return (
        f'<rect width="{w}" height="{h}" rx="{radius}" fill="{fill}"/>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{radius - .5}" fill="none" stroke="#fff" stroke-opacity=".09"/>'
    )


def card(x: float, y: float, w: float, h: float, radius: int = 14, fill: str = INK_900) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="#fff" stroke-opacity=".08"/>'
        f'<rect x="{x + radius}" y="{y + 1}" width="48" height="2" fill="url(#brand)"/>'
    )


def star(cx: float, cy: float, r: float) -> str:
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts.append(f"{cx + rad * math.cos(a):.1f},{cy + rad * math.sin(a):.1f}")
    return " ".join(pts)


def smooth(points: list[tuple[float, float]]) -> str:
    """A smooth line through the points (Catmull-Rom converted to cubic Beziers)."""
    d = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]
        p1, p2 = points[i], points[i + 1]
        p3 = points[min(i + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d


def cycle_css(names: str, count: int, seconds: float) -> str:
    """CSS that lights element `.{names}0..N` one after another, in a loop (resting state: hidden)."""
    step = seconds / count
    rules = "".join(f".{names}{i}{{animation-delay:{i * step:.2f}s}}" for i in range(count))
    return (
        f".{names}{{opacity:0;animation:{names}Act {seconds}s ease-in-out infinite}}{rules}"
        f"@keyframes {names}Act{{0%{{opacity:0}}5%{{opacity:1}}{int(100 / count) - 4}%{{opacity:1}}{int(100 / count)}%{{opacity:0}}100%{{opacity:0}}}}"
    )


# --- Assets ---------------------------------------------------------------------------------------
def banner() -> str:
    w, h = 900, 400
    left = 48
    word, word_size = "PUGZ", 118
    word_w = DISPLAY.width(word, word_size, -0.025)
    shafts = "".join(
        f'<g class="shaft s{i}">{para(x, -20, sw, h + 40, 150, fill="url(#shaftFill)", opacity=op)}</g>'
        for i, (x, sw, op) in enumerate([(430, 34, ".55"), (520, 90, ".35"), (650, 22, ".7"), (730, 120, ".28"), (860, 46, ".45")], 1)
    )
    live, live_w = tag(left, 38, "IN CLOSED BETA", AMBER, dot=True)
    comm, _ = tag(left + live_w + 10, 38, "THE COMPETITIVE HUB", CYAN)
    vx, vy, vw, vh = MARK_VIEW
    mx, my, mw = 566, 84, 300
    s = mw / vw
    mark_inner = (
        f'<g transform="translate({mx} {my}) scale({s:.4f}) translate({-vx} {-vy})">'
        f'<path d="{MARK_LOW}" fill="url(#markLow)"/><path d="{MARK_TOP}" fill="url(#markTop)"/>'
        '<g clip-path="url(#markClip)"><rect class="sheen" x="0" y="250" width="260" height="900" fill="url(#sheenFill)"/></g></g>'
    )
    glow_inner = (
        f'<g transform="translate({mx} {my}) scale({s:.4f}) translate({-vx} {-vy})">'
        f'<path d="{MARK_LOW}" fill="url(#markLow)"/><path d="{MARK_TOP}" fill="url(#markTop)"/></g>'
    )
    body = (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="24"/></clipPath>'
        f'<clipPath id="markClip"><path d="{MARK_LOW}"/><path d="{MARK_TOP}"/></clipPath>'
        f'<rect width="{w}" height="{h}" rx="24" fill="{INK_950}"/>'
        '<g clip-path="url(#card)">'
        f'<circle cx="90" cy="20" r="260" fill="{CYAN}" opacity=".16" filter="url(#glow-lg)"/>'
        f'<circle cx="700" cy="190" r="250" fill="{VIOLET}" opacity=".42" filter="url(#glow-lg)"/>'
        f'<circle cx="860" cy="400" r="170" fill="{PINK}" opacity=".2" filter="url(#glow-lg)"/>'
        f"{shafts}"
        f'<g opacity=".55" filter="url(#glow-lg)">{glow_inner}</g>'
        f'<g class="float">{mark_inner}</g>'
        "</g>"
        f"{live}{comm}"
        + text(DISPLAY, word, word_size, left - 4, 188, "url(#wordFill)", tracking=-0.025)
        + text(HEADING, "The competitive home of THE FINALS.", 27, left, 238, TEXT)
        + text(BODY, "PUGs, scrims, tournaments, coaching and seasons.", 15, left, 274, MUTED)
        + text(BODY, "Played on Discord. Tracked on the web.", 15, left, 296, MUTED)
        + button(left, 322, "Join the Discord")
        + f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="23.5" fill="none" stroke="#fff" stroke-opacity=".1"/>'
    )
    defs = (
        BLUR_FILTERS
        + f'<linearGradient id="wordFill" gradientUnits="userSpaceOnUse" x1="{left}" y1="0" x2="{left + word_w}" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}"/><stop offset=".34" stop-color="{BLUE}"/>'
        f'<stop offset=".66" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        '<linearGradient id="shaftFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{VIOLET}" stop-opacity="0"/><stop offset=".5" stop-color="{VIOLET}" stop-opacity=".5"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="sheenFill" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
    )
    style = (
        ".shaft{animation:drift 13s ease-in-out infinite alternate}"
        ".s2{animation-duration:17s;animation-delay:-5s}.s3{animation-duration:11s;animation-delay:-3s}"
        ".s4{animation-duration:20s;animation-delay:-9s}.s5{animation-duration:15s;animation-delay:-7s}"
        ".float{animation:float 7s ease-in-out infinite alternate}"
        ".sheen{transform:skewX(-20deg);animation:sheen 6s ease-in-out infinite}"
        "@keyframes drift{from{transform:translateX(-26px)}to{transform:translateX(30px)}}"
        "@keyframes float{from{transform:translateY(-7px)}to{transform:translateY(7px)}}"
        "@keyframes sheen{0%{transform:translateX(-520px) skewX(-20deg)}55%,100%{transform:translateX(1300px) skewX(-20deg)}}"
        + PULSE_CSS
    )
    return svg(w, h, "PUGZ", "PUGZ. The competitive home of THE FINALS: PUGs, scrims, tournaments, coaching and seasons. In closed beta. Join the Discord.", body, defs, style)


def eyebrow(label: str) -> str:
    """Section label: the slash glyph, then tracked uppercase text. Violet so it reads on light and dark."""
    size, tracking = 11, 0.18
    w, h = int(LABEL.width(label, size, tracking) + 34), 22
    body = (
        '<polygon points="4,17 10,5 14,5 8,17" fill="url(#brand)"/>'
        + text(LABEL, label, size, 24, 16.2, VIOLET_600, tracking=tracking)
    )
    return svg(w, h, label.title(), f"Section label: {label.title()}", body)


def divider() -> str:
    w = 900
    body = (
        '<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".2" stop-color="{CYAN}"/>'
        f'<stop offset=".5" stop-color="{VIOLET}"/><stop offset=".8" stop-color="{PINK}"/>'
        f'<stop offset="1" stop-color="{PINK}" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="glint" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        + para(0, 3, w, 2, 0, fill="url(#fade)")
        + para(w / 2 - 22, 0, 44, 8, 6, fill=VIOLET_600)
        + '<rect class="glint" x="-120" y="2.5" width="120" height="3" fill="url(#glint)"/>'
    )
    style = ".glint{animation:glint 7s ease-in-out infinite}@keyframes glint{0%{transform:translateX(0)}60%,100%{transform:translateX(1020px)}}"
    return svg(w, 8, "Divider", "A thin brand-gradient divider with a slanted notch.", body, "", style)


# The brand gradient, one colour per queue slot (as on the Discord queue panel).
SLOT_COLORS = [CYAN, "#45a8ff", BLUE, "#7663ff", VIOLET, PINK]

FLOW = [
    ("01", "Queue", "Join from Discord or the site. One click in, one click out.", "DISCORD · WEB"),
    ("02", "Lobby", "The queue pops. Ready up in voice, then vote the map.", "DISCORD"),
    ("03", "Match", "Team voice channels, a host and a lobby code.", "DISCORD · WEB"),
    ("04", "Result", "One team reports, the other confirms. Disputes go to staff.", "DISCORD · WEB"),
    ("05", "Rank", "Your rating, the season and the leaderboard move.", "WEB · DISCORD"),
]


def tick(x: float, y: float, color: str, s: float = 1.0) -> str:
    return (f'<polyline points="{x - 3.5 * s:.1f},{y:.1f} {x - 1 * s:.1f},{y + 2.6 * s:.1f} {x + 3.8 * s:.1f},{y - 2.8 * s:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{1.8 * s:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')


def flow_visual(i: int, cx: float, top: float) -> str:
    """A small picture of each step, drawn in the space under the step's title."""
    if i == 0:  # Queue: the six slots fill up in the brand gradient.
        sw, gap = 15, 4
        x0 = cx - (6 * sw + 5 * gap) / 2
        out = "".join(para(x0 + s * (sw + gap), top + 8, sw, 22, 5, fill=SLOT_COLORS[s]) for s in range(6))
        a, b = BODY_BOLD.width("6/6", 13), BODY.width(" · pops", 12)
        return out + text(BODY_BOLD, "6/6", 13, cx - (a + b) / 2, top + 52, TEXT) + text(BODY, " · pops", 12, cx - (a + b) / 2 + a, top + 52, PINK)
    if i == 1:  # Lobby: everyone ready, then the map vote.
        out = ""
        for s in range(6):
            x = cx - 47.5 + s * 19
            out += f'<circle cx="{x:.1f}" cy="{top + 16}" r="7.5" fill="{GREEN}" fill-opacity=".16" stroke="{GREEN}" stroke-opacity=".7"/>' + tick(x, top + 16, GREEN, 0.9)
        out += text(LABEL, "MAP VOTE", 8.5, cx - 52, top + 44, FAINT, tracking=0.14)
        out += f'<rect x="{cx - 52}" y="{top + 50}" width="104" height="6" rx="3" fill="#fff" fill-opacity=".08"/>'
        out += f'<rect x="{cx - 52}" y="{top + 50}" width="70" height="6" rx="3" fill="url(#brand)"/>'
        return out
    if i == 2:  # Match: two teams of three, and the lobby code.
        out = ""
        for side, (x, color) in enumerate(((cx - 58, CYAN), (cx + 12, PINK))):
            out += para(x, top + 4, 46, 30, 7, fill=color, fill_opacity=".12", stroke=color, stroke_opacity=".6")
            out += "".join(f'<circle cx="{x + 11 + d * 12:.1f}" cy="{top + 19}" r="3.6" fill="{color}"/>' for d in range(3))
        out += text(LABEL, "VS", 10, cx, top + 23, TEXT, anchor="middle", tracking=0.08)
        return out + text(MONO, "CODE 4F7K2Q", 10.5, cx, top + 54, FAINT, anchor="middle")
    if i == 3:  # Result: the score, reported and confirmed.
        out = text(DISPLAY, "2–1", 20, cx, top + 24, TEXT, anchor="middle")
        x0 = cx - (12 + BODY.width("Confirmed", 11)) / 2
        for r, label in enumerate(("Reported", "Confirmed")):
            y = top + 42 + r * 15
            out += tick(x0 + 4, y - 4, GREEN, 0.8) + text(BODY, label, 11, x0 + 12, y, MUTED)
        return out
    # Rank: up a rank, with the points gained.
    name, _, color, kind, _t = TIERS[4]
    out = shield(cx - 20, top + 2, 30, color, kind)
    out += f'<polyline points="{cx + 4},{top + 15} {cx + 9},{top + 10} {cx + 14},{top + 15}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    out += text(MONO, "+14", 14, cx + 19, top + 18, GREEN)
    return out + text(BODY_BOLD, name, 11, cx - 20, top + 49, color, anchor="middle") + text(BODY, "rank up", 11, cx + 4, top + 34, MUTED)


def flow() -> str:
    """How a match works, as a pipeline: five steps on a track, a marker running through them."""
    w, h = 900, 362
    n, gap = len(FLOW), 12
    cw = (w - 96 - (n - 1) * gap) / n
    cy, ch, track_y = 84, 252, 50
    centres = [48 + i * (cw + gap) + cw / 2 for i in range(n)]
    # The track along the top, with the step numbers on it.
    out = (
        f'<line x1="{centres[0]:.1f}" x2="{centres[-1]:.1f}" y1="{track_y}" y2="{track_y}" stroke="#fff" stroke-opacity=".1" stroke-width="2"/>'
        f'<rect x="{centres[0]:.1f}" y="{track_y - 1}" width="{centres[-1] - centres[0]:.1f}" height="2" fill="url(#brand)" opacity=".55"/>'
    )
    for i, c in enumerate(centres):
        out += f'<line x1="{c:.1f}" x2="{c:.1f}" y1="{track_y + 13}" y2="{cy}" stroke="#fff" stroke-opacity=".1" stroke-dasharray="2 3"/>'
    nodes, cards, lit = "", "", ""
    for i, ((num, title, desc, where), c) in enumerate(zip(FLOW, centres)):
        x = c - cw / 2
        nodes += (
            para(c - 26, track_y - 13, 52, 26, 7, fill=INK_850, stroke=VIOLET, stroke_opacity=".55")
            + text(MONO, num, 13, c, track_y + 4.6, CYAN, anchor="middle")
        )
        lit += f'<g class="step step{i}">{para(c - 28, track_y - 15, 56, 30, 7, fill=VIOLET_600, fill_opacity=".45", stroke="url(#brand)", stroke_width="1.5")}' \
               + text(MONO, num, 13, c, track_y + 4.6, TEXT, anchor="middle") \
               + f'<rect x="{x:.1f}" y="{cy}" width="{cw:.1f}" height="{ch}" rx="14" fill="{VIOLET}" fill-opacity=".09" stroke="url(#brand)" stroke-width="1.5"/></g>'
        color = CYAN if "·" in where else VIOLET
        tag_w = LABEL.width(where, 9, 0.16) + 28
        tag_svg, _ = tag(c - tag_w / 2, cy + ch - 36, where, color, h=20, size=9)
        lines = BODY.wrap(desc, 12, cw - 28)
        cards += (
            f'<rect x="{x:.1f}" y="{cy}" width="{cw:.1f}" height="{ch}" rx="14" fill="{INK_900}" stroke="#fff" stroke-opacity=".08"/>'
            f'<rect x="{x + 14:.1f}" y="{cy + 1}" width="40" height="2" fill="url(#brand)"/>'
            + text(HEADING, title, 18, c, cy + 34, TEXT, anchor="middle")
            + flow_visual(i, c, cy + 50)
            + "".join(text(BODY, line, 12, c, cy + 140 + k * 16, MUTED, anchor="middle") for k, line in enumerate(lines))
            + tag_svg
        )
    # The runner: a glowing marker that stops at each step while it is lit.
    step = 100 / n
    frames = []
    for i in range(n):
        dx = centres[i] - centres[0]
        frames.append(f"{i * step:.0f}%{{transform:translateX({dx:.1f}px);opacity:1}}")
        frames.append(f"{i * step + step * .7:.0f}%{{transform:translateX({dx:.1f}px);opacity:1}}")
    end = centres[-1] - centres[0]
    runner_css = (
        ".runner{animation:run 10s ease-in-out infinite}"
        f"@keyframes run{{{''.join(frames)}96%{{transform:translateX({end:.1f}px);opacity:0}}100%{{transform:translateX(0);opacity:0}}}}"
    )
    runner = (
        f'<g class="runner"><circle cx="{centres[0]:.1f}" cy="{track_y}" r="14" fill="{CYAN}" opacity=".35" filter="url(#glow-sm)"/>'
        f'<circle cx="{centres[0]:.1f}" cy="{track_y}" r="4.5" fill="#fff"/></g>'
    )
    body = panel(w, h, INK_925) + out + runner + cards + nodes + lit
    style = cycle_css("step", n, 10) + runner_css
    return svg(w, h, "How a match works", "Five steps: queue, lobby, match, result, rank. " + " ".join(f"{t}: {d}" for _, t, d, _ in FLOW),
               body, BLUR_FILTERS, style)


def rating() -> str:
    """How the PUG rating works (ADR 0040, 0042, 0048): drawn like the profile's rating chart."""
    w, h = 900, 350
    cx0, cx1, cy0, cy1 = 48, 852, 74, 166
    ys = [0.42, 0.36, 0.5, 0.58, 0.52, 0.64, 0.7, 0.6, 0.74, 0.8, 0.76, 0.9]
    pts = [(cx0 + (cx1 - cx0) * i / (len(ys) - 1), cy1 - (cy1 - cy0) * v) for i, v in enumerate(ys)]
    line = smooth(pts)
    area = f"{line}L{pts[-1][0]:.1f} {cy1 + 8}L{pts[0][0]:.1f} {cy1 + 8}Z"
    grid = "".join(
        f'<line x1="{cx0}" x2="{cx1}" y1="{y}" y2="{y}" stroke="#fff" stroke-opacity=".07" stroke-dasharray="3 5"/>'
        for y in (cy0 + 8, (cy0 + cy1) / 2, cy1)
    )
    chart = (
        text(LABEL, "RATING THIS SEASON", 11, cx0, 50, MUTED, tracking=0.14)
        + grid
        + f'<path class="fillfade" d="{area}" fill="url(#areaFill)"/>'
        + f'<path class="drawline" pathLength="1" d="{line}" fill="none" stroke="url(#brand)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
        + f'<g class="enddot"><circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="9" fill="{PINK}" opacity=".25"/>'
        f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4.5" fill="{PINK}" stroke="{INK_925}" stroke-width="2"/></g>'
    )
    rules = [
        ("01", "Every scoreline", "2-0 and 2-1 wins, 1-2 and 0-2 losses. Each is worth its own points."),
        ("02", "Upsets pay", "Beat a stronger team and you gain more. Staff tune how much."),
        ("03", "Fast placements", "Your first matches of a season move your rating further."),
        ("04", "Exact ranks", "Cross a threshold and your rank changes right away."),
    ]
    gap = 12
    tw, ty, th = (w - 96 - 3 * gap) / 4, 204, 126
    tiles = ""
    for i, (num, title, hint) in enumerate(rules):
        x = 48 + i * (tw + gap)
        tiles += (
            f'<rect x="{x}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="#fff" fill-opacity=".03" stroke="#fff" stroke-opacity=".06"/>'
            + text(MONO, num, 13, x + 16, ty + 28, CYAN)
            + text(HEADING, title, 16, x + 16, ty + 52, TEXT)
            + "".join(text(BODY, line_, 12.5, x + 16, ty + 74 + j * 16, MUTED) for j, line_ in enumerate(BODY.wrap(hint, 12.5, tw - 32)))
        )
    body = panel(w, h, INK_925) + card(1, 1, w - 2, h - 2, 24, "none") + chart + tiles
    defs = (
        f'<linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity=".38"/>'
        f'<stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>'
    )
    style = (
        ".drawline{animation:draw 9s ease-in-out infinite}"
        ".fillfade{animation:fillfade 9s ease-in-out infinite}.enddot{animation:enddot 9s ease-in-out infinite}"
        "@keyframes draw{0%{stroke-dasharray:1;stroke-dashoffset:1;opacity:1}38%{stroke-dasharray:1;stroke-dashoffset:0}"
        "88%{stroke-dasharray:1;stroke-dashoffset:0;opacity:1}97%{stroke-dasharray:1;stroke-dashoffset:0;opacity:0}"
        "100%{stroke-dasharray:1;stroke-dashoffset:1;opacity:0}}"
        "@keyframes fillfade{0%,8%{opacity:0}40%{opacity:1}88%{opacity:1}97%,100%{opacity:0}}"
        "@keyframes enddot{0%,36%{opacity:0}42%{opacity:1}88%{opacity:1}97%,100%{opacity:0}}"
    )
    return svg(w, h, "How the PUG rating works", "Your PUG rating moves with every result: each scoreline is worth its own points, beating a stronger team pays more, your first matches of a season move it further, and your rank changes the moment you cross a threshold. Illustration of a rating line over a season.", body, defs, style)


def mix(hex_color: str, other: str, t: float) -> str:
    """`hex_color` moved `t` of the way towards `other`."""
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


SHIELD_BODY = "M24 3L42 9V27C42 40 34 49 24 54C14 49 6 40 6 27V9Z"
SPARKLE = "M24 17C25.2 24 27 26 34 28C27 30 25.2 32 24 39C22.8 32 21 30 14 28C21 26 22.8 24 24 17Z"
WING_L = "M7 13C1 10-2 18 3 25C4 21 6 19 9 18Z"
WING_R = "M41 13C47 10 50 18 45 25C44 21 42 19 39 18Z"
CROWN = "M13 8L14-3L19 4L24-7L29 4L34-3L35 8Z"


def shield(cx: float, top: float, height: float, color: str, kind: str) -> str:
    """A rank shield in the style of the season's rank icons: tinted body, strong outline, a darker mark."""
    s = height / 56
    dark = mix(color, "#000000", 0.38)
    fill = mix(color, "#ffffff", 0.58)
    wings = kind in ("legend", "superstar", "allstar", "star", "elite")
    glyph = {
        "sparkle": f'<path d="{SPARKLE}" fill="{dark}"/>',
        "chevron": f'<polyline points="14,34 24,25 34,34" fill="none" stroke="{dark}" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/>',
        "chevron-low": f'<polyline points="14,36 24,27 34,36" fill="none" stroke="{dark}" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/>',
        "equals": f'<rect x="15" y="23" width="18" height="4.6" rx="2.3" fill="{dark}"/><rect x="15" y="31" width="18" height="4.6" rx="2.3" fill="{dark}"/>',
        "dash": f'<rect x="18" y="32" width="12" height="3.6" rx="1.8" fill="{dark}"/>',
    }[{"legend": "sparkle", "superstar": "sparkle", "allstar": "sparkle", "star": "sparkle", "elite": "sparkle",
       "pro": "sparkle", "challenger": "chevron", "contender": "equals", "prospect": "chevron-low", "rookie": "dash"}[kind]]
    parts = ""
    if wings:
        parts += f'<path d="{WING_L}" fill="{color}"/><path d="{WING_R}" fill="{color}"/>'
    if kind == "legend":
        parts += f'<path d="{CROWN}" fill="{color}"/>'
    parts += f'<path d="{SHIELD_BODY}" fill="{fill}" stroke="{color}" stroke-width="3.4" stroke-linejoin="round"/>' + glyph
    return f'<g transform="translate({cx - 24 * s:.1f} {top:.1f}) scale({s:.3f})">{parts}</g>'


def tiers() -> str:
    """The rating ladder: nine ranks in three tiers, lowest to highest, each with its threshold. A highlight climbs it."""
    w, h = 900, 400
    n = len(TIERS)
    col_w = (w - 96) / n
    base, shield_h = 306, 52
    out = [
        text(HEADING, "Climb the ladder.", 22, 48, 54, TEXT)
        + text(BODY, "Three ranks per tier. Cross a line and your rank, and your tier, change right away.", 14, 48, 78, MUTED)
    ]
    tier_colors = {"B": "#58A5E4", "A": "#5ECD6B", "S": "#FFB90E"}
    for k, letter in enumerate("BAS"):
        x0 = 48 + col_w * 3 * k + 6
        bw_ = col_w * 3 - 12
        c = tier_colors[letter]
        out.append(
            f'<rect x="{x0:.1f}" y="{base + 58}" width="{bw_:.1f}" height="2" rx="1" fill="{c}" fill-opacity=".55"/>'
            + text(LABEL, f"TIER {letter}", 11, x0 + bw_ / 2, base + 80, c, anchor="middle", tracking=0.16)
        )
    glow_defs = ""
    glows = ""
    for i, (name, threshold, color, kind, _tier) in enumerate(TIERS):
        cx = 48 + col_w * (i + 0.5)
        block_h = 26 + i * 17
        bx, by, bw = cx - col_w / 2 + 5, base - block_h, col_w - 10
        shield_top = by - 8 - shield_h
        out.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{block_h}" rx="10" fill="{color}" fill-opacity=".09" stroke="{color}" stroke-opacity=".3"/>'
            f'<rect x="{cx - 15:.1f}" y="{by + 1:.1f}" width="30" height="2" fill="{color}"/>'
            + shield(cx, shield_top, shield_h, color, kind)
            + text(BODY_BOLD, name, 12.5, cx, base + 24, color, anchor="middle")
            + text(MONO, threshold, 11.5, cx, base + 42, MUTED, anchor="middle")
        )
        glow_defs += f'<radialGradient id="g{i}"><stop offset="0" stop-color="{color}" stop-opacity=".55"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        glows += (
            f'<g class="climb climb{i}"><circle cx="{cx:.1f}" cy="{shield_top + shield_h / 2:.1f}" r="46" fill="url(#g{i})"/>'
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{block_h}" rx="10" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-width="1.5"/></g>'
        )
    body = panel(w, h, INK_925) + card(1, 1, w - 2, h - 2, 24, "none") + glows + "".join(out)
    style = cycle_css("climb", n, 14)
    return svg(w, h, "The PUG rating ladder", "Nine ranks in three tiers, from Rookie to Legend, set per season by staff. Tier B: Rookie, Prospect, Contender. Tier A: Challenger, Pro, Elite. Tier S: Star, All-Star, Legend. Thresholds: " + ", ".join(f"{t[0]} {t[1]}" for t in TIERS) + ". Ranks are Discord roles and change the moment your rating crosses a threshold; crossing into the next tier moves you up a tier.", body, glow_defs, style)


# --- Architecture diagram -------------------------------------------------------------------------
A_BLUE, A_AMBER, A_GREEN, A_VIOLET, A_RED, A_TEAL, A_GRAY = "#4c9bff", "#ffcc4d", "#3ee6a0", "#c27cff", "#ff5f7d", "#2dd4bf", "#a2a2c3"
ARROW_KEYS = {"blue": A_BLUE, "amber": A_AMBER, "green": A_GREEN, "violet": A_VIOLET, "red": A_RED, "teal": A_TEAL, "gray": A_GRAY}


def arrow_defs() -> str:
    return "".join(
        f'<marker id="m-{k}" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
        for k, c in ARROW_KEYS.items()
    )


def arrow(d: str, key: str, *, dashed: bool = False, both: bool = False, packets: bool = False, reverse: bool = False) -> str:
    color = ARROW_KEYS[key]
    marks = f'marker-end="url(#m-{key})"' + (f' marker-start="url(#m-{key})"' if both else "")
    dash = ' stroke-dasharray="6 5" class="dashflow"' if dashed else ""
    out = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" {marks}{dash}/>'
    if packets:
        cls = "pk pkr" if reverse else "pk"
        out += f'<path class="{cls}" d="{d}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="3" stroke-linecap="round" stroke-dasharray="0.1 28"/>'
    return out


def pill(cx: float, cy: float, label: str, key: str) -> str:
    color = ARROW_KEYS[key]
    pw = BODY_BOLD.width(label, 11) + 20
    return (
        f'<rect x="{cx - pw / 2:.1f}" y="{cy - 10}" width="{pw:.1f}" height="20" rx="10" fill="{INK_950}" stroke="{color}" stroke-opacity=".9"/>'
        + text(BODY_BOLD, label, 11, cx, cy + 3.9, color, anchor="middle")
    )


def icon_users(x: float, y: float) -> str:
    c = "#b8c4ff"
    return (
        f'<circle cx="{x + 10}" cy="{y + 9}" r="5.5" fill="{c}"/><path d="M{x + 1} {y + 26}C{x + 1} {y + 16} {x + 19} {y + 16} {x + 19} {y + 26}Z" fill="{c}"/>'
        f'<circle cx="{x + 22}" cy="{y + 11}" r="4.5" fill="{c}" opacity=".7"/><path d="M{x + 16} {y + 26}C{x + 17} {y + 19} {x + 29} {y + 19} {x + 31} {y + 26}Z" fill="{c}" opacity=".7"/>'
    )


def icon_cloud(x: float, y: float, color: str, solid: bool = True) -> str:
    d = "M8 24C3 24 1 18 6 16C6 9 15 7 18 12C23 8 30 13 27 19C32 20 31 24 26 24Z"
    paint = f'fill="{color}"' if solid else f'fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"'
    return f'<g transform="translate({x} {y - 1})"><path d="{d}" {paint}/></g>'


def icon_discord(x: float, y: float) -> str:
    return f'<g transform="translate({x} {y}) scale({30 / 24})"><path d="{DISCORD_GLYPH}" fill="#5865F2"/></g>'


def icon_window(x: float, y: float) -> str:
    return (
        f'<rect x="{x + 1}" y="{y + 3}" width="28" height="24" rx="4" fill="none" stroke="{A_BLUE}" stroke-width="2.2"/>'
        f'<line x1="{x + 1}" x2="{x + 29}" y1="{y + 10}" y2="{y + 10}" stroke="{A_BLUE}" stroke-width="2.2"/>'
        f'<circle cx="{x + 6}" cy="{y + 6.6}" r="1.2" fill="{A_BLUE}"/><circle cx="{x + 10}" cy="{y + 6.6}" r="1.2" fill="{A_BLUE}"/>'
    )


def icon_gear(x: float, y: float) -> str:
    teeth = "".join(f'<rect x="-2.6" y="-14" width="5.2" height="6" rx="1.2" fill="{A_BLUE}" transform="rotate({a})"/>' for a in range(0, 360, 45))
    return (
        f'<g transform="translate({x + 15} {y + 15})">{teeth}'
        f'<circle r="9.5" fill="none" stroke="{A_BLUE}" stroke-width="5"/><circle r="3.6" fill="{INK_900}"/></g>'
    )


def icon_db(x: float, y: float) -> str:
    c = A_BLUE
    return (
        f'<ellipse cx="{x + 15}" cy="{y + 6}" rx="12" ry="4.5" fill="none" stroke="{c}" stroke-width="2.4"/>'
        f'<path d="M{x + 3} {y + 6}V{y + 24}C{x + 3} {y + 29} {x + 27} {y + 29} {x + 27} {y + 24}V{y + 6}" fill="none" stroke="{c}" stroke-width="2.4"/>'
        f'<path d="M{x + 3} {y + 15}C{x + 3} {y + 20} {x + 27} {y + 20} {x + 27} {y + 15}" fill="none" stroke="{c}" stroke-width="2.4"/>'
    )


def icon_nginx(x: float, y: float) -> str:
    hexa = "15,2 27,8.5 27,21.5 15,28 3,21.5 3,8.5"
    return (
        f'<g transform="translate({x} {y})"><polygon points="{hexa}" fill="#1fa85a"/></g>'
        + text(BLACK, "N", 15, x + 15, y + 20.5, "#fff", anchor="middle")
    )


def icon_drop(x: float, y: float) -> str:
    return f'<path transform="translate({x} {y})" d="M12 1C12 1 3 11 3 17A9 9 0 0 0 21 17C21 11 12 1 12 1ZM12 21a4 4 0 0 1-4-4" fill="{A_BLUE}"/>'


def node(x: float, y: float, w: float, h: float, title: str, lines: list[str], icon: str, *, inline: bool = False,
         title_size: float = 17) -> str:
    out = card(x, y, w, h, 14)
    if inline:
        out += icon + text(HEADING, title, title_size, x + 64, y + 32, TEXT)
        tx, ty0 = x + 64, y + 53
    else:
        out += icon + text(HEADING, title, title_size, x + 58, y + 36, TEXT)
        tx, ty0 = x + 18, y + 70
    for i, line_ in enumerate(lines):
        size = BODY.fit(line_, 12.5, x + w - 14 - tx)
        out += text(BODY, line_, size, tx, ty0 + i * 19, MUTED)
    return out


def container(x: float, y: float, w: float, h: float, title: str) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{A_BLUE}" fill-opacity=".05" stroke="{A_BLUE}" stroke-opacity=".5" stroke-width="1.4"/>'
        + icon_drop(x + 18, y + 14)
        + text(HEADING, title, 17, x + 50, y + 33, "#dfe6ff")
    )


def architecture() -> str:
    w, h = 900, 812
    r1y, r1h = 20, 80
    # Row 1: Cloudflare, players, Discord.
    cf = node(24, r1y, 228, r1h, "Cloudflare", ["DNS and DDoS protection", "Proxy and caching"], icon_cloud(42, r1y + 24, "#f6821f"), inline=True)
    us = node(292, r1y, 252, r1h, "Players and staff", ["Website visitors", "Players, teams, coaches, admins"], icon_users(310, r1y + 22), inline=True)
    dc = node(584, r1y, 292, r1h, "Discord", ["Gateway (events)", "OAuth and REST API"], icon_discord(602, r1y + 22), inline=True)
    # Containers.
    my, mh = 134, 346
    main = container(24, my, 628, mh, "Main droplet")
    work = container(672, my, 204, mh, "Worker droplet")
    nginx = card(44, 176, 500, 50, 12) + icon_nginx(58, 186) + text(HEADING, "Nginx", 16, 98, 207, TEXT) + text(BODY, "TLS termination · Static files · Reverse proxy", 12.5, 164, 206.5, MUTED)
    web = node(44, 280, 212, 160, "Website", ["Public site · Player area", "Admin portal · API", "Discord login · Live updates", "Stripe checkout and webhooks"], icon_window(60, 292))
    bot = node(420, 280, 212, 160, "Bot", ["Discord connection", "Queues · Matches · Results", "Stats · Seasons · Rank roles", "Tournaments · Scrims · Tickets", "Coaching · Moderation"], icon_discord(436, 292))
    wrk = node(688, 236, 172, 204, "Worker", ["Job queue (pg-boss)", "Embark · Steam · Twitch", "Webhook processing", "Season detection", "Cleanup · nightly rebuilds", "Retries · dead-letter queue"], icon_gear(702, 244), title_size=17)
    # Row 3: database, backup, external services, legend.
    db = node(260, 530, 380, 108, "PostgreSQL 18", ["Primary data store · one schema per domain", "One login per program · job queue (pg-boss)"], icon_db(276, 546))
    bk = node(24, 672, 212, 108, "Nightly backup", ["Daily encrypted dump", "Off-site · weekly restore test"], icon_cloud(40, 680, "#9fb0ff", solid=False), title_size=16)
    ex = node(732, 530, 144, 126, "External", ["Embark · Steam · Twitch", "Stripe · Resend", "Liquipedia"], icon_cloud(748, 546, A_GRAY, solid=False), title_size=16)

    arrows = (
        # Traffic in and out (blue).
        arrow("M292 60H252", "blue", both=True) + arrow("M544 60H584", "blue", both=True)
        + arrow("M230 100V176", "blue", packets=True) + pill(230, 142, "HTTPS", "blue")
        + arrow("M149 226V280", "blue", packets=True)
        + arrow("M606 100V280", "blue", both=True) + pill(606, 188, "Events / API", "blue")
        # Web and bot talk through commands and responses (amber).
        + arrow("M256 336H420", "amber", packets=True) + pill(338, 336, "Commands", "amber")
        + arrow("M420 386H256", "amber", packets=True) + pill(338, 386, "Responses", "amber")
        # Database: notifications (green dashed) and reads and writes (violet).
        + arrow("M214 440V552H260", "violet", both=True) + pill(214, 494, "Read / Write", "violet")
        + arrow("M260 594H120V440", "green", dashed=True) + pill(120, 532, "LISTEN / NOTIFY", "green")
        + arrow("M560 440V530", "violet", both=True) + pill(560, 500, "Read / Write", "violet")
        + arrow("M470 530V440", "green", dashed=True) + pill(470, 466, "LISTEN / NOTIFY", "green")
        # Worker: process jobs from the queue (red), sync with the outside world (gray).
        # The worker picks jobs up from the queue in the database and writes the results back.
        + arrow("M640 612H712V440", "red", packets=True)
        + arrow("M690 440V584H640", "red", packets=True)
        + pill(701, 500, "Pick up · process jobs", "red")
        + arrow("M804 440V530", "gray", both=True) + pill(804, 492, "Sync", "gray")
        # Backups (teal dashed).
        + arrow("M260 622H130V672", "teal", dashed=True) + pill(195, 622, "Backup (daily)", "teal")
    )
    # Legend.
    lx, ly, lw, lh = 260, 672, 616, 108
    legend = card(lx, ly, lw, lh, 14) + text(HEADING, "Legend", 14, lx + 18, ly + 26, TEXT)
    items = [
        ("blue", False, "Users and external traffic"), ("amber", False, "Web and bot commands"), ("violet", False, "Database read / write"),
        ("green", True, "Database notifications"), ("red", False, "Job queue"), ("teal", True, "Backups"),
    ]
    for i, (key, dashed, label) in enumerate(items):
        cx = lx + 18 + (i % 3) * 198
        cy = ly + 54 + (i // 3) * 28
        dash = ' stroke-dasharray="6 5"' if dashed else ""
        legend += (
            f'<line x1="{cx}" x2="{cx + 30}" y1="{cy}" y2="{cy}" stroke="{ARROW_KEYS[key]}" stroke-width="2"{dash} marker-end="url(#m-{key})"/>'
            + text(BODY, label, 12, cx + 40, cy + 4, MUTED)
        )
    body = panel(w, h, INK_950) + main + work + cf + us + dc + nginx + web + bot + wrk + db + bk + ex + arrows + legend
    style = (
        ".pk{animation:pk 1.5s linear infinite}.pkr{animation-direction:reverse}"
        "@keyframes pk{to{stroke-dashoffset:-28.1}}"
        ".dashflow{animation:dash 1.2s linear infinite}@keyframes dash{to{stroke-dashoffset:-11}}"
        "@media (prefers-reduced-motion:reduce){.pk{display:none}}"
    )
    desc = (
        "How PUGZ fits together. Players and staff reach the website through Cloudflare and Nginx on the main droplet, and Discord talks to the bot "
        "over its gateway. The website sends commands to the bot and gets responses back. The website, the bot and the worker all use one PostgreSQL "
        "database with change notifications; the worker, on its own droplet, processes the job queue and syncs with Embark, Steam, Twitch, Stripe, "
        "Resend and Liquipedia. A nightly encrypted backup goes off-site."
    )
    return svg(w, h, "PUGZ architecture", desc, body, arrow_defs(), style)


# --- Tournaments: one card that morphs between six formats --------------------------------------
# Drawn and timed like the approved design preview. Plain SVG animation (SMIL), so it plays inside
# a README image where no script runs: every move, line and glow is worked out here on one shared
# timeline. The loop is simulated twice and the second pass is kept, so its end joins its start.

def _s(x, y, name, **o):
    return {"x": x, "y": y, "w": 158, "h": 26, "name": name, "meta": "", "win": False, **o}


def _row(x, y, name, meta, win=False):
    return {"x": x, "y": y, "w": 158, "h": 22, "name": name, "meta": meta, "win": win}


def _box(x, y, name, meta, **o):
    return {"x": x, "y": y, "w": 124, "h": 48, "name": name, "meta": meta, "win": False, "box": True, **o}


T_FORMATS = [
    {
        "name": "Single elimination",
        "labels": [(0, 52, "Quarter-finals"), (200, 52, "Semi-finals"), (400, 52, "Final")],
        "slots": [
            _s(0, 76, "Seed 1", win=True), _s(0, 104, "Seed 8"), _s(0, 140, "Seed 4"), _s(0, 168, "Seed 5", win=True),
            _s(0, 204, "Seed 3", win=True), _s(0, 232, "Seed 6"), _s(0, 268, "Seed 2", win=True), _s(0, 296, "Seed 7"),
            _s(200, 108, "Seed 1", win=True), _s(200, 136, "Seed 5"), _s(200, 236, "Seed 3"), _s(200, 264, "Seed 2", win=True),
            _s(400, 172, "Seed 1", win=True), _s(400, 200, "Seed 2"),
        ],
        "links": [(0, 8, 1), (3, 9, 0), (4, 10, 0), (6, 11, 0), (8, 12, 1), (11, 13, 0), (12, "c", 1)],
        "champ": {"x": 600, "y": 150, "w": 172, "title": "Champion", "who": "Seed 1", "line": "Recorded on every profile, forever."},
    },
    {
        "name": "Double elimination",
        "labels": [(0, 52, "Upper bracket"), (0, 202, "Lower bracket"), (400, 52, "Grand final")],
        "slots": [
            _s(0, 76, "Seed 1", win=True), _s(0, 104, "Seed 4"), _s(0, 140, "Seed 2", win=True), _s(0, 168, "Seed 3"),
            _s(200, 108, "Seed 1", win=True), _s(200, 136, "Seed 2"),
            _s(0, 226, "Seed 3", win=True, meta="from upper"), _s(0, 254, "Seed 4", meta="from upper"),
            _s(200, 240, "Seed 2", meta="from upper"), _s(200, 268, "Seed 3", win=True),
            _s(400, 172, "Seed 1", win=True), _s(400, 200, "Seed 3"),
        ],
        # drops (upper-bracket losers) are shown by the "from upper" note: timed, not drawn
        "links": [(0, 4, 1), (2, 5, 0), (1, 7, 0, {"drop": True}), (3, 6, 0, {"drop": True}), (4, 10, 1),
                  (5, 8, 0, {"drop": True}), (6, 9, 0), (9, 11, 0), (10, "c", 1)],
        "champ": {"x": 600, "y": 150, "w": 172, "title": "Champion", "who": "Seed 1", "line": "Lose once and you drop to the lower bracket."},
    },
    {
        "name": "Round robin",
        "labels": [(0, 52, "Standings"), (255, 52, "W–L"), (318, 52, "Pts")],
        "slots": [{"x": 0, "y": 76 + i * 36, "w": 360, "h": 30, "name": n, "meta": f"{wl}   {p:>2}", "win": win, "rr": True}
                  for i, (n, wl, p, win) in enumerate([("Seed 1", "5–0", 15, True), ("Seed 3", "4–1", 12, True), ("Seed 2", "3–2", 9, False),
                                                       ("Seed 5", "2–3", 6, False), ("Seed 4", "1–4", 3, False), ("Seed 6", "0–5", 0, False)])],
        "links": [(0, "c", 1)],
        "champ": {"x": 430, "y": 120, "w": 200, "title": "Leader", "who": "Seed 1 · 5–0", "line": "Everyone plays everyone. The top two meet in the final."},
    },
    {
        "name": "Swiss",
        "labels": [(0, 52, "Round 1"), (150, 52, "Round 2"), (300, 52, "Round 3"), (450, 52, "Result")],
        "slots": [
            _box(0, 176, "0–0", "8 teams"),
            _box(150, 116, "1–0", "4 teams"), _box(150, 236, "0–1", "4 teams"),
            _box(300, 76, "2–0", "2 teams"), _box(300, 176, "1–1", "4 teams"), _box(300, 276, "0–2", "2 teams"),
            _box(450, 106, "Advance", "2–0 and 2–1", win=True), _box(450, 246, "Out", "1–2 and 0–2", out=True),
        ],
        "links": [(0, 1, 1), (0, 2, 0), (1, 3, 1), (1, 4, 0), (2, 4, 1), (2, 5, 0), (3, 6, 1), (4, 6, 1), (4, 7, 0), (5, 7, 0), (6, "c", 1)],
        "champ": {"x": 610, "y": 106, "w": 172, "title": "Qualified", "who": "4 teams", "line": "Two wins and you are through. Two losses and you are out."},
    },
    {
        "name": "Groups into playoffs",
        "labels": [(0, 52, "Groups"), (200, 52, "Semi-finals"), (400, 52, "Final")],
        "frames": [(-8, 70, 174, 130, "Group A"), (-8, 208, 174, 130, "Group B")],
        "slots": [
            _row(0, 92, "Seed 1", "3–0", True), _row(0, 118, "Seed 4", "2–1", True), _row(0, 144, "Seed 5", "1–2"), _row(0, 170, "Seed 8", "0–3"),
            _row(0, 230, "Seed 2", "3–0", True), _row(0, 256, "Seed 3", "2–1", True), _row(0, 282, "Seed 6", "1–2"), _row(0, 308, "Seed 7", "0–3"),
            _s(200, 118, "Seed 1", win=True), _s(200, 146, "Seed 3"), _s(200, 246, "Seed 2", win=True), _s(200, 274, "Seed 4"),
            _s(400, 182, "Seed 1", win=True), _s(400, 210, "Seed 2"),
        ],
        "links": [(0, 8, 1, {"lane": 188}), (5, 9, 0, {"lane": 196}), (4, 10, 0, {"lane": 180}), (1, 11, 0, {"lane": 172}), (8, 12, 1), (10, 13, 0), (12, "c", 1)],
        "champ": {"x": 600, "y": 160, "w": 172, "title": "Champion", "who": "Seed 1", "line": "The top two of each group reach the playoffs."},
    },
    {
        "name": "Cashout lobbies",
        "labels": [(0, 52, "Round 1"), (240, 52, "Round 2")],
        "frames": [(-8, 70, 174, 130, "Lobby A"), (-8, 208, 174, 130, "Lobby B"), (232, 138, 174, 130, "Lobby C"), (432, 148, 174, 84, "Final round")],
        "slots": [
            _row(0, 92, "Seed 1", "$46,200", True), _row(0, 118, "Seed 6", "$38,900", True), _row(0, 144, "Seed 4", "$21,300"), _row(0, 170, "Seed 7", "$12,050"),
            _row(0, 230, "Seed 2", "$51,700", True), _row(0, 256, "Seed 3", "$44,100", True), _row(0, 282, "Seed 5", "$30,400"), _row(0, 308, "Seed 8", "$9,750"),
            _row(240, 160, "Seed 2", "$62,400", True), _row(240, 186, "Seed 1", "$57,800", True), _row(240, 212, "Seed 3", "$40,100"), _row(240, 238, "Seed 6", "$22,600"),
            _s(440, 170, "Seed 2", win=True), _s(440, 198, "Seed 1"),
        ],
        "links": [((0, 1), 9, 0, {"from": (166, 116), "to": (232, 182)}), ((4, 5), 10, 1, {"from": (166, 254), "to": (232, 226)}),
                  ((8, 9), 12, 1, {"from": (406, 184), "to": (432, 197)}), (12, "c", 1)],
        "champ": {"x": 628, "y": 145, "w": 160, "title": "Champion", "who": "Seed 2", "line": "The top two of each lobby advance. The last two settle it 1v1."},
    },
]

SOFT = "#cacae2"
T_SPEED = 0.3      # px per ms: the light along lines and across boxes
T_MORPH = 850      # ms for a piece to reach its new place
T_WAVE = 0.55      # ms of delay per px from the left: everything moves as one wave
T_EASE = ".65 0 .35 1"
T_LIN = "0 0 1 1"


class _Track:
    """One animated value over the simulated time. Segments: (start, end, to, spline)."""

    def __init__(self, init):
        self.init = init
        self.segs: list[tuple[float, float, object, str]] = []

    def to(self, t, dur, value, spline=T_EASE):
        self.segs.append((t, t + max(dur, .5), value, spline))

    def set(self, t, value):
        self.segs.append((t, t + .5, value, T_LIN))

    def window(self, a, b):
        """Points (time, value, spline into this point) over [a, b], starting from the value at a."""
        segs = sorted(self.segs, key=lambda s: s[0])
        cur, pts = self.init, []
        for t0, t1, v, sp in segs:
            if t1 <= a:
                cur = v
                continue
            if t0 >= b:
                break
            if not pts:
                pts.append((a, cur, T_LIN))
            pts.append((max(t0, a), cur, T_LIN))
            pts.append((min(t1, b), v, sp))
            cur = v
        if not pts:
            pts.append((a, cur, T_LIN))
        pts.append((b, cur, T_LIN))
        return pts


def _fmt(v):
    if isinstance(v, tuple):
        return " ".join(f"{x:.2f}".rstrip("0").rstrip(".") for x in v)
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(v)


def _smil(track, a, T, attr, kind="animate", extra=""):
    pts = track.window(a, a + T)
    # keyTimes must rise strictly
    times, vals, splines, last = [], [], [], -1.0
    for i, (t, v, sp) in enumerate(pts):
        k = (t - a) / T
        if i and k <= last:
            k = min(last + 1e-5, 1.0) if i < len(pts) - 1 else 1.0
            if k <= last:
                continue
        times.append(k); vals.append(_fmt(v)); last = k
        if i:
            splines.append(sp)
    times[0], times[-1] = 0.0, 1.0
    if len(set(vals)) == 1:
        return ""  # never changes
    kt = ";".join(f"{k:.5f}".rstrip("0").rstrip(".") or "0" for k in times)
    if kind == "motion":
        return (f'<animateMotion dur="{T / 1000:.3f}s" repeatCount="indefinite" calcMode="spline" keyPoints="{";".join(vals)}" '
                f'keyTimes="{kt}" keySplines="{";".join(splines)}" {extra}/>')
    tag_ = "animateTransform" if kind != "animate" else "animate"
    typ = f' type="{kind}"' if kind != "animate" else ""
    return (f'<{tag_} attributeName="{attr}"{typ} dur="{T / 1000:.3f}s" repeatCount="indefinite" calcMode="spline" '
            f'values="{";".join(vals)}" keyTimes="{kt}" keySplines="{";".join(splines)}" {extra}/>')


def _link_path(f, link):
    frm, to, _hot, *rest = link
    o = rest[0] if rest else {}
    sl = f["slots"]
    if "from" in o:
        x1, y1 = o["from"]
    elif isinstance(frm, tuple):
        x1 = max(sl[k]["x"] + sl[k]["w"] for k in frm)
        y1 = sum(sl[k]["y"] + sl[k]["h"] / 2 for k in frm) / len(frm)
    else:
        x1, y1 = sl[frm]["x"] + sl[frm]["w"], sl[frm]["y"] + sl[frm]["h"] / 2
    if "to" in o:
        x2, y2 = o["to"]
    elif to == "c":
        x2, y2 = f["champ"]["x"], f["champ"]["y"] + f["champ"]["h"] / 2
    else:
        x2, y2 = sl[to]["x"], sl[to]["y"] + sl[to]["h"] / 2
    mx = o.get("lane", round((x1 + x2) / 2))
    d = f"M{x1:g} {y1:g}H{mx:g}V{y2:g}H{x2:g}"
    return d, x1, abs(mx - x1) + abs(y2 - y1) + abs(x2 - mx)


def _schedule(f):
    """When each match is decided and each line runs, as in the preview: a match (boxes stacked
    tight in one column) is decided once every side has arrived; its winner lights, the light
    crosses the box, and the lines out of the match leave together."""
    sl, n = f["slots"], len(f["slots"])
    group = list(range(n))
    order = sorted(range(n), key=lambda k: (sl[k]["x"], sl[k]["y"]))
    for j in range(1, n):
        a, b = sl[order[j - 1]], sl[order[j]]
        if a["x"] == b["x"] and b["y"] - (a["y"] + a["h"]) <= 4:
            group[order[j]] = group[order[j - 1]]
    members = lambda g: [k for k in range(n) if group[k] == g]
    arrival = [0.0] * n
    done: set[int] = set()
    incoming = lambda k: [i for i, l in enumerate(f["links"]) if l[1] == k]
    decided = lambda g: max(arrival[k] for k in members(g))
    ready = lambda g: all(i in done for k in members(g) for i in incoming(k))

    def leaves(g):
        w = next((k for k in members(g) if sl[k]["win"]), None)
        return decided(g) + (sl[w]["w"] / T_SPEED if w is not None else 0)

    draws, champ_at = [], 0.0
    pending = list(range(len(f["links"])))
    while pending:
        nxt = [i for i in pending if all(ready(group[k]) for k in (f["links"][i][0] if isinstance(f["links"][i][0], tuple) else (f["links"][i][0],)))]
        if not nxt:
            break
        for i in nxt:
            l = f["links"][i]
            srcs = l[0] if isinstance(l[0], tuple) else (l[0],)
            t0 = max(leaves(group[k]) for k in srcs)
            drop = len(l) > 3 and l[3].get("drop")
            if drop:
                dur = 450
            else:
                d, x1, ln = _link_path(f, l)
                dur = ln / T_SPEED
                draws.append({"d": d, "x1": x1, "len": ln, "t0": t0, "dur": dur, "hot": bool(l[2]), "champ": l[1] == "c"})
            if l[1] == "c":
                champ_at = max(champ_at, t0 + dur)
            else:
                arrival[l[1]] = max(arrival[l[1]], t0 + dur)
            done.add(i)
        pending = [i for i in pending if i not in done]
    lit = {k: decided(group[k]) for k in range(n) if sl[k]["win"]}
    return draws, lit, champ_at


def tournaments() -> str:
    """Tournament formats: single and double elimination, round robin, Swiss, groups into
    playoffs and Cashout lobbies, morphing into one another on a loop."""
    W, H, OX, OY = 900, 404, 55, 26
    F = T_FORMATS
    for f in F:
        c = f["champ"]
        c["lines"] = BODY.wrap(c["line"], 12, c["w"] - 32)
        c["h"] = max(104, 72 + 16 * len(c["lines"]))
    start = T_MORPH * .85
    sched = [_schedule(f) for f in F]
    span = [start + s[2] for s in sched]  # each format lasts until its line reaches the champion
    T = sum(span)
    starts = []
    acc = 0.0
    for cyc in range(2):
        for i in range(len(F)):
            starts.append((acc, i))
            acc += span[i]
    wave = lambda x: max(0.0, x) * T_WAVE
    last = F[-1]

    # ---- slots ----
    NS = max(len(f["slots"]) for f in F)
    out_slots = []
    for k in range(NS):
        d0 = last["slots"][k] if k < len(last["slots"]) else None
        vis0 = d0 is not None
        pos = _Track((d0["x"], d0["y"]) if d0 else (0.0, 0.0))
        scl = _Track((1.0, 1.0) if vis0 else (0.0, 0.0))
        wid = _Track(d0["w"] if d0 else 158)
        hei = _Track(d0["h"] if d0 else 26)
        glow = _Track(1.0 if (d0 and d0["win"]) else 0.0)
        clip = _Track(d0["w"] if (d0 and d0["win"]) else 0)
        texts = {i: _Track(1.0 if (i == len(F) - 1 and vis0) else 0.0) for i, f in enumerate(F) if k < len(f["slots"])}
        fills = {i: _Track(TEXT if (i == len(F) - 1 and d0 and d0["win"]) else None) for i in texts}
        cur = dict(d0) if d0 else None
        shown_text = len(F) - 1 if vis0 else None
        lit_now = bool(d0 and d0["win"])
        visible = vis0
        for S, i in starts:
            f = F[i]
            d = f["slots"][k] if k < len(f["slots"]) else None
            cx = cur["x"] if cur else 0
            if lit_now:
                glow.to(S + wave(cx), 120, 0.0, T_LIN)
                clip.set(S + wave(cx) + 130, 0)
                glow.set(S + wave(cx) + 140, 1.0)
                lit_now = False
            if d is None:
                if visible:
                    pos.to(S + wave(cx), 400, (cur["x"] + cur["w"] / 2, cur["y"] + cur["h"] / 2))
                    scl.to(S + wave(cx), 400, (0.0, 0.0))
                    visible = False
                continue
            if not visible:
                pos.set(S, (d["x"] + d["w"] / 2, d["y"] + d["h"] / 2))
                wid.set(S, d["w"]); hei.set(S, d["h"])
                pos.to(S + wave(d["x"]), T_MORPH, (d["x"], d["y"]))
                scl.to(S + wave(d["x"]), T_MORPH, (1.0, 1.0))
                if shown_text is not None:
                    texts[shown_text].set(S, 0.0)
                texts[i].set(S + 1, 1.0)
                visible = True
            else:
                pos.to(S + wave(d["x"]), T_MORPH, (d["x"], d["y"]))
                wid.to(S + wave(d["x"]), T_MORPH, d["w"]); hei.to(S + wave(d["x"]), T_MORPH, d["h"])
                at = S + wave(cx) + 160
                if shown_text is not None and shown_text != i:
                    texts[shown_text].set(at, 0.0)
                texts[i].set(at + 1, 1.0)
            fills[i].set(S, MUTED if not d.get("box") else (FAINT if d.get("out") else SOFT))
            shown_text = i
            cur = dict(d)
            lit = sched[i][1]
            if k in lit:
                t = S + start + lit[k]
                clip.set(t - 1, 0)
                clip.to(t, d["w"] / T_SPEED, d["w"], T_LIN)
                fills[i].set(t, TEXT)
                lit_now = True
        a = T  # keep the second pass
        g = []
        size = _smil(wid, a, T, "width") + _smil(hei, a, T, "height")
        g.append(f'<g transform="translate({_fmt(pos.init)})">{_smil(pos, a, T, "transform", "translate")}'
                 f'<g transform="scale({_fmt(scl.init)})">{_smil(scl, a, T, "transform", "scale")}')
        g.append(f'<rect width="{wid.init}" height="{hei.init}" rx="7" fill="#0f0f28" stroke="#fff" stroke-opacity=".07">{size}</rect>')
        g.append(f'<clipPath id="sc{k}"><rect width="{clip.init}" height="60" x="-2" y="-2">{_smil(clip, a, T, "width")}</rect></clipPath>')
        g.append(f'<rect width="{wid.init}" height="{hei.init}" rx="7" fill="none" stroke="url(#slotGlow)" stroke-width="1.5" '
                 f'clip-path="url(#sc{k})" opacity="{glow.init}">{size}{_smil(glow, a, T, "opacity")}</rect>')
        for i, tr in texts.items():
            d = F[i]["slots"][k]
            base = MUTED if not d.get("box") else (FAINT if d.get("out") else SOFT)
            fl = fills[i]
            if fl.init is None:
                fl.init = base
            if d.get("box"):
                name = text(LABEL, d["name"], 15, 11, 22, "currentColor")
                meta = text(BODY, d["meta"], 10.5, 11, 38, FAINT)
            else:
                cy = d["h"] / 2 + 12.5 * BODY_BOLD.cap / 2
                name = text(BODY_BOLD, d["name"], 12.5, 11, cy, "currentColor")
                meta = text(BODY, d["meta"], 11.5, d["w"] - 11, cy, FAINT, anchor="end") if d["meta"] else ""
            g.append(f'<g opacity="{tr.init}" color="{fl.init}">{_smil(tr, a, T, "opacity")}{_smil(fl, a, T, "color")}{name}{meta}</g>')
        g.append("</g></g>")
        out_slots.append("".join(g))

    # ---- labels (a missing one rests on the nearest label of the format, with its words) ----
    out_labels = []
    for k in range(4):
        def lab(f, from_pos):
            if k < len(f["labels"]):
                return f["labels"][k]
            return min(f["labels"], key=lambda L: math.hypot(L[0] - from_pos[0], L[1] - from_pos[1]))
        init = lab(last, (0, 0))
        pos = _Track((init[0], init[1]))
        words = {}
        cur = init
        for S, i in starts:
            L = lab(F[i], (cur[0], cur[1]))
            pos.to(S + wave(L[0]), T_MORPH, (L[0], L[1]))
            for w_ in {L[2]} | set(words):
                words.setdefault(w_, _Track(1.0 if w_ == init[2] else 0.0))
            for w_, tr in words.items():
                tr.set(S, 1.0 if w_ == L[2] else 0.0)
            cur = L
        g = f'<g transform="translate({_fmt(pos.init)})">{_smil(pos, T, T, "transform", "translate")}'
        for w_, tr in words.items():
            g += f'<g opacity="{tr.init}">{_smil(tr, T, T, "opacity")}{text(BODY_BOLD, w_.upper(), 10.5, 0, 9, FAINT, tracking=0.16)}</g>'
        out_labels.append(g + "</g>")

    # ---- frames (groups and lobbies): shrink to a point and grow from one ----
    out_frames = []
    for k in range(4):
        def fr(f):
            fs = f.get("frames", [])
            return fs[k] if k < len(fs) else None
        d0 = fr(last)
        pos = _Track((d0[0], d0[1]) if d0 else (0.0, 0.0))
        wid, hei = _Track(d0[2] if d0 else 0), _Track(d0[3] if d0 else 0)
        titles: dict[str, _Track] = {}
        cur, gone = d0, d0 is None
        for S, i in starts:
            d = fr(F[i])
            if d is None:
                if not gone:
                    pos.to(S + wave(cur[0]), T_MORPH, (cur[0] + cur[2] / 2, cur[1] + cur[3] / 2))
                    wid.to(S + wave(cur[0]), T_MORPH, 0); hei.to(S + wave(cur[0]), T_MORPH, 0)
                    gone = True
                continue
            if gone:
                pos.set(S, (d[0] + d[2] / 2, d[1] + d[3] / 2)); wid.set(S, 0); hei.set(S, 0)
                gone = False
            pos.to(S + wave(d[0]), T_MORPH, (d[0], d[1]))
            wid.to(S + wave(d[0]), T_MORPH, d[2]); hei.to(S + wave(d[0]), T_MORPH, d[3])
            titles.setdefault(d[4], _Track(1.0 if d0 and d0[4] == d[4] else 0.0))
            for t_, tr in titles.items():
                tr.set(S, 1.0 if t_ == d[4] else 0.0)
            cur = d
        size = _smil(wid, T, T, "width") + _smil(hei, T, T, "height")
        g = (f'<g transform="translate({_fmt(pos.init)})">{_smil(pos, T, T, "transform", "translate")}'
             f'<clipPath id="fc{k}"><rect width="{wid.init}" height="{hei.init}">{size}</rect></clipPath>'
             f'<rect width="{wid.init}" height="{hei.init}" rx="12" fill="#fff" fill-opacity=".015" stroke="#fff" stroke-opacity=".1" stroke-dasharray="3 3">{size}</rect>'
             f'<g clip-path="url(#fc{k})">')
        for t_, tr in titles.items():
            g += f'<g opacity="{tr.init}">{_smil(tr, T, T, "opacity")}{text(BODY_BOLD, t_.upper(), 9.5, 10, 15, FAINT, tracking=0.16)}</g>'
        out_frames.append(g + "</g></g>")

    # ---- lines: drawn like a fuse, and pulled away left to right as the next format arrives ----
    out_links = []
    uid = 0
    line_tracks: dict = {}
    for idx, (S, i) in enumerate(starts):
        if idx >= len(F) * 2:
            break
        nxt = starts[idx + 1][0] if idx + 1 < len(starts) else starts[-1][0] + span[starts[-1][1]]
        for dr in sched[i][0]:
            ln = dr["len"]
            key = (i, dr["d"])
            # one element per line per format; both passes write into the same track
            lt = line_tracks.setdefault(key, {"mask": _Track(0.0 if i == len(F) - 1 else ln), "spark": _Track(1.0 if i == len(F) - 1 else 0.0),
                                                  "sop": _Track(0.0), "dr": dr})
            t0 = S + start + dr["t0"]
            lt["mask"].set(t0 - 1, ln)
            lt["mask"].to(t0, dr["dur"], 0.0, T_LIN)
            lt["mask"].to(nxt + dr["x1"] * T_WAVE, ln / (T_SPEED * 1.6), -ln, T_LIN)
            lt["spark"].set(t0 - 1, 0.0)
            lt["spark"].to(t0, dr["dur"], 1.0, T_LIN)
            lt["sop"].to(t0, dr["dur"] * .08, 1.0, T_LIN)
            lt["sop"].to(t0 + dr["dur"] * .9, dr["dur"] * .1, 0.0, T_LIN)
    for (i, dpath), lt in line_tracks.items():
        uid += 1
        dr = lt["dr"]
        ln = dr["len"]
        stroke = GOLD if dr["champ"] else ("url(#hotLine)" if dr["hot"] else "#fff")
        sop = "" if dr["hot"] or dr["champ"] else ' stroke-opacity=".16"'
        dash = ' stroke-dasharray="5 5"' if dr["hot"] or dr["champ"] else ""
        march = '<animate attributeName="stroke-dashoffset" values="20;0" dur="0.9s" repeatCount="indefinite"/>' if dash else ""
        out_links.append(
            f'<mask id="lm{uid}" maskUnits="userSpaceOnUse" x="-40" y="-40" width="880" height="440">'
            f'<path d="{dpath}" fill="none" stroke="#fff" stroke-width="8" stroke-dasharray="{ln:.1f} {ln:.1f}" stroke-dashoffset="{_fmt(lt["mask"].init)}">'
            f'{_smil(lt["mask"], T, T, "stroke-dashoffset")}</path></mask>'
            f'<path d="{dpath}" mask="url(#lm{uid})" fill="none" stroke="{stroke}"{sop} stroke-width="{1.6 if dash else 1.2}"{dash}>{march}</path>'
        )
        if dr["hot"]:
            col = GOLD if dr["champ"] else PINK
            out_links.append(
                f'<g opacity="0">{_smil(lt["sop"], T, T, "opacity")}<circle r="5" fill="{col}" opacity=".35" filter="url(#spark)"/><circle r="2.2" fill="#fff"/>'
                f'{_smil(lt["spark"], T, T, "", "motion", f"path=\"{dpath}\"")}</g>')

    # ---- champion card ----
    c0 = last["champ"]
    pos = _Track((c0["x"], c0["y"]))
    cw, chh = _Track(c0["w"]), _Track(c0["h"])
    lit = _Track(1.0)
    words = {i: _Track(1.0 if i == len(F) - 1 else 0.0) for i in range(len(F))}
    cur = c0
    for S, i in starts:
        c = F[i]["champ"]
        lit.to(S + wave(cur["x"]), 350, 0.0, T_LIN)
        pos.to(S + wave(c["x"]), T_MORPH, (c["x"], c["y"]))
        cw.to(S + wave(c["x"]), T_MORPH, c["w"]); chh.to(S + wave(c["x"]), T_MORPH, c["h"])
        for j, tr in words.items():
            tr.set(S, 1.0 if j == i else 0.0)
        lit.to(S + start + sched[i][2], 350, 1.0, T_LIN)
        cur = c
    csize = _smil(cw, T, T, "width") + _smil(chh, T, T, "height")
    champ = (f'<g transform="translate({_fmt(pos.init)})">{_smil(pos, T, T, "transform", "translate")}'
             f'<rect width="{c0["w"]}" height="{c0["h"]}" rx="14" fill="{GOLD}" fill-opacity=".4" opacity="1" filter="url(#halo)">{csize}{_smil(lit, T, T, "opacity")}</rect>'
             f'<rect width="{c0["w"]}" height="{c0["h"]}" rx="14" fill="#0d0d22" stroke="{GOLD}" stroke-opacity=".35">{csize}</rect>'
             f'<rect width="{c0["w"]}" height="{c0["h"]}" rx="14" fill="none" stroke="{GOLD}" stroke-opacity=".85" opacity="1">{csize}{_smil(lit, T, T, "opacity")}</rect>'
             f'<rect x="14" y="-1" width="44" height="2" rx="1" fill="{GOLD}"/>'
             + para(16, 16, 13, 22, 4, fill=GOLD))
    for i, tr in words.items():
        c = F[i]["champ"]
        champ += (f'<g opacity="{tr.init}">{_smil(tr, T, T, "opacity")}'
                  + text(LABEL, c["title"].upper(), 11, 40, 31, GOLD, tracking=0.16)
                  + text(BODY_BOLD, c["who"], 13, 16, 58, TEXT)
                  + "".join(text(BODY, ln_, 12, 16, 76 + j * 16, MUTED) for j, ln_ in enumerate(c["lines"]))
                  + "</g>")
    champ += "</g>"

    # ---- the format name: the old one lifts away, the new one's letters roll in from the right ----
    name_g = ""
    nx = 790  # right edge, stage coordinates
    for i, f in enumerate(F):
        letters, pen = [], 0.0
        for ch in f["name"]:
            gid, adv = LABEL.glyph(ch, 17)
            letters.append((ch, gid, pen))
            pen += adv
        x0, n, chars = nx - pen, len(letters), ""
        for m, (ch, gid, px) in enumerate(letters):
            if ch == " ":
                continue
            tr = _Track((0.0, 0.0) if i == len(F) - 1 else (0.0, 24.0))
            for S, j in starts:
                if j == i:
                    tr.set(S, (0.0, 24.0))
                    tr.to(S + 200 + (n - 1 - m) * 14, 420, (0.0, 0.0), ".2 .8 .3 1")
                if (j - 1) % len(F) == i:
                    tr.to(S, 260, (0.0, -24.0), ".55 0 .75 .3")
            chars += f'<g transform="translate({_fmt(tr.init)})">{_smil(tr, T, T, "transform", "translate")}<use href="#{gid}" x="{x0 + px:.1f}" y="31"/></g>'
        name_g += f'<g fill="{TEXT}">{chars}</g>'
    name_box = (f'<clipPath id="nameClip"><rect x="440" y="14" width="352" height="22"/></clipPath>'
                + text(BODY_BOLD, "FORMAT", 10, 790, 9, FAINT, anchor="end", tracking=0.18)
                + f'<g clip-path="url(#nameClip)">{name_g}</g>')

    # ---- stage chips ----
    chips, x = "", 0
    for label, color in [("REGISTRATION", CYAN), ("CHECK-IN", VIOLET), ("LIVE", GREEN), ("COMPLETED", GOLD)]:
        part, tw = tag(x, 0, label, color, h=26, dot=(label == "LIVE"), size=10.5)
        chips += part
        x += tw + 26
        if label != "COMPLETED":
            chips += f'<polyline points="{x - 20},13 {x - 12},13 {x - 16},9 {x - 12},13 {x - 16},17" fill="none" stroke="{FAINT}" stroke-width="1.5" stroke-linecap="round"/>'

    defs = (
        f'<linearGradient id="slotGlow" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<linearGradient id="hotLine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="790" y2="0"><stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
        '<filter id="spark" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3"/></filter>'
        '<filter id="halo" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="10"/></filter>'
    )
    stage = (f'<g transform="translate({OX} {OY})">' + chips + name_box + "".join(out_frames) + "".join(out_labels)
             + "".join(out_links) + "".join(out_slots) + champ + "</g>")
    body = panel(W, H, INK_925) + card(1, 1, W - 2, H - 2, 24, "none") + stage
    return svg(W, H, "Tournaments", "Tournament formats on PUGZ: single elimination, double elimination, round robin, Swiss, groups into playoffs and Cashout lobbies. The card morphs from one format to the next; in each, winners light up match by match and the line runs on to the champion.", body, defs, PULSE_CSS)


# The league (docs/plans/2026-11-02-league-format.md): divisions, prizes and rank limits as announced.
DIVISIONS = [
    ("DIVISION 1", "Open to every rank", 4),
    ("DIVISION 2", "No Ruby", 3),
    ("DIVISION 3", "Diamond 4 at most", 2),
    ("DIVISION 4", "Platinum 1 at most", 1),
]


def league() -> str:
    """A league season: the calendar along the top, four divisions of eight with promotion and relegation."""
    w, h = 900, 428
    # Season stepper: one highlight walks through the season.
    stages = [("SIGN-UPS", CYAN), ("PLACEMENT", VIOLET), ("WEEKS 1–7", BLUE), ("SEMI-FINALS", PINK), ("FINALS NIGHT", GOLD)]
    x, stepper, overlays = 48, "", ""
    for i, (label, color) in enumerate(stages):
        base, tw = tag(x, 26, label, color, h=26, size=10.5)
        stepper += base
        overlays += f'<g class="stage stage{i}">{para(x - 2, 24, tw + 4, 30, 6, fill=color, fill_opacity=".28", stroke=color, stroke_width="1.5")}</g>'
        x += tw + 26
        if i < len(stages) - 1:
            stepper += f'<polyline points="{x - 20},{39} {x - 12},{39} {x - 16},{35} {x - 12},{39} {x - 16},{43}" fill="none" stroke="{FAINT}" stroke-width="1.5" stroke-linecap="round"/>'
    # Divisions: eight teams each, finalists move up, the bottom two move down.
    rx, rw, top, rh, gap = 128, 724, 84, 62, 14
    slot_w, slot_h, slot_gap, slot_x0 = 40, 24, 8, 328
    rows, marks = "", ""
    centres = []
    for d, (name, limit, prize) in enumerate(DIVISIONS):
        y = top + d * (rh + gap)
        centres.append(y + rh / 2)
        rows += (
            f'<rect x="{rx}" y="{y}" width="{rw}" height="{rh}" rx="14" fill="{INK_900}" stroke="#fff" stroke-opacity=".08"/>'
            f'<rect x="{rx + 14}" y="{y + 1}" width="48" height="2" fill="url(#brand)"/>'
            + text(LABEL, name, 11, rx + 20, y + 27, TEXT, tracking=0.16)
            + text(BODY, limit, 12.5, rx + 20, y + 46, MUTED)
            + text(LABEL, "PRIZE", 9.5, rx + rw - 20, y + 25, FAINT, tracking=0.16, anchor="end")
            + text(DISPLAY, "€€€€", 19, rx + rw - 20, y + 48, "#fff", tracking=0.12, anchor="end", extra='fill-opacity=".12"')
            + "".join(text(DISPLAY, "€", 19, rx + rw - 20 - DISPLAY.width("€€€€", 19, 0.12) + k * (DISPLAY.width("€", 19) + 0.12 * 19), y + 48, GOLD) for k in range(prize))
        )
        for s in range(8):
            sx, sy = slot_x0 + s * (slot_w + slot_gap), y + (rh - slot_h) / 2
            if s == 0:
                color = GOLD  # the champion, who also moves up (except from Division 1)
            elif s == 1 and d > 0:
                color = GREEN  # the other finalist
            elif s > 5 and d < len(DIVISIONS) - 1:
                color = RED
            else:
                color = None
            if color:
                rows += para(sx, sy, slot_w, slot_h, 6, fill=color, fill_opacity=".14", stroke=color, stroke_opacity=".55")
                marks += f'<g class="hl">{para(sx, sy, slot_w, slot_h, 6, fill=color, fill_opacity=".35", stroke=color, stroke_width="1.5")}</g>'
            else:
                rows += para(sx, sy, slot_w, slot_h, 6, fill="#fff", fill_opacity=".04", stroke="#fff", stroke_opacity=".12")
    # Movement between divisions, in the left gutter: up (green) and down (red), dashes run with the arrow.
    moves = ""
    for d in range(len(DIVISIONS) - 1):
        upper, lower = centres[d], centres[d + 1]
        ux, dx = 72, 100
        moves += (
            f'<path d="M{ux} {lower - 4}V{upper + 12}" fill="none" stroke="{GREEN}" stroke-width="2" stroke-dasharray="6 5" class="move"/>'
            f'<polygon points="{ux - 6},{upper + 14} {ux + 6},{upper + 14} {ux},{upper + 4}" fill="{GREEN}"/>'
            f'<path d="M{dx} {upper + 4}V{lower - 12}" fill="none" stroke="{RED}" stroke-width="2" stroke-dasharray="6 5" class="move"/>'
            f'<polygon points="{dx - 6},{lower - 14} {dx + 6},{lower - 14} {dx},{lower - 4}" fill="{RED}"/>'
        )
    # Legend.
    items = [(GOLD, "The champion wins the prize"), (GREEN, "Both finalists move up"), (RED, "Bottom teams move down")]
    lx, legend = 128, ""
    for color, label in items:
        legend += para(lx, 392, 22, 14, 4, fill=color, fill_opacity=".3", stroke=color) + text(BODY, label, 12.5, lx + 30, 404, MUTED)
        lx += 30 + BODY.width(label, 12.5) + 28
    body = panel(w, h, INK_925) + stepper + overlays + rows + marks + moves + legend
    style = (
        cycle_css("stage", len(stages), 10)
        + ".hl{animation:hl 2.6s ease-in-out infinite}@keyframes hl{50%{opacity:.2}}"
        + ".move{animation:move 1.2s linear infinite}@keyframes move{to{stroke-dashoffset:-11}}"
    )
    desc = (
        "A league season runs from sign-ups and a placement weekend through seven weeks of matches to the semi-finals "
        "and Finals Night. Four divisions of eight teams: "
        + "; ".join(f"{n.title()}, {l.lower()}" for n, l, _ in DIVISIONS)
        + ". Every division has a cash prize, highest in Division 1"
        + ". The two finalists of each division move up, the bottom teams move down."
    )
    return svg(w, h, "The PUGZ League", desc, body, "", style)


# Tiered queues: in progress, so only the idea is shown (no thresholds or numbers yet).
# Every change is one player joining or leaving; only a pop clears the queue at once.
QUEUE_TIERS = [  # tier, colour, how the count moves over one loop: (players, from %, to %)
    ("S", "#ff4d7d", [(1, 0, 20), (2, 20, 26), (3, 26, 48), (2, 48, 70), (1, 70, 100)]),  # two quick joins, two leave
    ("A", CYAN, [(3, 0, 12), (4, 12, 30), (5, 30, 50), (4, 50, 64), (3, 64, 100)]),
    ("B", "#d6e0ff", [(5, 0, 24), (6, 24, 34), (0, 34, 50), (1, 50, 54), (2, 54, 58), (3, 58, 70), (4, 70, 84), (5, 84, 100)]),  # pops, then quick joins
]
QUEUE_LOOP = 14  # seconds


def window_css(name: str, start: int, end: int) -> str:
    """Keyframes that show an element only between `start`% and `end`% of the loop."""
    show = f"{start}%{{opacity:1}}" if start else "0%{opacity:1}"
    before = f"0%,{start - 1}%{{opacity:0}}" if start else ""
    after = f"{end - 1}%{{opacity:1}}{end}%,100%{{opacity:0}}" if end < 100 else "100%{opacity:1}"
    return f".{name}{{animation:{name} {QUEUE_LOOP}s linear infinite}}@keyframes {name}{{{before}{show}{after}}}"


def queues() -> str:
    """The queue panel, by tier: three 3v3 queues filling up. Still in progress, so only the idea is shown."""
    w, h = 900, 352
    out = (
        text(HEADING, "Queue in your tier.", 22, 48, 54, TEXT)
        + text(BODY, "Press Join and you are put in your tier's queue. Cross the next tier's line and you move up at once.", 14, 48, 78, MUTED)
    )
    # The panel: a Discord message with the violet accent bar down its left edge.
    px, py, pw_, ph = 48, 104, 804, 200
    out += (
        f'<rect x="{px}" y="{py}" width="{pw_}" height="{ph}" rx="12" fill="{INK_900}" stroke="#fff" stroke-opacity=".08"/>'
        f'<rect x="{px}" y="{py}" width="5" height="{ph}" rx="2.5" fill="{VIOLET}"/>'
        + text(HEADING, "3v3 · Final Round", 16, px + 28, py + 36, TEXT)
        + text(BODY, "balanced by PUG rating", 12.5, px + 28 + HEADING.width("3v3 · Final Round", 16) + 10, py + 36, FAINT)
    )
    slot_w, slot_h, slot_gap = 34, 26, 6
    states_css = ""
    for r, (letter, color, states) in enumerate(QUEUE_TIERS):
        y = py + 58 + r * 44
        out += para(px + 28, y, 40, slot_h, 6, fill=color, fill_opacity=".12", stroke=color, stroke_width="1.5")
        out += text(LABEL, letter, 13, px + 48, y + 18, color, anchor="middle")
        sx0 = px + 84
        cx = sx0 + 6 * (slot_w + slot_gap) + 10
        base = min(p for p, _, _ in states)  # always in the queue during the loop
        for s in range(6):
            sx = sx0 + s * (slot_w + slot_gap)
            if s < base:
                out += para(sx, y, slot_w, slot_h, 8, fill=SLOT_COLORS[s])
            else:
                out += para(sx, y, slot_w, slot_h, 8, fill="#fff", fill_opacity=".03", stroke="#fff", stroke_opacity=".16")
        # Each state: the players above the base, the count and a note. The first state is the resting one.
        for k, (players, start, end) in enumerate(states):
            name = f"q{r}s{k}"
            group = "".join(para(sx0 + s * (slot_w + slot_gap), y, slot_w, slot_h, 8, fill=SLOT_COLORS[s]) for s in range(base, players))
            group += text(BODY_BOLD, f"{players}/6", 15, cx, y + 19, TEXT)
            if players == 5:  # one player short: the last slot blinks
                group += f'<g class="join">{para(sx0 + 5 * (slot_w + slot_gap), y, slot_w, slot_h, 8, fill=SLOT_COLORS[5])}</g>'
                group += text(BODY, "· 1 more to pop", 14, cx + 40, y + 19, PINK)
            elif players == 6:
                group += text(BODY, "· popped, lobby open", 14, cx + 40, y + 19, GREEN)
            hidden = ' opacity="0"' if k else ""
            out += f'<g class="{name}"{hidden}>{group}</g>'
            states_css += window_css(name, start, end)
    # Join button, in the brand style, on the right of the panel.
    out += (
        f'<rect x="{px + pw_ - 196}" y="{py + 76}" width="168" height="44" rx="10" fill="url(#button)"/>'
        + para(px + pw_ - 172, py + 89, 8, 18, 4, fill=INK_TEXT) + para(px + pw_ - 161, py + 89, 8, 18, 4, fill=INK_TEXT)
        + text(LABEL, "Join 3v3", 15, px + pw_ - 145, py + 104, INK_TEXT)
        + text(BODY, "Your tier is on /stats", 12.5, px + pw_ - 112, py + 144, FAINT, anchor="middle")
    )
    out += text(BODY, "Each tier races for its own leaderboard spot and its own prizes.", 13, w / 2, 334, MUTED, anchor="middle")
    body = panel(w, h, INK_925) + card(1, 1, w - 2, h - 2, 24, "none") + out
    style = ".join{animation:join 2.2s ease-in-out infinite}@keyframes join{0%,100%{opacity:0}50%{opacity:.85}}" + states_css + PULSE_CSS
    return svg(w, h, "Tiered queues", "A 3v3 queue for each tier, S, A and B, with players joining and leaving like on the queue panel in Discord. Press Join and you are put in your tier's queue; cross the next tier's line and you move up at once. Each tier gets its own leaderboard race and its own prizes.", body, "", style)


def servers() -> str:
    """PUGZ on other servers: community servers feed one PUGZ, which feeds a shared leaderboard."""
    w, h = 900, 344
    # Left: community servers, each with its own queue.
    names = [("Your server", CYAN, 4), ("Community", VIOLET, 2), ("Organiser", PINK, 5)]
    lx, lw, ch = 48, 236, 72
    hub_x, hub_y = 452, 158
    out, paths = "", ""
    for i, (name, color, filled) in enumerate(names):
        y = 34 + i * 88
        out += card(lx, y, lw, ch)
        out += (f'<rect x="{lx + 16}" y="{y + 16}" width="40" height="40" rx="12" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-opacity=".6"/>'
                + text(DISPLAY, name[0], 18, lx + 36, y + 43, color, anchor="middle"))
        out += text(HEADING, name, 15, lx + 70, y + 31, TEXT)
        for s in range(6):
            sx = lx + 70 + s * 17
            if s < filled:
                out += para(sx, y + 41, 13, 14, 4, fill=SLOT_COLORS[s])
            else:
                out += para(sx, y + 41, 13, 14, 4, fill="#fff", fill_opacity=".04", stroke="#fff", stroke_opacity=".16")
        out += text(BODY_BOLD, f"{filled}/6", 11.5, lx + 178, y + 52, MUTED)
        sy = y + ch / 2
        d = f"M{lx + lw} {sy:.1f}C{lx + lw + 70} {sy:.1f} {hub_x - 110} {hub_y:.1f} {hub_x - 52} {hub_y:.1f}"
        paths += (f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity=".35" stroke-width="2"/>'
                  f'<path class="pk" style="animation-delay:-{i * 0.45:.2f}s" d="{d}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="3" stroke-linecap="round" stroke-dasharray="0.1 22"/>')
    # Centre: PUGZ.
    hub = (
        f'<circle cx="{hub_x}" cy="{hub_y}" r="70" fill="{VIOLET}" opacity=".35" filter="url(#glow-lg)"/>'
        f'<circle class="ring" cx="{hub_x}" cy="{hub_y}" r="52" fill="none" stroke="url(#brand)" stroke-width="2"/>'
        f'<circle cx="{hub_x}" cy="{hub_y}" r="50" fill="{INK_900}"/>'
        + mark(hub_x - 29, hub_y - 54 * MARK_VIEW[3] / MARK_VIEW[2] / 2, 54)
        + text(LABEL, "PUGZ", 12, hub_x, hub_y + 78, TEXT, tracking=0.2, anchor="middle")
        + text(BODY, "One profile · one rating", 12, hub_x, hub_y + 96, MUTED, anchor="middle")
    )
    # Right: the shared leaderboard across servers.
    rx, rw, ry, rh = 616, 236, 34, 248
    d = f"M{hub_x + 52} {hub_y}H{rx}"
    paths += (f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity=".25" stroke-width="2"/>'
              f'<path class="pk" d="{d}" fill="none" stroke="#fff" stroke-opacity=".9" stroke-width="3" stroke-linecap="round" stroke-dasharray="0.1 22"/>')
    board = card(rx, ry, rw, rh) + text(LABEL, "SHARED LEADERBOARD", 10.5, rx + 20, ry + 32, MUTED, tracking=0.16)
    rows = [("Your server", CYAN, .92), ("Organiser", PINK, .74), ("Community", VIOLET, .58), ("PUGZ", BLUE, .44)]
    for k, (name, color, share) in enumerate(rows):
        y = ry + 62 + k * 44
        board += (text(MONO, f"{k + 1:02d}", 12, rx + 20, y + 4, FAINT)
                  + text(BODY_BOLD, name, 13, rx + 50, y + 4, TEXT)
                  + f'<rect x="{rx + 50}" y="{y + 12}" width="{rw - 70}" height="6" rx="3" fill="#fff" fill-opacity=".06"/>'
                  + f'<rect class="bar bar{k}" x="{rx + 50}" y="{y + 12}" width="{(rw - 70) * share:.1f}" height="6" rx="3" fill="{color}"/>')
    planned, tw = tag(0, 0, "PLANNED · AFTER LAUNCH", AMBER, dot=True)
    planned, _ = tag(hub_x - tw / 2, 28, "PLANNED · AFTER LAUNCH", AMBER, dot=True)
    caption = text(BODY, "PUGs in your own server: your community and your staff, with one profile and one shared leaderboard.", 13, w / 2, 324, MUTED, anchor="middle")
    body = panel(w, h, INK_925) + card(1, 1, w - 2, h - 2, 24, "none") + paths + out + hub + board + planned + caption
    style = (
        PULSE_CSS
        + ".pk{animation:pk 1.6s linear infinite}@keyframes pk{to{stroke-dashoffset:-22.1}}"
        ".ring{animation:ring 3s ease-in-out infinite}@keyframes ring{50%{opacity:.35}}"
        ".bar{transform-box:fill-box;transform-origin:left;animation:bar 6s ease-in-out infinite}"
        ".bar1{animation-delay:-1.5s}.bar2{animation-delay:-3s}.bar3{animation-delay:-4.5s}"
        "@keyframes bar{50%{transform:scaleX(.86)}}"
        "@media (prefers-reduced-motion:reduce){.pk{display:none}}"
    )
    return svg(w, h, "PUGs on your server", "Planned, after the public launch: community servers run their own PUGZ queues and matches. Every server feeds one PUGZ, so players keep one profile and one rating, and servers compete on a shared leaderboard.", body, BLUR_FILTERS, style)


def coaching() -> str:
    w, h = 900, 372
    # Left: a coach card.
    lx, ly, lw, lh = 40, 36, 400, 236
    left = card(lx, ly, lw, lh)
    avatar = (
        f'<circle cx="{lx + 54}" cy="{ly + 58}" r="29" fill="none" stroke="url(#brand)" stroke-width="3"/>'
        f'<circle cx="{lx + 54}" cy="{ly + 58}" r="26" fill="{INK_850}"/>'
        + mark(lx + 38, ly + 46, 32)
    )
    verified, _ = tag(lx + 100, ly + 62, "VERIFIED", CYAN, h=20, size=9.5)
    star_row = "".join(
        f'<g class="star star{i}"><polygon points="{star(lx + 112 + i * 22, ly + 122, 9)}" fill="{GOLD}"/></g>'
        f'<polygon points="{star(lx + 112 + i * 22, ly + 122, 9)}" fill="none" stroke="{GOLD}" stroke-opacity=".5" stroke-width="1.2"/>'
        for i in range(5)
    )
    chips, cx, cy_ = "", lx + 24, ly + 152
    for label in ["Light", "Medium", "Heavy", "Aim", "Game sense", "Team play", "VOD review"]:
        cw_ = BODY_BOLD.width(label, 11.5) + 22
        if cx + cw_ > lx + lw - 20:
            cx, cy_ = lx + 24, cy_ + 30
        chips += (
            f'<rect x="{cx}" y="{cy_}" width="{cw_}" height="24" rx="12" fill="#fff" fill-opacity=".05" stroke="#fff" stroke-opacity=".12"/>'
            + text(BODY_BOLD, label, 11.5, cx + 11, cy_ + 16, TEXT)
        )
        cx += cw_ + 8
    left += (
        avatar
        + text(HEADING, "Verified coach", 19, lx + 100, ly + 52, TEXT)
        + verified
        + text(BODY, "Reviews", 12, lx + 24, ly + 126, MUTED)
        + star_row
        + text(BODY, "Only after a finished session.", 11.5, lx + 230, ly + 126, FAINT)
        + chips
    )
    # Right: availability, the next free slot pulses.
    rx, ry, rw, rh = 470, 36, 390, 236
    right = card(rx, ry, rw, rh) + text(LABEL, "NEXT AVAILABLE", 11, rx + 24, ry + 38, MUTED, tracking=0.14)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    taken = {(0, 1), (0, 4), (1, 0), (1, 2), (2, 3), (3, 1), (3, 5), (4, 4), (2, 6), (0, 2), (1, 6)}
    times = ["10:00", "14:00", "18:00", "21:00"]
    gx0, gy0, cellw, cellh, gapx, gapy = rx + 78, ry + 58, 34, 28, 6, 8
    for j, day in enumerate(days):
        right += text(LABEL, day, 9, gx0 + j * (cellw + gapx) + cellw / 2, gy0 - 6, FAINT, tracking=0.1, anchor="middle")
    for r, t in enumerate(times):
        right += text(MONO, t, 11, rx + 24, gy0 + r * (cellh + gapy) + cellh / 2 + 4, FAINT)
        for j in range(7):
            x, y = gx0 + j * (cellw + gapx), gy0 + r * (cellh + gapy)
            if (r, j) in taken:
                right += f'<rect x="{x}" y="{y}" width="{cellw}" height="{cellh}" rx="7" fill="#fff" fill-opacity=".03"/>'
            else:
                right += f'<rect x="{x}" y="{y}" width="{cellw}" height="{cellh}" rx="7" fill="{VIOLET_600}" fill-opacity=".22" stroke="{VIOLET}" stroke-opacity=".5"/>'
    nx, ny = gx0 + 2 * (cellw + gapx), gy0 + 0 * (cellh + gapy)
    right += (
        f'<g class="slot"><rect x="{nx - 2}" y="{ny - 2}" width="{cellw + 4}" height="{cellh + 4}" rx="9" fill="{CYAN}" fill-opacity=".25" stroke="{CYAN}" stroke-width="1.5"/></g>'
        + text(LABEL, "FREE", 9, nx + cellw / 2, ny + cellh / 2 + 3.2, CYAN, tracking=0.1, anchor="middle")
    )
    # Bottom: the booking journey.
    steps = ["REQUESTED", "CONFIRMED", "PAID", "COMPLETED", "REVIEWED"]
    sx, stepper, overlays = 40, "", ""
    total = sum(LABEL.width(s_, 10, 0.16) + 28 for s_ in steps) + 18 * (len(steps) - 1)
    sx = (w - total) / 2
    for i, label in enumerate(steps):
        base, tw = tag(sx, 304, label, VIOLET if i < 4 else GOLD, h=26, size=10)
        stepper += base
        overlays += f'<g class="stage stage{i}">{para(sx - 2, 302, tw + 4, 30, 6, fill=CYAN, fill_opacity=".25", stroke=CYAN, stroke_width="1.5")}</g>'
        sx += tw + 18
        if i < len(steps) - 1:
            stepper += f'<polyline points="{sx - 13},{317} {sx - 7},{317} {sx - 10},{314} {sx - 7},{317} {sx - 10},{320}" fill="none" stroke="{FAINT}" stroke-width="1.4" stroke-linecap="round"/>'
    caption = text(BODY, "Pay securely on the site. Card details never touch our servers.", 13, w / 2, 352, MUTED, anchor="middle")
    body = panel(w, h, INK_925) + left + right + stepper + overlays + caption
    style = (
        cycle_css("stage", len(steps), 10)
        + ".star{animation:star 5s ease-in-out infinite backwards}"
        + "".join(f".star{i}{{animation-delay:{i * 0.25:.2f}s}}" for i in range(5))
        + "@keyframes star{0%{opacity:0}12%{opacity:1}80%{opacity:1}95%,100%{opacity:0}}"
        + ".slot{animation:slot 2.4s ease-in-out infinite}@keyframes slot{50%{opacity:.35}}"
    )
    return svg(w, h, "Coaching", "A verified coach with specialties and reviews, a calendar showing the next free slot, and a booking that moves from requested to confirmed, paid, completed and reviewed.", body, "", style)


def cta() -> str:
    w, h = 900, 250
    headline = "Join the PUGZ Discord."
    size = DISPLAY.fit(headline, 31, w - 96, -0.02)
    shafts = "".join(
        f'<g class="shaft s{i}">{para(x, -20, sw, h + 40, 70, fill="url(#shaftFill)", opacity=op)}</g>'
        for i, (x, sw, op) in enumerate([(120, 26, ".5"), (230, 70, ".3"), (640, 18, ".6"), (720, 90, ".28")], 1)
    )
    body = (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="28"/></clipPath>'
        f'<rect width="{w}" height="{h}" rx="28" fill="{INK_900}"/>'
        '<g clip-path="url(#card)">'
        f'<circle cx="160" cy="250" r="190" fill="{VIOLET}" opacity=".38" filter="url(#glow-lg)"/>'
        f'<circle cx="760" cy="10" r="190" fill="{CYAN}" opacity=".2" filter="url(#glow-lg)"/>'
        f'<circle cx="860" cy="250" r="150" fill="{PINK}" opacity=".18" filter="url(#glow-lg)"/>'
        f"{shafts}</g>"
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="27" fill="none" stroke="url(#brand)" stroke-opacity=".55" stroke-width="1.5"/>'
        + text(LABEL, "JOIN THE COMMUNITY", 11, w / 2, 56, CYAN, tracking=0.18, anchor="middle")
        + text(DISPLAY, headline, size, w / 2, 108, TEXT, tracking=-0.02, anchor="middle")
        + text(BODY, "For launch updates, community discussions and access when public queues open.", 15, w / 2, 144, MUTED, anchor="middle")
        + button((w - 210) / 2, 168, "Join the Discord", w=210, h=48)
    )
    defs = (
        BLUR_FILTERS
        + '<linearGradient id="shaftFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{VIOLET}" stop-opacity="0"/><stop offset=".5" stop-color="{VIOLET}" stop-opacity=".5"/>'
        f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
    )
    style = (
        ".shaft{animation:drift 14s ease-in-out infinite alternate}.s2{animation-duration:18s;animation-delay:-4s}"
        ".s3{animation-duration:12s;animation-delay:-8s}.s4{animation-duration:21s;animation-delay:-6s}"
        "@keyframes drift{from{transform:translateX(-24px)}to{transform:translateX(28px)}}"
    )
    return svg(w, h, "Join the Discord", "Join the PUGZ Discord for launch updates, community discussions and access when public queues open.", body, defs, style)


def profit() -> str:
    """Where every euro goes: in, hosting, prize pools, and nothing kept.

    Drawn and timed like the approved design preview. One 7-second loop in plain CSS: a flat
    gold coin is minted at IN and eases (slow, fast, slow) to each stop; every arrival sends rings
    out from behind the circle. Hosting takes its share (the coin shrinks a touch), the prize pool
    spends the rest (a gold pulse, the circle and its label turn gold and the coin dissolves), and
    only wind travels on to the €0 of profit, which dims to a dusty pink as the air arrives.
    """
    w, h = 900, 262
    pad = 28
    col = (w - 2 * pad - 3 * 8) / 4
    xs = [round(pad + col / 2 + i * (col + 8), 1) for i in range(4)]
    ty = 167          # the rail and the circles' centres
    R = 23            # circle radius (46 px, as on the site)
    steps = [
        ("IN", "Donations and fees", "everything that comes in", CYAN),
        ("FIRST", "Hosting", "servers, database, backups", BLUE),
        ("THEN", "Prize pools", "seasons and tournaments", VIOLET),
        ("ALWAYS", "Profit", "kept by PUGZ", PINK),
    ]
    PANEL = "#09091f"
    ASH = "#c99ccf"  # the dusty pink the profit dims to
    T = 7.0
    ease = "cubic-bezier(.65,0,.35,1)"
    spring = "cubic-bezier(.3,1.3,.5,1)"
    ring_ease = "cubic-bezier(.2,.7,.3,1)"
    # The timeline, in seconds.
    t1s, t1e = .64, 1.79      # IN -> FIRST
    shrink = 2.21             # the coin settles a touch smaller at FIRST
    t2s, t2e = 2.35, 3.50     # FIRST -> THEN
    gone = 3.92               # the coin has dissolved at THEN; the wind leaves
    gold_in, gold_out = 3.95, 4.07 + 1.8
    always = gone + .95       # the air reaches the €0
    dim_s, back_s = gone + .6, gone + 2.42

    def p(t: float) -> str:
        return f"{max(0.0, min(100.0, t / T * 100)):.2f}%"

    css: list[str] = []

    def kf(name: str, frames: list[tuple[float, str]], origin: bool = True) -> None:
        body = "".join(f"{p(t)}{{{v}}}" for t, v in frames)
        if frames[0][0] > 0:
            body = f"0%{{{frames[0][1]}}}" + body
        if frames[-1][0] < T:
            body += f"100%{{{frames[-1][1]}}}"
        box = "transform-box:fill-box;transform-origin:center;" if origin else ""
        css.append(f".{name}{{{box}animation:{name} {T}s linear infinite}}@keyframes {name}{{{body}}}")

    gold_frames = lambda on, off: [(0, off), (t2e, off), (gold_in, on), (gold_out - 1.8, on + f";animation-timing-function:{ease}"), (gold_out, off)]
    dim = lambda on, off: [(0, off), (dim_s, off + f";animation-timing-function:{ease}"), (dim_s + .9, on),
                           (back_s, on + f";animation-timing-function:{ease}"), (back_s + .5, off)]

    # The card, the heading and the rail.
    out = (
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="{PANEL}" stroke="#fff" stroke-opacity=".08"/>'
        f'<rect x="{pad}" y="0" width="40" height="2" rx="1" fill="url(#accent)"/>'
        + text(H2, "Where every euro goes.", 28, pad, 30 + 28 * H2.cap + 4, TEXT)
        + text(LEAD, "Everything that comes in goes back into the community. Nothing is kept.", 15, pad, 80, MUTED)
        + f'<rect x="{xs[0]}" y="{ty - 1}" width="{xs[-1] - xs[0]}" height="2" rx="1" fill="url(#rail)" opacity=".85"/>'
    )

    # Pulses behind each circle: two glowing rings and a soft bloom, plus a small bump of the icon.
    pulses = [(0, 0.0, CYAN, False), (1, t1e, BLUE, False), (2, t2e, GOLD, False), (3, always, PINK, True)]
    for i, t, color, soft in pulses:
        peak = .45 if soft else .85
        x = xs[i]
        out += f'<circle class="bl{i}" cx="{x}" cy="{ty}" r="{R + 6}" fill="url(#bloom{i})" opacity="0"/>'
        for k, (delay, to, op) in enumerate([(0, 2.3, peak), (.16, 1.8, peak * .7)]):
            out += (f'<g class="r{i}{k}" opacity="0"><circle cx="{x}" cy="{ty}" r="{R}" fill="none" stroke="{color}" stroke-width="4" filter="url(#soft)"/>'
                    f'<circle cx="{x}" cy="{ty}" r="{R}" fill="none" stroke="{color}" stroke-width="2"/></g>')
            a = t + delay
            kf(f"r{i}{k}", [(0, "opacity:0;transform:scale(1)"), (a, f"opacity:{op};transform:scale(1);animation-timing-function:{ring_ease}"),
                            (a + .9, f"opacity:0;transform:scale({to})")])
        kf(f"bl{i}", [(0, "opacity:0;transform:scale(.8)"), (t, "opacity:0;transform:scale(.8);animation-timing-function:ease-out"),
                      (t + .24, f"opacity:{.25 if soft else .5};transform:scale(1.25);animation-timing-function:ease-out"),
                      (t + .8, "opacity:0;transform:scale(1.6)")])
        bump = 1.05 if soft else 1.1
        kf(f"ic{i}", [(0, "transform:scale(1)"), (t, f"transform:scale(1);animation-timing-function:{spring}"),
                      (t + .18, f"transform:scale({bump});animation-timing-function:ease-out"), (t + .52, "transform:scale(1)")])

    # The circles: a soft outer glow, the panel fill and a coloured border; labels above, names
    # and lines below.
    node_cls = {2: ("gglo", "gnode", "gtag"), 3: ("pglo", "pnode", "ptag")}
    for i, (x, (label, title, line, color)) in enumerate(zip(xs, steps)):
        glo, nd, tg = node_cls.get(i, ("", "", ""))
        out += (
            f'<circle class="{glo}" cx="{x}" cy="{ty}" r="{R}" fill="none" stroke="{color}" stroke-width="4" opacity=".55" filter="url(#soft)"/>'
            f'<circle class="{nd}" cx="{x}" cy="{ty}" r="{R - .75}" fill="{PANEL}" stroke="{color}" stroke-width="1.5"/>'
            + text(BODY_BOLD, label, 11, x, ty - R - 13, color, anchor="middle", tracking=0.16, extra=f'class="{tg}"' if tg else "")
            + text(BODY_BOLD, title, 15, x, ty + R + 25, TEXT, anchor="middle")
            + text(LEAD, line, 13, x, ty + R + 44, MUTED, anchor="middle")
        )
    kf("gnode", gold_frames(f"fill:#2b252a;stroke:{GOLD}", f"fill:{PANEL};stroke:{VIOLET}"), origin=False)
    kf("gglo", gold_frames(f"stroke:{GOLD}", f"stroke:{VIOLET}"), origin=False)
    kf("gtag", gold_frames(f"fill:{GOLD}", f"fill:{VIOLET}"), origin=False)
    kf("gicon", gold_frames(f"color:{GOLD}", f"color:{VIOLET}"), origin=False)
    kf("pnode", dim(f"stroke:{ASH}", f"stroke:{PINK}"), origin=False)
    kf("pglo", dim(f"stroke:{ASH}", f"stroke:{PINK}"), origin=False)
    kf("ptag", dim(f"fill:{ASH}", f"fill:{PINK}"), origin=False)
    kf("pzero", dim(f"fill:{ASH}", f"fill:{PINK}"), origin=False)

    # The icons (22 px, drawn on a 24 grid like the site's).
    def icon(x: float, inner: str, cls: str, extra: str = "") -> str:
        s = 22 / 24
        return f'<g class="{cls}" {extra}><g transform="translate({x - 11:.1f} {ty - 11}) scale({s:.4f})">{inner}</g></g>'
    out += icon(xs[0], f'<g fill="none" stroke="{CYAN}" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/>'
                       '<path d="M15.2 8.6a4 4 0 1 0 0 6.8M7.5 11h6M7.5 13.2h5.2"/></g>', "ic0")
    out += icon(xs[1], f'<rect x="4" y="4.5" width="16" height="4.5" rx="1.4" fill="{BLUE}" opacity=".9"/>'
                       f'<rect x="4" y="10" width="16" height="4.5" rx="1.4" fill="{BLUE}" opacity=".75"/>'
                       f'<rect x="4" y="15.5" width="16" height="4.5" rx="1.4" fill="{BLUE}" opacity=".6"/>'
                       + "".join(f'<circle cx="7" cy="{cy}" r="1" fill="{PANEL}"/>' for cy in (6.75, 12.25, 17.75)), "ic1")
    out += (f'<g class="gicon" style="color:{VIOLET}">'
            + icon(xs[2], '<g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
                          '<path d="M8 4h8v5a4 4 0 0 1-8 0V4Z"/><path d="M8 6H5.5a2.5 2.5 0 0 0 2.6 3.4M16 6h2.5a2.5 2.5 0 0 1-2.6 3.4M12 13v3.5M8.5 20h7M9.5 20l.6-3.5h3.8l.6 3.5"/></g>', "ic2")
            + "</g>")
    out += f'<g class="ic3">{text(LABEL, "€0", 15, xs[3], ty + 15 * LABEL.cap / 2, PINK, anchor="middle", tracking=-0.02, extra="class=\"pzero\"")}</g>'

    # The wind: four streaks that end in a curl, and a few specks carried along, from the prize
    # pool to the €0.
    a, L, r0, r1 = xs[2], xs[3] - xs[2], R + 4, R + 4
    gusts = [(-9, -1, .9, .62, 1.6, 0, 3.5), (1, 1, 1.3, .78, 2, .14, 4.2), (10, 1, 1.1, .55, 1.4, .28, 3.0), (-3, -1, 1.6, .86, 1.2, .42, 4.6)]
    wind = ""
    for n, (y, k, ss, ee, sw, d, amp) in enumerate(gusts):
        s0 = r0 * ss
        e0 = s0 + (L - r0 - r1 - 16) * ee
        seg = (e0 - s0) / 3
        path = (f"M{s0:.1f} {y}C{s0 + seg * .5:.1f} {y - amp} {s0 + seg:.1f} {y + amp} {s0 + seg * 1.5:.1f} {y}"
                f"S{s0 + seg * 2.5:.1f} {y - amp} {e0:.1f} {y}c7 0 11 {3 * k} 11 {8 * k}s-4 {7 * k}-9 {7 * k}s-7 {-3 * k}-5 {-7 * k}")
        wind += f'<path class="w{n}" d="{path}" pathLength="100" fill="none" stroke="url(#windGrad)" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="42 142" stroke-dashoffset="42" opacity="0"/>'
        t0 = gone + d
        kf(f"w{n}", [(0, "stroke-dashoffset:42;opacity:0;transform:translateX(0)"),
                     (t0, "stroke-dashoffset:42;opacity:0;transform:translateX(0);animation-timing-function:cubic-bezier(.45,.05,.3,1)"),
                     (t0 + .3, "opacity:.95"), (t0 + 1.05, "opacity:.8"),
                     (t0 + 1.5, f"stroke-dashoffset:-100;opacity:0;transform:translateX({L * .12:.0f}px)")], origin=False)
    specks = [(-8, .62, 2, "#c9b6ff"), (6, .8, -3, PINK), (-2, .7, 4, "#c9b6ff"), (9, .9, -2, PINK), (-11, .58, 3, "#c9b6ff"), (3, .75, -4, PINK)]
    for n, (y, reach, dy, color) in enumerate(specks):
        wind += f'<circle class="sp{n}" cx="{r0}" cy="{y}" r="1.5" fill="{color}" opacity="0"/>'
        t0, dur = gone + .12 + n * .09, 1.3 + (n % 3) * .12
        kf(f"sp{n}", [(0, "opacity:0;transform:translate(0,0)"),
                      (t0, "opacity:0;transform:translate(0,0);animation-timing-function:cubic-bezier(.3,.1,.3,1)"),
                      (t0 + dur * .25, "opacity:.9"),
                      (t0 + dur, f"opacity:0;transform:translate({(L - r0 - r1) * reach:.0f}px,{dy}px)")], origin=False)
    out += f'<g transform="translate({a} {ty})">{wind}</g>'

    # The coin: flat gold with a darker rim, a faint halo and a short trail while it moves.
    x0 = xs[0]
    glyph = text(LABEL, "€", 15, x0, ty + 15 * LABEL.cap / 2, "#8a5a0c", anchor="middle")
    coin = (f'<g class="cmove"><rect class="trail" x="{x0 - 74}" y="{ty - 2}" width="74" height="4" rx="2" fill="url(#trailGrad)" opacity="0" filter="url(#hair)"/>'
            f'<g class="cface" opacity="0"><circle cx="{x0}" cy="{ty}" r="16" fill="{GOLD}" opacity=".35" filter="url(#soft)"/>'
            f'<circle cx="{x0}" cy="{ty}" r="13" fill="{GOLD}" stroke="#e9a93a" stroke-width="2"/>{glyph}</g></g>')
    d1, d2 = xs[1] - xs[0], xs[2] - xs[0]
    m1, m2 = (t1s + t1e) / 2, (t2s + t2e) / 2
    kf("cmove", [(0, "transform:translateX(0)"), (t1s, f"transform:translateX(0);animation-timing-function:{ease}"),
                 (t1e, f"transform:translateX({d1}px)"), (t2s, f"transform:translateX({d1}px);animation-timing-function:{ease}"),
                 (t2e, f"transform:translateX({d2}px)")], origin=False)
    kf("cface", [(0, f"opacity:0;transform:scale(.2);animation-timing-function:{spring}"), (.29, "opacity:1;transform:scale(1.15)"),
                 (.42, "opacity:1;transform:scale(1)"),
                 (t1s, f"transform:scale(1);animation-timing-function:{ease}"), (m1, f"transform:scale(1.12);animation-timing-function:{ease}"),
                 (t1e, f"transform:scale(1);animation-timing-function:{ease}"), (shrink, "transform:scale(.86)"),
                 (t2s, f"transform:scale(.86);animation-timing-function:{ease}"), (m2, f"transform:scale(.96);animation-timing-function:{ease}"),
                 (t2e, "opacity:1;transform:scale(.86);filter:blur(0);animation-timing-function:ease-in"),
                 (gone, "opacity:0;transform:scale(.35);filter:blur(3px)")])
    tr = lambda a0, a1: [(a0, f"opacity:0;transform:scaleX(.13);animation-timing-function:{ease}"),
                          ((a0 + a1) / 2, f"opacity:1;transform:scaleX(1);animation-timing-function:{ease}"), (a1, "opacity:0;transform:scaleX(.13)")]
    trail_frames = [(0, "opacity:0;transform:scaleX(.13)")] + tr(t1s, t1e) + tr(t2s, t2e)
    css.append(f".trail{{transform-box:fill-box;transform-origin:right center;animation:trail {T}s linear infinite}}"
               "@keyframes trail{" + "".join(f"{p(t)}{{{v}}}" for t, v in trail_frames) + "100%{opacity:0}}")

    blooms = "".join(f'<radialGradient id="bloom{i}"><stop offset="0" stop-color="{c}"/><stop offset=".68" stop-color="{c}" stop-opacity="0"/></radialGradient>'
                     for i, c in enumerate([CYAN, BLUE, GOLD, PINK]))
    defs = (
        '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>'
        '<filter id="hair" x="-10%" y="-200%" width="120%" height="500%"><feGaussianBlur stdDeviation="1"/></filter>'
        f'<linearGradient id="rail" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}"/><stop offset=".35" stop-color="{BLUE}"/>'
        f'<stop offset=".68" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BLUE}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<linearGradient id="windGrad" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{L}" y2="0">'
        f'<stop offset="0" stop-color="#c9b6ff"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
        f'<linearGradient id="trailGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{GOLD}" stop-opacity=".55"/></linearGradient>' + blooms
    )
    return svg(w, h, "Where every euro goes", "Where every euro goes: donations and fees come in, pay for hosting first, then go to season and tournament prize pools. PUGZ keeps nothing: zero profit.", out + coin, defs, "".join(css))


def footer_wordmark() -> str:
    w = 900
    word = "PUGZ"
    size = DISPLAY.fit(word, 300, w - 48, -0.03)
    cap = size * DISPLAY.cap
    h = int(cap + 36)
    x = (w - DISPLAY.width(word, size, -0.03)) / 2
    d = DISPLAY.outline(word, size, x, 18 + cap, -0.03)
    body = (
        f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width="1.4"/>'
        f'<path d="{d}" fill="none" stroke="url(#wordStroke)" stroke-width="2.2" stroke-linejoin="round"/>'
    )
    defs = (
        f'<linearGradient id="wordStroke" gradientUnits="userSpaceOnUse" x1="{x:.1f}" y1="0" x2="{w - x:.1f}" y2="0">'
        f'<stop offset="0" stop-color="{CYAN}"/><stop offset=".35" stop-color="{BLUE}"/>'
        f'<stop offset=".65" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>'
    )
    return svg(w, h, "PUGZ", "The PUGZ wordmark in an outlined brand gradient.", body, defs)


def mark_file() -> str:
    vx, vy, vw, vh = MARK_VIEW
    body = f'<path d="{MARK_LOW}" fill="url(#markLow)"/><path d="{MARK_TOP}" fill="url(#markTop)"/>'
    out = svg(vw, vh, "PUGZ mark", "The PUGZ P mark: two slanted strokes in the brand gradient.", body)
    return out.replace(f'viewBox="0 0 {vw} {vh}"', f'viewBox="{vx} {vy} {vw} {vh}"')


EYEBROWS = {
    "eyebrow-platform": "THE PLATFORM",
    "eyebrow-flow": "HOW A MATCH WORKS",
    "eyebrow-fair": "BUILT TO BE FAIR",
    "eyebrow-rating": "RATINGS, SEASONS AND QUEUES",
    "eyebrow-teams": "TEAMS AND SCRIMS",
    "eyebrow-tournaments": "TOURNAMENTS",
    "eyebrow-league": "LEAGUE",
    "eyebrow-coaching": "COACHING",
    "eyebrow-servers": "FOR ORGANISERS",
    "eyebrow-status": "DEVELOPMENT STATUS",
    "eyebrow-stack": "UNDER THE HOOD",
    "eyebrow-profit": "ZERO PROFIT",
}


# Status badges for the status table. A dark backing keeps them readable on GitHub's light theme too.
# Transparent, so they sit on GitHub's light and dark themes alike; mid-tone colours read on both.
BADGES = {"badge-in-testing": ("IN TESTING", "#1fb57f"), "badge-in-progress": ("IN PROGRESS", "#1ea7d6"), "badge-planned": ("PLANNED", "#d99a0b"), "badge-in-refinement": ("IN REFINEMENT", "#9b6cf0")}


def badge(label: str, color: str) -> str:
    _, tw = tag(0, 0, label, color, h=22, dot=True, size=9.5)
    w, h = int(tw + 4), 24
    body = tag(2, 1, label, color, h=22, dot=True, size=9.5)[0]
    return svg(w, h, label.title(), f"Status: {label.lower()}", body, "", PULSE_CSS)


def stamp_readme() -> None:
    """Add `?v=<hash>` to every graphic in the profile README.

    GitHub caches README images by URL for a long time. The hash changes whenever a graphic does, so
    a redrawn graphic is fetched fresh instead of the old one being served from the cache.
    """
    readme = ROOT / "profile" / "README.md"
    original = readme.read_text(encoding="utf-8")

    def stamp(match: re.Match[str]) -> str:
        name = match.group(1)
        digest = hashlib.md5((OUT / f"{name}.svg").read_bytes()).hexdigest()[:8]
        return f"profile/assets/{name}.svg?v={digest}"

    stamped = re.sub(r"profile/assets/([a-z0-9-]+)\.svg(?:\?v=[0-9a-f]+)?", stamp, original)
    if stamped != original:
        readme.write_text(stamped, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "banner.svg": banner(),
        "divider.svg": divider(),
        "flow.svg": flow(),
        "rating.svg": rating(),
        "tiers.svg": tiers(),
        "architecture.svg": architecture(),
        "tournaments.svg": tournaments(),
        "league.svg": league(),
        "queues.svg": queues(),
        "coaching.svg": coaching(),
        "servers.svg": servers(),
        "cta.svg": cta(),
        "profit.svg": profit(),
        "wordmark.svg": footer_wordmark(),
        "pugz-mark.svg": mark_file(),
        **{f"{name}.svg": eyebrow(label) for name, label in EYEBROWS.items()},
        **{f"{name}.svg": badge(label, color) for name, (label, color) in BADGES.items()},
    }
    for stale in OUT.glob("*.svg"):
        if stale.name not in files:
            stale.unlink()
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"{name:26s} {len(content) / 1024:6.1f} KB")
    stamp_readme()


if __name__ == "__main__":
    main()
