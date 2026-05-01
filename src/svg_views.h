#pragma once
#include <cairo.h>
#include <glib.h>
#include "body_outlines.h"

/* Search known directories for SVG body-view files and cache handles.
   Call once at startup before creating the window. */
void     svg_views_init(void);

gboolean svg_view_available(BodyView view);

/* Render SVG for view into the current cairo context.
   Coordinate space: 200×400 units (same as body_outline_draw). */
void     svg_view_draw(cairo_t *cr, BodyView view);
