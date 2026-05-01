#pragma once
#include <cairo.h>
#include <stdint.h>
#include <stddef.h>

typedef enum {
    OVERLAY_NONE = 0,
    OVERLAY_DERMATOME,
    OVERLAY_PERIPHERAL,
    OVERLAY_SOMATIC,
    OVERLAY_CATEGORY_COUNT
} OverlayCategory;

typedef struct {
    const char      *id;
    const char      *label;
    const char      *short_label;   /* for toolbar badge */
    OverlayCategory  category;
    /* SVG path strings per view — NULL if not applicable */
    const char      *path_anterior;
    const char      *path_posterior;
    const char      *path_lateral_r;
    const char      *path_lateral_l;
    const char      *path_hand;
    const char      *path_foot;
    /* RGBA colour for this overlay (semi-transparent filled region) */
    float            r, g, b;
} OverlayDef;

/* Populated by overlay_data/ *.c */
extern const OverlayDef DERMATOME_OVERLAYS[];
extern int               DERMATOME_COUNT;
extern const OverlayDef PERIPHERAL_OVERLAYS[];
extern int               PERIPHERAL_COUNT;
extern const OverlayDef SOMATIC_OVERLAYS[];
extern int               SOMATIC_COUNT;

/* Draw a single overlay onto cr.
   Coordinate space matches body_outline_draw (200×400 units).
   alpha: 0.0 = invisible, 1.0 = fully opaque (use ~0.35–0.65 in practice) */
void overlay_draw(cairo_t *cr, const OverlayDef *ov, int view_index, float alpha);

/* Convenience: get overlay by flat index across all categories */
const OverlayDef *overlay_get(OverlayCategory cat, int index);
int               overlay_count(OverlayCategory cat);
const char       *overlay_category_label(OverlayCategory cat);
