# PhysioBodyChart Settings

Config file: `~/.config/physio-bodychart/settings.conf`  
All settings are optional. Remove a line to use the built-in default.  
Changes take effect on next launch.

---

## Pen / stylus

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pen_gamma` | float 0.1–2.0 | `0.3` | Pressure curve exponent. Lower = more sensitive. 0.3 = max sensitivity for Lenovo pen. |
| `pen_wide_mode` | 0 or 1 | `0` | Start in wide-line mode (1) or fine-line mode (0). |
| `palm_reject` | 0 or 1 | `1` | Suppress touch events within 500 ms of stylus contact. |

### Pen gamma guide

| Value | Feel |
|-------|------|
| 0.1–0.3 | Maximum sensitivity — light touch gives full width |
| 0.5–0.7 | Moderate — good for varied pressure styles |
| 1.0 | Linear — pressure maps directly to width |
| 1.5–2.0 | Firm — needs heavy pressure for wide lines |

### Pressure response

All pens respond to stylus pressure. `pen_gamma` shapes the curve for all pens simultaneously.

**Solid/dashed pens** (constant + intermittent pain) vary stroke *width* continuously with pressure.

**Pattern pens** (P&N, anaesthesia, deep ache) vary *count* of marks placed side-by-side perpendicular to the stroke:

| Effective pressure (post-gamma) | Dots / Xs | Dashes |
|---------------------------------|-----------|--------|
| < 0.40 | 1 mark | 1 short dash |
| 0.40 – 0.65 | 2 marks | 1 long dash |
| 0.65 – 0.82 | 3 marks | 2 short dashes |
| ≥ 0.82 | 4 marks | 2 long dashes |

To make count transitions happen at **lighter** touches: lower `pen_gamma` (e.g. 0.2).  
To require **firmer** pressure for 3–4 marks: raise `pen_gamma` toward 1.0.

### Tilt sensitivity

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pen_tilt_weight` | float 0.0–1.0 | `0.0` | How much pen tilt adds to effective pressure. 0 = ignored. 0.3 = 45° tilt adds ~0.21 to pressure reading. |

---

## Pattern pen sizes

All sizes are in body units (200 × 400 bu total). At default zoom on a ~900 px canvas, 1 bu ≈ 4–5 px. Changes take effect on next launch.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `pen_dot_radius` | float 0.2–10.0 | `1.0` | P&N dot radius. Fixed — pressure changes count, not size. |
| `pen_dot_spacing` | float 1.0–30.0 | `4.5` | Along-path spacing between dot stamp positions. |
| `pen_dash_len` | float 0.5–15.0 | `2.0` | Short-dash half-width. Long dash = 1.4×, short = 0.7×. |
| `pen_dash_spacing` | float 1.0–30.0 | `5.0` | Along-path spacing between dash stamp positions. |
| `pen_dash_width` | float 0.1–5.0 | `0.5` | Stroke thickness of each dash line. |
| `pen_x_arm` | float 0.5–12.0 | `2.0` | X arm length (half-diagonal of each X). |
| `pen_x_spacing` | float 1.0–30.0 | `6.0` | Along-path spacing between X stamp positions. |
| `pen_x_width` | float 0.1–5.0 | `0.5` | Stroke thickness of each X line. |

---

## Overlay

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `overlay_opacity` | float 0.0–1.0 | `0.5` | Default opacity for dermatome/peripheral overlay. |

---

## Mouse

| Action | How |
|--------|-----|
| Zoom | Scroll wheel (zooms around cursor) |
| Pan | Middle-button click + drag |
| Draw | Left-button drag |

---

## Hotkeys

All hotkeys are rebindable. Format: `hotkey_<action>=<key>`

Modifiers: `ctrl+`, `shift+`, `alt+` — combine freely, e.g. `ctrl+shift+s`

Key names: single characters (`d`, `1`), function keys (`F1`–`F12`), and named keys:
`Home`, `End`, `Delete`, `BackSpace`, `Tab`, `Page_Up`, `Page_Down`,
`[` or `bracketleft`, `]` or `bracketright`, `minus`, `equal`, `slash`

Set to `none` to disable a hotkey.

### Symptom selection (also activates Draw tool)

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_symptom_constant` | `1` | Constant pain — red solid line |
| `hotkey_symptom_intermittent` | `2` | Intermittent pain — red dashed |
| `hotkey_symptom_paraesthesia` | `3` | Paraesthesia (pins & needles) — blue dots |
| `hotkey_symptom_anaesthesia` | `4` | Anaesthesia (numbness) — blue dashes |
| `hotkey_symptom_para` | `5` | Deep ache — amber X marks |
| `hotkey_symptom_tick` | `6` | Symptom-free / clear — green tick (single stamp per tap) |

### Tools

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_tool_draw` | `d` | Switch to Draw mode |
| `hotkey_tool_erase` | `e` | Switch to Erase mode |
| `hotkey_tool_note` | `n` | Switch to Note annotation mode |
| `hotkey_tool_link` | `l` | Switch to Link tool |
| `hotkey_wide_mode` | `b` | Toggle Bold / Fine line width |

