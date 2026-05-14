#include "obj_chart.h"
#include "canvas.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

/* ── Zone appearance table ───────────────────────────────────────────────── */
const ObjZoneDef OBJ_ZONE_DEFS[OBJ_ZONE_COUNT] = {
    { 0.96f, 0.82f, 0.00f, "Allodynia",    "Allodynia"    },
    { 0.94f, 0.47f, 0.13f, "Hyperalgesia", "Hyperalgesia" },
    { 0.91f, 0.38f, 0.48f, "Erythema",     "Erythema"     },
    { 0.25f, 0.63f, 0.88f, "Temp Cool",    "Temp Cool"    },
    { 0.75f, 0.19f, 0.19f, "Temp Warm",    "Temp Warm"    },
    { 0.69f, 0.69f, 0.75f, "Numb",         "Numb"         },
    { 0.60f, 0.31f, 0.75f, "Oedema",       "Oedema"       },
    { 0.70f, 0.44f, 0.19f, "Trophic",      "Trophic"      },
};

/* ── ObjZone lifecycle ───────────────────────────────────────────────────── */

ObjZone *obj_zone_new(ObjZoneType type, int view)
{
    ObjZone *z = g_malloc0(sizeof(ObjZone));
    z->type = type;
    z->view = view;
    z->cap  = 64;
    z->bx   = g_malloc(z->cap * sizeof(float));
    z->by   = g_malloc(z->cap * sizeof(float));
    return z;
}

void obj_zone_add_pt(ObjZone *z, float bx, float by)
{
    if (z->n >= z->cap) {
        z->cap *= 2;
        if (z->cap > MAX_OBJ_ZONE_PTS) z->cap = MAX_OBJ_ZONE_PTS;
        z->bx = g_realloc(z->bx, z->cap * sizeof(float));
        z->by = g_realloc(z->by, z->cap * sizeof(float));
    }
    if (z->n < MAX_OBJ_ZONE_PTS) {
        z->bx[z->n] = bx;
        z->by[z->n] = by;
        z->n++;
    }
}

void obj_zone_free(ObjZone *z)
{
    if (!z) return;
    g_free(z->bx);
    g_free(z->by);
    g_free(z);
}

/* ── Zone path drawing helper ────────────────────────────────────────────── */

static void draw_zone_body(cairo_t *cr, const ObjZone *z,
                            float r, float g, float b)
{
    if (z->n < 2) return;

    cairo_save(cr);
    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
    cairo_set_line_join(cr, CAIRO_LINE_JOIN_ROUND);

    cairo_move_to(cr, z->bx[0], z->by[0]);
    for (int i = 1; i < z->n; i++)
        cairo_line_to(cr, z->bx[i], z->by[i]);

    if (z->n >= 3) {
        cairo_close_path(cr);
        cairo_set_source_rgba(cr, r, g, b, 0.35);
        cairo_fill_preserve(cr);
    }
    cairo_set_source_rgba(cr, r, g, b, 0.80);
    cairo_set_line_width(cr, 1.2);
    cairo_stroke(cr);

    cairo_restore(cr);
}

/* ── Rendering — body space (after apply_col_transform) ─────────────────── */

void obj_chart_render_body(AppState *app, cairo_t *cr, int view)
{
    for (int i = 0; i < app->obj_zone_count; i++) {
        const ObjZone *z = app->obj_zones[i];
        if (!z || z->view != view) continue;
        const ObjZoneDef *d = &OBJ_ZONE_DEFS[z->type];
        draw_zone_body(cr, z, d->r, d->g, d->b);
    }
}

void obj_chart_render_active_body(AppState *app, cairo_t *cr, int view)
{
    ObjZone *z = app->obj_active_zone;
    if (!z || z->view != view || z->n < 1) return;

    const ObjZoneDef *d = &OBJ_ZONE_DEFS[z->type];
    cairo_save(cr);
    cairo_set_line_cap(cr, CAIRO_LINE_CAP_ROUND);
    cairo_set_line_join(cr, CAIRO_LINE_JOIN_ROUND);
    cairo_move_to(cr, z->bx[0], z->by[0]);
    for (int i = 1; i < z->n; i++)
        cairo_line_to(cr, z->bx[i], z->by[i]);
    cairo_set_source_rgba(cr, d->r, d->g, d->b, 0.70);
    cairo_set_line_width(cr, 1.5);
    cairo_stroke(cr);
    cairo_restore(cr);
}

/* ── Rendering — screen space ────────────────────────────────────────────── */

void obj_chart_render_screen(AppState *app, cairo_t *cr, int view,
                               double s, double cx, double cy)
{
    for (int i = 0; i < app->obj_point_count; i++) {
        const ObjPoint *p = &app->obj_points[i];
        if (p->view != view) continue;

        double sx = (p->bx - 100.0) * s + cx;
        double sy = (p->by - 200.0) * s + cy;

        /* Dot */
        cairo_save(cr);
        if (p->type == OBJ_POINT_PPT)
            cairo_set_source_rgba(cr, 0.15, 0.40, 0.80, 0.90);   /* blue */
        else if (p->type == OBJ_POINT_MONOFILAMENT)
            cairo_set_source_rgba(cr, 0.20, 0.65, 0.45, 0.90);   /* teal */
        else
            cairo_set_source_rgba(cr, 0.55, 0.15, 0.65, 0.90);   /* purple (TS) */
        cairo_arc(cr, sx, sy, 5.0, 0, 2 * G_PI);
        cairo_fill(cr);

        /* Label */
        cairo_set_source_rgba(cr, 1.0, 1.0, 1.0, 1.0);
        cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL,
                               CAIRO_FONT_WEIGHT_BOLD);
        cairo_set_font_size(cr, 13.5);   /* 50% larger than original 9.0 */

        const char *unit = (p->type == OBJ_POINT_PPT)          ? " kg/cm²" :
                           (p->type == OBJ_POINT_MONOFILAMENT)  ? " g"      : "";
        char buf[32];
        snprintf(buf, sizeof(buf), "%s%s", p->label, unit);

        /* Background box */
        cairo_text_extents_t ext;
        cairo_text_extents(cr, buf, &ext);
        double tx = sx + 7.0;
        double ty = sy - 4.0;
        cairo_set_source_rgba(cr, 0.0, 0.0, 0.0, 0.55);
        cairo_rectangle(cr, tx - 1, ty + ext.y_bearing - 1,
                        ext.width + 4, ext.height + 2);
        cairo_fill(cr);

        cairo_set_source_rgba(cr, 0.95, 0.95, 0.95, 1.0);
        cairo_move_to(cr, tx, ty);
        cairo_show_text(cr, buf);
        cairo_restore(cr);
    }
}
