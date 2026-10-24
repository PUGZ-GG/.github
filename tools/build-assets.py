#!/usr/bin/env python3
"""Builds the SVG graphics used by profile/README.md into profile/assets/.

GitHub renders README images without our web fonts, so every piece of text here is converted to
outlines with the real brand fonts (Archivo, JetBrains Mono). The colours and shapes follow the
PUGZ design system ("Velocity"): deep navy, the cyan -> blue -> violet -> pink gradient and the
logo's slanted strokes.

Usage:  pip install fonttools brotli && python3 tools/build-assets.py
The fonts are downloaded once into tools/.fonts (not committed).
"""

from __future__ import annotations

import urllib.request
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
GREEN, AMBER, INK_TEXT = "#63f0b5", "#ffcc4d", "#07071a"
RANKS = [
    ("Bronze", "#d79a6b"),
    ("Silver", "#c3c8d8"),
    ("Gold", "#ffd36b"),
    ("Platinum", "#d6e4ff"),
    ("Diamond", "#7fd8ff"),
    ("Ruby", "#ff4d7d"),
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

# The logo's two strokes (apps/web/client/src/brand/PugzMark.tsx), viewBox 170 290 940 730.
MARK_VIEW = (170, 290, 940, 730)
MARK_TOP = "M325 312 L1010 312 L1080 418 L835 742 L660 742 L800 516 L470 496 Z"
MARK_LOW = "M482 562 L720 562 L540 868 L198 996 L470 592 Z"


# --- Text as outlines -----------------------------------------------------------------------------
class Face:
    """One instance of a variable font, able to measure text and turn it into an SVG path."""

    def __init__(self, family: str, filename: str, axes: dict[str, float]):
        FONTS.mkdir(exist_ok=True)
        path = FONTS / filename
        if not path.exists():
            urllib.request.urlretrieve(f"{CDN}/{family}/files/{filename}", path)
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
            name = self._glyph(ch)
            glyph = self.glyphs[name]
            pen = SVGPathPen(self.glyphs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
            glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, pen_x, y)))
            parts.append(pen.getCommands())
            pen_x += glyph.width * scale + tracking * size
        return "".join(parts)

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


DISPLAY = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 800, "wdth": 125})
HEADING = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 700, "wdth": 112})
BODY = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 500, "wdth": 100})
BODY_BOLD = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 700, "wdth": 100})
LABEL = Face("archivo", "archivo-latin-wdth-normal.woff2", {"wght": 800, "wdth": 100})
MONO = Face("jetbrains-mono", "jetbrains-mono-latin-wght-normal.woff2", {"wght": 600})


def text(face: Face, s: str, size: float, x: float, y: float, fill: str, *, tracking: float = 0.0,
         anchor: str = "start", extra: str = "") -> str:
    width = face.width(s, size, tracking)
    x0 = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
    return f'<path d="{face.outline(s, size, x0, y, tracking)}" fill="{fill}" {extra}/>'


# --- Shared SVG pieces ----------------------------------------------------------------------------
def svg(width: int, height: int, title: str, desc: str, body: str, defs: str = "", style: str = "") -> str:
    style_tag = f"<style>{style}</style>" if style else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">'
        f'<title id="t">{title}</title><desc id="d">{desc}</desc>'
        f"<defs>{GRADIENTS}{defs}</defs>{style_tag}{body}</svg>\n"
    )


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


def para(x: float, y: float, w: float, h: float, slant: float, **attrs: str) -> str:
    """The brand's slanted parallelogram (a "/" lean), top edge shifted right by `slant`."""
    pts = f"{x + slant:.1f},{y:.1f} {x + w:.1f},{y:.1f} {x + w - slant:.1f},{y + h:.1f} {x:.1f},{y + h:.1f}"
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{pts}" {extra}/>'


