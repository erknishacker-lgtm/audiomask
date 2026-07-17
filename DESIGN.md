# AudioShield Design System

## Mood
Signal lab at night — quiet instruments, indigo tooling on pure near-black.

## Color strategy
**Restrained.** Accent ≤10% of surface. Primary for actions and active layer state only.

## Palette (OKLCH → hex for Streamlit CSS)

| Role | OKLCH | Hex |
|------|-------|-----|
| bg | oklch(0.12 0 0) | `#141414` |
| surface | oklch(0.17 0.008 270) | `#1c1c22` |
| surface-2 | oklch(0.21 0.012 270) | `#252530` |
| border | oklch(0.28 0.015 270) | `#343445` |
| ink | oklch(0.96 0.005 270) | `#f2f2f7` |
| muted | oklch(0.72 0.02 270) | `#a8a8b8` |
| primary | oklch(0.55 0.18 275) | `#6b5cff` |
| primary-hover | oklch(0.62 0.17 275) | `#8478ff` |
| success | oklch(0.72 0.14 155) | `#3dd68c` |
| warning | oklch(0.78 0.14 85) | `#e8b84a` |
| danger | oklch(0.62 0.18 25) | `#e85d4c` |

## Typography
- Family: `IBM Plex Sans` (UI) + `IBM Plex Mono` (métricas/código)
- Scale: 12 / 14 / 16 / 20 / 28 / 36 (rem fixed, product)
- Letter-spacing display: -0.02em max tight

## Layout
- Max content ~1120px
- Sidebar dense controls
- Cards radius 12px, border 1px, **no** wide drop-shadow
- Primary CTA full-width in main flow

## Motion
- 180ms ease-out on hover/focus only
- prefers-reduced-motion: none
