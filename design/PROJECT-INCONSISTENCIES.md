# Project vs. Style Guide Inconsistencies

Observations from cross-referencing all five project CSS files against STYLE-GUIDE.md.
These are not acted on — they are candidates for a future alignment pass.

---

## 1. Token Naming: `--color-bg` vs `--color-light-gray`

The style guide defines `--color-bg: #f5f5f5` as the page background token.

**Reality:** Four of five projects use `--color-light-gray` for the same value. One project (`xqt5-ai-platform`) uses `--color-gray-light`. None of the projects use `--color-bg`.

| Project | Token name used |
|---------|----------------|
| view-invoices | `--color-light-gray` |
| stammdatenmanagement | `--color-light-gray` |
| resourcemgmt | `--color-light-gray` |
| xqt5-ai-platform | `--color-gray-light` |
| insAIghts | `--color-light-gray` |

**Action needed:** Either rename `--color-bg` → `--color-light-gray` in the style guide, or update all projects to use `--color-bg`.

---

## 2. xqt5-ai-platform Token Values Are Wrong

The xqt5-ai-platform CSS defines tokens that conflict with the style guide values:

| Token | Style Guide | xqt5-ai-platform |
|-------|-------------|-----------------|
| `--color-primary-dark` | `#d97200` | `#cc6d00` |
| `--color-dark` | `#213452` | `#2d4263` (lighter, incorrect) |
| `--color-black` | not defined | `#213452` (should be `--color-dark`) |
| `--color-gray` | `#e0e0e0` | `#888` (completely different) |

The sidebar uses `var(--color-black)` to get the correct navy (`#213452`), while `--color-dark` resolves to an incorrect lighter value. This is a naming accident from early development.

---

## 3. Login Page Background

The style guide specifies `background: var(--color-bg)` (light gray) for the login page.

**Reality:** Every project uses `background-color: var(--color-dark)` (navy) for the login container. The dark background is the actual established convention.

**Action needed:** Update the style guide login pattern to use `var(--color-dark)`.

---

## 4. `.btn` Base Styles

The style guide defines `.btn` with `display: inline-flex`, `gap: 0.4rem`, and `border: 1px solid transparent`.

**Reality:** No project CSS includes these properties. All use `border: none` and do not set `display` or `gap` on the base `.btn`.

| Property | Style Guide | All Projects |
|----------|-------------|-------------|
| `display` | `inline-flex` | not set |
| `gap` | `0.4rem` | not set |
| `border` | `1px solid transparent` | `none` or not set |

The `border: 1px solid transparent` approach is useful for the outline variant (prevents layout shift), but it's not applied consistently.

---

## 5. `.btn-danger` Hover Color