def mark(x: float, y: float, width: float, extra: str = "") -> str:
    vx, vy, vw, _ = MARK_VIEW
    s = width / vw
    return (
        f'<g transform="translate({x} {y}) scale({s:.4f}) translate({-vx} {-vy})" {extra}>'
        f'<path d="{MARK_TOP}" fill="url(#markTop)" stroke="url(#markTop)" stroke-width="26" stroke-linejoin="round"/>'
        f'<path d="{MARK_LOW}" fill="url(#markLow)" stroke="url(#markLow)" stroke-width="26" stroke-linejoin="round"/>'
        "</g>"
    )


def button(x: float, y: float, label: str, w: float = 196, h: float = 46) -> str:
    """The primary button: brand-button fill, ink text, violet glow."""
    size = 15
    label_w = LABEL.width(label, size, 0.01)
    icon = 20
    gap = 10
    start = x + (w - (icon + gap + label_w)) / 2
    return (
        f'<rect x="{x}" y="{y + 6}" width="{w}" height="{h}" rx="12" fill="{VIOLET}" opacity=".45" filter="url(#glow-sm)"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="url(#button)"/>'
        f'<g transform="translate({start:.1f} {y + (h - icon) / 2:.1f}) scale({icon / 24})">'
        f'<path d="{DISCORD_GLYPH}" fill="{INK_TEXT}"/></g>'
        + text(LABEL, label, size, start + icon + gap, y + h / 2 + size * LABEL.cap / 2, INK_TEXT, tracking=0.01)
    )


BLUR_FILTERS = (
    '<filter id="glow-sm" x="-30%" y="-60%" width="160%" height="240%"><feGaussianBlur stdDeviation="9"/></filter>'
    '<filter id="glow-lg" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="34"/></filter>'
)


def tag(x: float, y: float, label: str, color: str, *, h: float = 24, dot: bool = False) -> tuple[str, float]:
    """A slanted tag with tinted fill; returns (svg, width)."""
    size = 10.5
    label_w = LABEL.width(label, size, 0.16)
    pad = 14 + (14 if dot else 0)
    w = label_w + pad * 2
    shape = para(x, y, w, h, 6, fill=color, fill_opacity=".14", stroke=color, stroke_opacity=".45", stroke_width="1")
    tx = x + pad + (14 if dot else 0)
    parts = [shape]
    if dot:
        parts.append(f'<circle class="pulse" cx="{x + pad + 3:.1f}" cy="{y + h / 2:.1f}" r="3.5" fill="{color}"/>')
    parts.append(text(LABEL, label, size, tx, y + h / 2 + size * LABEL.cap / 2, color, tracking=0.16))
    return "".join(parts), w


def panel(w: int, h: int, fill: str = INK_950, radius: int = 24) -> str:
    return (
        f'<rect width="{w}" height="{h}" rx="{radius}" fill="{fill}"/>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{radius - .5}" fill="none" stroke="#fff" stroke-opacity=".09"/>'
    )


def hairline(x: float, y: float, w: float = 64) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="2" fill="url(#brand)"/>'


