#pragma once
#include <cairo.h>

/* Load overlay SVGs (dermatome + peripheral) from the views directory.
 * Call once at startup, same search path as svg_views_init(). */
void overlay_svg_init(void);

/* Render the dermatome SVG for the given view into the current Cairo context.
 * Caller is responsible for push/pop group and alpha painting.
 * view_index: 0=anterior, 1=posterior. Does nothing for other views. */
void overlay_svg_draw_derm(cairo_t *cr, int view_index);

/* Render the peripheral nerve SVG for the given view.
 * Same calling convention as overlay_svg_draw_derm. */
void overlay_svg_draw_periph(cairo_t *cr, int view_index);
