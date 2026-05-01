#include "session.h"
#include <cairo/cairo.h>
#include <cairo/cairo-svg.h>
#include <cairo/cairo-pdf.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include <errno.h>

/* ── Export layout constants ─────────────────────────────────────────────── *
 * Quad: ant(EU×EU*2) | post(EU×EU*2) | right-top(EU/2×EU) + right-bot      *
 *       Total: 2.5EU × 2EU = 750×600 px  — tight 1:2 body ratio, no gaps.  *
 * Single: one view at SINGLE_W × SINGLE_H (1:2 tight).                      */
#define EU        300.0
#define EXPORT_W  (EU * 2.5)   /* 750: ant(300) + post(300) + right(150) */
#define EXPORT_H  (EU * 2.0)   /* 600 */
#define SINGLE_W  400.0
#define SINGLE_H  800.0

typedef struct {
    BodyView view;
    double   x, y, w, h;
    int      col_idx;   /* which col_zoom/pan_x/pan_y array index to use */
} ExportSlot;

/* slot 0-3 → BodyView, matching AppState single_zoom/pan arrays */
static const BodyView SINGLE_VIEWS[4] = {
    VIEW_ANTERIOR, VIEW_POSTERIOR, VIEW_LATERAL_L, VIEW_LATERAL_R
};

static void export_dims(AppState *app, double *out_w, double *out_h)
{
    if (app->layout_mode == LAYOUT_QUAD) { *out_w = EXPORT_W; *out_h = EXPORT_H; }
    else                                 { *out_w = SINGLE_W; *out_h = SINGLE_H; }
}

/* ── Path helpers ────────────────────────────────────────────────────────── */
static void ensure_save_dir(char *buf, size_t len)
{
    const char *home = g_get_home_dir();
    snprintf(buf, len, "%s/PhysioChart", home);
    if (mkdir(buf, 0755) != 0 && errno != EEXIST)
        snprintf(buf, len, "%s", home);
}

void session_auto_path(char *buf, size_t len, const char *ext)
{
    char dir[512];
    ensure_save_dir(dir, sizeof(dir));
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    char ts[20];
    strftime(ts, sizeof(ts), "%Y%m%d%H%M", t);
    snprintf(buf, len, "%s/BodyChart%s.%s", dir, ts, ext);
}

/* ── Render current view to any Cairo context, respecting live zoom/pan ──── */
static void render_all_views(AppState *app, cairo_t *cr)
{
    cairo_set_source_rgb(cr, 1.0, 1.0, 1.0);
    cairo_paint(cr);

    if (app->layout_mode == LAYOUT_QUAD) {
        /* Build slots dynamically so right column reflects cycled views */
        ExportSlot slots[4] = {
            { VIEW_ANTERIOR,               0,      0,         EU,    EU*2, 0 },
            { VIEW_POSTERIOR,              EU,     0,         EU,    EU*2, 1 },
            { app->right_slot_views[0],    EU*2,   0,         EU/2,  EU,   2 },
            { app->right_slot_views[1],    EU*2,   EU,        EU/2,  EU,   3 },
        };
        for (int i = 0; i < 4; i++) {
            cairo_save(cr);
            cairo_translate(cr, slots[i].x, slots[i].y);
            cairo_rectangle(cr, 0, 0, slots[i].w, slots[i].h);
            cairo_clip(cr);
            canvas_render_view(app, cr, slots[i].view,
                               slots[i].w, slots[i].h,
                               app->col_zoom[slots[i].col_idx],
                               app->col_pan_x[slots[i].col_idx],
                               app->col_pan_y[slots[i].col_idx]);
            cairo_restore(cr);
        }
        /* No dividers — panels are flush */
    } else {
        int slot = (int)app->layout_mode - 1;  /* LAYOUT_ANTERIOR=1 → slot 0, etc. */
        canvas_render_view(app, cr, SINGLE_VIEWS[slot],
                           SINGLE_W, SINGLE_H,
                           app->single_zoom[slot],
                           app->single_pan_x[slot],
                           app->single_pan_y[slot]);
    }
}

/* ── Public API ──────────────────────────────────────────────────────────── */

gboolean session_save(AppState *app, const char *path)
{
    double w, h;
    export_dims(app, &w, &h);
    cairo_surface_t *surf = cairo_svg_surface_create(path, w, h);
    if (cairo_surface_status(surf) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "session_save: cannot create SVG surface at %s\n", path);
        cairo_surface_destroy(surf);
        return FALSE;
    }
    cairo_t *cr = cairo_create(surf);
    render_all_views(app, cr);
    cairo_destroy(cr);
    cairo_surface_destroy(surf);
    fprintf(stderr, "session_save: %s\n", path);
    return TRUE;
}

gboolean session_load(AppState *app, const char *path)
{
    (void)app; (void)path;
    fprintf(stderr, "session_load: not yet implemented\n");
    return FALSE;
}

gboolean session_export_png(AppState *app, const char *path)
{
    double w, h;
    export_dims(app, &w, &h);
    cairo_surface_t *surf = cairo_image_surface_create(
        CAIRO_FORMAT_RGB24, (int)w, (int)h);
    cairo_t *cr = cairo_create(surf);
    render_all_views(app, cr);
    cairo_destroy(cr);
    cairo_status_t st = cairo_surface_write_to_png(surf, path);
    cairo_surface_destroy(surf);
    if (st != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "session_export_png: write failed: %s\n",
                cairo_status_to_string(st));
        return FALSE;
    }
    fprintf(stderr, "session_export_png: %s\n", path);
    return TRUE;
}

gboolean session_export_pdf(AppState *app, const char *path)
{
    double w, h;
    export_dims(app, &w, &h);
    cairo_surface_t *surf = cairo_pdf_surface_create(path, w, h);
    if (cairo_surface_status(surf) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "session_export_pdf: cannot create PDF surface at %s\n", path);
        cairo_surface_destroy(surf);
        return FALSE;
    }
    cairo_t *cr = cairo_create(surf);
    render_all_views(app, cr);
    cairo_show_page(cr);
    cairo_destroy(cr);
    cairo_surface_destroy(surf);
    fprintf(stderr, "session_export_pdf: %s\n", path);
    return TRUE;
}