# --- Assets ---------------------------------------------------------------------------------------
def banner() -> str:
    w, h = 900, 400
    left = 48
    word = "PUGZ"
    word_size = 118
    word_w = DISPLAY.width(word, word_size, -0.025)
    shafts = "".join(
        f'<g class="shaft s{i}">{para(x, -20, sw, h + 40, 150, fill="url(#shaftFill)", opacity=op)}</g>'
        for i, (x, sw, op) in enumerate([(430, 34, ".55"), (520, 90, ".35"), (650, 22, ".7"), (730, 120, ".28"), (860, 46, ".45")], 1)
    )
    live, live_w = tag(left, 38, "LAUNCHING SOON", AMBER, dot=True)
    comm, _ = tag(left + live_w + 10, 38, "COMMUNITY PUGS", CYAN)
    sub1 = "Queue on Discord. Play fair matches. Climb a rating"
    sub2 = "that means something. Built for THE FINALS."
    body = (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="24"/></clipPath>'
        f'<rect width="{w}" height="{h}" rx="24" fill="{INK_950}"/>'
        '<g clip-path="url(#card)">'
        f'<circle cx="90" cy="20" r="260" fill="{CYAN}" opacity=".16" filter="url(#glow-lg)"/>'
        f'<circle cx="700" cy="190" r="250" fill="{VIOLET}" opacity=".42" filter="url(#glow-lg)"/>'
        f'<circle cx="860" cy="400" r="170" fill="{PINK}" opacity=".2" filter="url(#glow-lg)"/>'
        f"{shafts}"
        f'<g opacity=".9">{para(560, 52, 250, 296, 70, fill="none", stroke="#fff", stroke_opacity=".07", stroke_width="1.5")}'
        f'{para(600, 52, 250, 296, 70, fill="none", stroke="#fff", stroke_opacity=".05", stroke_width="1.5")}</g>'
        f'<g opacity=".55" filter="url(#glow-lg)">{mark(560, 90, 300)}</g>'
        f'{mark(560, 90, 300)}'
        "</g>"
        f"{live}{comm}"
        + text(DISPLAY, word, word_size, left - 4, 188, "url(#wordFill)", tracking=-0.025)
        + text(HEADING, "Pick-up games, run properly.", 27, left, 238, TEXT)
        + text(BODY, sub1, 15, left, 274, MUTED)
        + text(BODY, sub2, 15, left, 296, MUTED)
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
    )
    style = (
        ".shaft{animation:drift 13s ease-in-out infinite alternate}"
        ".s2{animation-duration:17s;animation-delay:-5s}.s3{animation-duration:11s;animation-delay:-3s}"
        ".s4{animation-duration:20s;animation-delay:-9s}.s5{animation-duration:15s;animation-delay:-7s}"
        ".pulse{animation:pulse 2.2s ease-in-out infinite}"
        "@keyframes drift{from{transform:translateX(-26px)}to{transform:translateX(30px)}}"
        "@keyframes pulse{50%{opacity:.3}}"
        "@media (prefers-reduced-motion:reduce){.shaft,.pulse{animation:none}}"
    )
    return svg(w, h, "PUGZ", "PUGZ: pick-up games for THE FINALS, run properly. Launching soon. Join the Discord.", body, defs, style)


def eyebrow(label: str) -> str:
    """Section label: the slash glyph, then tracked uppercase text. Violet so it reads on light and dark."""
    size = 11
    tracking = 0.18
    tw = LABEL.width(label, size, tracking)
    w, h = int(tw + 34), 22
    body = (
        f'<polygon points="4,17 10,5 14,5 8,17" fill="url(#brand)"/>'
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
        + para(0, 3, w, 2, 0, fill="url(#fade)")
        + para(w / 2 - 22, 0, 44, 8, 6, fill=VIOLET_600)
    )
    return svg(w, 8, "Divider", "A thin brand-gradient divider with a slanted notch.", body)


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
            + hairline(x + 14, y + 1, 48)
            + para(x + 16, y + (row_h - 34) / 2, 58, 34, 8, fill=VIOLET_600, fill_opacity=".2", stroke=VIOLET, stroke_opacity=".5")
            + text(MONO, num, 15, x + 16 + 29, y + row_h / 2 + 5.3, CYAN, anchor="middle")
            + text(HEADING, title, 18, x + 92, y + 26, TEXT)
            + text(BODY, desc, 13.5, x + 92, y + 46, MUTED)
            + tag_svg
        )
    body = panel(w, h, INK_925) + "".join(rows)
    return svg(w, h, "How a match works", "Five steps: queue, lobby, match, result, rank. " + " ".join(f"{t}: {d}" for _, t, d, _ in FLOW), body)


def ranks() -> str:
    w, h = 900, 150
    items = []
    start, step = 48, 136
    for i, (name, color) in enumerate(RANKS):
        x = start + i * step
        items.append(
            para(x, 96, 14, 22, 5, fill=color)
            + text(BODY_BOLD, name, 14, x + 26, 112, color)
        )
    body = (
        panel(w, h, INK_925)
        + hairline(24, 1, 64)
        + text(HEADING, "Every rank, one community.", 22, 48, 54, TEXT)
        + text(BODY, "From Bronze to Ruby. Your THE FINALS rank sits on your profile, next to its name.", 14, 48, 78, MUTED)
        + "".join(items)
    )
    return svg(w, h, "Every rank, one community", "Bronze, Silver, Gold, Platinum, Diamond and Ruby ranks are shown on player profiles.", body)


