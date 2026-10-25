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
# The PUG rating ladder as it is set for the current season (PUG settings, Ratings): a name, the
# rating it starts at and its colour. Staff can change all of it per season.
TIERS = [  # lowest first
    ("Rookie", "<750", "#748192", "rookie"),
    ("Prospect", "750+", "#658CB9", "prospect"),
    ("Contender", "850+", "#449ED7", "contender"),
    ("Challenger", "950+", "#26B7D3", "challenger"),
    ("Pro", "1050+", "#25CFBF", "pro"),
    ("Elite", "1150+", "#64DE8C", "elite"),
    ("Star", "1250+", "#98E36B", "star"),
    ("All-Star", "1350+", "#D8DF44", "allstar"),
    ("Superstar", "1500+", "#FFD547", "superstar"),
    ("Legend", "1650+", "#FF7F16", "legend"),
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
    live, live_w = tag(left, 38, "IN PRE-LAUNCH TESTING", AMBER, dot=True)
    comm, _ = tag(left + live_w + 10, 38, "COMMUNITY PUGS", CYAN)
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
        + text(HEADING, "Pick-up games for THE FINALS.", 27, left, 238, TEXT)
        + text(BODY, "Play matches through Discord. Track your rating,", 15, left, 274, MUTED)
        + text(BODY, "results and match history on the website.", 15, left, 296, MUTED)
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
    return svg(w, h, "PUGZ", "PUGZ. Pick-up games for THE FINALS. In pre-launch testing. Join the Discord.", body, defs, style)


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


FLOW = [
    ("01", "Queue", "Join from Discord or the site. One click in, one click out.", "DISCORD · WEB"),
    ("02", "Lobby", "The queue pops. Join the voice channel to ready up, then vote the map.", "DISCORD"),
    ("03", "Match", "Team voice channels, a host and a lobby code. Staff are one click away.", "DISCORD · WEB"),
    ("04", "Result", "One team reports, the other confirms. Disputes go to staff.", "DISCORD · WEB"),
    ("05", "Rank", "Your rating, the season and the leaderboard move with every result.", "WEB · DISCORD"),
]


def flow() -> str:
    w, pad, row_h, gap = 900, 22, 60, 10
    h = pad * 2 + len(FLOW) * row_h + (len(FLOW) - 1) * gap
    rows = []
    for i, (num, title, desc, where) in enumerate(FLOW):
        y = pad + i * (row_h + gap)
        x, rw = pad, w - pad * 2
        color = CYAN if "·" in where else VIOLET
        _, tag_w = tag(0, 0, where, color, h=22)
        tag_svg, _ = tag(x + rw - 16 - tag_w, y + (row_h - 22) / 2, where, color, h=22)
        rows.append(
            f'<rect x="{x}" y="{y}" width="{rw}" height="{row_h}" rx="14" fill="{INK_900}" stroke="#fff" stroke-opacity=".08"/>'
            f'<g class="step step{i}"><rect x="{x}" y="{y}" width="{rw}" height="{row_h}" rx="14" fill="{VIOLET}" fill-opacity=".1" stroke="url(#brand)" stroke-width="1.5"/>'
            f"{para(x + 4, y + 10, 6, row_h - 20, 2, fill='url(#brand)')}</g>"
            + f'<rect x="{x + 14}" y="{y + 1}" width="48" height="2" fill="url(#brand)"/>'
            + para(x + 16, y + (row_h - 34) / 2, 58, 34, 8, fill=VIOLET_600, fill_opacity=".2", stroke=VIOLET, stroke_opacity=".5")
            + text(MONO, num, 15, x + 16 + 29, y + row_h / 2 + 5.3, CYAN, anchor="middle")
            + text(HEADING, title, 18, x + 92, y + 26, TEXT)
            + text(BODY, desc, 13.5, x + 92, y + 46, MUTED)
            + tag_svg
        )
    body = panel(w, h, INK_925) + "".join(rows)
    return svg(w, h, "How a match works", "Five steps: queue, lobby, match, result, rank. " + " ".join(f"{t}: {d}" for _, t, d, _ in FLOW),
               body, "", cycle_css("step", len(FLOW), 10))


# The queue as it looks on the website (the Play page) and in the Discord queue embed, kept in sync.
# One scripted loop: you join on the website, Kai joins from Discord, you leave, Kai leaves, while
# the other queues in the embed have their own traffic (1v1 AMER fills and pops).
QUEUE_SECONDS = 18.0
QUEUES = [  # name, players needed, the line under the name in Discord, waiting since
    ("3v3 EMEA", 6, "EMEA · Final Round · 3v3 · balanced by PUG rating", "4 minutes ago"),
    ("1v1 EMEA", 2, "EMEA · Final Round · 1v1", "3 minutes ago"),
    ("3v3 AMER", 6, "AMER · Final Round · 3v3 · random teams", "12 minutes ago"),
    ("1v1 AMER", 2, "AMER · Final Round · 1v1", "a few seconds ago"),
]
QUEUE_START = {"3v3 EMEA": ["Mira", "Toast"], "1v1 EMEA": ["Vex"], "3v3 AMER": ["Onyx", "Sable", "Juno", "Okami"], "1v1 AMER": []}
QUEUE_EVENTS = [  # second, queue, player, joined (False = left), where it happened
    (2.0, "3v3 EMEA", "ENIGMA", True, "web"),
    (3.5, "1v1 AMER", "Hex", True, "discord"),
    (5.0, "1v1 AMER", "Ziggy", True, "discord"),
    (6.5, "3v3 EMEA", "Kai", True, "discord"),
    (8.0, "3v3 AMER", "Nova", True, "discord"),
    (11.5, "3v3 EMEA", "ENIGMA", False, "web"),
    (13.0, "3v3 AMER", "Nova", False, "discord"),
    (15.0, "3v3 EMEA", "Kai", False, "discord"),
]
QUEUE_POP = ("1v1 AMER", 5.0, 10.0, "PUG-1290")  # queue, popped at, open again at, match
QUEUE_REST = 7.0  # the moment shown when motion is off
PLAYER_TAGS = {"Mira": ("2210", VIOLET), "Toast": ("0417", AMBER), "ENIGMA": ("7810", PINK), "Kai": ("5532", CYAN)}
DC_BG, DC_EMBED, DC_TEXT, DC_HEAD, DC_MUTED = "#313338", "#2b2d31", "#dbdee1", "#f2f3f5", "#949ba4"
DC_BLURPLE, DC_GREEN, DC_RED, DC_GREY, DC_LINE = "#5865f2", "#23a55a", "#da373c", "#4e5058", "#3f4147"


class Timeline:
    """Swaps between pre-drawn states on one shared clock: each state is shown for its stretch of
    the loop, fading in over the one before it. `rest` picks the states shown when motion is off."""

    def __init__(self, seconds: float, rest: float, breaks: list[float], fade: float = 0.15):
        self.seconds, self.rest, self.fade = seconds, rest, fade
        self.breaks = sorted({0.0, seconds, *breaks})
        self.frames: dict[tuple[float, float], str] = {}
        self.flashes: dict[float, str] = {}

    def pct(self, t: float) -> str:
        return f"{max(0.0, min(100.0, t / self.seconds * 100)):.2f}%"

    def show(self, t0: float, t1: float, body: str) -> str:
        if t0 <= 0 and t1 >= self.seconds:
            return body
        name = self.frames.setdefault((t0, t1), f"s{len(self.frames)}")
        rest = " rest" if t0 <= self.rest < t1 else ""
        return f'<g class="st {name}{rest}">{body}</g>'

    def states(self, draw) -> str:
        """`draw(t)` for every stretch between breaks, with identical neighbours merged."""
        spans: list[list] = []
        for t0, t1 in zip(self.breaks, self.breaks[1:]):
            out = draw((t0 + t1) / 2)
            if spans and spans[-1][2] == out:
                spans[-1][1] = t1
            else:
                spans.append([t0, t1, out])
        return "".join(self.show(t0, t1, out) for t0, t1, out in spans if out)

    def flash(self, t: float, body: str) -> str:
        name = self.flashes.setdefault(t, f"f{len(self.flashes)}")
        return f'<g class="fl {name}">{body}</g>'

    def css(self) -> str:
        p, f, T = self.pct, self.fade, self.seconds
        rules = [f".st{{opacity:0}}.fl{{opacity:0}}"]
        # The next state fades in on top while this one stays, then this one cuts out underneath.
        cut = lambda t: f"{p(t + f)}{{opacity:1}}{p(t + f + .01)}{{opacity:0}}100%{{opacity:0}}"
        for (t0, t1), name in self.frames.items():
            if t0 <= 0:
                frames = f"0%{{opacity:1}}{cut(t1)}"
            elif t1 >= T:
                frames = f"0%{{opacity:0}}{p(t0)}{{opacity:0}}{p(t0 + f)}{{opacity:1}}100%{{opacity:1}}"
            else:
                frames = f"0%{{opacity:0}}{p(t0)}{{opacity:0}}{p(t0 + f)}{{opacity:1}}{cut(t1)}"
            rules.append(f".{name}{{animation:{name} {T}s linear infinite}}@keyframes {name}{{{frames}}}")
        for t, name in self.flashes.items():
            frames = f"0%{{opacity:0}}{p(t)}{{opacity:0}}{p(t + .15)}{{opacity:1}}{p(t + 1.6)}{{opacity:0}}100%{{opacity:0}}"
            rules.append(f".{name}{{animation:{name} {T}s ease-out infinite}}@keyframes {name}{{{frames}}}")
        return "".join(rules) + ".rest{opacity:1}"


def queue_state(t: float) -> dict:
    """Who is in which queue at second `t`, and whether a queue is showing its pop."""
    players = {name: list(start) for name, start in QUEUE_START.items()}
    for when, queue, player, joined, _ in QUEUE_EVENTS:
        if when <= t:
            players[queue].append(player) if joined else players[queue].remove(player)
    queue, popped_at, open_at, _ = QUEUE_POP
    popped = popped_at <= t < open_at
    if t >= popped_at:
        players[queue] = []
    joined_at = next((w for w, q, p, j, _ in QUEUE_EVENTS if p == "ENIGMA" and j and w <= t), None)
    left_at = next((w for w, q, p, j, _ in QUEUE_EVENTS if p == "ENIGMA" and not j and w <= t), None)
    timer = int(t - joined_at) if joined_at is not None and left_at is None else None
    return {"players": players, "popped": queue if popped else None, "timer": timer}


def chevron(cx: float, cy: float, left: bool, opacity: float) -> str:
    d = f"M{cx + 2:.1f} {cy - 5:.1f}l-5 5 5 5" if left else f"M{cx - 2:.1f} {cy - 5:.1f}l5 5-5 5"
    return (
        f'<g opacity="{opacity}"><circle cx="{cx}" cy="{cy}" r="15" fill="#fff" fill-opacity=".04" stroke="#fff" stroke-opacity=".12"/>'
        f'<path d="{d}" fill="none" stroke="{TEXT}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )


def web_queue(tl: Timeline, x: float, w: float, bottom: float) -> str:
    """The Play page: the queue ring with its button, and the queue block below it."""
    name, cap = QUEUES[0][0], QUEUES[0][1]
    cx, cy, r = x + w / 2, 132, 54
    arc = 2 * math.pi * (r + 11)

    def ring(t: float) -> str:
        n = len(queue_state(t)["players"][name])
        return (
            f'<circle cx="{cx}" cy="{cy}" r="{r + 11}" fill="none" stroke="url(#ringArc)" stroke-width="2.5" stroke-linecap="round" '
            f'stroke-dasharray="{arc * n / cap:.1f} {arc:.1f}" transform="rotate(-90 {cx} {cy})"/>'
            + text(MONO, f"{n}/{cap}", 30, cx, cy + 7, TEXT, anchor="middle")
        )

    def status(t: float) -> str:
        timer = queue_state(t)["timer"]
        label = "IN QUEUE" if timer is None else f"IN QUEUE · 0:{timer:02d}"
        return text(LABEL, label, 7.5, cx, cy + 25, MUTED, tracking=0.16, anchor="middle")

    def controls(t: float) -> str:
        inside = queue_state(t)["timer"] is not None
        bw, bh, by = 150, 32, 230
        bx = cx - bw / 2
        if inside:
            btn = (f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="{INK_850}" stroke="#fff" stroke-opacity=".14"/>'
                   + text(LABEL, "LEAVE QUEUE", 10.5, cx, by + bh / 2 + 3.8, TEXT, tracking=0.04, anchor="middle"))
        else:
            btn = (f'<rect x="{bx}" y="{by + 4}" width="{bw}" height="{bh}" rx="8" fill="{VIOLET}" opacity=".4" filter="url(#glow-sm)"/>'
                   f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="8" fill="url(#button)"/>'
                   + text(LABEL, "QUEUE UP", 10.5, cx, by + bh / 2 + 3.8, INK_TEXT, tracking=0.04, anchor="middle"))
        dim = ".35" if inside else "1"
        return chevron(cx - 104, cy, True, dim) + chevron(cx + 104, cy, False, dim) + btn

    clicks = "".join(
        tl.flash(when, f'<rect x="{cx - 79}" y="226" width="158" height="40" rx="11" fill="none" stroke="{CYAN}" stroke-width="2"/>')
        for when, _, player, _, where in QUEUE_EVENTS if player == "ENIGMA"
    )
    hero = (
        para(x - 4, 60, 150, 200, 70, fill=VIOLET, fill_opacity=".05")
        + f'<circle cx="{cx}" cy="{cy}" r="{r + 4}" fill="none" stroke="{VIOLET}" stroke-opacity=".35" stroke-width="10" filter="url(#glow-sm)"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{INK_950}" stroke="url(#ringFace)" stroke-width="4"/>'
        + f'<circle cx="{cx}" cy="{cy}" r="{r + 11}" fill="none" stroke="#fff" stroke-opacity=".06" stroke-width="2.5"/>'
        + tl.states(ring) + tl.states(status) + tl.states(controls) + clicks
        + text(BODY, "3v3 · Final Round · EMEA", 11.5, cx, 214, MUTED, anchor="middle")
        + text(BODY, "Every queue is on the Play page", 10, cx, 282, FAINT, anchor="middle")
    )

    # The queue block
    top, pad = 300, 16
    ix, iw = x + pad, w - pad * 2
    badge, badge_w = tag(0, 0, "QUEUE OPEN", GREEN, h=20, size=8.5)
    badge, _ = tag(ix + iw - badge_w, top + 16, "QUEUE OPEN", GREEN, h=20, size=8.5)
    rows_top, row_h = top + 104, (bottom - 40 - (top + 104)) / cap

    def count(t: float) -> str:
        n = len(queue_state(t)["players"][name])
        return (text(MONO, f"{n}/{cap}", 11, ix + iw, top + 76, TEXT, anchor="end")
                + f'<rect x="{ix}" y="{top + 85}" width="{iw * n / cap:.1f}" height="5" rx="2.5" fill="url(#brand)"/>')

    def rows(t: float) -> str:
        state, out = queue_state(t), []
        for i in range(cap):
            y = rows_top + i * row_h
            mid = y + row_h / 2
            players = state["players"][name]
            if i < len(players):
                player = players[i]
                number, color = PLAYER_TAGS[player]
                you = player == "ENIGMA"
                if you:
                    out.append(f'<rect x="{x + 1}" y="{y}" width="{w - 2}" height="{row_h:.1f}" fill="{VIOLET}" fill-opacity=".12"/>')
                out.append(
                    f'<circle cx="{ix + 12}" cy="{mid:.1f}" r="12" fill="{color}" fill-opacity=".18" stroke="{color}" stroke-opacity=".6"/>'
                    + text(LABEL, player[0], 10, ix + 12, mid + 3.6, color, anchor="middle")
                    + text(BODY_BOLD, player, 12, ix + 34, mid - 1, TEXT)
                    + text(BODY, f"{player}#{number}", 9.5, ix + 34, mid + 12, MUTED)
                )
                if you:
                    out.append(text(LABEL, "YOU", 8, ix + 40 + BODY_BOLD.width(player, 12), mid - 1, CYAN, tracking=0.12))
            else:
                out.append(f'<circle cx="{ix + 12}" cy="{mid:.1f}" r="11" fill="none" stroke="#fff" stroke-opacity=".25" stroke-dasharray="2.5 3"/>'
                           + text(BODY, "Open place", 11.5, ix + 34, mid + 4, FAINT))
        return "".join(out)

    def timer(t: float) -> str:
        state = queue_state(t)
        if state["timer"] is None:
            return ""
        mid = rows_top + (state["players"][name].index("ENIGMA") + .5) * row_h
        return text(MONO, f"0:{state['timer']:02d}", 10.5, ix + iw, mid + 4, MUTED, anchor="end")

    seps = "".join(f'<line x1="{x}" x2="{x + w}" y1="{rows_top + i * row_h:.1f}" y2="{rows_top + i * row_h:.1f}" stroke="#fff" stroke-opacity=".06"/>'
                   for i in range(cap + 1))
    flashes = "".join(
        tl.flash(when, f'<rect x="{x + 1}" y="{top + 56}" width="{w - 2}" height="{bottom - 40 - top - 56:.1f}" fill="{CYAN}" fill-opacity=".06"/>')
        for when, queue, *_ in QUEUE_EVENTS if queue == name
    )
    block = (
        card(x, top, w, bottom - top)
        + text(HEADING, name, 15, ix, top + 30, TEXT)
        + text(BODY, "Final Round · EMEA", 11, ix, top + 46, MUTED)
        + badge
        + f'<line x1="{x}" x2="{x + w}" y1="{top + 56}" y2="{top + 56}" stroke="#fff" stroke-opacity=".08"/>'
        + text(BODY, "In queue", 11, ix, top + 76, MUTED)
        + f'<rect x="{ix}" y="{top + 85}" width="{iw}" height="5" rx="2.5" fill="#fff" fill-opacity=".08"/>'
        + flashes + tl.states(count) + seps + tl.states(rows) + tl.states(timer)
        + text(BODY, "Best of 3 · Balanced by PUG rating · Map vote · 2 min ready check", 10.5, ix, bottom - 16, MUTED)
    )
    return hero + block


def slots(x: float, y: float, filled: int, cap: int, popped: bool) -> tuple[str, float]:
    sw, sh, gap = 13, 12, 3.5
    out = []
    for i in range(cap):
        sx = x + i * (sw + gap)
        if popped:
            out.append(para(sx, y, sw, sh, 3.5, fill=DC_GREEN))
        elif i < filled:
            out.append(para(sx, y, sw, sh, 3.5, fill=mix(CYAN, VIOLET, i / max(cap - 1, 1))))
        else:
            out.append(para(sx + .5, y + .5, sw - 1, sh - 1, 3.5, fill="none", stroke=DC_MUTED, stroke_opacity=".7"))
    return "".join(out), cap * (sw + gap)


def discord_queue(tl: Timeline, x: float, w: float) -> tuple[str, float]:
    """The queue embed the bot posts in Discord. Returns (svg, bottom)."""
    ax, ay = x + 18, 72
    app_x = ax + 38 + BODY_BOLD.width("PUGZ", 13) + 6
    head = (
        f'<circle cx="{ax + 14}" cy="{ay + 6}" r="15" fill="{INK_900}"/>' + mark(ax + 3, ay - 2, 22)
        + text(BODY_BOLD, "PUGZ", 13, ax + 38, ay + 5, DC_HEAD)
        + f'<rect x="{app_x:.1f}" y="{ay - 6}" width="26" height="13" rx="3" fill="{DC_BLURPLE}"/>'
        + text(LABEL, "APP", 7.5, app_x + 13, ay + 3.6, "#fff", anchor="middle", tracking=0.04)
        + text(BODY, "Today at 20:14", 10, app_x + 34, ay + 4, DC_MUTED)
    )
    ex, ey, ew = ax + 38, ay + 18, w - 18 - 38 - 14
    cx, cw = ex + 14, ew - 28
    banner_h = 58
    art = (
        f'<clipPath id="bannerClip"><rect x="{cx}" y="{ey + 12}" width="{cw}" height="{banner_h}" rx="6"/></clipPath>'
    )
    banner = (
        f'<g clip-path="url(#bannerClip)"><rect x="{cx}" y="{ey + 12}" width="{cw}" height="{banner_h}" fill="url(#dcBanner)"/>'
        + para(cx + cw * .52, ey + 12, 60, banner_h, 30, fill=VIOLET, fill_opacity=".22")
        + para(cx + cw * .52 + 66, ey + 12, 14, banner_h, 30, fill=PINK, fill_opacity=".18") + "</g>"
        + para(cx + 12, ey + 27, 9, 5, 2, fill=VIOLET)
        + text(LABEL, "PUGZ · THE FINALS PUGS", 7, cx + 25, ey + 32, CYAN, tracking=0.16)
        + text(BLACK, "QUEUE UP", 22, cx + 12, ey + 58, "url(#brand)")
        + mark(cx + cw - 52, ey + 22, 38)
    )
    y = ey + 12 + banner_h + 24
    intro = text(BODY_BOLD, "Pick your queues", 13.5, cx, y, DC_HEAD)
    blurb = "Join as many as you like. The first one to fill pops, and you leave the rest."
    intro += text(BODY, blurb, BODY.fit(blurb, 10.5, cw), cx, y + 17, DC_TEXT)
    sy = y + 35

    def summary(t: float) -> str:
        state = queue_state(t)
        total = sum(len(p) for p in state["players"].values())
        close = sum(1 for n, cap, *_ in QUEUES if len(state["players"][n]) == cap - 1)
        lead = "Nobody queuing yet" if total == 0 else f"{total} player{'s' if total != 1 else ''} queuing"
        rest = "" if not close else f" · {close} queue{' is' if close == 1 else 's are'} one away from popping"
        return text(BODY_BOLD, lead, 10, cx + 10, sy, DC_TEXT) + text(BODY, rest, 10, cx + 10 + BODY_BOLD.width(lead, 10), sy, DC_MUTED)

    status = f'<circle cx="{cx + 3.5}" cy="{sy - 3.5}" r="3.5" fill="{DC_GREEN}"/>' + tl.states(summary)
    line_y = sy + 12
    rows = f'<line x1="{cx}" x2="{cx + cw}" y1="{line_y}" y2="{line_y}" stroke="{DC_LINE}"/>'
    row_h = 80
    for qi, (name, cap, sub, since) in enumerate(QUEUES):
        top = line_y + qi * row_h
        jx = cx + cw - 52

        def row(t: float, name=name, cap=cap, since=since, top=top) -> str:
            state = queue_state(t)
            players, popped = state["players"][name], state["popped"] == name
            sl, sw = slots(cx, top + 39, len(players), cap, popped)
            tx = cx + sw + 4
            if popped:
                match = QUEUE_POP[3]
                lead = text(BODY_BOLD, "Popped", 11, tx, top + 49.5, DC_HEAD)
                ax_ = tx + BODY_BOLD.width("Popped", 11) + 5
                arrow_ = f'<path d="M{ax_:.1f} {top + 45.5}h10m-3.5-3.5 3.5 3.5-3.5 3.5" fill="none" stroke="{DC_HEAD}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
                line = (lead + arrow_ + text(BODY_BOLD, match, 11, ax_ + 16, top + 49.5, DC_HEAD)
                        + text(BODY, f"{cap} players are heading to the lobby. The queue is open again.", 9.5, cx, top + 67, DC_MUTED))
                return sl + line
            more = cap - len(players)
            lead = f"{len(players)}/{cap}"
            line = (text(BODY_BOLD, lead, 11, tx, top + 49.5, DC_HEAD)
                    + text(BODY, f" · {more} more to pop", 11, tx + BODY_BOLD.width(lead, 11), top + 49.5, DC_TEXT))
            if not players:
                return sl + line + text(BODY, "Nobody yet. Be the first.", 9.5, cx, top + 67, DC_MUTED)
            chips, px = [], cx
            for p in players:
                label = f"@{p}"
                lw = BODY_BOLD.width(label, 9.5) + 6
                chips.append(f'<rect x="{px:.1f}" y="{top + 57}" width="{lw:.1f}" height="14" rx="3" fill="{DC_BLURPLE}" fill-opacity=".3"/>'
                             + text(BODY_BOLD, label, 9.5, px + 3, top + 67.5, "#c9cdfb"))
                px += lw + 4
            wait = f"· waiting since {since}"
            if px + BODY.width(wait, 9.5) <= cx + cw:
                chips.append(text(BODY, wait, 9.5, px, top + 67.5, DC_MUTED))
            return sl + line + "".join(chips)

        flashes = "".join(
            tl.flash(when, f'<rect x="{ex + 4}" y="{top + 1}" width="{ew - 4}" height="{row_h - 2}" fill="{DC_BLURPLE}" fill-opacity=".12"/>')
            for when, queue, *_ in QUEUE_EVENTS if queue == name
        )
        rows += (
            flashes
            + text(BODY_BOLD, name, 12.5, cx, top + 18, DC_HEAD)
            + text(BODY, sub, 9.5, cx, top + 31, DC_MUTED)
            + tl.states(row)
            + f'<rect x="{jx}" y="{top + 24}" width="52" height="22" rx="4" fill="{DC_BLURPLE}"/>'
            + para(jx + 10, top + 30.5, 4, 9, 2, fill="#fff") + para(jx + 15, top + 30.5, 4, 9, 2, fill="#fff")
            + text(BODY_BOLD, "Join", 10.5, jx + 23, top + 38.8, "#fff")
            + f'<line x1="{cx}" x2="{cx + cw}" y1="{top + row_h}" y2="{top + row_h}" stroke="{DC_LINE}"/>'
        )
    fy = line_y + len(QUEUES) * row_h + 12
    leave_w = BODY_BOLD.width("Leave all", 10.5) + 36
    web_w = BODY_BOLD.width("Play on the web", 10.5) + 38
    footer = (
        f'<rect x="{cx}" y="{fy}" width="{leave_w:.1f}" height="24" rx="4" fill="{DC_RED}"/>'
        f'<path d="M{cx + 16} {fy + 7}h-4v10h4M{cx + 15} {fy + 12}h7m-2.5-2.5 2.5 2.5-2.5 2.5" fill="none" stroke="#fff" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>'
        + text(BODY_BOLD, "Leave all", 10.5, cx + 27, fy + 15.8, "#fff")
        + f'<rect x="{cx + leave_w + 8:.1f}" y="{fy}" width="{web_w:.1f}" height="24" rx="4" fill="{DC_GREY}"/>'
        + text(BODY_BOLD, "Play on the web", 10.5, cx + leave_w + 18, fy + 15.8, "#fff")
        + f'<path d="M{cx + leave_w + web_w - 6:.1f} {fy + 8}h5v5m0-5-6 6" fill="none" stroke="#fff" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
        + text(BODY, "Your spot lasts 60 minutes. Press Join again to stay in.", 9.5, cx, fy + 42, DC_MUTED)
    )
    bottom = fy + 54
    embed = (
        f'<rect x="{ex}" y="{ey}" width="{ew}" height="{bottom - ey}" rx="5" fill="{DC_EMBED}"/>'
        f'<path d="M{ex + 4} {ey}h-0a4 4 0 0 0-4 4v{bottom - ey - 8}a4 4 0 0 0 4 4z" fill="{VIOLET}"/>'
    )
    return art + embed + head + banner + intro + status + rows + footer, bottom


def queues() -> str:
    w, pad, gap = 900, 22, 16
    cw = (w - pad * 2 - gap) / 2
    lx, rx = pad, pad + cw + gap
    breaks = [e[0] for e in QUEUE_EVENTS] + list(QUEUE_POP[1:3])
    joined = next(e[0] for e in QUEUE_EVENTS if e[2] == "ENIGMA" and e[3])
    left = next(e[0] for e in QUEUE_EVENTS if e[2] == "ENIGMA" and not e[3])
    breaks += [float(s) for s in range(math.ceil(joined), math.ceil(left))]
    tl = Timeline(QUEUE_SECONDS, QUEUE_REST, breaks)

    discord, bottom = discord_queue(tl, rx, cw)
    h = int(bottom + 14 + pad)
    web_tag, _ = tag(lx, 18, "ON THE WEBSITE", CYAN, h=22, size=9.5)
    dc_tag, _ = tag(rx, 18, "IN DISCORD", VIOLET, h=22, size=9.5)
    body = (
        panel(w, h, INK_925)
        + web_tag + dc_tag
        + f'<rect x="{rx}" y="52" width="{cw}" height="{h - 52 - pad}" rx="14" fill="{DC_BG}"/>'
        + web_queue(tl, lx, cw, h - pad)
        + discord
    )
    defs = (
        BLUR_FILTERS
        + f'<linearGradient id="ringFace" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}"/>'
        f'<stop offset=".55" stop-color="{BLUE}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
        + f'<linearGradient id="ringArc" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{VIOLET}"/>'
        f'<stop offset="1" stop-color="{PINK}"/></linearGradient>'
        + f'<linearGradient id="dcBanner" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0a0a22"/>'
        f'<stop offset="1" stop-color="#1c1046"/></linearGradient>'
    )
    desc = (
        "The same queue on the website and in Discord, kept in sync. On the Play page you queue up for 3v3 EMEA: "
        "the ring goes from 2/6 to 3/6 and you appear in the queue block below it, while the Discord queue embed shows "
        "you joining 3v3 EMEA at the same moment. A player who joins from Discord shows up on the website too. The embed "
        "also lists 1v1 EMEA, 3v3 AMER and 1v1 AMER, where other players join and leave and a queue pops into a match."
    )
    return svg(w, h, "The queue on the website and in Discord", desc, body, defs, tl.css())


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
    """The rating ladder: ten ranks, lowest to highest, each with its threshold. A highlight climbs it."""
    w, h = 900, 372
    n = len(TIERS)
    col_w = (w - 96) / n
    base, shield_h = 306, 52
    out = [
        text(HEADING, "Climb the ladder.", 22, 48, 54, TEXT)
        + text(BODY, "Ranks are Discord roles. Cross a threshold and your rank changes right away.", 14, 48, 78, MUTED)
    ]
    glow_defs = ""
    glows = ""
    for i, (name, threshold, color, kind) in enumerate(TIERS):
        cx = 48 + col_w * (i + 0.5)
        block_h = 26 + i * 15
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
    return svg(w, h, "The PUG rating ladder", "Ten ranks from Rookie to Legend, set per season by staff: " + ", ".join(f"{t[0]} {t[1]}" for t in TIERS) + ". Ranks are Discord roles and change the moment your rating crosses a threshold.", body, glow_defs, style)


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
    ex = node(716, 530, 160, 126, "External", ["Embark · Steam · Twitch", "Stripe · Resend", "Liquipedia"], icon_cloud(732, 546, A_GRAY, solid=False), title_size=16)

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
        + arrow("M696 440V590H640", "red", packets=True, reverse=True) + pill(696, 520, "Process jobs", "red")
        + arrow("M796 440V530", "gray", both=True) + pill(796, 492, "Sync", "gray")
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


def tournaments() -> str:
    w, h = 900, 400
    # Stage stepper along the top: the real tournament states.
    stages = [("REGISTRATION", CYAN), ("CHECK-IN", VIOLET), ("LIVE", GREEN), ("COMPLETED", GOLD)]
    x, stepper, overlays = 48, "", ""
    for i, (label, color) in enumerate(stages):
        base, tw = tag(x, 26, label, color, h=26, dot=(label == "LIVE"), size=10.5)
        stepper += base
        overlays += f'<g class="stage stage{i}">{para(x - 2, 24, tw + 4, 30, 6, fill=color, fill_opacity=".28", stroke=color, stroke_width="1.5")}</g>'
        x += tw + 26
        if i < len(stages) - 1:
            stepper += f'<polyline points="{x - 20},{39} {x - 12},{39} {x - 16},{35} {x - 12},{39} {x - 16},{43}" fill="none" stroke="{FAINT}" stroke-width="1.5" stroke-linecap="round"/>'
    # Bracket: 8 seeds, quarter-finals -> semi-finals -> final -> champion.
    sw, sh = 168, 26
    cols = [48, 262, 476]
    top, pitch = 92, 68
    qf = [top + i * pitch + 28 for i in range(4)]  # centres of the four quarter-finals
    sf = [(qf[0] + qf[1]) / 2, (qf[2] + qf[3]) / 2]
    fn = (sf[0] + sf[1]) / 2
    seeds = [("Seed 1", "Seed 8"), ("Seed 4", "Seed 5"), ("Seed 3", "Seed 6"), ("Seed 2", "Seed 7")]
    winners = {"qf": [0, 1, 0, 0]}

    def slot(xx: float, cy: float, label: str, hot: bool, placeholder: bool = False) -> str:
        yy = cy - sh / 2
        stroke = 'url(#brand)' if hot else "#fff"
        sop = "1" if hot else ".1"
        fill = f'<rect x="{xx}" y="{yy}" width="{sw}" height="{sh}" rx="8" fill="{INK_900}" stroke="{stroke}" stroke-opacity="{sop}" stroke-width="{1.4 if hot else 1}"/>'
        col = TEXT if hot else (FAINT if placeholder else MUTED)
        return fill + text(BODY_BOLD, label, 12, xx + 12, cy + 4.2, col)

    lines_dim, lines_hot, slots = "", "", ""
    for i, (a, b) in enumerate(seeds):
        c = qf[i]
        win = winners["qf"][i]
        slots += slot(cols[0], c - 15, a, win == 0) + slot(cols[0], c + 15, b, win == 1)
        # connector to the semi-final
        target = sf[i // 2]
        mid = cols[0] + sw + 22
        path = f"M{cols[0] + sw} {c - 15 + (30 if win else 0)}H{mid}V{target - (15 if i % 2 == 0 else -15)}H{cols[1]}"
        if i == 0:
            lines_hot += f'<path d="{path}" class="flow" fill="none" stroke="url(#brand)" stroke-width="2" stroke-dasharray="7 6"/>'
        else:
            lines_dim += f'<path d="{path}" fill="none" stroke="#fff" stroke-opacity=".14" stroke-width="1.5"/>'
    semis = [("Seed 1", "Seed 5"), ("Seed 3", "Seed 2")]
    for j, (a, b) in enumerate(semis):
        c = sf[j]
        slots += slot(cols[1], c - 15, a, j == 0) + slot(cols[1], c + 15, b, False)
        target = fn
        mid = cols[1] + sw + 22
        path = f"M{cols[1] + sw} {c - 15}H{mid}V{target - (15 if j == 0 else -15)}H{cols[2]}"
        if j == 0:
            lines_hot += f'<path d="{path}" class="flow" fill="none" stroke="url(#brand)" stroke-width="2" stroke-dasharray="7 6"/>'
        else:
            lines_dim += f'<path d="{path}" fill="none" stroke="#fff" stroke-opacity=".14" stroke-width="1.5"/>'
    slots += slot(cols[2], fn - 15, "Seed 1", True) + slot(cols[2], fn + 15, "Winner SF2", False, True)
    champ_x = cols[2] + sw + 44
    # A flat line has no bounding box, so a gradient can't paint it: this last leg is gold.
    lines_hot += f'<path d="M{cols[2] + sw} {fn - 15}H{champ_x}" class="flow" fill="none" stroke="{GOLD}" stroke-width="2" stroke-dasharray="7 6"/>'
    live_tag, _ = tag(cols[1], sf[1] - 15 - sh / 2 - 26, "LIVE", GREEN, h=20, dot=True, size=9.5)
    # Round labels.
    labels = "".join(
        text(LABEL, name, 10.5, x0, 80, FAINT, tracking=0.16)
        for name, x0 in (("QUARTER-FINALS", cols[0]), ("SEMI-FINALS", cols[1]), ("FINAL", cols[2]))
    )
    # Champion card.
    cw, ch = 900 - champ_x - 40, 104
    cy = fn - ch / 2
    champion = (
        f'<rect x="{champ_x}" y="{cy}" width="{cw}" height="{ch}" rx="14" fill="{INK_900}" stroke="{GOLD}" stroke-opacity=".5"/>'
        f'<rect x="{champ_x + 14}" y="{cy + 1}" width="48" height="2" fill="{GOLD}"/>'
        + para(champ_x + 16, cy + 22, 22, 26, 6, fill=GOLD)
        + text(LABEL, "CHAMPION", 11, champ_x + 48, cy + 40, GOLD, tracking=0.16)
        + "".join(text(BODY, line, 12, champ_x + 16, cy + 68 + i * 16, MUTED) for i, line in enumerate(BODY.wrap("Recorded on every profile, forever.", 12, cw - 32)))
    )
    body = panel(w, h, INK_925) + stepper + overlays + labels + lines_dim + lines_hot + slots + live_tag + champion
    style = (
        cycle_css("stage", len(stages), 8)
        + ".flow{animation:flow 1.4s linear infinite}@keyframes flow{to{stroke-dashoffset:-26}}"
        + PULSE_CSS
    )
    return svg(w, h, "Tournaments", "A tournament moves from registration to check-in to live to completed. A bracket of eight seeds runs quarter-finals, semi-finals and a final, and the champion is recorded on every profile.", body, "", style)


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
    "eyebrow-rating": "RATINGS AND SEASONS",
    "eyebrow-teams": "TEAMS AND SCRIMS",
    "eyebrow-tournaments": "TOURNAMENTS",
    "eyebrow-coaching": "COACHING",
    "eyebrow-status": "DEVELOPMENT STATUS",
    "eyebrow-stack": "UNDER THE HOOD",
}


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
        "queues.svg": queues(),
        "rating.svg": rating(),
        "tiers.svg": tiers(),
        "architecture.svg": architecture(),
        "tournaments.svg": tournaments(),
        "coaching.svg": coaching(),
        "cta.svg": cta(),
        "wordmark.svg": footer_wordmark(),
        "pugz-mark.svg": mark_file(),
        **{f"{name}.svg": eyebrow(label) for name, label in EYEBROWS.items()},
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
