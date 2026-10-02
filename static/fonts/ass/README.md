# ASS font vault

Drop `.woff2` (preferred), `.ttf`, or `.otf` files under the subfolders listed in `manifest.json`.
Font binaries are gitignored; only this README and `manifest.json` are tracked.

JASSUB fetches each URL **on demand** when an ASS/SSA track references that `Fontname` (or `\fn` tag).

**JASSUB 1.x** matches `Fontname` with **lowercase** keys in `availableFonts` (`video.js` normalizes manifest entries). Display names in `manifest.json` can stay title case; the worker lookup is always lower case.

## Sample release (Gandhi Sans / QType / etc.)

| ASS name | Expected file |
|----------|----------------|
| Gandhi Sans | `gandhi-sans/GandhiSans-Bold.woff2` |
| QType | `qtype/QType.woff2` |
| Marco GRK Sb | `marco-grk/MarcoGRKSb.woff2` |
| Adobe Caslon Pro Bold | `adobe-caslon-pro/CaslonPro-Bold.woff2` |
| Marquis De Sade Ornaments | `marquis/MarquisDeSadeOrnaments.woff2` |

Extract attachments from MKV releases or copy from your local font collection, then convert to WOFF2 if needed.

## Bundled stand-ins (local dev)

The repo ships **OFL/Google Font substitutes** at the manifest paths so URLs return 200. Replace with real release fonts when you have them:

| Manifest name | File on disk | Stand-in (not identical to fansub original) |
|---------------|--------------|---------------------------------------------|
| Gandhi Sans | `gandhi-sans/GandhiSans-Bold.woff2` | Hind Bold |
| QType | `qtype/QType.woff2` | Orbitron Bold |
| Marco GRK Sb | `marco-grk/MarcoGRKSb.woff2` | Source Serif 4 Semibold |
| Adobe Caslon Pro Bold | `adobe-caslon-pro/CaslonPro-Bold.woff2` | EB Garamond Bold |
| Marquis De Sade Ornaments | `marquis/MarquisDeSadeOrnaments.woff2` | Noto Sans Symbols |
| Open Sans / Signika / Noto Sans JP / Liberation Serif | respective folders | matching Fontsource files |

Font binaries remain gitignored; copy this tree to production or run the download step on each server.

## Tier A starter (optional)

See `manifest.json` for Open Sans, Signika, Noto Sans JP aliases, and generic Arial/Times substitutes pointing at bundled Liberation or Noto when you add those files.