def cta() -> str:
    w, h = 900, 250
    headline = "Your next match is one click away."
    size = DISPLAY.fit(headline, 31, w - 96, -0.02)
    body = (
        f'<clipPath id="card"><rect width="{w}" height="{h}" rx="28"/></clipPath>'
        f'<rect width="{w}" height="{h}" rx="28" fill="{INK_900}"/>'
        '<g clip-path="url(#card)">'
        f'<circle cx="160" cy="250" r="190" fill="{VIOLET}" opacity=".38" filter="url(#glow-lg)"/>'
        f'<circle cx="760" cy="10" r="190" fill="{CYAN}" opacity=".2" filter="url(#glow-lg)"/>'
        f'<circle cx="860" cy="250" r="150" fill="{PINK}" opacity=".18" filter="url(#glow-lg)"/>'
        f'<g opacity=".8">{para(40, -10, 80, 270, 70, fill="none", stroke="#fff", stroke_opacity=".06", stroke_width="1.5")}'
        f'{para(w - 130, -10, 80, 270, 70, fill="none", stroke="#fff", stroke_opacity=".06", stroke_width="1.5")}</g>'
        "</g>"
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="27" fill="none" stroke="url(#brand)" stroke-opacity=".55" stroke-width="1.5"/>'
        + text(LABEL, "JOIN THE COMMUNITY", 11, w / 2, 56, CYAN, tracking=0.18, anchor="middle")
        + text(DISPLAY, headline, size, w / 2, 108, TEXT, tracking=-0.02, anchor="middle")
        + text(BODY, "Join the Discord, link your Embark name and take a seat in the queue.", 15, w / 2, 144, MUTED, anchor="middle")
        + button((w - 210) / 2, 168, "Join the Discord", w=210, h=48)
    )
    return svg(w, h, "Join the Discord", "Your next match is one click away. Join the Discord, link your Embark name and take a seat in the queue.", body, BLUR_FILTERS)


def footer_wordmark() -> str:
    w = 900
    word = "PUGZ"
    size = DISPLAY.fit(word, 300, w - 48, -0.03)
    cap = size * DISPLAY.cap
    h = int(cap + 36)
    base = 18 + cap
    x = (w - DISPLAY.width(word, size, -0.03)) / 2
    d = DISPLAY.outline(word, size, x, base, -0.03)
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
    body = (
        f'<path d="{MARK_TOP}" fill="url(#markTop)" stroke="url(#markTop)" stroke-width="26" stroke-linejoin="round"/>'
        f'<path d="{MARK_LOW}" fill="url(#markLow)" stroke="url(#markLow)" stroke-width="26" stroke-linejoin="round"/>'
    )
    out = svg(vw, vh, "PUGZ mark", "The PUGZ P mark: two slanted strokes in the brand gradient.", body)
    return out.replace(f'viewBox="0 0 {vw} {vh}"', f'viewBox="{vx} {vy} {vw} {vh}"')


EYEBROWS = {
    "eyebrow-platform": "THE PLATFORM",
    "eyebrow-flow": "HOW A MATCH WORKS",
    "eyebrow-fair": "BUILT TO BE FAIR",
    "eyebrow-rating": "RATINGS AND SEASONS",
    "eyebrow-status": "WHERE WE ARE",
    "eyebrow-stack": "UNDER THE HOOD",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "banner.svg": banner(),
        "divider.svg": divider(),
        "flow.svg": flow(),
        "ranks.svg": ranks(),
        "cta.svg": cta(),
        "wordmark.svg": footer_wordmark(),
        "pugz-mark.svg": mark_file(),
        **{f"{name}.svg": eyebrow(label) for name, label in EYEBROWS.items()},
    }
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
        print(f"{name:24s} {len(content) / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