Style guide: `background: #c82333`
resourcemgmt and stammdatenmanagement: `background-color: #b02a37`
view-invoices: `background-color: #c82333` (matches guide, but for secondary btn hover #d0d0d0 matches)

Two different hardcoded values in use. Neither is a token.

---

## 6. Shadow Tokens Not Used

The style guide defines `--shadow-sm`, `--shadow-md`, `--shadow-lg` and instructs using them via `var()`.

**Reality:** No project uses shadow tokens. All hardcode shadow values directly:
- Cards: `0 2px 4px rgba(0,0,0,0.08)` or `0 2px 4px rgba(0,0,0,0.1)`
- Login boxes: `0 4px 12px rgba(0,0,0,0.2)` or `0 8px 24px rgba(0,0,0,0.3)`

The `0,0,0,0.1` variant (view-invoices, stammdaten) also deviates from the guide's `0.08` value.

---

## 7. `--transition` Token Not Used

The style guide says to use `transition: var(--transition)` on interactive elements.

**Reality:** All projects hardcode `0.2s` or `0.15s` directly. No project uses `var(--transition)`.

---

## 8. Missing Patterns: `--color-primary-dark`, `--color-dark-hover`

Most projects define only the minimal token set from the early style:

| Token | view-invoices | stammdaten | resourcemgmt | xqt5 | insAIghts |
|-------|:---:|:---:|:---:|:---:|:---:|
| `--color-primary-dark` | — | — | — | ✓ (wrong value) | ✓ |
| `--color-dark-hover` | — | — | — | ✓ | — |
| `--color-border` | — | — | — | ✓ | — |
| `--shadow-sm/md/lg` | — | — | — | — | — |
| `--transition` | — | — | — | — | — |
| `--color-warning` | — | ✓ | ✓ | — | — |

---

## 9. Missing Component Patterns in Projects (present in style guide)

These style guide patterns are not defined in some or all projects:

- **`.btn-success`** — defined in resourcemgmt only; missing from all others despite `--color-success` being present
- **`.btn-outline-light`** — defined in resourcemgmt and insAIghts; missing from view-invoices and stammdaten

---

## 10. Missing Patterns in Style Guide (present in projects)

These patterns exist in projects but are not documented in the style guide:

| Pattern | Project | Notes |
|---------|---------|-------|
| `.empty-state` | resourcemgmt | centered placeholder for empty lists |
| `.modal-close` button | resourcemgmt | `×` button in modal header (guide has `justify-content: space-between` implying it) |
| `.toggle-wrap` / checkbox styling | resourcemgmt | `accent-color: var(--color-primary)` |
| `textarea { resize: vertical; min-height: 70px }` | resourcemgmt, stammdaten | guide has no guidance on textarea resize |
| `.form-row` (side-by-side fields) | resourcemgmt | `display: flex; gap: 1rem` with flex `.form-group` children |
| `.stat-card-sub` | resourcemgmt | secondary line below the stat value |
| `line-height: 1.5` on body | all 5 projects | guide's typography section omits `line-height` |
| `font-variant-numeric: tabular-nums` on number cells | resourcemgmt | useful for aligned columns |
| `.form-actions` | resourcemgmt | `display: flex; gap: 0.75rem; margin-top: 1.25rem` |

---

## 11. Table Class Names

The style guide defines `.table` as the canonical class. Projects use their own names:

| Project | Class name |
|---------|-----------|
| view-invoices | `.leistungen-table` |
| stammdatenmanagement | `.records-table`, `.fuzzy-compare-table` |
| resourcemgmt | `.data-table`, `.time-grid table` |
| insAIghts | `.table` ✓ |
| xqt5-ai-platform | `.table` ✓ |

**Note:** table header `letter-spacing` also varies — guide says `0.5px`, resourcemgmt and stammdaten use `0.4px`.

---

## 12. List Item Class Names

The style guide defines `.list-item` / `.list-item-title` / `.list-item-sub`. Projects vary:

| Project | Container | Title | Subtitle |
|---------|-----------|-------|----------|
| view-invoices | `.tree-item` | `.tree-item-nummer` | `.tree-item-datum` |
| stammdatenmanagement | `.tree-item` | `.tree-item-name` | `.tree-item-ort` |
| resourcemgmt | `.list-item` ✓ | `.list-item-title` ✓ | `.list-item-sub` ✓ |
| insAIghts | `.inbox-item` | `.inbox-item-number` | `.inbox-item-date` |

---

## 13. Header Height Pattern

Style guide: `height: 56px; padding: 0 2rem` (fixed height, padding only horizontal)

| Project | Pattern |
|---------|---------|
| view-invoices | `padding: 1rem 2rem` (no fixed height) |
| stammdatenmanagement | `padding: 1rem 2rem` (no fixed height) |
| resourcemgmt | `padding: 0 2rem; min-height: 56px` (closest to guide) |
| xqt5-ai-platform | sidebar layout — no top header bar |
| insAIghts | `padding: 0.9rem 1.2rem; border-radius: 8px` (card-style, not fixed bar) |

---

## 14. Nav Tab Active State

Style guide (§4d): active tab uses background highlight (`background: rgba(255,255,255,0.15)`)

resourcemgmt actual: active tab uses bottom border (`border-bottom: 3px solid var(--color-primary)`)

Both are valid patterns; the guide documents only one.

---

## 15. Toast Slide Direction

Style guide: `toast-in` slides from Y (`translateY(8px)` → `translateY(0)`)
resourcemgmt: `slideIn` slides from X (`translateX(100%)` → `translateX(0)`)

Different animation, different keyframe name.

---

## 16. insAIghts — Most Divergent Project

insAIghts has the most deviations from the style guide:

- **Hardcoded off-palette colors**: `#7b7b7b`, `#cfcfcf`, `#243a5a`, `#2a2a2a`, `#d7d7d7`, `#efefef`, `#676767`, `#4f4f4f` — none of these are style guide tokens
- **Login box `border-radius: 12px`** — guide max is `10px`
- **Login logo `h1` is orange** (`color: var(--color-primary)`) — guide says use navy for headings, orange for accent spans
- **Header is a floating card** (`border-radius: 8px`) rather than the full-width fixed bar defined in §4a; uses `h2` not `h1`
- **No `--color-success`, `--color-warning`, `--color-border`** defined in tokens
- **Has responsive `@media` queries** — the only project with breakpoint behavior

---

## 17. Sidebar Padding Unit (xqt5-ai-platform)

Style guide §4c: `padding: 16px` — already flagged in the guide's own §20 as a mixed-unit violation. Should be `1rem`.

---

## 18. `--color-gray` and `--color-border` are Identical

Both are `#e0e0e0`. Flagged in §20 of the style guide as a known redundancy. No project differentiates them either — most projects only define `--color-gray` and skip `--color-border` entirely.
