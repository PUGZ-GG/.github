# PUGZ-GG/.github

The home of the PUGZ organisation profile. GitHub shows [`profile/README.md`](profile/README.md) at the top of [github.com/PUGZ-GG](https://github.com/PUGZ-GG).

```
profile/
  README.md          the organisation profile
  assets/            the SVG graphics it uses (generated, see below)
tools/
  build-assets.py    generates profile/assets/ in the PUGZ brand
```

## Editing the text

Edit `profile/README.md`. Keep to the PUGZ voice: short, direct, verbs first, no exclamation marks and no emoji as icons. Only describe what is built; the status table says what is in testing and what is planned.

## Editing the graphics

The graphics are generated so they stay on-brand: the colours, shapes and type come from the PUGZ design system (deep navy, the cyan to pink gradient, wide Archivo type, the slanted strokes of the logo). Text inside them is converted to outlines, so it looks the same everywhere, including on machines without our fonts.

```bash
pip install fonttools brotli
python3 tools/build-assets.py
```

The script downloads the two brand fonts once into `tools/.fonts` (not committed) and rewrites `profile/assets/`. Commit the result.

## Banner links

The top banner and the closing call to action in `profile/README.md` link to the website, https://pugz.gg (search for `pugz.gg`).

---

PUGZ is an independent community project. Not affiliated with Embark Studios.
