#pragma once
#include <cairo.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* The 8 body views */
typedef enum {
    VIEW_ANTERIOR = 0,
    VIEW_POSTERIOR,
    VIEW_LATERAL_R,
    VIEW_LATERAL_L,
    VIEW_HAND_PALMAR,
    VIEW_HAND_DORSAL,
    VIEW_FOOT_PLANTAR,
    VIEW_FOOT_DORSAL,
    VIEW_COUNT
} BodyView;

extern const char *VIEW_LABELS[VIEW_COUNT];

/* Draw the outline for a given view into the current Cairo context.
   The outline is normalised to a 200×400 unit coordinate space.
   Caller should scale/translate as needed before calling. */
void body_outline_draw(cairo_t *cr, BodyView view);

/* Natural aspect ratio (w/h) for each view */
float body_outline_aspect(BodyView view);
