# Style Guide

Visual language blending [MakerWorld](https://makerworld.com/en) (modern maker platform) with [McMaster-Carr](https://www.mcmaster.com/) (industrial parts catalog). The layout stays simple; expression lives in **CSS tokens**, typography, and surface treatment.

## Design intent

| Source | What we borrow |
|--------|----------------|
| **MakerWorld** | Soft cards, generous radius, maker green for actions, friendly spacing, dark-mode readiness |
| **McMaster-Carr** | Catalog yellow header, high-contrast body text, blue links, tight borders, utilitarian tables |

The app bridges both worlds: **import from MakerWorld → source parts like McMaster**.

---

## Color palette

### Light mode

| Token | Hex | Role |
|-------|-----|------|
| `--accent` | `#FFCC00` | McMaster-style header / catalog chrome |
| `--accent-foreground` | `#1A1A1A` | Text on yellow surfaces |
| `--primary` | `#12B76A` | MakerWorld-style primary actions (Import, Save) |
| `--primary-foreground` | `#FFFFFF` | Text on green buttons |
| `--link` | `#0B57D0` | McMaster-style hyperlinks |
| `--background` | `#F5F5F3` | Warm catalog page background |
| `--card` | `#FFFFFF` | Card / input surfaces |
| `--foreground` | `#1A1A1A` | Body text |
| `--muted` | `#EEEEE9` | Hover rows, secondary panels |
| `--muted-foreground` | `#5C5C5C` | Descriptions, labels |
| `--border` | `#D4D4CF` | Dividers, input borders |

### Dark mode

| Token | Role |
|-------|------|
| `--accent` | Muted gold `#C9A000` — header remains “catalog” without glare |
| `--primary` | Brighter green `#34D399` for contrast on dark |
| `--background` | `#141414` near-black catalog backdrop |
| `--card` | `#1E1E1E` elevated panels |

### Semantic colors (both modes)

| Token | Use |
|-------|-----|
| `--success` | High-confidence McMaster match |
| `--warning` | Verify / unlikely match |
| `--danger` | Errors, low confidence |
| `--destructive` | Destructive actions |

---

## Typography

```css
--font-sans: "DM Sans", "Helvetica Neue", Arial, sans-serif;
```

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Page title (`CardTitle`) | `1.125rem` | 600 | Slightly compact — catalog clarity |
| Body | `0.875rem` | 400 | McMaster-dense default |
| Labels / nav | `0.875rem` | 500 | |
| Captions | `0.75rem` | 400 | `text-muted-foreground` |
| Table data | `0.875rem` | 400 | Monospace only for numeric confidence |

**Letter-spacing:** Headings ` -0.01em` for a crisp industrial feel.

---

## Spacing & radius

| Token | Value | MakerWorld / McMaster |
|-------|-------|------------------------|
| `--radius-sm` | `6px` | Inputs, badges |
| `--radius-md` | `10px` | Buttons (MakerWorld soft) |
| `--radius-lg` | `12px` | Cards |
| Page padding | `1rem` → `2rem` at `max-w-7xl` | |
| Card padding | `1.5rem` | |

---

## Surfaces

### Header (McMaster chrome)

- Background: `var(--accent)` (yellow)
- Bottom border: `1px solid` darkened accent
- Logo + title: dark text on yellow
- Active nav: green bottom border (`--primary`), not filled pill

### Cards (MakerWorld)

```css
background: var(--card);
border: 1px solid var(--border);
border-radius: var(--radius-lg);
box-shadow: var(--shadow-card); /* 0 1px 3px rgba(0,0,0,.06) */
```

### Tables (McMaster catalog)

- Full width, `border-collapse` feel via row borders
- Header row: `bg-muted`, uppercase optional at `text-xs`
- Row hover: `bg-muted/60`

### Inputs

- White/`card` fill, `1px` border
- Focus ring: `2px` green (`--primary`) at 40% opacity
- Placeholder: `--muted-foreground`

---

## Components

### Buttons

| Variant | Style |
|---------|-------|
| **default** | Green fill (`--primary`) — main actions |
| **outline** | White card + border — secondary (Export) |
| **ghost** | Transparent — nav utilities, theme toggle |
| **destructive** | Red — delete row |

Height: `40px` default, `32px` sm. Radius: `--radius-md`.

### Links

Always `color: var(--link)` with underline on hover. External McMaster links open in new tab.

### Badges (McMaster status)

| Status | Background | Text |
|--------|------------|------|
| Likely | `--success-muted` | `--success` |
| Verify / Unlikely | `--muted` | `--warning` |
| N/A | `--muted` | `--muted-foreground` |

---

## Motion

Keep minimal — catalog tools should feel instant.

| Property | Duration |
|----------|----------|
| `background-color`, `border-color` | `150ms ease` |
| Focus rings | instant |

No bounce, parallax, or heavy animation.

---

## Dark mode

- Yellow header uses `--accent` dark variant (darker gold)
- Cards lift via border contrast, not heavy shadows
- Green primary brightened for WCAG contrast on `#1E1E1E`

Toggle: header ghost button cycles light / dark / system.

---

## CSS file map

| File | Responsibility |
|------|----------------|
| `frontend/src/index.css` | All design tokens (`:root`, `.dark`), `@theme` bridge, base `body` |
| `frontend/src/components/ui/*` | Component classes referencing tokens |
| `frontend/src/components/Layout.tsx` | McMaster yellow header |

### Adding a new token

1. Define on `:root` and `.dark` in `index.css`
2. Expose via `@theme { --color-your-token: var(--your-token); }`
3. Use in Tailwind as `bg-your-token`, `text-your-token`, etc.

---

## Do / Don't

**Do**

- Use green for forward progress (import, save, success)
- Use yellow only for top chrome / catalog identity
- Use blue for outbound McMaster links
- Keep tables readable at a glance

**Don't**

- Put yellow behind long body text (contrast)
- Use green for the header (conflicts with MakerWorld button language)
- Mix more than one accent on the same control
- Add decorative gradients — both reference sites are flat

---

## Reference links

- [MakerWorld](https://makerworld.com/en) — cards, green CTAs, maker-friendly spacing
- [McMaster-Carr](https://www.mcmaster.com/) — yellow catalog bar, blue links, dense SKU tables