> **Arrow tool** has no default hotkey — use the toolbar button. Draws a thin black arrow (curved if drawn curvy). Tap the arrowhead to delete.

### History

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_undo` | `ctrl+z` | Undo last stroke |
| `hotkey_clear` | `ctrl+Delete` | Clear all strokes |

### Overlay

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_overlay_derm` | `F5` | Toggle dermatome overlay |
| `hotkey_overlay_periph` | `F6` | Toggle peripheral nerve overlay |
| `hotkey_overlay_somatic` | `F7` | Toggle somatic referral overlay (hotkey only — button removed from toolbar) |
| `hotkey_overlay_toggle` | `o` | Show/hide current overlay |
| `hotkey_overlay_prev` | `[` | Previous overlay pattern |
| `hotkey_overlay_next` | `]` | Next overlay pattern |

**Dermatome and peripheral nerve overlays** load SVG files from a `views/` directory alongside the body background SVGs (`anterior peripheral n.svg`, `posterior peripheral n.svg`, etc.). If the SVG files are not found the overlay silently shows nothing.

**Note:** The somatic referral overlay button was removed from the sidebar; use `F7` or rebind `hotkey_overlay_somatic` if you need it.

### Views

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_view_quad` | `F9` | Quad view (all four panels) |
| `hotkey_view_anterior` | `F1` | Anterior full-screen |
| `hotkey_view_posterior` | `F2` | Posterior full-screen |
| `hotkey_view_lateral_l` | `F3` | Left lateral full-screen |
| `hotkey_view_lateral_r` | `F4` | Right lateral full-screen |

### Navigation

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_zoom_reset` | `Home` | Reset zoom and pan on all panels |

### Save / export

| Action | Default | Description |
|--------|---------|-------------|
| `hotkey_save_svg` | `ctrl+s` | Save as SVG to ~/Physio-Bodychart/ |
| `hotkey_save_png` | `ctrl+shift+s` | Export PNG to ~/Physio-Bodychart/ |
| `hotkey_save_pdf` | `ctrl+p` | Export PDF to ~/Physio-Bodychart/ |

---

## Command-line arguments

Arguments are parsed before GTK sees them.

| Argument | Description |
|----------|-------------|
| `--pen-gamma=N` | Override pen_gamma (float 0.1–2.0) |
| `--wide` | Start in wide-line mode |
| `--no-palm-reject` | Disable palm rejection |
| `--overlay-opacity=N` | Override overlay opacity (float 0.0–1.0) |

---

## Precedence

Settings apply in this order (later wins):

1. Built-in defaults
2. Config file (`~/.config/physio-bodychart/settings.conf`)
3. Command-line arguments

---

## Subjective interview template

File: `~/.config/physio-bodychart/subjective_prompts.md`

Written automatically on first launch. Edit it in Obsidian or any text editor; changes take effect on next launch. The file uses plain Markdown so it is Obsidian-compatible.

### Format

```markdown
## Field name
> One-line hint shown at the top of the popup.
- Top-level option
  - Sub-option (2-space indent)
- Another option
  - Sub-option A
  - Sub-option B
```

**Rules:**

| Syntax | Meaning |
|--------|---------|
| `## History` | Declares the History field. Must match one of the four field names exactly (case-insensitive): `History`, `Aggs`, `Ease`, `24hr Pattern`. |
| `> hint text` | Sets the grey italic hint line shown at the top of the popup for that field. |
| `- option` | Top-level quick-fill button (brighter, larger). Tapping it appends the option text to the entry on a new line. |
| `  - sub-option` | Sub-option button (slightly dimmer). Two-space indent required. Behaves the same as a top-level option. |
| `<!-- comment -->` | Ignored. Use for notes to yourself. |

### How the popup works

1. Tap **History**, **Aggs**, **Ease**, or **24hr Pattern** below any note in the Report view.
2. The popup appears on the right side of the screen with the hint at the top, quick-fill buttons below, and a text entry box at the bottom.
3. Tap any quick-fill button to append that text on a new line in the entry box.
4. Type freely in the entry box at any time.
5. Press **Shift+Enter** to save the entry and close the popup. The text appears in the report under that note.
6. Tap the same button again to re-open and edit the entry.

### Adding new fields or sub-menus

Add options under any field heading. Sub-options are shown with slightly different styling but otherwise behave identically to top-level options. Future versions will support nested sub-menus.

Example — extending History with more onset options:

```markdown
## History
> Onset, mechanism, duration, previous episodes, relevant medical history.
- Onset
  - Gradual — weeks to months
  - Sudden — seconds to days
  - Insidious — no clear start
  - Post-surgical
- Duration
  - Acute — < 6 weeks
  - Sub-acute — 6 weeks – 3 months
  - Chronic — > 3 months
```
