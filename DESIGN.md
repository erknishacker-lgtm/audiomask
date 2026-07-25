# GhostWave Design System

## Brand
**GhostWave** — fantasma branco com waveform (logo PNG em fundo preto).

## Mood
Dark monochrome product lab. Off-black surfaces, white accent, high trust for media buyers.

## Color strategy
**Restrained.** White accent ≤12% of surface. No cyan primary (legacy MASK.SOUND retired for brand consistency).

## Palette

| Role | Hex / value | Use |
|------|-------------|-----|
| bg | `#0a0a0b` | App background (never pure black) |
| bg-elev | `#111113` | Nested surfaces |
| surface | `#141416` | Cards / panels |
| surface-2 | `#1c1c1f` | Secondary controls |
| border | `rgba(255,255,255,0.08)` | 1px borders only |
| ink | `#f4f4f5` | Body text |
| muted | `#a1a1aa` | Secondary text |
| faint | `#71717a` | Meta / labels |
| accent | `#fafafa` | Primary CTA fill, focus |
| danger | `#f87171` | Errors |
| ok | `#4ade80` | Success / AI layer cue |
| warn | `#fbbf24` | Admin / warning |

## Critical rules
- **Never** put the logo on white/cream — the character disappears.
- Logo always on off-black `#0a0a0b`–`#141416` or transparent over dark.
- Primary CTA = white fill, text `#0a0a0b`.
- No purple glows, no gradient text, no side-stripe accents.
- Radius: 8 / 12 / 16 max (no 24px+ cards).
- Motion: transform + opacity only; honor `prefers-reduced-motion`.

## Typography
- UI: Instrument Sans (400–700)
- Mono / prices / chips: JetBrains Mono
- Display letter-spacing floor: ≥ -0.03em
- Body max width ~42–65ch

## Spacing & layout
- Shell max-width: 1080px
- Nav sticky height ~64px
- Stats as single strip (not three equal metric cards)
- Pricing: 4-col desktop → 2 → 1

## Assets
- `assets/logo.png` — master logo
- `assets/favicon.png`
- `assets/cta-protect.jpg` — featured protect tile
