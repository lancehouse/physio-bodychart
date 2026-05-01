#pragma once
#include <gtk/gtk.h>
#include "canvas.h"

void window_create(AppState *app, GtkApplication *gtk_app);

/* Trigger an auto-named export. ext = "svg" | "png" | "pdf".
 * Updates the File tab status label. Safe to call from keyboard shortcuts. */
void window_do_export(const char *ext);
