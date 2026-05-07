#pragma once
#include <gtk/gtk.h>
#include "canvas.h"

/* Show the launch dialog (patient ID + recent sessions).
 * Calls window_create internally when the user commits a session. */
void window_show_launch(AppState *app, GtkApplication *gtk_app);

void window_create(AppState *app, GtkApplication *gtk_app);

/* Trigger an auto-named export. ext = "svg" | "png" | "pdf".
 * Updates the File tab status label. Safe to call from keyboard shortcuts. */
void window_do_export(const char *ext);

/* Auto-save JSON + subjective PNG for the current session.
 * No-op if no session has been started (session_file is empty). */
void window_autosave(AppState *app);
