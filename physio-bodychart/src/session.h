#pragma once
#include "canvas.h"

/* ── Path helper ─────────────────────────────────────────────────────────── */

/* Build a file path inside the session folder.
 * suffix example: "subj.png", "report.txt", "session.json"
 * Result: {session_dir}/{session_name}_{suffix} */
void session_build_path(AppState *app, const char *suffix, char *buf, size_t len);

/* Legacy: generate an auto-named path in ~/PhysioChart/ (pre-session system).
 * Still used by keyboard-shortcut exports when no session is active. */
void session_auto_path(char *buf, size_t len, const char *ext);

/* ── Render exports ──────────────────────────────────────────────────────── */

/* Render the subjective chart to a PNG at the session path.
 * Uses a fixed export zoom (0.92) so edge content is never clipped. */
gboolean session_export_subj_png(AppState *app);

/* Render the objective chart to a PNG at the session path. */
gboolean session_export_obj_png(AppState *app);

/* Render both subjective (top) and objective (bottom) in one image with labels. */
gboolean session_export_combined_png(AppState *app);

/* Place the combined PNG onto ~/.local/bin/template.pdf and save as combined.pdf. */
gboolean session_export_combined_pdf(AppState *app);

/* Render to an arbitrary path (for legacy keyboard shortcut exports). */
gboolean session_export_png(AppState *app, const char *path);
gboolean session_export_pdf(AppState *app, const char *path);

/* Legacy SVG export (render-only, not reloadable). */
gboolean session_save(AppState *app, const char *path);

/* Stub — kept for source compatibility; real load is via persistence_load. */
gboolean session_load(AppState *app, const char *path);
