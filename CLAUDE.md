# PhysioBodyChart — Claude context

GTK4 + Cairo stylus-based body chart app for physiotherapy documentation.

## Build

```
ninja -C build
```

Reconfigure after adding source files: `cd build && meson setup --reconfigure ..`

## Source layout

| File | Purpose |
|---|---|
| `src/canvas.c` | Drawing areas, gesture input, draw pipeline |
| `src/canvas.h` | AppState struct — all app state |
| `src/obj_chart.c/.h` | Obj mode zone/point types and render |
| `src/window.c` | Sidebar UI, mode switching, dialogs |
| `src/persistence.c` | JSON save/load (json-c) |
| `src/input.c` | Stroke input logic |
| `src/session.c` | PNG/PDF export |
| `meson.build` | Source list — add new .c files here |

## Mode architecture

Three modes in `AppMode`: `APP_MODE_SUBJECTIVE`, `APP_MODE_OBJECTIVE`, `APP_MODE_REPORT`.

- Sx mode: strokes (symptoms), arrows, notes
- Obj mode: freehand zones (Allodynia/Hyperalgesia/Erythema/Temp Cool/Warm) + PPT/TS point markers
- Rpt mode: placeholder

The sidebar switches content via `g_sidebar_content_stack` ("sx" / "obj" / "rpt").

## Current state (2026-05-02)

- Phase 2A committed: session identity, JSON save/load, sidebar mode strip
- Obj mode fully wired (unstaged): draw pipeline, input, sidebar tab, PPT/TS dialog, persistence
- Next: commit obj work, then Report mode / obj PNG export
