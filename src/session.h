#pragma once
#include "canvas.h"

/* Generate an auto-named export path in ~/PhysioChart/.
 * ext should be "svg", "png", or "pdf". */
void     session_auto_path(char *buf, size_t len, const char *ext);

gboolean session_save(AppState *app, const char *path);        /* SVG */
gboolean session_load(AppState *app, const char *path);        /* stub */
gboolean session_export_png(AppState *app, const char *path);
gboolean session_export_pdf(AppState *app, const char *path);
